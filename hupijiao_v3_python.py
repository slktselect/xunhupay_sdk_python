# *-* coding: UTF-8 *-*

import hashlib
from urllib.parse import urlencode, unquote_plus

import requests


def ksort(d):
    return [(k, d[k]) for k in sorted(d.keys())]


class Hupi(object):
    def __init__(self, appid, AppSecret, notify_url, return_url, callback_url):
        self.appid = appid  # 在虎皮椒V3申请的appid
        self.AppSecret = AppSecret  # 在虎皮椒V3申请的AppSecret
        self.notify_url = notify_url
        self.return_url = return_url
        self.callback_url = callback_url

    def curl(self, data, url):
        data['hash'] = self.sign(data)
        headers = {"Referer": "https://www.focusinfluencer.com/"}  # 自己的网站地址
        r = requests.post(url, data=data, headers=headers)
        return r

    def sign(self, attributes):
        attributes = ksort(attributes)
        m = hashlib.md5()
        m.update((unquote_plus(urlencode(attributes)) + self.AppSecret).encode(encoding='utf-8'))
        sign = m.hexdigest()
        # sign = sign.upper()
        return sign

    def Pay(self, trade_order_id, payment, total_fee, title, simple, wap_name):
        url = "https://api.xunhupay.com/payment/do.html"
        data = {
            "version": "1.1",
            "lang": "zh-cn",
            "plugins": "flask",
            "appid": self.appid,
            "trade_order_id": trade_order_id,
            "payment": payment,
            "is_app": "Y",
            "total_fee": total_fee,
            "title": title,
            "description": "",
            "time": simple,
            "wap_name": wap_name,
            "notify_url": "{}?trade_order_id={}".format(self.notify_url, trade_order_id),  # 回调URL（订单支付成功后，WP开放平台会把支付成功消息异步回调到这个地址上）
            "return_url": self.return_url,  # 支付成功url(订单支付成功后，浏览器会跳转到这个地址上)
            "callback_url": self.callback_url,  # 商品详情URL或支付页面的URL（移动端，商品支付失败时，会跳转到这个地址上）
            "nonce_str": "nonce_str" + trade_order_id + simple,  # 随机字符串(一定要每次都不一样，保证请求安全)
        }
        return self.curl(data, url)
