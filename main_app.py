from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk, filedialog
import socket
import threading
import json
import os
from tkinter import messagebox

from network_handler import NetworkHandler

DISCOVERY_PORT = 12345
FILE_PORT = 12346
MAGIC_HEADER = "Len_zh_trans"

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("文件传输")
        self.geometry("400x300")

        self.my_hostname = socket.gethostname()
        self.my_ip = socket.gethostbyname(self.my_hostname)

        self.init_gui()

        self.selected_file = None

        self.network = NetworkHandler(self)
        self.network.start_network()

    def init_gui(self):
        self.peer_list_label = ttk.Label(self, text="发现的设备")
        self.peer_list_label.pack(pady=5)

        self.peer_listbox = tk.Listbox(self)
        self.peer_listbox.pack(fill=tk.BOTH, expand=True, padx=10)
        self.peer_listbox.bind("<<ListboxSelect>>", self.on_peer_select)

        self.button_frame = ttk.Frame(self)
        self.button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        self.select_file_button = ttk.Button(self.button_frame, text="选择文件", command=self.select_file)
        self.select_file_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5,0))

        self.send_button = ttk.Button(self.button_frame, text="发送文件", state=tk.DISABLED, command=self.send_file)
        self.send_button.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5,0))

        self.status_label = ttk.Label(self, text=f"本机IP {self.my_ip}")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 5))

    def update_peer_list(self):
        self.peer_listbox.delete(0, tk.END)

        self.peer_listbox.insert(tk.END, f"本机 ({self.my_ip})")
        self.peer_listbox.itemconfig(0, {'fg':'blue'})

        for ip, hostname in self.network.peers.items():
            if ip==self.my_ip:
                self.peer_listbox.insert(tk.END, f"本机!!! ({ip})")
            else :
                self.peer_listbox.insert(tk.END, f"{hostname} ({ip})")

    def update_status(self, text):
        self.after(0, lambda :self.status_label.config(text=text))

    def select_file(self):
        file_path = filedialog.askopenfilename()

        if file_path:
            self.selected_file = file_path
            filename = os.path.basename(file_path)
            self.status_label.config(text=f"已选择 {filename}")
            self.on_peer_select(None)

        else:
            self.send_button.config(state=tk.DISABLED)
        
    def send_file(self):
        selection = self.peer_listbox.curselection()     
        selected_text = self.peer_listbox.get(selection[0])
        ip_match = re.search(r'\((\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\)', selected_text)

        if not ip_match:
            messagebox.showerror("错误")
            return
        
        target_ip = ip_match.group(1)
        threading.Thread(
            target=self.network.send_file,
            args = (target_ip, self.selected_file),
            daemon=True
        ).start()

    def on_peer_select(self, event):
        if self.select_file and self.peer_listbox.curselection():
            self.send_button.config(state=tk.NORMAL)

        

        


if __name__ == '__main__':
    app = App()
    app.mainloop()
                        