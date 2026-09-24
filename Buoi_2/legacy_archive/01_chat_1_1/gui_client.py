"""Bài 1 - GUI Client Chat TCP 1:1 (Dành cho MÁY A - CLIENT GỬI)."""

import socket
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PORT = 5000
ENCODING = "utf-8"


class ChatClientGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MÁY A: CLIENT CHAT TCP 1:1 (GỬI SANG MÁY B SERVER)")
        self.root.geometry("660x570")
        self.root.minsize(560, 460)

        self.sock: socket.socket | None = None
        self.is_connected = False
        self.recv_thread: threading.Thread | None = None

        self._build_ui()
        # Auto connect to 127.0.0.1 after short delay with auto-retry
        self.root.after(500, lambda: self.connect(auto_retry=True))

    def _build_ui(self):
        # Header Banner
        header = tk.Frame(self.root, bg="#2B6CB0", padx=12, pady=10)
        header.pack(fill=tk.X)

        tk.Label(header, text="💬 MÁY A: CLIENT CHAT TCP 1:1 (GỬI SANG MÁY B)", font=("Segoe UI", 13, "bold"), fg="#FFFFFF", bg="#2B6CB0").pack(anchor=tk.W)
        tk.Label(header, text="Máy A đóng vai trò CLIENT GỬI - Nhập IP Máy B Server để mở kết nối", font=("Segoe UI", 9), fg="#E2E8F0", bg="#2B6CB0").pack(anchor=tk.W, pady=(2, 0))

        # Connection Config Frame
        conn_frame = tk.Frame(self.root, bg="#F7FAFC", padx=10, pady=8)
        conn_frame.pack(fill=tk.X)

        tk.Label(conn_frame, text="IPv4 Server (Máy B):", font=("Segoe UI", 9, "bold"), bg="#F7FAFC").grid(row=0, column=0, sticky=tk.W)
        self.ip_entry = tk.Entry(conn_frame, font=("Segoe UI", 9), width=13)
        self.ip_entry.delete(0, tk.END)
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.grid(row=0, column=1, padx=2)

        btn_local = tk.Button(conn_frame, text="⚡ Localhost", font=("Segoe UI", 8, "bold"), bg="#EDF2F7", fg="#2D3748", command=self.set_localhost)
        btn_local.grid(row=0, column=2, padx=2)

        tk.Label(conn_frame, text="Port:", font=("Segoe UI", 9, "bold"), bg="#F7FAFC").grid(row=0, column=3, sticky=tk.W, padx=(4, 0))
        self.port_entry = tk.Entry(conn_frame, font=("Segoe UI", 9), width=6)
        self.port_entry.insert(0, str(PORT))
        self.port_entry.grid(row=0, column=4, padx=2)

        tk.Label(conn_frame, text="Username:", font=("Segoe UI", 9, "bold"), bg="#F7FAFC").grid(row=0, column=5, sticky=tk.W, padx=(4, 0))
        self.user_entry = tk.Entry(conn_frame, font=("Segoe UI", 9), width=9)
        self.user_entry.insert(0, "Nam")
        self.user_entry.grid(row=0, column=6, padx=2)

        self.btn_connect = tk.Button(conn_frame, text="🔌 KẾT NỐI", font=("Segoe UI", 9, "bold"), bg="#2B6CB0", fg="#FFFFFF", activebackground="#2C5282", activeforeground="#FFFFFF", padx=6, command=self.toggle_connection)
        self.btn_connect.grid(row=0, column=7, padx=6)

        # Hint Label
        hint_lbl = tk.Label(conn_frame, text="💡 Gợi ý: Bấm '⚡ Localhost' để kết nối lại khi mở Server Máy B.", font=("Segoe UI", 9, "italic"), fg="#718096", bg="#F7FAFC")
        hint_lbl.grid(row=1, column=0, columnspan=8, sticky=tk.W, pady=(4, 0))

        # Status Bar
        status_frame = tk.Frame(self.root, bg="#EDF2F7", padx=10, pady=5, bd=1, relief=tk.SOLID)
        status_frame.pack(fill=tk.X, padx=10, pady=4)
        self.status_label = tk.Label(status_frame, text="🔴 Trạng thái: Chưa kết nối", font=("Segoe UI", 9, "bold"), fg="#E53E3E", bg="#EDF2F7")
        self.status_label.pack(side=tk.LEFT)

        # Chat Area
        chat_frame = tk.Frame(self.root, bg="#F7FAFC", padx=10, pady=4)
        chat_frame.pack(fill=tk.BOTH, expand=True)

        self.chat_area = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, font=("Segoe UI", 10), state=tk.DISABLED, bg="#FFFFFF", fg="#2D3748")
        self.chat_area.pack(fill=tk.BOTH, expand=True)

        self.chat_area.tag_config("me", foreground="#2B6CB0", font=("Segoe UI", 10, "bold"))
        self.chat_area.tag_config("server", foreground="#2C7A7B", font=("Segoe UI", 10, "bold"))
        self.chat_area.tag_config("system", foreground="#D69E2E", font=("Segoe UI", 9, "italic"))
        self.chat_area.tag_config("error", foreground="#E53E3E", font=("Segoe UI", 9, "bold"))

        # Quick Commands Frame & File Launch
        quick_frame = tk.Frame(self.root, bg="#F7FAFC", padx=10, pady=2)
        quick_frame.pack(fill=tk.X)

        tk.Label(quick_frame, text="Lệnh nhanh:", font=("Segoe UI", 9, "bold"), fg="#4A5568", bg="#F7FAFC").pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(quick_frame, text="⏱️ /time", font=("Segoe UI", 8, "bold"), bg="#EDF2F7", fg="#2D3748", command=lambda: self.send_quick("/time")).pack(side=tk.LEFT, padx=3)
        tk.Button(quick_frame, text="👤 /whoami", font=("Segoe UI", 8, "bold"), bg="#EDF2F7", fg="#2D3748", command=lambda: self.send_quick("/whoami")).pack(side=tk.LEFT, padx=3)
        tk.Button(quick_frame, text="🚪 /quit", font=("Segoe UI", 8, "bold"), bg="#FED7D7", fg="#9B2C2C", command=lambda: self.send_quick("/quit")).pack(side=tk.LEFT, padx=3)
        
        tk.Button(quick_frame, text="📁 Mở GUI Truyền Tệp (Bài 2)", font=("Segoe UI", 8, "bold"), bg="#E6FFFA", fg="#234E52", command=self.open_file_gui).pack(side=tk.RIGHT, padx=3)

        # Input Frame
        input_frame = tk.Frame(self.root, bg="#F7FAFC", padx=10, pady=8)
        input_frame.pack(fill=tk.X)

        self.msg_entry = tk.Entry(input_frame, font=("Segoe UI", 10), bg="#FFFFFF")
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.msg_entry.bind("<Return>", lambda e: self.send_message())

        self.btn_send = tk.Button(input_frame, text="GỬI TIN NHẮN 📤", font=("Segoe UI", 9, "bold"), bg="#2B6CB0", fg="#FFFFFF", activebackground="#2C5282", activeforeground="#FFFFFF", command=self.send_message, state=tk.DISABLED)
        self.btn_send.pack(side=tk.RIGHT)

    def set_localhost(self):
        self.ip_entry.delete(0, tk.END)
        self.ip_entry.insert(0, "127.0.0.1")
        if not self.is_connected:
            self.connect(auto_retry=False)

    def open_file_gui(self):
        import subprocess
        ip = self.ip_entry.get().strip() or "127.0.0.1"
        try:
            subprocess.Popen([sys.executable, "02_file_transfer/gui_client.py", ip])
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không thể mở GUI Truyền Tệp: {exc}")

    def log(self, text: str, tag: str = "normal"):
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.insert(tk.END, text + "\n", tag)
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)

    def toggle_connection(self):
        if not self.is_connected:
            self.connect(auto_retry=False)
        else:
            self.disconnect()

    def connect(self, auto_retry: bool = False, retry_count: int = 0):
        if self.is_connected:
            return
        ip = self.ip_entry.get().strip() or "127.0.0.1"
        try:
            port = int(self.port_entry.get().strip() or str(PORT))
        except ValueError:
            messagebox.showerror("Lỗi", "Cổng (Port) phải là số nguyên.")
            return

        username = self.user_entry.get().strip()
        if not username:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập Username (REQ-1).")
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(2.0)
            self.sock.connect((ip, port))
            self.sock.settimeout(None)

            # REQ-1 Handshake
            self.sock.sendall((username + "\n").encode(ENCODING))

            self.is_connected = True
            self.btn_connect.config(text="❌ NGẮT KẾT NỐI", bg="#CBD5E0", fg="#2D3748", activebackground="#E2E8F0")
            self.btn_send.config(state=tk.NORMAL)
            self.status_label.config(text=f"🟢 Đã kết nối tới Máy B (Server {ip}:{port}) - User: {username}", fg="#38A169")
            self.log(f"[HỆ THỐNG] Đã kết nối thành công tới Server Máy B ({ip}:{port})", "system")

            self.recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
            self.recv_thread.start()

        except Exception as exc:
            self.sock = None
            if auto_retry and retry_count < 2:
                self.status_label.config(text=f"⏳ Đang chờ Server Máy B mở cổng {port}... (thử lại sau 1s)", fg="#D69E2E")
                self.root.after(1200, lambda: self.connect(auto_retry=True, retry_count=retry_count + 1))
            else:
                self.status_label.config(text=f"🔴 Chưa kết nối {ip}:{port}. Bấm '⚡ Localhost' hoặc '🔌 KẾT NỐI' để kết nối!", fg="#E53E3E")

    def disconnect(self):
        self.is_connected = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

        self.btn_connect.config(text="🔌 KẾT NỐI", bg="#2B6CB0", fg="#FFFFFF", activebackground="#2C5282")
        self.btn_send.config(state=tk.DISABLED)
        self.status_label.config(text="🔴 Trạng thái: Chưa kết nối", fg="#E53E3E")
        self.log("[HỆ THỐNG] Đã ngắt kết nối.", "system")

    def send_message(self):
        if not self.is_connected or not self.sock:
            messagebox.showinfo("Thông báo", "Chưa kết nối tới Máy B (Server). Bấm '⚡ Localhost' để kết nối.")
            return

        msg = self.msg_entry.get().strip()
        if not msg:
            messagebox.showwarning("Cảnh báo", "Không được gửi tin nhắn rỗng (REQ-4).")
            return

        try:
            self.sock.sendall((msg + "\n").encode(ENCODING))
            self.log(f"Máy A ({self.user_entry.get().strip()}) > {msg}", "me")
            self.msg_entry.delete(0, tk.END)

            if msg.lower() == "/quit":
                self.root.after(500, self.disconnect)

        except Exception as exc:
            self.log(f"[LỖI GỬI] {exc}", "error")
            self.disconnect()

    def send_quick(self, cmd: str):
        if not self.is_connected:
            messagebox.showinfo("Thông báo", "Vui lòng kết nối tới Máy B (Server) trước.")
            return
        self.msg_entry.delete(0, tk.END)
        self.msg_entry.insert(0, cmd)
        self.send_message()

    def _recv_loop(self):
        data = bytearray()
        while self.is_connected and self.sock:
            try:
                chunk = self.sock.recv(1)
                if not chunk:
                    self.root.after(0, lambda: self.log("[HỆ THỐNG] Máy B (Server) đã đóng kết nối.", "system"))
                    self.root.after(0, self.disconnect)
                    break

                if chunk == b"\n":
                    line = data.decode(ENCODING).rstrip("\r")
                    data.clear()
                    self.root.after(0, lambda l=line: self.log(f"{l}", "server"))
                else:
                    data.extend(chunk)

            except Exception:
                if self.is_connected:
                    self.root.after(0, lambda: self.log("[LỖI MẠNG] Mất kết nối tới Máy B.", "error"))
                    self.root.after(0, self.disconnect)
                break


def main():
    root = tk.Tk()
    app = ChatClientGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
