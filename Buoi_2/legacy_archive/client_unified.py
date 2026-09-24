"""Giao diện Máy A (Client) Hợp nhất: Chat 1:1, Truyền File, và Group Chat nhiều máy trong cùng một ứng dụng."""

import socket
import sys
import threading
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CHAT_PORT = 5000
FILE_PORT = 5001
GROUP_PORT = 5002
ENCODING = "utf-8"
BUFFER_SIZE = 64 * 1024


class UnifiedClientGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("💬 MÁY A: CLIENT CHAT & TRUYỀN TỆP & GROUP CHAT (SANG MÁY B)")
        self.root.geometry("760x640")
        self.root.minsize(640, 520)

        self.chat_sock: socket.socket | None = None
        self.is_connected = False
        self.mode = "chat11"  # "chat11" or "group"

        self._build_ui()
        # Auto connect to 127.0.0.1 on launch with retry
        self.root.after(500, lambda: self.connect(auto_retry=True))

    def _build_ui(self):
        # Header Banner
        header = tk.Frame(self.root, bg="#2B6CB0", padx=14, pady=10)
        header.pack(fill=tk.X)

        tk.Label(header, text="💬 MÁY A: CLIENT HOÀN CHỈNH (CHAT 1:1, GỬI FILE & GROUP CHAT)", font=("Segoe UI", 13, "bold"), fg="#FFFFFF", bg="#2B6CB0").pack(anchor=tk.W)
        tk.Label(header, text="Máy A đóng vai trò CLIENT GỬI - Kết nối tới Máy B (Server 5000 / 5001 / 5002)", font=("Segoe UI", 9), fg="#E2E8F0", bg="#2B6CB0").pack(anchor=tk.W, pady=(2, 0))

        # Connection Config Frame
        conn_frame = tk.Frame(self.root, bg="#F7FAFC", padx=10, pady=8)
        conn_frame.pack(fill=tk.X)

        tk.Label(conn_frame, text="IPv4 Server (Máy B):", font=("Segoe UI", 9, "bold"), bg="#F7FAFC").grid(row=0, column=0, sticky=tk.W)
        self.ip_entry = tk.Entry(conn_frame, font=("Segoe UI", 9), width=13)
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.grid(row=0, column=1, padx=2)

        btn_local = tk.Button(conn_frame, text="⚡ Localhost", font=("Segoe UI", 8, "bold"), bg="#EDF2F7", fg="#2D3748", command=self.set_localhost)
        btn_local.grid(row=0, column=2, padx=2)

        tk.Label(conn_frame, text="Chế độ:", font=("Segoe UI", 9, "bold"), bg="#F7FAFC").grid(row=0, column=3, sticky=tk.W, padx=(4, 0))
        self.mode_var = tk.StringVar(value="chat11")
        self.mode_combo = ttk.Combobox(conn_frame, textvariable=self.mode_var, values=["Chat 1:1 (Port 5000)", "Group Chat (Port 5002)"], state="readonly", width=18, font=("Segoe UI", 9))
        self.mode_combo.grid(row=0, column=4, padx=2)
        self.mode_combo.current(0)

        tk.Label(conn_frame, text="User:", font=("Segoe UI", 9, "bold"), bg="#F7FAFC").grid(row=0, column=5, sticky=tk.W, padx=(4, 0))
        self.user_entry = tk.Entry(conn_frame, font=("Segoe UI", 9), width=9)
        self.user_entry.insert(0, "Nam")
        self.user_entry.grid(row=0, column=6, padx=2)

        self.btn_connect = tk.Button(conn_frame, text="🔌 KẾT NỐI", font=("Segoe UI", 9, "bold"), bg="#2B6CB0", fg="#FFFFFF", activebackground="#2C5282", activeforeground="#FFFFFF", padx=6, command=self.toggle_connection)
        self.btn_connect.grid(row=0, column=7, padx=6)

        # Status Bar
        status_frame = tk.Frame(self.root, bg="#EDF2F7", padx=10, pady=5, bd=1, relief=tk.SOLID)
        status_frame.pack(fill=tk.X, padx=10, pady=4)
        self.status_label = tk.Label(status_frame, text="🔴 Trạng thái: Chưa kết nối Máy B", font=("Segoe UI", 9, "bold"), fg="#E53E3E", bg="#EDF2F7")
        self.status_label.pack(side=tk.LEFT)

        # Chat & Event History Window
        chat_frame = tk.Frame(self.root, bg="#F7FAFC", padx=10, pady=4)
        chat_frame.pack(fill=tk.BOTH, expand=True)

        self.chat_area = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, font=("Segoe UI", 10), state=tk.DISABLED, bg="#FFFFFF", fg="#2D3748")
        self.chat_area.pack(fill=tk.BOTH, expand=True)

        self.chat_area.tag_config("me", foreground="#2B6CB0", font=("Segoe UI", 10, "bold"))
        self.chat_area.tag_config("server", foreground="#2C7A7B", font=("Segoe UI", 10, "bold"))
        self.chat_area.tag_config("file", foreground="#38A169", font=("Segoe UI", 10, "bold"))
        self.chat_area.tag_config("private", foreground="#D69E2E", font=("Segoe UI", 10, "bold"))
        self.chat_area.tag_config("system", foreground="#805AD5", font=("Segoe UI", 9, "italic"))
        self.chat_area.tag_config("error", foreground="#E53E3E", font=("Segoe UI", 9, "bold"))

        # Progress bar frame for File Send
        self.progress_frame = tk.Frame(self.root, bg="#F7FAFC", padx=10, pady=2)
        self.progress_frame.pack(fill=tk.X)
        
        self.file_info_label = tk.Label(self.progress_frame, text="Sẵn sàng truyền file...", font=("Segoe UI", 9, "italic"), fg="#718096", bg="#F7FAFC")
        self.file_info_label.pack(side=tk.LEFT, padx=(0, 6))

        self.progress_bar = ttk.Progressbar(self.progress_frame, orient=tk.HORIZONTAL, mode="determinate")
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Quick Commands Toolbar
        quick_frame = tk.Frame(self.root, bg="#F7FAFC", padx=10, pady=2)
        quick_frame.pack(fill=tk.X)

        tk.Label(quick_frame, text="Lệnh nhanh:", font=("Segoe UI", 9, "bold"), fg="#4A5568", bg="#F7FAFC").pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(quick_frame, text="👥 /who (Online)", font=("Segoe UI", 8, "bold"), bg="#EBF8FF", fg="#2B6CB0", command=lambda: self.send_quick("/who")).pack(side=tk.LEFT, padx=3)
        tk.Button(quick_frame, text="⏱️ /time", font=("Segoe UI", 8, "bold"), bg="#EDF2F7", fg="#2D3748", command=lambda: self.send_quick("/time")).pack(side=tk.LEFT, padx=3)
        tk.Button(quick_frame, text="👤 /whoami", font=("Segoe UI", 8, "bold"), bg="#EDF2F7", fg="#2D3748", command=lambda: self.send_quick("/whoami")).pack(side=tk.LEFT, padx=3)
        tk.Button(quick_frame, text="🚪 /quit", font=("Segoe UI", 8, "bold"), bg="#FED7D7", fg="#9B2C2C", command=lambda: self.send_quick("/quit")).pack(side=tk.LEFT, padx=3)

        # Input Frame (Text Chat + Attach File)
        input_frame = tk.Frame(self.root, bg="#F7FAFC", padx=10, pady=8)
        input_frame.pack(fill=tk.X)

        self.btn_attach = tk.Button(input_frame, text="📎 GỬI FILE...", font=("Segoe UI", 9, "bold"), bg="#2C7A7B", fg="#FFFFFF", activebackground="#234E52", activeforeground="#FFFFFF", command=self.send_file_action)
        self.btn_attach.pack(side=tk.LEFT, padx=(0, 6))

        self.msg_entry = tk.Entry(input_frame, font=("Segoe UI", 10), bg="#FFFFFF")
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.msg_entry.bind("<Return>", lambda e: self.send_message())

        self.btn_send = tk.Button(input_frame, text="GỬI TEXT 📤", font=("Segoe UI", 9, "bold"), bg="#2B6CB0", fg="#FFFFFF", activebackground="#2C5282", activeforeground="#FFFFFF", command=self.send_message, state=tk.DISABLED)
        self.btn_send.pack(side=tk.RIGHT)

    def set_localhost(self):
        self.ip_entry.delete(0, tk.END)
        self.ip_entry.insert(0, "127.0.0.1")
        if not self.is_connected:
            self.connect(auto_retry=False)

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
        is_group = "Group" in self.mode_combo.get()
        port = GROUP_PORT if is_group else CHAT_PORT

        username = self.user_entry.get().strip()
        if not username:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập Username.")
            return

        try:
            self.chat_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.chat_sock.settimeout(2.0)
            self.chat_sock.connect((ip, port))
            self.chat_sock.settimeout(None)

            if is_group:
                # Group Chat protocol Handshake: Wait for NAME?, send username, wait for OK/ERROR
                prompt = self._recv_line(self.chat_sock)
                if prompt != "NAME?":
                    raise ConnectionError("Protocol không khớp với Group Server.")
                self.chat_sock.sendall((username + "\n").encode(ENCODING))
                res = self._recv_line(self.chat_sock)
                if not res or res.startswith("ERROR|"):
                    err_msg = res.split("|", 1)[1] if res and "|" in res else "Kết nối thất bại"
                    raise ConnectionError(err_msg)
                mode_str = "Group Chat nhiều máy"
            else:
                # Chat 1:1 Handshake
                self.chat_sock.sendall((username + "\n").encode(ENCODING))
                mode_str = "Chat 1:1"

            self.is_connected = True
            self.btn_connect.config(text="❌ NGẮT KẾT NỐI", bg="#CBD5E0", fg="#2D3748", activebackground="#E2E8F0")
            self.btn_send.config(state=tk.NORMAL)
            self.status_label.config(text=f"🟢 Đã kết nối Máy B ({ip}:{port}) - [{mode_str}] User: {username}", fg="#38A169")
            self.log(f"[HỆ THỐNG] Đã kết nối thành công tới Server Máy B ({ip}:{port}) [{mode_str}]", "system")

            threading.Thread(target=self._recv_chat_loop, daemon=True).start()

        except Exception as exc:
            self.chat_sock = None
            if auto_retry and retry_count < 2:
                self.status_label.config(text=f"⏳ Đang chờ Máy B mở cổng {port}... (thử lại sau 1s)", fg="#D69E2E")
                self.root.after(1200, lambda: self.connect(auto_retry=True, retry_count=retry_count + 1))
            else:
                self.status_label.config(text=f"🔴 Chưa kết nối {ip}:{port}. Bấm '⚡ Localhost' hoặc '🔌 KẾT NỐI'!", fg="#E53E3E")

    def disconnect(self):
        self.is_connected = False
        if self.chat_sock:
            try:
                self.chat_sock.close()
            except Exception:
                pass
            self.chat_sock = None

        self.btn_connect.config(text="🔌 KẾT NỐI", bg="#2B6CB0", fg="#FFFFFF", activebackground="#2C5282")
        self.btn_send.config(state=tk.DISABLED)
        self.status_label.config(text="🔴 Trạng thái: Chưa kết nối", fg="#E53E3E")
        self.log("[HỆ THỐNG] Đã ngắt kết nối.", "system")

    def send_message(self):
        if not self.is_connected or not self.chat_sock:
            messagebox.showinfo("Thông báo", "Chưa kết nối tới Máy B. Bấm '⚡ Localhost' để thử.")
            return

        msg = self.msg_entry.get().strip()
        if not msg:
            messagebox.showwarning("Cảnh báo", "Không được gửi tin nhắn rỗng.")
            return

        try:
            self.chat_sock.sendall((msg + "\n").encode(ENCODING))
            user = self.user_entry.get().strip()
            ts = datetime.now().strftime("%H:%M:%S")

            if msg.startswith("/msg "):
                self.log(f"[{ts}] [GỬI RIÊNG] {msg}", "private")
            else:
                self.log(f"[{ts}] [{user}] {msg}", "me")

            self.msg_entry.delete(0, tk.END)

            if msg.lower() == "/quit":
                self.root.after(500, self.disconnect)

        except Exception as exc:
            self.log(f"[LỖI GỬI] {exc}", "error")
            self.disconnect()

    def send_quick(self, cmd: str):
        if not self.is_connected:
            messagebox.showinfo("Thông báo", "Vui lòng kết nối tới Máy B trước.")
            return
        self.msg_entry.delete(0, tk.END)
        self.msg_entry.insert(0, cmd)
        self.send_message()

    def send_file_action(self):
        file_path = filedialog.askopenfilename(
            title="Chọn tệp nhị phân gửi sang Máy B (Cổng 5001)",
            filetypes=[("Tất cả tệp", "*.*"), ("Ảnh PNG/JPG", "*.png;*.jpg;*.jpeg"), ("Văn bản", "*.txt;*.pdf;*.docx")]
        )
        if not file_path:
            return

        selected = Path(file_path)
        ip = self.ip_entry.get().strip() or "127.0.0.1"
        f_port = FILE_PORT

        self.btn_attach.config(state=tk.DISABLED)
        self.progress_bar["value"] = 0
        self.file_info_label.config(text=f"Đang gửi '{selected.name}' ({selected.stat().st_size:,} bytes)...", fg="#2B6CB0")

        threading.Thread(target=self._send_file_worker, args=(selected, ip, f_port), daemon=True).start()

    def _send_file_worker(self, file_path: Path, ip: str, port: int):
        file_size = file_path.stat().st_size

        try:
            self.root.after(0, lambda: self.log(f"[TRUYỀN FILE MÁY A] Bắt đầu kết nối Cổng File Máy B ({ip}:{port})...", "system"))
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                client.settimeout(10.0)
                client.connect((ip, port))

                # Step 1 Header
                header_line = f"{file_path.name}|{file_size}\n"
                client.sendall(header_line.encode(ENCODING))

                # Step 2 Payload
                sent = 0
                with file_path.open("rb") as f_in:
                    while True:
                        chunk = f_in.read(BUFFER_SIZE)
                        if not chunk:
                            break
                        client.sendall(chunk)
                        sent += len(chunk)
                        progress = (sent / file_size) * 100
                        self.root.after(0, lambda p=progress: self._update_file_progress(p))

                # Step 3 Response
                client.settimeout(10.0)
                response_line = self._recv_line(client)
                if response_line and response_line.startswith("OK|"):
                    self.root.after(0, lambda: self._update_file_progress(100))
                    self.root.after(0, lambda: self.file_info_label.config(text=f"✅ Đã gửi xong '{file_path.name}'!", fg="#38A169"))
                    self.root.after(0, lambda f=file_path.name, s=file_size: self.log(f"📁 Máy A (Đã gửi Tệp) > {f} ({s:,} bytes) - Phản hồi: OK", "file"))
                    self.root.after(0, lambda r=response_line: messagebox.showinfo("Thành công", f"Máy B đã lưu tệp '{file_path.name}' thành công!\n\nPhản hồi: {r}"))
                else:
                    err = response_line or "Không phản hồi"
                    self.root.after(0, lambda e=err: self.log(f"[MÁY B BÁO LỖI FILE] {e}", "error"))
                    self.root.after(0, lambda e=err: messagebox.showerror("Lỗi từ Máy B", f"Thất bại: {e}"))

        except socket.timeout:
            self.root.after(0, lambda: self.log(f"[LỖI QUÁ THỜI GIAN] Máy B ({ip}:{port}) không phản hồi. Hãy chắc chắn Máy B đang chạy!", "error"))
            self.root.after(0, lambda: messagebox.showerror("Lỗi timeout", f"Không kết nối được tới Cổng File {port} trên Máy B ({ip})."))

        except Exception as exc:
            self.root.after(0, lambda e=exc: self.log(f"[LỖI TRUYỀN FILE] {e}", "error"))
            self.root.after(0, lambda e=exc: messagebox.showerror("Lỗi gửi file", f"Lỗi: {e}"))

        finally:
            self.root.after(0, lambda: self.btn_attach.config(state=tk.NORMAL))

    def _update_file_progress(self, val: float):
        self.progress_bar["value"] = val
        self.root.update_idletasks()

    def _recv_chat_loop(self):
        data = bytearray()
        while self.is_connected and self.chat_sock:
            try:
                chunk = self.chat_sock.recv(1)
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
    app = UnifiedClientGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
