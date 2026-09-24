"""DNU Socket TCP Lab - Messenger & Zalo Style Unified Chat & File Transfer App.

Ứng dụng Hợp nhất chuẩn phong cách Messenger / Zalo:
- 1 Khung Chat duy nhất gửi cả Văn bản (Text) và Tệp tin (File).
- 1 Cổng TCP duy nhất (Port 5000).
- Loại bỏ bảng điều khiển và các tab dư thừa.
"""

import json
import os
import socket
import sys
import threading
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Constants
DEFAULT_HOST = "0.0.0.0"
DEFAULT_CONNECT_IP = "127.0.0.1"
PORT = 5000
ENCODING = "utf-8"
BUFFER_SIZE = 64 * 1024
BASE_DIR = Path(__file__).resolve().parent
SAVE_DIR = BASE_DIR / "02_file_transfer" / "received_files"
SAVE_DIR.mkdir(parents=True, exist_ok=True)


class ZaloMessengerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("💬 Zalo / Messenger Socket TCP - Gửi Text & File")
        self.root.geometry("860x680")
        self.root.minsize(720, 560)

        # State variables
        self.role = tk.StringVar(value="CLIENT")  # "SERVER" (Máy B) or "CLIENT" (Máy A)
        self.is_connected = False
        self.is_server_running = False

        self.server_sock: socket.socket | None = None
        self.active_sock: socket.socket | None = None

        # Lock for socket send ops
        self.send_lock = threading.Lock()

        # Build GUI
        self._setup_styles()
        self._build_ui()

        # Auto select role based on standard start
        self._on_role_changed()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Custom colors
        self.bg_main = "#F0F2F5"
        self.bg_header = "#0068FF"  # Zalo / Messenger Blue
        self.bg_card = "#FFFFFF"
        self.fg_text = "#1C1E21"

        self.root.configure(bg=self.bg_main)

    def _build_ui(self):
        # ---------------- 1. TOP HEADER (Zalo / Messenger Blue) ----------------
        header = tk.Frame(self.root, bg=self.bg_header, padx=16, pady=12)
        header.pack(fill=tk.X)

        title_frame = tk.Frame(header, bg=self.bg_header)
        title_frame.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(
            title_frame,
            text="💬 ZALO & MESSENGER SOCKET TCP",
            font=("Segoe UI", 13, "bold"),
            fg="#FFFFFF",
            bg=self.bg_header,
        ).pack(anchor=tk.W)
        tk.Label(
            title_frame,
            text="Trò chuyện & Truyền file trực tiếp qua 1 Cổng (Port 5000)",
            font=("Segoe UI", 9),
            fg="#EBF4FF",
            bg=self.bg_header,
        ).pack(anchor=tk.W, pady=(2, 0))

        # Role Selector Pill (Máy B - Server / Máy A - Client)
        role_frame = tk.Frame(header, bg=self.bg_header)
        role_frame.pack(side=tk.RIGHT)

        tk.Label(
            role_frame,
            text="Vai trò thiết bị:",
            font=("Segoe UI", 9, "bold"),
            fg="#FFFFFF",
            bg=self.bg_header,
        ).pack(side=tk.LEFT, padx=(0, 6))

        rb_server = tk.Radiobutton(
            role_frame,
            text="🖥️ MÁY B (Server Nhận)",
            value="SERVER",
            variable=self.role,
            font=("Segoe UI", 9, "bold"),
            fg="#FFFFFF",
            bg=self.bg_header,
            activebackground=self.bg_header,
            selectcolor="#0046B8",
            command=self._on_role_changed,
        )
        rb_server.pack(side=tk.LEFT, padx=4)

        rb_client = tk.Radiobutton(
            role_frame,
            text="💬 MÁY A (Client Gửi)",
            value="CLIENT",
            variable=self.role,
            font=("Segoe UI", 9, "bold"),
            fg="#FFFFFF",
            bg=self.bg_header,
            activebackground=self.bg_header,
            selectcolor="#0046B8",
            command=self._on_role_changed,
        )
        rb_client.pack(side=tk.LEFT, padx=4)

        # ---------------- 2. CONNECTION CONTROL BAR ----------------
        cfg_bar = tk.Frame(self.root, bg="#FFFFFF", padx=14, pady=8, bd=1, relief=tk.SOLID)
        cfg_bar.pack(fill=tk.X, padx=10, pady=(8, 4))

        self.lbl_ip_prompt = tk.Label(cfg_bar, text="IPv4 Server (Máy B):", font=("Segoe UI", 9, "bold"), bg="#FFFFFF")
        self.lbl_ip_prompt.pack(side=tk.LEFT, padx=(0, 4))

        self.ip_entry = tk.Entry(cfg_bar, font=("Segoe UI", 9), width=14, bd=1, relief=tk.SOLID)
        self.ip_entry.insert(0, DEFAULT_CONNECT_IP)
        self.ip_entry.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_localhost = tk.Button(
            cfg_bar,
            text="⚡ Localhost",
            font=("Segoe UI", 8, "bold"),
            bg="#EBF4FF",
            fg="#0068FF",
            bd=0,
            padx=6,
            pady=2,
            command=self._set_localhost,
        )
        self.btn_localhost.pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(cfg_bar, text="Tên đại diện:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(side=tk.LEFT, padx=(6, 4))
        self.user_entry = tk.Entry(cfg_bar, font=("Segoe UI", 9), width=10, bd=1, relief=tk.SOLID)
        self.user_entry.insert(0, "Máy A")
        self.user_entry.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_action = tk.Button(
            cfg_bar,
            text="🔌 KẾT NỐI TỚI MÁY B",
            font=("Segoe UI", 9, "bold"),
            bg="#0068FF",
            fg="#FFFFFF",
            activebackground="#0052CC",
            activeforeground="#FFFFFF",
            bd=0,
            padx=12,
            pady=4,
            command=self.toggle_action,
        )
        self.btn_action.pack(side=tk.LEFT)

        self.btn_open_folder = tk.Button(
            cfg_bar,
            text="📁 Thư mục File",
            font=("Segoe UI", 9, "bold"),
            bg="#F0F2F5",
            fg="#1C1E21",
            bd=0,
            padx=8,
            pady=4,
            command=self.open_received_folder,
        )
        self.btn_open_folder.pack(side=tk.RIGHT)

        # Status Line
        status_bar = tk.Frame(self.root, bg=self.bg_main, padx=12, pady=2)
        status_bar.pack(fill=tk.X)

        self.status_label = tk.Label(
            status_bar,
            text="🔴 Chưa kết nối. Bấm 'KẾT NỐI TỚI MÁY B' hoặc 'BẮT ĐẦU MÁY B'",
            font=("Segoe UI", 9, "bold"),
            fg="#E53E3E",
            bg=self.bg_main,
        )
        self.status_label.pack(side=tk.LEFT)

        # ---------------- 3. SINGLE CHAT FEED (MESSENGER / ZALO STYLE) ----------------
        chat_card = tk.Frame(self.root, bg="#FFFFFF", bd=1, relief=tk.SOLID, padx=1, pady=1)
        chat_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        self.chat_feed = ScrolledText(
            chat_card,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            bg="#FFFFFF",
            fg="#1C1E21",
            state=tk.DISABLED,
            bd=0,
            padx=12,
            pady=10,
        )
        self.chat_feed.pack(fill=tk.BOTH, expand=True)

        # Configure tags for Messenger style bubbles
        self.chat_feed.tag_config("system", foreground="#65676B", font=("Segoe UI", 9, "italic"), justify=tk.CENTER)
        self.chat_feed.tag_config("me_tag", foreground="#0068FF", font=("Segoe UI", 10, "bold"), justify=tk.RIGHT)
        self.chat_feed.tag_config("me_msg", foreground="#000000", font=("Segoe UI", 10), justify=tk.RIGHT, rmargin=10)
        self.chat_feed.tag_config("other_tag", foreground="#2E7D32", font=("Segoe UI", 10, "bold"), justify=tk.LEFT)
        self.chat_feed.tag_config("other_msg", foreground="#000000", font=("Segoe UI", 10), justify=tk.LEFT, lmargin1=10)
        self.chat_feed.tag_config("file_card", foreground="#1565C0", font=("Segoe UI", 9, "bold"))
        self.chat_feed.tag_config("time_lbl", foreground="#8D949E", font=("Segoe UI", 8), justify=tk.CENTER)

        # ---------------- 4. BOTTOM INPUT BAR (ATTACH FILE & TEXT INPUT) ----------------
        input_bar = tk.Frame(self.root, bg="#FFFFFF", padx=10, pady=8, bd=1, relief=tk.SOLID)
        input_bar.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Attach File Button (📎)
        self.btn_attach = tk.Button(
            input_bar,
            text="📎 ĐÍNH KÈM FILE",
            font=("Segoe UI", 9, "bold"),
            bg="#EBF4FF",
            fg="#0068FF",
            activebackground="#D0E2FF",
            bd=0,
            padx=10,
            pady=6,
            command=self.send_file_action,
        )
        self.btn_attach.pack(side=tk.LEFT, padx=(0, 6))

        # Text Message Entry Box
        self.msg_entry = tk.Entry(input_bar, font=("Segoe UI", 10), bg="#F0F2F5", fg="#1C1E21", bd=0, highlightthickness=1, highlightcolor="#0068FF")
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6), ipady=6)
        self.msg_entry.bind("<Return>", lambda e: self.send_text_message())

        # Send Button (📤)
        self.btn_send = tk.Button(
            input_bar,
            text="GỬI TEXT 📤",
            font=("Segoe UI", 9, "bold"),
            bg="#0068FF",
            fg="#FFFFFF",
            activebackground="#0052CC",
            activeforeground="#FFFFFF",
            bd=0,
            padx=14,
            pady=6,
            command=self.send_text_message,
        )
        self.btn_send.pack(side=tk.RIGHT)

    # ---------------- UI STATE HANDLERS ----------------
    def _on_role_changed(self):
        role = self.role.get()
        if role == "SERVER":
            self.lbl_ip_prompt.config(text="Host Lắng nghe:")
            self.ip_entry.delete(0, tk.END)
            self.ip_entry.insert(0, DEFAULT_HOST)
            self.user_entry.delete(0, tk.END)
            self.user_entry.insert(0, "Máy B (Server)")
            self.btn_action.config(text="🚀 BẮT ĐẦU MÁY B (SERVER)", bg="#2E7D32", activebackground="#1B5E20")
            self.status_label.config(text="🔴 Máy B (Server) chưa chạy. Bấm 'BẮT ĐẦU MÁY B'", fg="#E53E3E")
        else:
            self.lbl_ip_prompt.config(text="IPv4 Server (Máy B):")
            self.ip_entry.delete(0, tk.END)
            self.ip_entry.insert(0, DEFAULT_CONNECT_IP)
            self.user_entry.delete(0, tk.END)
            self.user_entry.insert(0, "Máy A (Client)")
            self.btn_action.config(text="🔌 KẾT NỐI TỚI MÁY B", bg="#0068FF", activebackground="#0052CC")
            self.status_label.config(text="🔴 Chưa kết nối. Bấm 'KẾT NỐI TỚI MÁY B'", fg="#E53E3E")

    def _set_localhost(self):
        if self.role.get() == "CLIENT":
            self.ip_entry.delete(0, tk.END)
            self.ip_entry.insert(0, "127.0.0.1")

    def open_received_folder(self):
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(SAVE_DIR)
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không thể mở thư mục: {exc}")

    def append_system_msg(self, text: str):
        self.chat_feed.config(state=tk.NORMAL)
        ts = datetime.now().strftime("%H:%M:%S")
        self.chat_feed.insert(tk.END, f"\n──────── {ts} ────────\n", "time_lbl")
        self.chat_feed.insert(tk.END, f"{text}\n", "system")
        self.chat_feed.see(tk.END)
        self.chat_feed.config(state=tk.DISABLED)

    def append_chat_msg(self, sender: str, text: str, is_me: bool):
        self.chat_feed.config(state=tk.NORMAL)
        ts = datetime.now().strftime("%H:%M:%S")

        if is_me:
            self.chat_feed.insert(tk.END, f"\n[{ts}] Bạn ({sender}):\n", "me_tag")
            self.chat_feed.insert(tk.END, f"{text}\n", "me_msg")
        else:
            self.chat_feed.insert(tk.END, f"\n[{ts}] {sender}:\n", "other_tag")
            self.chat_feed.insert(tk.END, f"{text}\n", "other_msg")

        self.chat_feed.see(tk.END)
        self.chat_feed.config(state=tk.DISABLED)

    def append_file_msg(self, sender: str, filename: str, file_size: int, is_me: bool, local_path: Path | None = None):
        self.chat_feed.config(state=tk.NORMAL)
        ts = datetime.now().strftime("%H:%M:%S")
        size_str = f"{file_size / 1024:.1f} KB" if file_size >= 1024 else f"{file_size} Bytes"

        tag_hdr = "me_tag" if is_me else "other_tag"
        align = "Bạn" if is_me else sender

        self.chat_feed.insert(tk.END, f"\n[{ts}] {align} đã gửi tệp:\n", tag_hdr)

        # File Card Block
        card_text = f"  📄 [{filename}]  ({size_str})\n"
        self.chat_feed.insert(tk.END, card_text, "file_card")

        if local_path and local_path.exists():
            # Add an inline button to open the file directly
            btn = tk.Button(
                self.chat_feed,
                text=f"📁 Mở file: {filename}",
                font=("Segoe UI", 8, "bold"),
                bg="#EBF4FF",
                fg="#0068FF",
                bd=1,
                padx=6,
                pady=2,
                command=lambda p=local_path: self._open_file(p),
            )
            self.chat_feed.window_create(tk.END, window=btn)
            self.chat_feed.insert(tk.END, "\n")

        self.chat_feed.see(tk.END)
        self.chat_feed.config(state=tk.DISABLED)

    def _open_file(self, path: Path):
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror("Lỗi mở file", f"Không thể mở file {path.name}: {exc}")

    # ---------------- NETWORK ACTION TOGGLES ----------------
    def toggle_action(self):
        if self.role.get() == "SERVER":
            if not self.is_server_running:
                self.start_server()
            else:
                self.stop_server()
        else:
            if not self.is_connected:
                self.connect_client()
            else:
                self.disconnect_client()

    # ---------------- SERVER LOGIC (MÁY B) ----------------
    def start_server(self):
        host = self.ip_entry.get().strip() or DEFAULT_HOST
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if sys.platform != "win32":
                self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind((host, PORT))
            self.server_sock.listen(5)

            self.is_server_running = True
            self.btn_action.config(text="🛑 DỪNG MÁY B (SERVER)", bg="#E53E3E", activebackground="#C53030")
            self.status_label.config(text=f"🟢 Máy B (Server) đang lắng nghe trên {host}:{PORT}", fg="#2E7D32")
            self.append_system_msg(f"🖥️ Máy B (Server) đã bắt đầu dịch vụ trên Cổng {PORT}. Chờ Máy A kết nối...")

            threading.Thread(target=self._server_accept_loop, daemon=True).start()

        except Exception as exc:
            self.is_server_running = False
            messagebox.showerror("Lỗi khởi chạy Máy B", f"Không thể bind Cổng {PORT}: {exc}")

    def stop_server(self):
        self.is_server_running = False
        if self.active_sock:
            try:
                self.active_sock.close()
            except Exception:
                pass
            self.active_sock = None

        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
            self.server_sock = None

        self.btn_action.config(text="🚀 BẮT ĐẦU MÁY B (SERVER)", bg="#2E7D32", activebackground="#1B5E20")
        self.status_label.config(text="🔴 Máy B (Server) đã dừng", fg="#E53E3E")
        self.append_system_msg("🛑 Máy B (Server) đã dừng lắng nghe.")

    def _server_accept_loop(self):
        while self.is_server_running and self.server_sock:
            try:
                client_s, client_a = self.server_sock.accept()
                if not self.is_server_running:
                    break

                self.active_sock = client_s
                ip, port_num = client_a[0], client_a[1]

                self.root.after(0, lambda i=ip, p=port_num: self.status_label.config(text=f"🟢 Máy A đã kết nối từ {i}:{p}", fg="#2E7D32"))
                self.root.after(0, lambda i=ip, p=port_num: self.append_system_msg(f"🟢 Máy A từ {i}:{p} đã kết nối tới Máy B!"))

                # Send welcome protocol packet
                user_name = self.user_entry.get().strip() or "Máy B (Server)"
                welcome_pkt = {"type": "text", "sender": user_name, "content": "Xin chào! Kết nối Máy B thành công. Bạn có thể gửi text hoặc đính kèm tệp nhị phân."}
                self._send_pkt(self.active_sock, welcome_pkt)

                # Handle connection loop
                self._handle_socket_rx(self.active_sock)

            except Exception:
                if self.is_server_running:
                    break

    # ---------------- CLIENT LOGIC (MÁY A) ----------------
    def connect_client(self):
        ip = self.ip_entry.get().strip() or DEFAULT_CONNECT_IP
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            sock.connect((ip, PORT))
            sock.settimeout(None)

            self.active_sock = sock
            self.is_connected = True

            self.btn_action.config(text="❌ NGẮT KẾT NỐI", bg="#65676B", activebackground="#4B4C4F")
            self.status_label.config(text=f"🟢 Đã kết nối Máy B ({ip}:{PORT})", fg="#0068FF")
            self.append_system_msg(f"🟢 Đã kết nối thành công tới Máy B ({ip}:{PORT})!")

            threading.Thread(target=self._handle_socket_rx, args=(self.active_sock,), daemon=True).start()

        except Exception as exc:
            self.active_sock = None
            self.is_connected = False
            self.status_label.config(text=f"🔴 Không thể kết nối {ip}:{PORT}. Hãy chắc chắn Máy B đang chạy!", fg="#E53E3E")
            messagebox.showerror("Lỗi kết nối", f"Không thể kết nối Máy B ({ip}:{PORT}):\n{exc}")

    def disconnect_client(self):
        self.is_connected = False
        if self.active_sock:
            try:
                self.active_sock.close()
            except Exception:
                pass
            self.active_sock = None

        self.btn_action.config(text="🔌 KẾT NỐI TỚI MÁY B", bg="#0068FF", activebackground="#0052CC")
        self.status_label.config(text="🔴 Đã ngắt kết nối", fg="#E53E3E")
        self.append_system_msg("❌ Đã ngắt kết nối tới Máy B.")

    # ---------------- RECV / RX LOOP ----------------
    def _handle_socket_rx(self, sock: socket.socket):
        while True:
            try:
                line = self._readline(sock)
                if not line:
                    break

                pkt = json.loads(line)
                p_type = pkt.get("type")
                sender = pkt.get("sender", "Đối phương")

                if p_type == "text":
                    content = pkt.get("content", "")
                    self.root.after(0, lambda s=sender, c=content: self.append_chat_msg(s, c, is_me=False))

                elif p_type == "file_header":
                    filename = pkt.get("filename", "file_nhan")
                    file_size = int(pkt.get("size", 0))

                    # Receive binary payload directly from stream
                    out_path = SAVE_DIR / Path(filename).name
                    # Handle duplicate names
                    counter = 1
                    stem = out_path.stem
                    suffix = out_path.suffix
                    while out_path.exists():
                        out_path = SAVE_DIR / f"{stem}_{counter}{suffix}"
                        counter += 1

                    received = 0
                    with out_path.open("wb") as f_out:
                        while received < file_size:
                            chunk_len = min(BUFFER_SIZE, file_size - received)
                            chunk = sock.recv(chunk_len)
                            if not chunk:
                                raise ConnectionError("Ngắt kết nối khi đang nhận file.")
                            f_out.write(chunk)
                            received += len(chunk)

                    self.root.after(
                        0,
                        lambda s=sender, fn=out_path.name, sz=file_size, p=out_path: self.append_file_msg(
                            s, fn, sz, is_me=False, local_path=p
                        ),
                    )
                    self.root.after(0, lambda fn=out_path.name: self.append_system_msg(f"✅ Đã nhận và lưu tệp '{fn}' vào received_files!"))

            except Exception:
                break

        self.root.after(0, lambda: self.append_system_msg("⚠️ Kết nối đã kết thúc."))

    # ---------------- SENDING ACTIONS ----------------
    def send_text_message(self):
        if not self.active_sock:
            messagebox.showinfo("Thông báo", "Chưa có kết nối. Hãy kết nối hoặc khởi chạy Máy B trước.")
            return

        text = self.msg_entry.get().strip()
        if not text:
            return

        user_name = self.user_entry.get().strip() or ("Máy A" if self.role.get() == "CLIENT" else "Máy B")
        pkt = {"type": "text", "sender": user_name, "content": text}

        try:
            self._send_pkt(self.active_sock, pkt)
            self.append_chat_msg(user_name, text, is_me=True)
            self.msg_entry.delete(0, tk.END)
        except Exception as exc:
            messagebox.showerror("Lỗi gửi text", f"Không thể gửi: {exc}")

    def send_file_action(self):
        if not self.active_sock:
            messagebox.showinfo("Thông báo", "Chưa có kết nối. Vui lòng kết nối trước khi đính kèm file.")
            return

        file_path = filedialog.askopenfilename(
            title="Chọn tệp đính kèm gửi qua Messenger/Zalo",
            filetypes=[("Tất cả tệp", "*.*"), ("Ảnh JPG/PNG", "*.png;*.jpg;*.jpeg"), ("Văn bản PDF/TXT", "*.txt;*.pdf;*.docx")],
        )
        if not file_path:
            return

        selected = Path(file_path)
        user_name = self.user_entry.get().strip() or ("Máy A" if self.role.get() == "CLIENT" else "Máy B")

        # Disable button during upload
        self.btn_attach.config(state=tk.DISABLED)

        threading.Thread(target=self._send_file_worker, args=(selected, user_name), daemon=True).start()

    def _send_file_worker(self, file_path: Path, user_name: str):
        try:
            file_size = file_path.stat().st_size
            header_pkt = {"type": "file_header", "sender": user_name, "filename": file_path.name, "size": file_size}

            with self.send_lock:
                # Step 1: Send Header JSON
                self._send_pkt(self.active_sock, header_pkt)

                # Step 2: Stream raw bytes
                sent = 0
                with file_path.open("rb") as f_in:
                    while True:
                        chunk = f_in.read(BUFFER_SIZE)
                        if not chunk:
                            break
                        self.active_sock.sendall(chunk)
                        sent += len(chunk)

            self.root.after(
                0,
                lambda s=user_name, fn=file_path.name, sz=file_size, p=file_path: self.append_file_msg(
                    s, fn, sz, is_me=True, local_path=p
                ),
            )
            self.root.after(0, lambda fn=file_path.name: self.append_system_msg(f"📤 Đã gửi tệp '{fn}' thành công!"))

        except Exception as exc:
            self.root.after(0, lambda e=exc: messagebox.showerror("Lỗi gửi file", f"Thất bại: {e}"))
        finally:
            self.root.after(0, lambda: self.btn_attach.config(state=tk.NORMAL))

    # ---------------- PROTOCOL HELPERS ----------------
    def _send_pkt(self, sock: socket.socket, pkt: dict):
        raw = (json.dumps(pkt, ensure_ascii=False) + "\n").encode(ENCODING)
        with self.send_lock:
            sock.sendall(raw)

    def _readline(self, sock: socket.socket) -> str | None:
        buf = bytearray()
        while True:
            try:
                chunk = sock.recv(1)
            except Exception:
                return None
            if not chunk:
                return None if not buf else buf.decode(ENCODING)
            if chunk == b"\n":
                return buf.decode(ENCODING).rstrip("\r")
            buf.extend(chunk)


def main():
    root = tk.Tk()
    app = ZaloMessengerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
