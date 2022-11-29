import time
from json import loads as json_loads
from os import path as os_path
from sys import exit as sys_exit
from sys import argv as sys_argv

from lxml import etree
import requests
from requests import session
import logging
from geo_disturbance import geoDisturbance

logging.basicConfig(
    level=logging.INFO,
    format=
    '%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')
from api import GET_CAPTCHA

import requests
import urllib3
import ssl


class CustomHttpAdapter (requests.adapters.HTTPAdapter):
    # "Transport adapter" that allows us to use custom ssl_context.

    def __init__(self, ssl_context=None, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = urllib3.poolmanager.PoolManager(
            num_pools=connections, maxsize=maxsize,
            block=block, ssl_context=self.ssl_context)


def get_legacy_session():
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
    session = requests.session()
    session.mount('https://', CustomHttpAdapter(ctx))
    return session

class Fudan:
    """
    建立与复旦服务器的会话，执行登录/登出操作
    """
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:76.0) Gecko/20100101 Firefox/76.0"

    # 初始化会话
    def __init__(self,
                 uid,
                 psw,
                 api_usr,
                 api_pwd,
                 url_login='https://uis.fudan.edu.cn/authserver/login'):
        """
        初始化一个session，及登录信息
        :param uid: 学号
        :param psw: 密码
        :param url_login: 登录页，默认服务为空
        """
        self.session = get_legacy_session()
        self.session.headers['User-Agent'] = self.UA
        self.url_login = url_login
        self.api_usr, self.api_pwd = api_usr, api_pwd
        self.uid = uid
        self.psw = psw

    def _page_init(self):
        """
        检查是否能打开登录页面
        :return: 登录页page source
        """
        logging.debug("Initiating——")
        page_login = self.session.get(self.url_login)

        logging.debug("return status code " + str(page_login.status_code))

        if page_login.status_code == 200:
            logging.debug("Initiated——")
            return page_login.text
        else:
            logging.debug(
                "Fail to open Login Page, Check your Internet connection\n")
            self.close()

    def login(self):
        """
        执行登录
        """
        page_login = self._page_init()

        logging.debug("parsing Login page——")
        html = etree.HTML(page_login, etree.HTMLParser())

        logging.debug("getting tokens")
        data = {
            "username": self.uid,
            "password": self.psw,
            "service": "https://zlapp.fudan.edu.cn/site/ncov/fudanDaily"
        }

        # 获取登录页上的令牌
        data.update(
            zip(html.xpath("/html/body/form/input/@name"),
                html.xpath("/html/body/form/input/@value")))

        headers = {
            "Host": "uis.fudan.edu.cn",
            "Origin": "https://uis.fudan.edu.cn",
            "Referer": self.url_login,
            "User-Agent": self.UA
        }

        logging.debug("Login ing——")
        post = self.session.post(self.url_login,
                                 data=data,
                                 headers=headers,
                                 allow_redirects=False)

        logging.debug("return status code %d" % post.status_code)

        if post.status_code == 302:
            logging.debug("登录成功")
        else:
            logging.debug("登录失败，请检查账号信息")
            self.close()

    def logout(self):
        """
        执行登出
        """
        exit_url = 'https://uis.fudan.edu.cn/authserver/logout?service=/authserver/login'
        expire = self.session.get(exit_url).headers.get('Set-Cookie')

        if '01-Jan-1970' in expire:
            logging.debug("登出完毕")
        else:
            logging.debug("登出异常")

    def close(self):
        """
        执行登出并关闭会话
        """
        self.logout()
        self.session.close()
        logging.debug("关闭会话")
        sys_exit()


class Zlapp(Fudan):
    last_info = ''

    def check(self):
        """
        检查
        """
        logging.debug("检测是否已提交")
        get_info = self.session.get(
            'https://zlapp.fudan.edu.cn/ncov/wap/fudan/get-info')
        last_info = get_info.json()

        logging.info("上一次提交日期为: %s " % last_info["d"]["info"]["date"])

        position = last_info["d"]["info"]['geo_api_info']
        position = json_loads(position)

        logging.info("上一次提交地址为: %s" % position['formattedAddress'])
        # logging.debug("上一次提交GPS为", position["position"])

        today = time.strftime("%Y%m%d", time.localtime())

        if last_info["d"]["info"]["date"] == today:
            logging.info("今日已提交")
            self.close()
        else:
            logging.info("未提交")
            self.last_info = last_info["d"]["info"]

    def get_captcha_code(self):
        logging.debug("获取验证码")
        captcha_url = "https://zlapp.fudan.edu.cn/backend/default/code"
        r = self.session.get(captcha_url)
        logging.info(f"获取验证码成功")
        return r.content

    def checkin(self):
        """
        提交
        """
        headers = {
            "Host": "zlapp.fudan.edu.cn",
            "Referer":
            "https://zlapp.fudan.edu.cn/site/ncov/fudanDaily?from=history",
            "DNT": "1",
            "TE": "Trailers",
            "User-Agent": self.UA
        }

        logging.debug("提交中")
        captcha_code = GET_CAPTCHA(self.api_usr,
                                   self.api_pwd).get_captcha_from_api(
                                       self.get_captcha_code())
        logging.info(f"验证码为{captcha_code}")
        geo_api_info = json_loads(self.last_info["geo_api_info"])
        province = geo_api_info["addressComponent"].get("province", "")
        city = geo_api_info["addressComponent"].get("city", "") or province
        district = geo_api_info["addressComponent"].get("district", "")
        self.last_info.update({
            "tw": "13",
            "province": province,
            "city": city,
            "area": " ".join(set((province, city, district))),
            "ismoved": 0,
            'sfzx': 1,
            "sfzgn": 1,
            "xs_sfdyz": 1,
            "xs_dyzdd": 1,
            "xs_sfdez": 1,
            "xs_dezdd": 1,
            "xs_ymtype": 1,
            "xs_sfwcjqz": 1,
            "code": captcha_code,
            "geo_api_info": geoDisturbance(self.last_info["geo_api_info"]),
        })
        # logging.debug(self.last_info)

        save = self.session.post(
            'https://zlapp.fudan.edu.cn/ncov/wap/fudan/save',
            data=self.last_info,
            headers=headers,
            allow_redirects=False)

        save_msg = json_loads(save.text)["m"]
        logging.info(save_msg)


def get_account():
    """
    获取账号信息
    """
    uid, psw, api_usr, api_pwd = sys_argv[1].strip().split(' ')
    return uid, psw, api_usr, api_pwd


if __name__ == '__main__':
    uid, psw,api_usr, api_pwd = get_account()
    # logging.debug("ACCOUNT：" + uid + psw)
    zlapp_login = 'https://uis.fudan.edu.cn/authserver/login?' \
                  'service=https://zlapp.fudan.edu.cn/site/ncov/fudanDaily'
    daily_fudan = Zlapp(uid, psw, api_usr, api_pwd, url_login=zlapp_login)
    daily_fudan.login()

    daily_fudan.check()
    daily_fudan.checkin()
    # 再检查一遍
    daily_fudan.check()

    daily_fudan.close()
