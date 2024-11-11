# -*- coding:utf-8 -*-

import os
import time
from http.cookies import SimpleCookie
from threading import Thread

import requests

from utils import COMMON_HEADERS
from account_manager import AccountManager


class SunoCookie:
    def __init__(self):
        self.cookie = SimpleCookie()
        self.session_id = None
        self.token = None
        self.account_manager = AccountManager()
        self.current_account_email = None

    def initialize(self):
        """在FastAPI启动事件后调用此方法进行初始化"""
        self.load_next_account()

    def load_next_account(self):
        account_email, account_data = self.account_manager.get_next_account()
        self.current_account_email = account_email
        print(f"Loading account: {account_email}")
        self.set_session_id(account_data['session_id'])
        self.load_cookie(account_data['cookie'])
        update_token(self)

    def handle_insufficient_credits(self):
        self.account_manager.disable_account(self.current_account_email)
        print(f"*** disabled account: {self.current_account_email} ***")
        self.load_next_account()
        print(f"*** loaded account: {self.current_account_email} ***")

    def load_cookie(self, cookie_str):
        self.cookie.load(cookie_str)

    def get_cookie(self):
        return ";".join([f"{i}={self.cookie.get(i).value}" for i in self.cookie.keys()])

    def set_session_id(self, session_id):
        self.session_id = session_id

    def get_session_id(self):
        return self.session_id

    def get_token(self):
        return self.token

    def set_token(self, token: str):
        self.token = token


suno_auth = SunoCookie()


def update_token(suno_cookie: SunoCookie):
    headers = {"cookie": suno_cookie.get_cookie()}
    headers.update(COMMON_HEADERS)
    session_id = suno_cookie.get_session_id()
    print(f"*** session_id -> {session_id} ***")
    print(f"*** headers -> {headers} ***")

    resp = requests.post(
        url=f"https://clerk.suno.com/v1/client/sessions/{session_id}/tokens?_clerk_js_version=4.72.0-snapshot.vc141245",
        headers=headers,
    )

    resp_headers = dict(resp.headers)
    set_cookie = resp_headers.get("Set-Cookie")
    suno_cookie.load_cookie(set_cookie)
    token = resp.json().get("jwt")
    suno_cookie.set_token(token)
    # print(set_cookie)
    print(f"*** token -> {token} ***")


def keep_alive(suno_cookie: SunoCookie):
    while True:
        try:
            update_token(suno_cookie)
        except Exception as e:
            print(e)
        finally:
            time.sleep(5)


def start_keep_alive(suno_cookie: SunoCookie):
    suno_cookie.initialize()  # 确保账号已加载
    t = Thread(target=keep_alive, args=(suno_cookie,))
    t.daemon = True  # 设置为守护线程
    t.start()
