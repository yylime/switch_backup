import re
import flet as ft
from netmiko import SSHDetect, ConnectHandler
from datetime import datetime
import os

import socks
import socket

# # 设置代理服务器地址和端口
# socks.set_default_proxy(socks.HTTP,
#                         addr="172.20.255.4",
#                         port=32123,
#                         username="yiyulin",
#                         password="yyl123456")

# # 设置socket包装
# socket.socket = socks.socksocket


def netmiko_ssh_detect_stype(ip: str, usrname: str, password: str) -> str:
    dev = {
        "device_type": "autodetect",
        "host": ip,
        "username": usrname,
        "password": password,
    }
    guesser = SSHDetect(**dev)
    best_match = guesser.autodetect()
    return best_match


def backup_sw(ip: str, usrname: str, password: str) -> str:
    device_type = netmiko_ssh_detect_stype(ip, usrname, password)
    # h3c 交换机不支持自动检测需要修改源码
    if device_type is None:
        device_type = "hp_comware"
    try:
        with ConnectHandler(
            device_type=device_type,
            ip=ip,
            username=usrname,
            password=password,
            conn_timeout=5,
            fast_cli=False,
            auth_timeout=10,
        ) as net_connect:
            if "cisco" not in device_type:
                configuration = net_connect.send_command(
                    "display current-configuration",
                    read_timeout=30,
                    expect_string="return",
                )
                # 正则提取H3C的配置，华为和思科没有这个问题
                if device_type == "hp_comware":
                    match = re.search(r"#.*?return", configuration, re.DOTALL)
                    if match:
                        matched_text = match.group(0)
                        configuration = matched_text
            else:
                configuration = net_connect.send_command(
                    "show running-config", read_timeout=30
                )
            # create Datetime
            date = datetime.today().strftime("%Y-%m-%d")
            if not os.path.exists(date):
                os.makedirs(date)

            with open(os.path.join(date, f"{ip}.config"), "w") as f:
                f.write(configuration)
            return f"{ip}_success"

    except Exception as e:
        return f"{ip}_{e.__class__.__name__}"


def backup_switches(lines: str) -> str:
    res = []
    for line in lines.split("\n"):
        line = line.strip()
        ip, username, password = line.split(" ")
        info = backup_sw(ip, username, password)
        res.append(info)
    return "\n".join(res)


def main(page: ft.Page):
    page.title = "交换机备份小工具"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.MainAxisAlignment.CENTER
    page.window_width = 400

    def open_dlg(message):
        page.dialog = ft.AlertDialog(title=ft.Text(message))
        page.dialog.open = True
        page.update()

    def btn_click(e):
        if not txt_name.value:
            txt_name.error_text = "请输入规范的行（格式：IP, 用户名, 密码）"
            page.update()
        else:
            page.client_storage.set("switch_info", txt_name.value)
            res = backup_switches(txt_name.value)
            open_dlg(res)

    values = page.client_storage.get("switch_info")
    txt_name = ft.TextField(
        label="交换机管理IP, 用户名, 密码",
        multiline=True,
        width=350,
        height=500,
        value=values,
    )

    page.add(
        txt_name,
        ft.ElevatedButton(
            "开始备份~",
            on_click=btn_click,
        ),
    )


if __name__ == "__main__":
    ft.app(target=main)

    # with open("data") as f:
    #     data = f.read()
    # res = backup_switches(data)
    # print(res)
