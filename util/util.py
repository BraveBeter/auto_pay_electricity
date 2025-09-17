import json
import os
import socket
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from queue import Queue

import requests
from bs4 import BeautifulSoup


class AuthServiceError(Exception):
    """当未登陆或登陆失败时引发此异常。"""

    pass


class VPNError(Exception):
    """当疑似未开启 VPN 时引发此异常。"""

    pass


def test_network(timeout: float = 0.5) -> bool:
    """检测设备是否连接学校内网。

    若超时时间小于 0.5 秒，则可能会有误报。
    """
    ip_addrs = ["10.50.2.206", "10.166.18.114", "10.166.19.26", "10.168.103.76"]
    test_result = Queue()

    def test_helper(addr: str) -> None:
        try:
            socket.create_connection((addr, 80), timeout=timeout)
            test_result.put(1)
        except TimeoutError:
            pass

    with ThreadPoolExecutor(max_workers=5) as executor:
        for addr in ip_addrs:
            executor.submit(test_helper, addr)
    count = 0
    while not test_result.empty():
        count += test_result.get()
    return count / len(ip_addrs) >= 0.5


def semester_week() -> int:
    """获取当前教学周。

    特别地，`-1` 表示暑假，`-2` 表示寒假。
    """
    jwc_url = "https://jwc.shiep.edu.cn/"
    response = requests.get(jwc_url)
    response.raise_for_status()
    dom = BeautifulSoup(response.text, features="html.parser")

    semeter_start = date.fromisoformat(dom.select("div#semester_start")[0].text)
    semeter_end = date.fromisoformat(dom.select("div#semester_end")[0].text)
    if (date.today() - semeter_start).days < 0 or (date.today() - semeter_end).days > 0:
        return -1 if date.today().month > 5 else -2
    else:
        return (date.today() - semeter_start).days // 7

def get_resource_path(relative_path):
    """ 获取资源的绝对路径，兼容开发环境和打包后的环境 """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 会创建一个临时文件夹 _MEIPASS 来存放解压后的文件
        base_path = sys._MEIPASS
    else:
        # 开发环境或者未打包的情况
        base_path = os.path.abspath("..") # 或者 os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

# === 加载配置 ===
def load_config(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileExistsError:
        return {}

__all__ = (
    "AuthServiceError",
    "VPNError",
    "test_network",
    "semester_week",
    "get_resource_path",
    "load_config",
)