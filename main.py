#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   main.py
@Time    :   2024/03/23 20:31:00
@Author  :   Yi yulin 
@Contact :   844202100@qq.com
@Desc    :   a switch backup model
"""


import os
import re
from datetime import datetime
from netmiko import SSHDetect, ConnectHandler
import customtkinter
from concurrent.futures import ThreadPoolExecutor

def netmiko_ssh_detect_stype(ip: str, usrname: str, password: str) -> str:
    """netmiko_ssh_detect_stype

    Args:
        ip (str): login/manage ip
        usrname (str): login/manage username
        password (str): login/manage password

    Returns:
        str: switch device type
    """
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
    """backup_sw
    AArgs:
        ip (str): login/manage ip
        usrname (str): login/manage username
        password (str): login/manage password

    Returns:
        str: info of result
    """
    device_type = netmiko_ssh_detect_stype(ip, usrname, password)
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

            with open(os.path.join(date, f"{ip}.config"), "w", encoding="utf-8") as f:
                f.write(configuration)
            return f"{ip}_success"

    except Exception as e:
        return f"{ip}_{e.__class__.__name__}"


def backup_switches(lines: str) -> str:
    """readlines to backup_switches

    Args:
        lines (str): lines

    Returns:
        str: result
    """
    # use threadpool in mainloop instead of waiting
    res = []
    with ThreadPoolExecutor(8) as pool:
        for line in lines.split("\n"):
            line = line.strip()
            if len(line) > 1:
                ip, username, password = re.split(r"\s+", line)
                future = pool.submit(backup_sw, (ip, username, password))
                res.append(future.result())
    return "\n".join(res)


def get_local_storage() -> str:
    """Get local Storage"""
    data = ""
    if os.path.exists("data"):
        with open("data", "r", encoding="utf-8") as f:
            data = f.read()
    return data


def set_local_storage(data: str):
    """set local Storage"""
    with open("data", "w", encoding="utf-8") as f:
        f.write(data)


class ToplevelWindow(customtkinter.CTkToplevel):

    def __init__(self, *args, text="top", **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry("300x500")
        self.label = customtkinter.CTkLabel(self, text=text)
        self.label.pack(padx=20, pady=20)


class App(customtkinter.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.toplevel_window = None
        self.title("Switch Backup")
        self.geometry("300x600")
        self.grid_columnconfigure((0), weight=1)

        self.label = customtkinter.CTkLabel(self, text="Input ip, username, password")
        self.label.configure(corner_radius=0.2, font=("Golos UI Bold", 19))
        self.label.grid(row=0, column=0, pady=10)

        self.textbox = customtkinter.CTkTextbox(self)
        self.textbox.configure(height=500, font=("Golos UI Bold", 15))
        self.textbox.grid(row=1, column=0, padx=20, sticky="ew")
        self.textbox.insert("0.0", get_local_storage())

        self.button = customtkinter.CTkButton(
            self, text="Start Backup~", command=self.button_backup
        )
        self.button.grid(row=2, column=0, padx=20, pady=8, sticky="ew", columnspan=2)

        self.toplevel_window = None

    def button_backup(self):
        """button_backup"""
        text = self.textbox.get("0.0", "end")
        set_local_storage(text)
        # backup switch
        res = backup_switches(text)
        if self.toplevel_window is None or not self.toplevel_window.winfo_exists():
            self.toplevel_window = ToplevelWindow(text=res)
            # top one the info window
            self.toplevel_window.attributes("-topmost", 1)
        else:
            self.toplevel_window.focus()


if __name__ == "__main__":
    switch_app = App()
    switch_app.mainloop()
