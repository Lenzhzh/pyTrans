from __future__ import annotations

import socket
import threading
import json
import os
import struct
import time
import typing

if typing.TYPE_CHECKING:
    from main_app import App


DISCOVERY_PORT = 12345
FILE_PORT = 12346
MAGIC_HEADER = "Len_zh_trans"
BUFFER_SIZE = 4096


class NetworkHandler:
    def __init__(self, app: App):
        self.app = app
        self.my_hostname = socket.gethostname()
        self.my_ip = socket.gethostbyname(self.my_hostname)

        self.peers = {}
        self.selected_file = None

    def start_network(self):
        listener_thread = threading.Thread(target=self.listen_for_peers, daemon=True)
        listener_thread.start()

        broadcaster_thread = threading.Thread(target=self.broadcast_presence, daemon=True)
        broadcaster_thread.start()

        receiver_thread = threading.Thread(target=self.start_file_receiver, daemon=True)
        receiver_thread.start()

    
    def listen_for_peers(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            s.bind(("", DISCOVERY_PORT))
            print(f"[*] 侦听已在端口 {DISCOVERY_PORT} 启动")

            while True:
                try:
                    data, addr = s.recvfrom(1024)
                    message = json.loads(data.decode('utf-8'))

                    if message.get("header") == MAGIC_HEADER:
                        peer_ip = addr[0]
                        peer_host_name = message.get("hostname")

                        if peer_ip not in self.peers:
                            self.peers[peer_ip] = peer_host_name

                            self.app.after(0, self.app.update_peer_list)

                except Exception as e:
                    print(f"[!] {e}")

            
    def broadcast_presence(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            message = json.dumps({
                "header" : MAGIC_HEADER,
                "hostname" : self.my_hostname,
            }).encode('utf-8')

            while True:
                s.sendto(message, ('255.255.255.255', DISCOVERY_PORT))
                print(f"[*] 已广播")
                time.sleep(5)

    
    def start_file_receiver(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", FILE_PORT))
            s.listen()
            print(f"[*] 文件接收服务已在端口 {FILE_PORT} 启动")

            while True:
                conn, addr = s.accept()

                handler_thread = threading.Thread(target=self.handle_file_receive, args=(conn, addr), daemon=True)
                handler_thread.start()
        
    def handle_file_receive(self, conn, addr):
        print(f"[+] 接收到来自 {addr[0]} 的文件传输")
        self.app.update_status(f"接收到来自 {addr[0]} 的文件传输")
        with conn:
            header_len_data = conn.recv(4)
            if not header_len_data:
                self.app.update_status(f"传输不合法")
                return 
            header_len = struct.unpack('>I', header_len_data)[0]

            header_data = conn.recv(header_len)
            metadata = json.loads(header_data.decode('utf-8'))
            filename = metadata['filename']
            filesize = metadata['filesize']

            self.app.update_status(f"正在接收文件 {filename}")

            downloads_dir = 'Downloads'
            os.makedirs(downloads_dir, exist_ok=True)

            save_path = os.path.join(downloads_dir, filename)

            bytes_received = 0
            with open(save_path, 'wb') as f:
                while bytes_received < filesize:
                    chunk = conn.recv(BUFFER_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_received += len(chunk)
                
            print(f"[*] 文件 {filename} 成功保存至 {save_path}")
            self.app.update_status(f"{filename} 接收完毕！")

        print(f"[-] 来自 {addr[0]} 的连接已经关闭")

    def send_file(self, target_ip, filepath):
        try:
            self.app.update_status(f"正在连接到 {target_ip}")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((target_ip, FILE_PORT))
                self.app.update_status(f"已连接")
            
                filename = os.path.basename(filepath)
                filesize = os.path.getsize(filepath)

                header = json.dumps({
                    "filename": filename,
                    "filesize": filesize
                }).encode('utf-8')

                header_len = struct.pack('>I', len(header))
                s.sendall(header_len)

                s.sendall(header)

                self.app.update_status(f"正在发送 {filename}")
                with open(filepath, 'rb') as f:
                    while True:
                        chunk = f.read(BUFFER_SIZE)
                        if not chunk:
                            break
                        s.sendall(chunk)

                self.app.update_status(f"文件 {filename} 发送成功")
            
        except Exception as e:
            print(f"[!] 发送文件出错 {e}")
            self.app.update_status(f"错误 {e}")