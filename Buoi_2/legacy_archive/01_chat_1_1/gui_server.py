"""Bài 1 - GUI Server Chat TCP 1:1 (Dành cho MÁY B - SERVER NHẬN)."""

import os
import socket
import sys
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HOST = "0.0.0.0"
PORT = 5000
ENCODING = "utf-8"


class ChatServerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MÁY B: SERVER CHAT TCP 1:1 (Cổng 5000)")
        self.root.geometry("680x580")
        self.root.minsize(580, 480)

        self.server_sock: socket.socket | None = None
        self.client_sock: socket.socket | None = None
        self.client_addr: tuple[str, int] | None = None
        self.client_user: str = "Client"

        self.is_running = False
        self.listen_thread: threading.Thread | None = None

        self._build_ui()
        # Auto-start server listening on launch
        self.root.after(300, lambda: self.start_server(is_manual=False))

    def _build_ui(self):
        # Header Banner
        header = tk.Frame(self.root, bg="#1A365D", padx=12, pady=10)
        header.pack(fill=tk.X)

        tk.Label(header, text="🖥️ MÁY B: SERVER CHAT TCP 1:1 (PORT 5000)", font=("Segoe UI", 13, "bold"), fg="#FFFFFF", bg="#1A365D").pack(anchor=tk.W)
        tk.Label(header, text="Máy B đóng vai trò SERVER NHẬN - Lắng nghe kết nối từ Máy A (Client)", font=("Segoe UI", 9), fg="#E2E8F0", bg="#1A365D").pack(anchor=tk.W, pady=(2, 0))

        # Config Bar
        cfg_frame = tk.Frame(self.root, bg="#F7FAFC", padx=10, pady=8)
        cfg_frame.pack(fill=tk.X)

        tk.Label(cfg_frame, text="Host lắng nghe:", font=("Segoe UI", 9, "bold"), bg="#F7FAFC").grid(row=0, column=0, sticky=tk.W)
        self.host_entry = tk.Entry(cfg_frame, font=("Segoe UI", 9), width=10)
        self.host_entry.insert(0, HOST)
        self.host_entry.grid(row=0, column=1, padx=4)

        tk.Label(cfg_frame, text="Port:", font=("Segoe UI", 9, "bold"), bg="#F7FAFC").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        self.port_entry = tk.Entry(cfg_frame, font=("Segoe UI", 9), width=6)
        self.port_entry.insert(0, str(PORT))
        self.port_entry.grid(row=0, column=3, padx=4)

        self.btn_toggle = tk.Button(cfg_frame, text="🚀 BẮT ĐẦU LẮNG NGHE", font=("Segoe UI", 9, "bold"), bg="#38A169", fg="#FFFFFF", activebackground="#2F855A", activeforeground="#FFFFFF", padx=8, command=self.toggle_server)
        self.btn_toggle.grid(row=0, column=4, padx=12)

        # Status & Connection Banner
        status_frame = tk.Frame(self.root, bg="#EDF2F7", padx=10, pady=6, bd=1, relief=tk.SOLID)
        status_frame.pack(fill=tk.X, padx=10, pady=4)

        self.status_label = tk.Label(status_frame, text="🔴 Server đã dừng", font=("Segoe UI", 9, "bold"), fg="#E53E3E", bg="#EDF2F7")
        self.status_label.pack(side=tk.LEFT)

        self.client_info_label = tk.Label(status_frame, text="Chưa có Máy A kết nối.", font=("Segoe UI", 9, "italic"), fg="#4A5568", bg="#EDF2F7")
        self.client_info_label.pack(side=tk.RIGHT)

        # Log Window
        log_frame = tk.Frame(self.root, bg="#F7FAFC", padx=10, pady=4)
        log_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(log_frame, text="Nhật ký Server & Phản hồi Tự động (/time, /whoami):", font=("Segoe UI", 9, "bold"), fg="#2B6CB0", bg="#F7FAFC").pack(anchor=tk.W, pady=(2, 4))

        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=("Segoe UI", 10), state=tk.DISABLED, bg="#FFFFFF", fg="#2D3748")
        self.log_area.pack(fill=tk.BOTH, expand=True)

        self.log_area.tag_config("server", foreground="#2B6CB0", font=("Segoe UI", 10, "bold"))
        self.log_area.tag_config("client", foreground="#2C7A7B", font=("Segoe UI", 10, "bold"))
        self.log_area.tag_config("auto", foreground="#805AD5", font=("Segoe UI", 9, "italic"))
        self.log_area.tag_config("system", foreground="#D69E2E", font=("Segoe UI", 9, "bold"))

        # Operator Reply Frame
        reply_frame = tk.Frame(self.root, bg="#F7FAFC", padx=10, pady=8)
        reply_frame.pack(fill=tk.X)

        tk.Label(reply_frame, text="Máy B (Server) > ", font=("Segoe UI", 9, "bold"), bg="#F7FAFC").pack(side=tk.LEFT)
        self.reply_entry = tk.Entry(reply_frame, font=("Segoe UI", 10), bg="#FFFFFF")
        self.reply_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self.reply_entry.bind("<Return>", lambda e: self.send_operator_reply())

        self.btn_send = tk.Button(reply_frame, text="GỬI PHẢN HỒI 📤", font=("Segoe UI", 9, "bold"), bg="#2B6CB0", fg="#FFFFFF", activebackground="#2C5282", activeforeground="#FFFFFF", command=self.send_operator_reply, state=tk.DISABLED)
        self.btn_send.pack(side=tk.RIGHT)

    def log(self, text: str, tag: str = "normal"):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, text + "\n", tag)
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def toggle_server(self):
        if not self.is_running:
            self.start_server(is_manual=True)
        else:
            self.stop_server()

    def start_server(self, is_manual: bool = False):
        if self.is_running:
            return
        host = self.host_entry.get().strip() or HOST
        try:
            port = int(self.port_entry.get().strip() or str(PORT))
        except ValueError:
            if is_manual:
                messagebox.showerror("Lỗi", "Cổng Port phải là số nguyên.")
            return

        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if sys.platform != "win32":
                self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind((host, port))
            self.server_sock.listen(5)

            self.is_running = True
            self.btn_toggle.config(text="🛑 DỪNG SERVER", bg="#E53E3E", fg="#FFFFFF", activebackground="#C53030")
            self.status_label.config(text=f"🟢 Máy B đang lắng nghe tại {host}:{port}", fg="#38A169")
            self.log(f"[SERVER MÁY B] Đã bắt đầu lắng nghe tại {host}:{port}", "system")

            self.listen_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.listen_thread.start()

        except Exception as exc:
            self.server_sock = None
            if is_manual:
                messagebox.showerror("Lỗi Server Máy B", f"Không thể bind tại {host}:{port}\n\nCổng {port} đang được sử dụng bởi một ứng dụng/cửa sổ khác!\n\nLỗi chi tiết: {exc}")
            else:
                self.status_label.config(text=f"🟡 Cổng {port} đang được mở bởi Server khác!", fg="#D69E2E")
                self.log(f"[THÔNG BÁO] Cổng {port} đang có cửa sổ Server khác lắng nghe. Bấm 'Bắt đầu' khi muốn thử lại.", "system")

    def stop_server(self):
        self.is_running = False
        if self.client_sock:
            try:
                self.client_sock.close()
            except Exception:
                pass
            self.client_sock = None

        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
            self.server_sock = None

        self.btn_toggle.config(text="🚀 BẮT ĐẦU LẮNG NGHE", bg="#38A169", fg="#FFFFFF", activebackground="#2F855A")
        self.btn_send.config(state=tk.DISABLED)
        self.status_label.config(text="🔴 Server đã dừng", fg="#E53E3E")
        self.client_info_label.config(text="Chưa có Máy A kết nối.", fg="#4A5568")
        self.log("[SERVER MÁY B] Đã dừng server.", "system")

    def _accept_loop(self):
        while self.is_running and self.server_sock:
            try:
                client_s, client_a = self.server_sock.accept()
                if not self.is_running:
                    break

                self.client_sock = client_s
                self.client_addr = client_a

                # REQ-1 Handshake
                username_line = self._recv_line(self.client_sock)
                if not username_line:
                    self.client_sock.close()
                    continue

                self.client_user = username_line.strip()
                ip, port = self.client_addr[0], self.client_addr[1]

                self.root.after(0, lambda u=self.client_user, i=ip, p=port: self._on_client_connected(u, i, p))

                # Send welcome
                self._send_line(self.client_sock, f"Xin chào {self.client_user}! Kết nối Máy B (Server) thành công. Gõ /time, /whoami, hoặc /quit.")

                # Chat loop
                self._handle_client_messages()

            except Exception:
                if self.is_running:
                    break

    def _on_client_connected(self, user: str, ip: str, port: int):
        self.client_info_label.config(text=f"🟢 Máy A kết nối: {user} ({ip}:{port})", fg="#2B6CB0", font=("Segoe UI", 9, "bold"))
        self.log(f"[SERVER MÁY B] Máy A ({user}) từ {ip}:{port} đã kết nối (REQ-1)", "system")
        self.btn_send.config(state=tk.NORMAL)

    def _handle_client_messages(self):
        while self.is_running and self.client_sock:
            msg = self._recv_line(self.client_sock)
            if msg is None:
                user = self.client_user
                self.root.after(0, lambda u=user: self._on_client_disconnected(u))
                break

            text = msg.strip()
            if not text:
                continue

            if text.lower() == "/quit":
                self._send_line(self.client_sock, "Tạm biệt!")
                user = self.client_user
                self.root.after(0, lambda u=user: self.log(f"[SERVER MÁY B] Máy A ({u}) đã thoát (/quit).", "system"))
                break

            # REQ-2: /time
            elif text.lower() == "/time":
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                reply = f"[Hệ thống] Thời gian hiện tại của Máy B (Server): {now_str}"
                self._send_line(self.client_sock, reply)
                self.root.after(0, lambda u=self.client_user, t=now_str: self.log(f"[Auto-Reply /time] Gửi {t} tới Máy A ({u})", "auto"))

            # REQ-3: /whoami
            elif text.lower() == "/whoami":
                ip, p = self.client_addr[0], self.client_addr[1]
                reply = f"[Hệ thống] Địa chỉ IP Máy A: {ip}, Source Port: {p}"
                self._send_line(self.client_sock, reply)
                self.root.after(0, lambda u=self.client_user, i=ip, pr=p: self.log(f"[Auto-Reply /whoami] Gửi {i}:{pr} tới Máy A ({u})", "auto"))

            # Normal chat text
            else:
                user = self.client_user
                self.root.after(0, lambda u=user, t=text: self.log(f"Máy A ({u}) > {t}", "client"))

        if self.client_sock:
            try:
                self.client_sock.close()
            except Exception:
                pass
            self.client_sock = None

    def _on_client_disconnected(self, user: str):
        self.client_info_label.config(text="Chưa có Máy A kết nối.", fg="#4A5568", font=("Segoe UI", 9, "italic"))
        self.log(f"[SERVER MÁY B] Máy A ({user}) đã ngắt kết nối.", "system")
        self.btn_send.config(state=tk.DISABLED)

    def send_operator_reply(self):
        if not self.client_sock:
            messagebox.showinfo("Thông báo", "Chưa có Máy A (Client) kết nối.")
            return

        reply = self.reply_entry.get().strip()
        if not reply:
            messagebox.showwarning("Cảnh báo", "Không gửi tin nhắn rỗng (REQ-4).")
            return

        try:
            self._send_line(self.client_sock, reply)
            self.log(f"Máy B (Server) > {reply}", "server")
            self.reply_entry.delete(0, tk.END)
        except Exception as exc:
            self.log(f"[LỖI GỬI] {exc}", "system")

    def _send_line(self, sock: socket.socket, text: str):
        sock.sendall((text + "\n").encode(ENCODING))

    def _recv_line(self, sock: socket.socket) -> str | None:
        data = bytearray()
        while True:
            try:
                chunk = sock.recv(1)
            except Exception:
                return None
            if not chunk:
                return None if not data else data.decode(ENCODING)
            if chunk == b"\n":
                return data.decode(ENCODING).rstrip("\r")
            data.extend(chunk)


def main():
    root = tk.Tk()
    app = ChatServerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
