import time
import uuid
import json
import configparser

import requests

from hupijiao_v3_python import Hupi
from flask import Flask, request, redirect
from flask_sqlalchemy import SQLAlchemy


pay_conf = configparser.ConfigParser()
pay_conf.read("./only_pay_python.ini")
pay = pay_conf.items("pay")

mysql_db = pay_conf.items("db")
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://{}:{}@{}:{}/{}".format(mysql_db[0][1],
                                                                                mysql_db[1][1],
                                                                                mysql_db[2][1],
                                                                                mysql_db[3][1],
                                                                                mysql_db[4][1])
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
print(app.config["SQLALCHEMY_DATABASE_URI"])
db = SQLAlchemy(app)


class OrderList(db.Model):
    """
    订单表
    """
    id = db.Column(db.Integer, primary_key=True)
    orderId = db.Column(db.String(52), nullable=False, unique=True)
    orderTime = db.Column(db.Integer(), nullable=False)
    orderPayment = db.Column(db.Enum('wechat', 'paypal'), nullable=False)
    orderTotalFee = db.Column(db.BigInteger(), nullable=False)
    orderTitle = db.Column(db.String(255), nullable=False)
    wapName = db.Column(db.String(52), nullable=False)
    orderStatus = db.Column(db.Enum('TBC', 'FAIL', 'SUCCEED'), nullable=False)
    payUser = db.Column(db.String(52))


@app.route('/api/create_order/', methods=["GET"])
def create_order():  # put application's code here
    money = ''
    mode_of_payment = ''
    try:
        # 接收传参
        money = request.args.get("money")
        mode_of_payment = request.args.get("mode_of_payment")
        # 参数校验
        if float(money) < 0.01:
            return "参数错误"
        if mode_of_payment not in ["wechat", "paypal"]:
            return "参数错误"
    except Exception as err:
        print(err)
        print("参数错误", money, mode_of_payment)
        return "参数错误"

    if mode_of_payment == "wechat":

        simple = str(int(time.time()))
        trade_order_id = str(uuid.uuid4())[:32]
        hu_pi = Hupi(pay[0][1], pay[1][1], pay[2][1], pay[3][1], pay[4][1])
        # 店铺名称
        wap_name = "xxxx店铺"
        # 增加订单列表
        order_list = OrderList(orderId=trade_order_id, orderTime=simple, orderPayment=mode_of_payment,
                               orderTotalFee=int(float(money) * 1000), orderTitle="交易", wapName=wap_name,
                               orderStatus="TBC")
        db.session.add(order_list)
        db.session.commit()
        res = hu_pi.Pay(trade_order_id, mode_of_payment, money, "交易", simple, wap_name)
        return redirect(json.loads(res.text).get("url"))
    elif mode_of_payment == "paypal":
        pass
    else:
        return "未知错误"


@app.route('/api/edit_order/', methods=["GET"])
def edit_order():  # put application's code here
    trade_order_id = ''
    try:
        # 接收传参
        trade_order_id = request.args.get("trade_order_id")
        # 校验参数
        if len(trade_order_id) != 32:
            return "参数错误"

    except Exception as err:
        print(err)
        print("参数错误", trade_order_id)
        return "参数错误"
    # 校验接口
    simple = str(int(time.time()))
    hu_pi = Hupi(pay[0][1], pay[1][1], pay[2][1], pay[3][1], pay[4][1])
    data = {
        "appid": pay[0][1],
        "out_trade_order": trade_order_id,
        "time": simple,
        "nonce_str": simple,
    }
    hash = hu_pi.sign(data)
    data["hash"] = hash
    verify_url = "https://api.xunhupay.com/payment/query.html"
    res = requests.request("POST", verify_url, params=data, timeout=20)
    res_dict = json.loads(res.text)

    if res_dict.get("errcode") == 0:
        order_list = OrderList.query.filter_by(orderId=trade_order_id).first()
        if res_dict.get("data").get("out_trade_order") == trade_order_id:
            if res_dict.get("data").get("status") == "OD":
                order_list.update({"orderId": "SUCCEED"})
                db.session.commit()
                return "修改成功，交易状态置为成功。"
            elif res_dict.get("data").get("status") == "CD":
                order_list.update({"orderId": "FAIL"})
                db.session.commit()
                return "修改成功，交易状态置为失败。"
    else:
        return "修改失败，{}".format(res_dict)


if __name__ == '__main__':
    db.create_all()
    app.run(host="0.0.0.0", port=5000)
