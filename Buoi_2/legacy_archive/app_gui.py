"""DNU Socket Lab - Ứng dụng Messenger Tích hợp (Unified Messenger GUI App).

Tích hợp Bài 1 (Chat TCP 1:1) và Bài 2 (File Transfer) trên cùng 1 kênh Messenger trực quan, hỗ trợ gửi cả Tin Nhắn Text và Tệp Dữ Liệu (File) như Messenger / Zalo / Telegram.
"""

import os
import sys
import socket
import threading
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
CHAT_PORT = 5000
ENCODING = "utf-8"
BUFFER_SIZE = 64 * 1024
SAVE_DIR = BASE_DIR / "02_file_transfer" / "received_files"


class UnifiedMessengerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("DNU Socket Lab - Messenger TCP (Text & File Transfer)")
        self.root.geometry("880x680")
        self.root.minsize(780, 580)

        # Server state
        self.server_sock: socket.socket | None = None
        self.srv_client_sock: socket.socket | None = None
        self.server_running = False

        # Client state
        self.client_sock: socket.socket | None = None
        self.client_connected = False

        SAVE_DIR.mkdir(parents=True, exist_ok=True)

        self._build_ui()

        # Auto start server and auto connect client locally
        self.root.after(300, self.start_server)
        self.root.after(800, self.connect_client)

    def _build_ui(self):
        # Header Banner
        header = tk.Frame(self.root, bg="#1A365D", padx=12, pady=10)
        header.pack(fill=tk.X)

        tk.Label(header, text="🌐 BẢNG ĐIỀU KHIỂN MESSENGER TCP (TEXT & FILE TRANSFER)", font=("Segoe UI", 14, "bold"), fg="#FFFFFF", bg="#1A365D").pack(anchor=tk.W)
        tk.Label(header, text="Đại học Nam Cần Thơ • Tích hợp Chat Văn Bản (Text) & Gửi Tệp (File Transfer) trên cùng 1 Cửa Sổ Messenger", font=("Segoe UI", 9), fg="#CBD5E0", bg="#1A365D").pack(anchor=tk.W, pady=(2, 0))

        # Tab Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Tab 1: Messenger Unified (Chat & File)
        self.tab_chat = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_chat, text=" 💬 KÊNH MESSENGER (TEXT & FILE TRANSFER) ")
        self._build_messenger_tab()

        # Tab 2: Báo Cáo PDF
        self.tab_report = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_report, text=" 📑 BÁO CÁO PDF & KIỂM THỬ ")
        self._build_report_tab()

    # =========================================================================
    # TAB 1: UNIFIED MESSENGER (TEXT & FILE)
    # =========================================================================
    def _build_messenger_tab(self):
        paned = ttk.PanedWindow(self.tab_chat, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # --- LEFT PANEL: SERVER CONTROL (MÁY A) ---
        srv_frame = ttk.LabelFrame(paned, text=" 🖥️ MÁY A: SERVER (CỔNG 5000) ", padding=8)
        paned.add(srv_frame, weight=1)

        srv_top = tk.Frame(srv_frame, bg="#EDF2F7", bd=1, relief=tk.SOLID, padx=6, pady=4)
        srv_top.pack(fill=tk.X, pady=(0, 6))

        self.srv_status_lbl = tk.Label(srv_top, text="🔴 Server: Đang dừng", font=("Segoe UI", 9, "bold"), fg="#E53E3E", bg="#EDF2F7")
        self.srv_status_lbl.pack(side=tk.LEFT)

        btn_toggle_srv = tk.Button(srv_top, text="Bật/Tắt Server", font=("Segoe UI", 8, "bold"), bg="#CBD5E0", fg="#2D3748", command=self.toggle_server)
        btn_toggle_srv.pack(side=tk.RIGHT)

        tk.Label(srv_frame, text="Log Server & Tệp Đã Nhận:", font=("Segoe UI", 9, "bold"), fg="#2B6CB0").pack(anchor=tk.W, pady=(2, 2))

        self.srv_log_area = scrolledtext.ScrolledText(srv_frame, wrap=tk.WORD, font=("Segoe UI", 9), state=tk.DISABLED, bg="#FFFFFF", fg="#2D3748")
        self.srv_log_area.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        btn_open_dir = tk.Button(srv_frame, text="📁 Mở thư mục received_files", font=("Segoe UI", 9, "bold"), bg="#EDF2F7", fg="#2D3748", command=self.open_received_folder)
        btn_open_dir.pack(fill=tk.X)

        # --- RIGHT PANEL: CLIENT MESSENGER INTERFACE (MÁY B) ---
        cli_frame = ttk.LabelFrame(paned, text=" 💬 MÁY B: CLIENT MESSENGER INTERFACE ", padding=8)
        paned.add(cli_frame, weight=1)

        cli_top = tk.Frame(cli_frame, bg="#EBF8FF", bd=1, relief=tk.SOLID, padx=6, pady=6)
        cli_top.pack(fill=tk.X, pady=(0, 6))

        tk.Label(cli_top, text="IP Server:", font=("Segoe UI", 9, "bold"), bg="#EBF8FF").grid(row=0, column=0, sticky=tk.W)
        self.cli_ip_entry = tk.Entry(cli_top, font=("Segoe UI", 9), width=11)
        self.cli_ip_entry.insert(0, "127.0.0.1")
        self.cli_ip_entry.grid(row=0, column=1, padx=2)

        tk.Label(cli_top, text="Tên:", font=("Segoe UI", 9, "bold"), bg="#EBF8FF").grid(row=0, column=2, sticky=tk.W, padx=(4, 0))
        self.cli_user_entry = tk.Entry(cli_top, font=("Segoe UI", 9), width=8)
        self.cli_user_entry.insert(0, "Nam")
        self.cli_user_entry.grid(row=0, column=3, padx=2)

        self.btn_connect_cli = tk.Button(cli_top, text="Kết Nối", font=("Segoe UI", 8, "bold"), bg="#2B6CB0", fg="#FFFFFF", command=self.toggle_client)
        self.btn_connect_cli.grid(row=0, column=4, padx=4)

        self.cli_status_lbl = tk.Label(cli_top, text="🔴 Chưa kết nối", font=("Segoe UI", 9, "bold"), fg="#E53E3E", bg="#EBF8FF")

        self.cli_status_lbl.grid(row=0, column=5, padx=4)

        # Quick command buttons
        quick_frame = tk.Frame(cli_frame, bg="#F7FAFC")
        quick_frame.pack(fill=tk.X, pady=(0, 4))

        tk.Label(quick_frame, text="Lệnh nhanh:", font=("Segoe UI", 8, "bold"), fg="#4A5568").pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(quick_frame, text="⏱️ /time", font=("Segoe UI", 8, "bold"), bg="#EDF2F7", fg="#2D3748", command=lambda: self.send_text_msg("/time")).pack(side=tk.LEFT, padx=2)
        tk.Button(quick_frame, text="👤 /whoami", font=("Segoe UI", 8, "bold"), bg="#EDF2F7", fg="#2D3748", command=lambda: self.send_text_msg("/whoami")).pack(side=tk.LEFT, padx=2)
        tk.Button(quick_frame, text="🚪 /quit", font=("Segoe UI", 8, "bold"), bg="#FED7D7", fg="#9B2C2C", command=lambda: self.send_text_msg("/quit")).pack(side=tk.LEFT, padx=2)

        # Chat & File Messages Area
        self.cli_chat_area = scrolledtext.ScrolledText(cli_frame, wrap=tk.WORD, font=("Segoe UI", 10), state=tk.DISABLED, bg="#FFFFFF", fg="#2D3748")
        self.cli_chat_area.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.cli_chat_area.tag_config("me", foreground="#2B6CB0", font=("Segoe UI", 10, "bold"))
        self.cli_chat_area.tag_config("server", foreground="#2C7A7B", font=("Segoe UI", 10, "bold"))
        self.cli_chat_area.tag_config("file", foreground="#D69E2E", font=("Segoe UI", 10, "bold"))
        self.cli_chat_area.tag_config("system", foreground="#718096", font=("Segoe UI", 9, "italic"))

        # Input & File Attach Toolbar
        input_frame = tk.Frame(cli_frame)
        input_frame.pack(fill=tk.X)

        self.btn_attach_file = tk.Button(input_frame, text="📎 GỬI TỆP", font=("Segoe UI", 9, "bold"), bg="#2C7A7B", fg="#FFFFFF", command=self.send_file_msg)
        self.btn_attach_file.pack(side=tk.LEFT, padx=(0, 4))

        self.cli_msg_entry = tk.Entry(input_frame, font=("Segoe UI", 10), bg="#FFFFFF")
        self.cli_msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.cli_msg_entry.bind("<Return>", lambda e: self.send_text_msg())

        self.btn_send_msg = tk.Button(input_frame, text="GỬI 📤", font=("Segoe UI", 9, "bold"), bg="#2B6CB0", fg="#FFFFFF", command=self.send_text_msg)
        self.btn_send_msg.pack(side=tk.RIGHT)

    def log_srv(self, text: str):
        self.srv_log_area.config(state=tk.NORMAL)
        self.srv_log_area.insert(tk.END, text + "\n")
        self.srv_log_area.see(tk.END)
        self.srv_log_area.config(state=tk.DISABLED)

    def log_cli(self, text: str, tag: str = "normal"):
        self.cli_chat_area.config(state=tk.NORMAL)
        self.cli_chat_area.insert(tk.END, text + "\n", tag)
        self.cli_chat_area.see(tk.END)
        self.cli_chat_area.config(state=tk.DISABLED)

    def open_received_folder(self):
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(SAVE_DIR)
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không thể mở thư mục: {exc}")

    # --- SERVER LOGIC ---
    def toggle_server(self):
        if not self.server_running:
            self.start_server()
        else:
            self.stop_server()

    def start_server(self):
        if self.server_running:
            return
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind(("0.0.0.0", CHAT_PORT))
            self.server_sock.listen(5)

            self.server_running = True
            self.srv_status_lbl.config(text="🟢 Server Messenger: Cổng 5000", fg="#38A169")
            self.log_srv("[SERVER] Đã khởi động Server Messenger tại 0.0.0.0:5000.")

            threading.Thread(target=self._server_accept_loop, daemon=True).start()
        except Exception as exc:
            self.srv_status_lbl.config(text=f"🔴 Server lỗi: {exc}", fg="#E53E3E")

    def stop_server(self):
        self.server_running = False
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
            self.server_sock = None
        self.srv_status_lbl.config(text="🔴 Server Messenger: Đang dừng", fg="#E53E3E")
        self.log_srv("[SERVER] Đã dừng server.")

    def _server_accept_loop(self):
        while self.server_running and self.server_sock:
            try:
                client_sock, client_addr = self.server_sock.accept()
                self.srv_client_sock = client_sock

                # Handshake
                header = self._recv_line(client_sock)
                if not header:
                    client_sock.close()
                    continue

                user = header.split("|", 1)[1].strip() if header.startswith("USER|") else header.strip()
                ip, port = client_addr[0], client_addr[1]
                self.root.after(0, lambda u=user, i=ip, p=port: self.log_srv(f"[SERVER] {u} từ {i}:{p} đã kết nối"))

                self._send_line(client_sock, f"Xin chào {user}! Đã kết nối Messenger. Gõ tin nhắn, gửi tệp hoặc dùng /time, /whoami, /quit.")

                # Loop
                while self.server_running and self.srv_client_sock:
                    h = self._recv_line(client_sock)
                    if h is None:
                        self.root.after(0, lambda u=user: self.log_srv(f"[SERVER] Client {u} đã ngắt kết nối."))
                        break

                    line = h.strip()
                    if not line:
                        continue

                    if line.startswith("FILE|"):
                        _, fn, sz_str = line.split("|", 2)
                        sz = int(sz_str)
                        out_p = SAVE_DIR / Path(fn).name

                        rec = 0
                        rem = sz
                        with out_p.open("wb") as f_out:
                            while rem > 0:
                                chunk = client_sock.recv(min(BUFFER_SIZE, rem))
                                if not chunk:
                                    break
                                f_out.write(chunk)
                                rec += len(chunk)
                                rem -= len(chunk)

                        ok_m = f"OK_FILE|{out_p.name}|{rec}"
                        self._send_line(client_sock, ok_m)
                        self.root.after(0, lambda u=user, p=out_p.name, r=rec: self.log_srv(f"📎 ✅ NHẬN TỆP: {p} ({r:,} bytes) từ {u}"))
                    else:
                        text = line.split("|", 1)[1] if line.startswith("TEXT|") else line

                        if text.lower() == "/quit":
                            self._send_line(client_sock, "Tạm biệt!")
                            self.root.after(0, lambda u=user: self.log_srv(f"[SERVER] Client {u} đã thoát (/quit)."))
                            break
                        elif text.lower() == "/time":
                            now_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            self._send_line(client_sock, f"[Hệ thống] Thời gian hiện tại của server: {now_s}")
                            self.root.after(0, lambda u=user, t=now_s: self.log_srv(f"[Auto-Reply /time] Đã gửi {t} tới {u}"))
                        elif text.lower() == "/whoami":
                            self._send_line(client_sock, f"[Hệ thống] Địa chỉ IP: {ip}, Source Port: {port}")
                            self.root.after(0, lambda u=user, i=ip, pr=port: self.log_srv(f"[Auto-Reply /whoami] Đã gửi {i}:{pr} tới {u}"))
                        else:
                            self.root.after(0, lambda u=user, t=text: self.log_srv(f"{u} > {t}"))

            except Exception:
                break

    # --- CLIENT LOGIC ---
    def toggle_client(self):
        if not self.client_connected:
            self.connect_client()
        else:
            self.disconnect_client()

    def connect_client(self):
        if self.client_connected:
            return
        ip = self.cli_ip_entry.get().strip() or "127.0.0.1"
        username = self.cli_user_entry.get().strip() or "Nam"

        try:
            self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_sock.connect((ip, CHAT_PORT))

            # Handshake
            self.client_sock.sendall(f"USER|{username}\n".encode(ENCODING))

            self.client_connected = True
            self.cli_status_lbl.config(text=f"🟢 Đã kết nối (User: {username})", fg="#38A169")
            self.btn_connect_cli.config(text="Ngắt Kết Nối", bg="#CBD5E0", fg="#2D3748")
            self.log_cli(f"[HỆ THỐNG] Đã kết nối tới Messenger Server ({ip}:{CHAT_PORT})", "system")

            threading.Thread(target=self._client_recv_loop, daemon=True).start()
        except Exception as exc:
            self.cli_status_lbl.config(text=f"🔴 Lỗi kết nối {ip}", fg="#E53E3E")

    def disconnect_client(self):
        self.client_connected = False
        if self.client_sock:
            try:
                self.client_sock.close()
            except Exception:
                pass
            self.client_sock = None
        self.cli_status_lbl.config(text="🔴 Chưa kết nối", fg="#E53E3E")
        self.btn_connect_cli.config(text="Kết Nối", bg="#2B6CB0", fg="#FFFFFF")
        self.log_cli("[HỆ THỐNG] Đã ngắt kết nối.", "system")

    def send_text_msg(self, preset: str = ""):
        if not self.client_connected or not self.client_sock:
            messagebox.showinfo("Thông báo", "Chưa kết nối tới Server Messenger.")
            return

        text = preset if preset else self.cli_msg_entry.get().strip()
        if not text:
            messagebox.showwarning("Cảnh báo", "Không được gửi tin nhắn rỗng (REQ-4).")
            return

        try:
            self.client_sock.sendall(f"TEXT|{text}\n".encode(ENCODING))
            self.log_cli(f"Bạn > {text}", "me")
            if not preset:
                self.cli_msg_entry.delete(0, tk.END)

            if text.lower() == "/quit":
                self.root.after(500, self.disconnect_client)
        except Exception as exc:
            self.log_cli(f"[LỖI GỬI] {exc}", "system")
            self.disconnect_client()

    def send_file_msg(self):
        if not self.client_connected or not self.client_sock:
            messagebox.showinfo("Thông báo", "Chưa kết nối tới Server Messenger.")
            return

        path_str = filedialog.askopenfilename(title="Chọn tệp đính kèm gửi trong Chat Messenger")
        if not path_str:
            return

        file_path = Path(path_str)
        file_size = file_path.stat().st_size

        def worker():
            try:
                header = f"FILE|{file_path.name}|{file_size}\n"
                self.client_sock.sendall(header.encode(ENCODING))

                sent = 0
                with file_path.open("rb") as f_in:
                    while True:
                        chunk = f_in.read(BUFFER_SIZE)
                        if not chunk:
                            break
                        self.client_sock.sendall(chunk)
                        sent += len(chunk)

                self.root.after(0, lambda: self.log_cli(f"📎 Bạn đã gửi tệp: '{file_path.name}' ({file_size:,} bytes)", "file"))
            except Exception as exc:
                self.root.after(0, lambda e=exc: self.log_cli(f"[LỖI GỬI TỆP] {e}", "system"))

        threading.Thread(target=worker, daemon=True).start()

    def _client_recv_loop(self):
        while self.client_connected and self.client_sock:
            line = self._recv_line(self.client_sock)
            if line is None:
                self.root.after(0, lambda: self.log_cli("[HỆ THỐNG] Server đã đóng kết nối.", "system"))
                self.root.after(0, self.disconnect_client)
                break
            self.root.after(0, lambda l=line: self.log_cli(f"{l}", "server"))

    # =========================================================================
    # TAB 2: BÁO CÁO PDF
    # =========================================================================
    def _build_report_tab(self):
        frame = ttk.Frame(self.tab_report, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="📄 BÁO CÁO DỰ ÁN & HƯỚNG DẪN THỰC THI", font=("Segoe UI", 13, "bold"), fg="#1A365D").pack(anchor=tk.W, pady=(0, 10))

        btn_pdf = tk.Button(frame, text="📄 MỞ BÁO CÁO PDF CHI TIẾT (Bao_Cao_Lab_Socket_TCP.pdf)", font=("Segoe UI", 11, "bold"), bg="#6B46C1", fg="#FFFFFF", padx=16, pady=8, command=self.open_pdf)
        btn_pdf.pack(fill=tk.X, pady=8)

        desc_text = (
            "📌 ĐẶC TẢ GIAO THỨC MESSENGER TÍCH HỢP (TEXT & FILE TRANSFER):\n\n"
            "• KÊNH TRUYỀN DỮ LIỆU ĐỒNG THỜI (PORT 5000):\n"
            "  - Gửi Tin Nhắn Text: HEADER dạng TEXT|<nội_dung>\\n.\n"
            "  - Gửi Tệp Nhị Phân: HEADER dạng FILE|<ten_file>|<kich_thuoc_bytes>\\n + payload byte stream.\n"
            "  - REQ-1 (Username Handshake): Gửi USER|<username>\\n ngay sau khi mở kết nối.\n"
            "  - REQ-2 (/time): Phản hồi tự động thời gian hệ thống của Server.\n"
            "  - REQ-3 (/whoami): Phản hồi tự động địa chỉ IP và Source Port của Client.\n"
            "  - REQ-4 (Tính Ổn Định): Ngăn gửi tin rỗng, bắt lỗi ngắt kết nối đột ngột.\n"
            "  - Tệp nhận được tự động lưu vào thư mục received_files/."
        )

        st = scrolledtext.ScrolledText(frame, font=("Segoe UI", 10), bg="#EDF2F7", fg="#2D3748", bd=1, relief=tk.SOLID)
        st.insert(tk.END, desc_text)
        st.config(state=tk.DISABLED)
        st.pack(fill=tk.BOTH, expand=True, pady=8)

    def open_pdf(self):
        pdf_path = BASE_DIR / "Bao_Cao_Lab_Socket_TCP.pdf"
        if not pdf_path.is_file():
            try:
                import generate_pdf_report
                pdf_path = generate_pdf_report.create_report()
            except Exception as exc:
                messagebox.showerror("Lỗi", f"Không tạo được file PDF: {exc}")
                return
        try:
            os.startfile(pdf_path)
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không mở được file PDF: {exc}")

    # =========================================================================
    # UTILS
    # =========================================================================
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
    app = UnifiedMessengerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
