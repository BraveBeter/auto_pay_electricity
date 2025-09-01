import json
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox
import subprocess
import time
import pyautogui
import psutil
from requests import HTTPError
import electricity
import auth
from electricity import RechargeInfo
from util import get_resource_path
from util import  load_config
# 使用示例
config_path = get_resource_path("config.json")
cfg = load_config(config_path)

# === 检查 VPN 进程是否已运行 ===
def is_vpn_running(exe_name='SangforCSClient.exe') -> bool:
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and exe_name.lower() in proc.info['name'].lower():
            return True
    return False

# === 核心流程函数 ===
def login_vpn(vpn_exe, username, password, delay):
    if is_vpn_running():
        print("🔗 VPN 已连接，无需重新启动。")
        return

    subprocess.Popen([vpn_exe])
    time.sleep(delay * 1.5)
    pyautogui.write(username, interval=0.1)
    pyautogui.press('tab')
    pyautogui.write(password, interval=0.1)
    pyautogui.press('enter')
    time.sleep(delay)
    print("✅ VPN 已连接。")


def login(username, password, site = "http://10.50.2.206:80/"):
    # service 必须与下面一行所展示的精确相符，都为 22 个字符！
    service = auth.AuthService(username, password, service=site, renew="true")
    # 是否需要输入验证码？
    if service.need_captcha():
        # 获取并保存验证码:
        with open("captcha.jpg", "wb") as captcha_image:
            captcha_image.write(service.get_captcha_image())
        # 填写验证码:
        service.set_captcha_code("验证码")
    # time.sleep(3)
    # 登陆:
    try:
        service.login()
    except HTTPError as e:
        print(e)
    return service

def pay_electricity(fee_site, site_user, site_pass, room, amount, delay)->RechargeInfo:

    service = login(site_user, site_pass, site=fee_site)
    time.sleep(delay)
    em = electricity.ElectricityManagement(service.session)
    # 获取电表参数：
    # print(em.meter_state)
    # 充值电费
    em.recharge("C1", room, amount)
    # 获取历次的电表充值账单：
    all_payments = list(em.recharge_info)
    # print(list(em.recharge_info)[0])
    service.logout()
    return all_payments[0]


# === GUI 界面 ===
class App:
    def __init__(self, root):
        self.root = root
        root.title("自动电费缴纳工具")

        # 读取默认配置
        self.vpn_exe = cfg.get('vpn_client_exe', '')
        self.vpn_user = cfg.get('vpn_username', '')
        self.vpn_pass = cfg.get('vpn_password', '')
        self.fee_site = cfg.get('fee_site', '')
        self.site_user = cfg.get('site_username', '')
        self.site_pass = cfg.get('site_password', '')
        self.delay = cfg.get('step_delay', 5)

        # Input fields
        tk.Label(root, text="充值房间号：").grid(row=0, column=0)
        self.entry_room = tk.Entry(root)
        self.entry_room.grid(row=0, column=1)

        tk.Label(root, text="充值金额：").grid(row=1, column=0)
        self.entry_amount = tk.Entry(root)
        self.entry_amount.grid(row=1, column=1)

        tk.Label(root, text="VPN 用户：").grid(row=2, column=0)
        self.entry_vpn_user = tk.Entry(root)
        self.entry_vpn_user.insert(0, self.vpn_user)
        self.entry_vpn_user.grid(row=2, column=1)

        tk.Label(root, text="VPN 密码：").grid(row=3, column=0)
        self.entry_vpn_pass = tk.Entry(root, show="*")
        self.entry_vpn_pass.insert(0, self.vpn_pass)
        self.entry_vpn_pass.grid(row=3, column=1)

        # Start按钮
        self.btn_start = tk.Button(root, text="开始缴费", command=self.start)
        self.btn_start.grid(row=6, column=0, columnspan=2, pady=10)

    def start(self):
        room = self.entry_room.get().strip()
        amount = self.entry_amount.get().strip()
        vpn_user = self.entry_vpn_user.get().strip() or self.vpn_user
        vpn_pass = self.entry_vpn_pass.get().strip() or self.vpn_pass
        site_user = vpn_user
        site_pass = vpn_pass

        if not room or not amount:
            messagebox.showwarning("输入错误", "请填写充值房间号和金额！")
            return

        self.btn_start.config(state=tk.DISABLED)
        messagebox.showinfo("提示", "开始执行自动缴费，请勿操作鼠标键盘。")

        # 后台线程执行
        def task():
            try:
                login_vpn(self.vpn_exe, vpn_user, vpn_pass, self.delay)
                get = pay_electricity(self.fee_site, site_user, site_pass, room, amount, self.delay)
                messagebox.showinfo("完成", "自动缴费流程已完成！\n时间：" + str(get.time) + "\n 充值金额：" + str(get.money))
            except Exception as e:
                messagebox.showerror("错误", f"发生异常: {e}")
            finally:
                self.btn_start.config(state=tk.NORMAL)

        threading.Thread(target=task, daemon=True).start()

if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()