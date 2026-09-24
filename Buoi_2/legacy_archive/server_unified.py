"""Giao diện Máy B (Server) Hợp nhất Toàn bộ: Lắng nghe đồng thời Cổng 5000 (Chat 1:1), Cổng 5001 (Truyền file), và Cổng 5002 (Group Chat nhiều máy)."""

import os
import socket
import sys
import threading
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HOST = "0.0.0.0"
CHAT_PORT = 5000
FILE_PORT = 5001
GROUP_PORT = 5002
ENCODING = "utf-8"
BUFFER_SIZE = 64 * 1024
SAVE_DIR = Path(__file__).resolve().parent / "02_file_transfer" / "received_files"


class UnifiedServerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🖥️ MÁY B: SERVER SOCKET TCP HOÀN CHỈNH (CỔNG 5000, 5001, 5002)")
        self.root.geometry("820x680")
        self.root.minsize(720, 540)

        self.chat_server_sock: socket.socket | None = None
        self.file_server_sock: socket.socket | None = None
        self.group_server_sock: socket.socket | None = None

        self.client_chat_sock: socket.socket | None = None
        self.client_chat_addr: tuple[str, int] | None = None
        self.client_chat_user: str = "Client"

        # Group chat active clients mapping: sock -> username
        self.group_clients: dict[socket.socket, str] = {}
        self.group_clients_lock = threading.Lock()
        self.group_send_lock = threading.Lock()

        self.is_running = False

        SAVE_DIR.mkdir(parents=True, exist_ok=True)

        # Checkbox selection variables for selective port listening
        self.enable_chat_var = tk.BooleanVar(value=True)
        self.enable_file_var = tk.BooleanVar(value=True)
        self.enable_group_var = tk.BooleanVar(value=False)

        self._build_ui()
        self.refresh_files_list()
        # Auto start selected services on launch
        self.root.after(400, lambda: self.start_server(is_manual=False))

    def _build_ui(self):
        # Header Banner
        header = tk.Frame(self.root, bg="#1A365D", padx=14, pady=10)
        header.pack(fill=tk.X)

        tk.Label(header, text="🖥️ MÁY B: SERVER NHẬN DỮ LIỆU (TÙY CHỌN DỊCH VỤ)", font=("Segoe UI", 13, "bold"), fg="#FFFFFF", bg="#1A365D").pack(anchor=tk.W)
        tk.Label(header, text="Tự chọn bật/tắt dịch vụ cần lắng nghe: Chat 1:1 (5000), Nhận Tệp (5001), Group Chat (5002)", font=("Segoe UI", 9), fg="#E2E8F0", bg="#1A365D").pack(anchor=tk.W, pady=(2, 0))

        # Config & Selection Bar
        cfg_frame = tk.Frame(self.root, bg="#F7FAFC", padx=10, pady=8)
        cfg_frame.pack(fill=tk.X)

        tk.Label(cfg_frame, text="Host:", font=("Segoe UI", 9, "bold"), bg="#F7FAFC").grid(row=0, column=0, sticky=tk.W)
        self.host_entry = tk.Entry(cfg_frame, font=("Segoe UI", 9), width=8)
        self.host_entry.insert(0, HOST)
        self.host_entry.grid(row=0, column=1, padx=2)

        # Checkboxes for selecting which servers to run
        chk_chat = tk.Checkbutton(cfg_frame, text="Chat 1:1 (5000)", variable=self.enable_chat_var, font=("Segoe UI", 9, "bold"), fg="#2B6CB0", bg="#F7FAFC", activebackground="#F7FAFC")
        chk_chat.grid(row=0, column=2, padx=4)

        chk_file = tk.Checkbutton(cfg_frame, text="Nhận File (5001)", variable=self.enable_file_var, font=("Segoe UI", 9, "bold"), fg="#2C7A7B", bg="#F7FAFC", activebackground="#F7FAFC")
        chk_file.grid(row=0, column=3, padx=4)

        chk_group = tk.Checkbutton(cfg_frame, text="Group Chat (5002)", variable=self.enable_group_var, font=("Segoe UI", 9, "bold"), fg="#805AD5", bg="#F7FAFC", activebackground="#F7FAFC")
        chk_group.grid(row=0, column=4, padx=4)

        self.btn_toggle = tk.Button(cfg_frame, text="🚀 BẮT ĐẦU DỊCH VỤ ĐÃ CHỌN", font=("Segoe UI", 9, "bold"), bg="#38A169", fg="#FFFFFF", activebackground="#2F855A", activeforeground="#FFFFFF", padx=8, command=self.toggle_server)
        self.btn_toggle.grid(row=0, column=5, padx=8)

        self.btn_open_folder = tk.Button(cfg_frame, text="📁 Thư mục File", font=("Segoe UI", 9, "bold"), bg="#EDF2F7", fg="#2D3748", command=self.open_received_folder)
        self.btn_open_folder.grid(row=0, column=6, padx=2)

        # Status Bar
        status_frame = tk.Frame(self.root, bg="#EDF2F7", padx=10, pady=5, bd=1, relief=tk.SOLID)
        status_frame.pack(fill=tk.X, padx=10, pady=4)

        self.status_label = tk.Label(status_frame, text="🔴 Server Máy B đã dừng", font=("Segoe UI", 9, "bold"), fg="#E53E3E", bg="#EDF2F7")
        self.status_label.pack(side=tk.LEFT)

        self.client_info_label = tk.Label(status_frame, text="Chưa có Máy A kết nối.", font=("Segoe UI", 9, "italic"), fg="#4A5568", bg="#EDF2F7")
        self.client_info_label.pack(side=tk.RIGHT)

        # Notebook Tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        # Tab 1: Chat 1:1
        tab_chat = tk.Frame(notebook, bg="#F7FAFC", padx=8, pady=8)
        notebook.add(tab_chat, text=" 💬 Chat 1:1 (Port 5000) ")

        self.chat_log_area = scrolledtext.ScrolledText(tab_chat, wrap=tk.WORD, font=("Segoe UI", 10), state=tk.DISABLED, bg="#FFFFFF", fg="#2D3748")
        self.chat_log_area.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.chat_log_area.tag_config("server", foreground="#2B6CB0", font=("Segoe UI", 10, "bold"))
        self.chat_log_area.tag_config("client", foreground="#2C7A7B", font=("Segoe UI", 10, "bold"))
        self.chat_log_area.tag_config("auto", foreground="#805AD5", font=("Segoe UI", 9, "italic"))
        self.chat_log_area.tag_config("system", foreground="#D69E2E", font=("Segoe UI", 9, "bold"))

        reply_frame = tk.Frame(tab_chat, bg="#F7FAFC")
        reply_frame.pack(fill=tk.X)

        tk.Label(reply_frame, text="Máy B (Server) > ", font=("Segoe UI", 9, "bold"), bg="#F7FAFC").pack(side=tk.LEFT)
        self.reply_entry = tk.Entry(reply_frame, font=("Segoe UI", 10), bg="#FFFFFF")
        self.reply_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self.reply_entry.bind("<Return>", lambda e: self.send_operator_reply())

        self.btn_send_reply = tk.Button(reply_frame, text="GỬI PHẢN HỒI 📤", font=("Segoe UI", 9, "bold"), bg="#2B6CB0", fg="#FFFFFF", activebackground="#2C5282", activeforeground="#FFFFFF", command=self.send_operator_reply, state=tk.DISABLED)
        self.btn_send_reply.pack(side=tk.RIGHT)

        # Tab 2: File Transfer
        tab_files = tk.Frame(notebook, bg="#F7FAFC", padx=8, pady=8)
        notebook.add(tab_files, text=" 📥 Nhận Tệp (Port 5001) ")

        files_frame = tk.LabelFrame(tab_files, text=" Tệp Nhận Từ Máy A (Lưu tại received_files) ", font=("Segoe UI", 9, "bold"), fg="#2C7A7B", bg="#F7FAFC", padx=6, pady=6)
        files_frame.pack(fill=tk.X, pady=(0, 6))

        self.files_tree = ttk.Treeview(files_frame, columns=("name", "size", "time"), show="headings", height=5)
        self.files_tree.heading("name", text="Tên Tệp Đã Nhận")
        self.files_tree.heading("size", text="Dung Lượng")
        self.files_tree.heading("time", text="Thời Gian Lưu")
        self.files_tree.column("name", width=300)
        self.files_tree.column("size", width=140, anchor=tk.E)
        self.files_tree.column("time", width=200, anchor=tk.CENTER)
        self.files_tree.pack(fill=tk.BOTH, expand=True)

        tk.Label(tab_files, text="Nhật ký tiến trình nhận file (Port 5001):", font=("Segoe UI", 9, "bold"), fg="#2B6CB0", bg="#F7FAFC").pack(anchor=tk.W, pady=(4, 2))

        self.file_log_area = scrolledtext.ScrolledText(tab_files, wrap=tk.WORD, font=("Segoe UI", 9), state=tk.DISABLED, bg="#FFFFFF", fg="#2D3748")
        self.file_log_area.pack(fill=tk.BOTH, expand=True)

        self.file_log_area.tag_config("info", foreground="#2B6CB0")
        self.file_log_area.tag_config("success", foreground="#38A169", font=("Segoe UI", 9, "bold"))
        self.file_log_area.tag_config("error", foreground="#E53E3E", font=("Segoe UI", 9, "bold"))
        self.file_log_area.tag_config("system", foreground="#D69E2E", font=("Segoe UI", 9, "bold"))

        # Tab 3: Group Chat (Port 5002)
        tab_group = tk.Frame(notebook, bg="#F7FAFC", padx=8, pady=8)
        notebook.add(tab_group, text=" 👥 Group Chat (Port 5002) ")

        grp_top_frame = tk.Frame(tab_group, bg="#F7FAFC")
        grp_top_frame.pack(fill=tk.BOTH, expand=True)

        # Left: Group Chat Logs
        left_grp = tk.Frame(grp_top_frame, bg="#F7FAFC")
        left_grp.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

        tk.Label(left_grp, text="Nhật ký Phòng Chat Nhóm (Port 5002):", font=("Segoe UI", 9, "bold"), fg="#805AD5", bg="#F7FAFC").pack(anchor=tk.W, pady=(0, 4))

        self.group_log_area = scrolledtext.ScrolledText(left_grp, wrap=tk.WORD, font=("Segoe UI", 9), state=tk.DISABLED, bg="#FFFFFF", fg="#2D3748")
        self.group_log_area.pack(fill=tk.BOTH, expand=True)

        self.group_log_area.tag_config("join", foreground="#38A169", font=("Segoe UI", 9, "bold"))
        self.group_log_area.tag_config("leave", foreground="#E53E3E", font=("Segoe UI", 9, "bold"))
        self.group_log_area.tag_config("msg", foreground="#2B6CB0")
        self.group_log_area.tag_config("private", foreground="#D69E2E", font=("Segoe UI", 9, "bold"))
        self.group_log_area.tag_config("system", foreground="#805AD5", font=("Segoe UI", 9, "bold"))

        # Right: Active Group Members List
        right_grp = tk.Frame(grp_top_frame, bg="#F7FAFC", width=180)
        right_grp.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0))
        right_grp.pack_propagate(False)

        tk.Label(right_grp, text="Thành viên Online:", font=("Segoe UI", 9, "bold"), fg="#2D3748", bg="#F7FAFC").pack(anchor=tk.W, pady=(0, 4))

        self.member_listbox = tk.Listbox(right_grp, font=("Segoe UI", 9), bg="#FFFFFF", fg="#2D3748")
        self.member_listbox.pack(fill=tk.BOTH, expand=True)

    def log_chat(self, text: str, tag: str = "normal"):
        self.chat_log_area.config(state=tk.NORMAL)
        self.chat_log_area.insert(tk.END, text + "\n", tag)
        self.chat_log_area.see(tk.END)
        self.chat_log_area.config(state=tk.DISABLED)

    def log_file(self, text: str, tag: str = "normal"):
        self.file_log_area.config(state=tk.NORMAL)
        self.file_log_area.insert(tk.END, text + "\n", tag)
        self.file_log_area.see(tk.END)
        self.file_log_area.config(state=tk.DISABLED)

    def log_group(self, text: str, tag: str = "normal"):
        self.group_log_area.config(state=tk.NORMAL)
        self.group_log_area.insert(tk.END, text + "\n", tag)
        self.group_log_area.see(tk.END)
        self.group_log_area.config(state=tk.DISABLED)

    def refresh_group_members(self):
        self.member_listbox.delete(0, tk.END)
        with self.group_clients_lock:
            for user in sorted(self.group_clients.values()):
                self.member_listbox.insert(tk.END, f"👤 {user}")

    def refresh_files_list(self):
        for item in self.files_tree.get_children():
            self.files_tree.delete(item)

        if SAVE_DIR.exists():
            for p in sorted(SAVE_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if p.is_file():
                    size_bytes = p.stat().st_size
                    mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    self.files_tree.insert("", tk.END, values=(p.name, f"{size_bytes:,} B", mtime))

    def open_received_folder(self):
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(SAVE_DIR)
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không thể mở thư mục: {exc}")

    def toggle_server(self):
        if not self.is_running:
            self.start_server(is_manual=True)
        else:
            self.stop_server()

    def start_server(self, is_manual: bool = False):
        if self.is_running:
            return
        host = self.host_entry.get().strip() or HOST
        c_port = CHAT_PORT
        f_port = FILE_PORT
        g_port = GROUP_PORT

        do_chat = self.enable_chat_var.get()
        do_file = self.enable_file_var.get()
        do_group = self.enable_group_var.get()

        if not (do_chat or do_file or do_group):
            if is_manual:
                messagebox.showwarning("Cảnh báo", "Vui lòng tích chọn ít nhất 1 dịch vụ (Chat 1:1, Nhận File, hoặc Group Chat) để lắng nghe.")
            return

        active_services = []

        try:
            # Bind Chat 1:1 Port if checked
            if do_chat:
                self.chat_server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if sys.platform != "win32":
                    self.chat_server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.chat_server_sock.bind((host, c_port))
                self.chat_server_sock.listen(5)
                threading.Thread(target=self._chat_accept_loop, daemon=True).start()
                active_services.append(f"Chat 1:1({c_port})")
                self.log_chat(f"[SERVER MÁY B] Bắt đầu dịch vụ Chat 1:1 trên Cổng {c_port}", "system")

            # Bind File Transfer Port if checked
            if do_file:
                self.file_server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if sys.platform != "win32":
                    self.file_server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.file_server_sock.bind((host, f_port))
                self.file_server_sock.listen(5)
                threading.Thread(target=self._file_accept_loop, daemon=True).start()
                active_services.append(f"File({f_port})")
                self.log_file(f"[FILE SERVER MÁY B] Bắt đầu dịch vụ Nhận Tệp trên Cổng {f_port}", "system")

            # Bind Group Chat Port if checked
            if do_group:
                self.group_server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if sys.platform != "win32":
                    self.group_server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.group_server_sock.bind((host, g_port))
                self.group_server_sock.listen(20)
                threading.Thread(target=self._group_accept_loop, daemon=True).start()
                active_services.append(f"Group({g_port})")
                self.log_group(f"[GROUP SERVER MÁY B] Bắt đầu dịch vụ Phòng Chat Nhóm trên Cổng {g_port}", "system")

            self.is_running = True
            self.btn_toggle.config(text="🛑 DỪNG MÁY B", bg="#E53E3E", fg="#FFFFFF", activebackground="#C53030")
            serv_str = ", ".join(active_services)
            self.status_label.config(text=f"🟢 Đang lắng nghe: {serv_str}", fg="#38A169")

        except Exception as exc:
            self.stop_server()
            if is_manual:
                messagebox.showerror("Lỗi Server Máy B", f"Không thể lắng nghe các cổng đã chọn.\n\nCổng có thể đang bị ứng dụng khác chiếm giữ!\n\nLỗi: {exc}")
            else:
                self.status_label.config(text="🟡 Cổng đã chọn đang được Server khác sử dụng!", fg="#D69E2E")
                self.log_chat(f"[THÔNG BÁO] Cổng đang có Server khác chạy. Bấm 'Bắt đầu' khi muốn thử lại.", "system")

    def stop_server(self):
        self.is_running = False
        if self.client_chat_sock:
            try:
                self.client_chat_sock.close()
            except Exception:
                pass
            self.client_chat_sock = None

        if self.chat_server_sock:
            try:
                self.chat_server_sock.close()
            except Exception:
                pass
            self.chat_server_sock = None

        if self.file_server_sock:
            try:
                self.file_server_sock.close()
            except Exception:
                pass
            self.file_server_sock = None

        if self.group_server_sock:
            try:
                self.group_server_sock.close()
            except Exception:
                pass
            self.group_server_sock = None

        self.btn_toggle.config(text="🚀 BẮT ĐẦU MÁY B (START ALL)", bg="#38A169", fg="#FFFFFF", activebackground="#2F855A")
        self.btn_send_reply.config(state=tk.DISABLED)
        self.status_label.config(text="🔴 Server Máy B đã dừng", fg="#E53E3E")
        self.client_info_label.config(text="Chưa có Máy A kết nối.", fg="#4A5568")
        self.log_chat("[SERVER MÁY B] Đã dừng các dịch vụ.", "system")

    # ----- Chat TCP (Port 5000) Loop -----
    def _chat_accept_loop(self):
        while self.is_running and self.chat_server_sock:
            try:
                client_s, client_a = self.chat_server_sock.accept()
                if not self.is_running:
                    break

                self.client_chat_sock = client_s
                self.client_chat_addr = client_a

                # Handshake
                username_line = self._recv_line(self.client_chat_sock)
                if not username_line:
                    self.client_chat_sock.close()
                    continue

                self.client_chat_user = username_line.strip()
                ip, port = self.client_chat_addr[0], self.client_chat_addr[1]

                self.root.after(0, lambda u=self.client_chat_user, i=ip, p=port: self._on_client_connected(u, i, p))
                self._send_line(self.client_chat_sock, f"Xin chào {self.client_chat_user}! Kết nối Máy B (Server) thành công. Gõ /time, /whoami, hoặc /quit.")

                self._handle_chat_messages()

            except Exception:
                if self.is_running:
                    break

    def _on_client_connected(self, user: str, ip: str, port: int):
        self.client_info_label.config(text=f"🟢 Máy A kết nối: {user} ({ip}:{port})", fg="#2B6CB0", font=("Segoe UI", 9, "bold"))
        self.log_chat(f"[SERVER MÁY B] Máy A ({user}) từ {ip}:{port} đã kết nối Chat 1:1", "system")
        self.btn_send_reply.config(state=tk.NORMAL)

    def _handle_chat_messages(self):
        while self.is_running and self.client_chat_sock:
            msg = self._recv_line(self.client_chat_sock)
            if msg is None:
                user = self.client_chat_user
                self.root.after(0, lambda u=user: self._on_client_disconnected(u))
                break

            text = msg.strip()
            if not text:
                continue

            if text.lower() == "/quit":
                self._send_line(self.client_chat_sock, "Tạm biệt!")
                user = self.client_chat_user
                self.root.after(0, lambda u=user: self.log_chat(f"[SERVER MÁY B] Máy A ({u}) đã ngắt kết nối (/quit).", "system"))
                break

            elif text.lower() == "/time":
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                reply = f"[Hệ thống] Thời gian hiện tại của Máy B: {now_str}"
                self._send_line(self.client_chat_sock, reply)
                self.root.after(0, lambda u=self.client_chat_user, t=now_str: self.log_chat(f"[Auto-Reply /time] Gửi {t} tới Máy A ({u})", "auto"))

            elif text.lower() == "/whoami":
                ip, pr = self.client_chat_addr[0], self.client_chat_addr[1]
                reply = f"[Hệ thống] IP Máy A: {ip}, Source Port: {pr}"
                self._send_line(self.client_chat_sock, reply)
                self.root.after(0, lambda u=self.client_chat_user, i=ip, p=pr: self.log_chat(f"[Auto-Reply /whoami] Gửi {i}:{p} tới Máy A ({u})", "auto"))

            else:
                user = self.client_chat_user
                self.root.after(0, lambda u=user, t=text: self.log_chat(f"Máy A ({u}) > {t}", "client"))

        if self.client_chat_sock:
            try:
                self.client_chat_sock.close()
            except Exception:
                pass
            self.client_chat_sock = None

    def _on_client_disconnected(self, user: str):
        self.client_info_label.config(text="Chưa có Máy A kết nối.", fg="#4A5568", font=("Segoe UI", 9, "italic"))
        self.log_chat(f"[SERVER MÁY B] Máy A ({user}) đã ngắt kết nối Chat 1:1.", "system")
        self.btn_send_reply.config(state=tk.DISABLED)

    def send_operator_reply(self):
        if not self.client_chat_sock:
            messagebox.showinfo("Thông báo", "Chưa có Máy A (Client) kết nối.")
            return

        reply = self.reply_entry.get().strip()
        if not reply:
            messagebox.showwarning("Cảnh báo", "Không gửi tin nhắn rỗng.")
            return

        try:
            self._send_line(self.client_chat_sock, reply)
            self.log_chat(f"Máy B (Server) > {reply}", "server")
            self.reply_entry.delete(0, tk.END)
        except Exception as exc:
            self.log_chat(f"[LỖI GỬI] {exc}", "system")

    # ----- File TCP (Port 5001) Loop -----
    def _file_accept_loop(self):
        while self.is_running and self.file_server_sock:
            try:
                client_s, client_a = self.file_server_sock.accept()
                if not self.is_running:
                    break

                with client_s:
                    self._handle_client_file(client_s, client_a)

            except Exception:
                if self.is_running:
                    break

    def _handle_client_file(self, client_sock: socket.socket, client_addr: tuple[str, int]):
        header = self._recv_line(client_sock)
        if header is None:
            return

        try:
            filename, size_text = header.rsplit("|", 1)
            size = int(size_text)
            if size < 0:
                raise ValueError
        except Exception as exc:
            err_msg = f"ERROR|Header không đúng định dạng ({exc})\n"
            client_sock.sendall(err_msg.encode(ENCODING))
            return

        out_path = self._choose_output_path(filename)
        ip, port = client_addr[0], client_addr[1]
        self.root.after(0, lambda f=filename, s=size, i=ip, pr=port: self.log_file(f"[BƯỚC 1 HEADER] Nhận '{f}' ({s:,} bytes) từ Máy A ({i}:{pr})", "info"))

        try:
            received = 0
            remaining = size
            client_sock.settimeout(10.0)
            with out_path.open("wb") as f_out:
                while remaining > 0:
                    chunk = client_sock.recv(min(BUFFER_SIZE, remaining))
                    if not chunk:
                        raise ConnectionError("Máy A ngắt kết nối dở dang.")
                    f_out.write(chunk)
                    received += len(chunk)
                    remaining -= len(chunk)

            self.root.after(0, lambda p=out_path.name, r=received: self.log_file(f"[BƯỚC 2 ĐÃ LƯU] Thành công: {p} ({r:,} bytes)", "success"))

            ok_line = f"OK|{out_path.name}|{received}\n"
            client_sock.sendall(ok_line.encode(ENCODING))
            self.root.after(0, lambda o=ok_line.strip(): self.log_file(f"[BƯỚC 3 XÁC NHẬN] Trả về '{o}' cho Máy A", "success"))
            self.root.after(0, self.refresh_files_list)

        except Exception as exc:
            if out_path.exists():
                out_path.unlink(missing_ok=True)
            err_line = f"ERROR|{exc}\n"
            try:
                client_sock.sendall(err_line.encode(ENCODING))
            except Exception:
                pass
            self.root.after(0, lambda e=exc: self.log_file(f"[LỖI XỬ LÝ FILE] {e}", "error"))

    def _choose_output_path(self, filename: str) -> Path:
        safe_name = Path(filename).name or "received_file"
        output = SAVE_DIR / safe_name
        if not output.exists():
            return output

        stem = output.stem
        suffix = output.suffix
        counter = 1
        while True:
            candidate = SAVE_DIR / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    # ----- Group Chat TCP (Port 5002) Loop -----
    def _group_accept_loop(self):
        while self.is_running and self.group_server_sock:
            try:
                client_sock, client_addr = self.group_server_sock.accept()
                if not self.is_running:
                    break

                threading.Thread(target=self._handle_group_client, args=(client_sock, client_addr), daemon=True).start()
            except Exception:
                if self.is_running:
                    break

    def _handle_group_client(self, client_sock: socket.socket, client_addr: tuple[str, int]):
        username: str | None = None
        try:
            self._send_line(client_sock, "NAME?")
            proposed = self._recv_line(client_sock)
            if proposed is None:
                return

            username = proposed.strip()
            if not username or len(username) > 20 or "|" in username:
                self._send_line(client_sock, "ERROR|Tên phải từ 1-20 ký tự và không chứa '|'.")
                return

            with self.group_clients_lock:
                if any(u.casefold() == username.casefold() for u in self.group_clients.values()):
                    self._send_line(client_sock, "ERROR|Tên này đã được sử dụng trong phòng.")
                    return
                self.group_clients[client_sock] = username

            self.root.after(0, self.refresh_group_members)
            self._send_line(client_sock, f"OK|Chào mừng {username} vào phòng Group Chat (Port 5002)!")
            
            ip, port = client_addr[0], client_addr[1]
            now_ts = datetime.now().strftime("%H:%M:%S")
            self.root.after(0, lambda u=username, i=ip, pr=port: self.log_group(f"[{now_ts}] [JOIN] Thành viên '{u}' từ {i}:{pr} đã vào phòng.", "join"))
            self._group_broadcast(f"[{now_ts}] [HỆ THỐNG] '{username}' đã tham gia phòng chat.", exclude=client_sock)

            # Group Message Loop
            while self.is_running:
                msg = self._recv_line(client_sock)
                if msg is None:
                    break

                text = msg.strip()
                if not text:
                    continue

                if text.lower() == "/quit":
                    break

                ts = datetime.now().strftime("%H:%M:%S")

                # REQ-1: /who
                if text.lower() == "/who":
                    with self.group_clients_lock:
                        online_users = list(self.group_clients.values())
                    users_str = ", ".join(online_users)
                    self._send_line(client_sock, f"[{ts}] [HỆ THỐNG /who] Danh sách online ({len(online_users)}): {users_str}")
                    continue

                # REQ-2: /msg <user> <text>
                if text.lower().startswith("/msg "):
                    parts = text.split(" ", 2)
                    if len(parts) >= 3:
                        target_name = parts[1].strip()
                        priv_text = parts[2].strip()

                        target_sock = None
                        with self.group_clients_lock:
                            for s, u in self.group_clients.items():
                                if u.casefold() == target_name.casefold():
                                    target_sock = s
                                    break

                        if target_sock:
                            self._send_line(target_sock, f"[{ts}] [RIÊNG TỪ {username}] {priv_text}")
                            self._send_line(client_sock, f"[{ts}] [GỬI RIÊNG TỚI {target_name}] {priv_text}")
                            self.root.after(0, lambda u=username, t=target_name, p=priv_text: self.log_group(f"[{ts}] [PRIVATE] {u} -> {t}: {p}", "private"))
                        else:
                            self._send_line(client_sock, f"[{ts}] [LỖI] Không tìm thấy thành viên '{target_name}'.")
                    else:
                        self._send_line(client_sock, f"[{ts}] [LỖI] Cú pháp /msg: /msg <username> <nội dung>")
                    continue

                # REQ-3: /rename <ten_moi>
                if text.lower().startswith("/rename "):
                    parts = text.split(" ", 1)
                    if len(parts) == 2:
                        new_name = parts[1].strip()
                        if not new_name or len(new_name) > 20 or "|" in new_name:
                            self._send_line(client_sock, f"[{ts}] [LỖI] Tên mới không hợp lệ.")
                        else:
                            with self.group_clients_lock:
                                if any(u.casefold() == new_name.casefold() for u in self.group_clients.values()):
                                    self._send_line(client_sock, f"[{ts}] [LỖI] Tên '{new_name}' đã được dùng.")
                                else:
                                    old_name = self.group_clients[client_sock]
                                    self.group_clients[client_sock] = new_name
                                    self._send_line(client_sock, f"[{ts}] [HỆ THỐNG] Đổi tên thành công thành '{new_name}'.")
                                    self._group_broadcast(f"[{ts}] [HỆ THỐNG] '{old_name}' đã đổi tên thành '{new_name}'.")
                                    self.root.after(0, self.refresh_group_members)
                    continue

                # REQ-4: Normal Broadcast with Timestamp
                formatted_msg = f"[{ts}] [{username}] {text}"
                self.root.after(0, lambda m=formatted_msg: self.log_group(m, "msg"))
                self._group_broadcast(formatted_msg, exclude=client_sock)

        except Exception as exc:
            pass
        finally:
            self._remove_group_client(client_sock, username)

    def _group_broadcast(self, text: str, exclude: socket.socket | None = None):
        with self.group_clients_lock:
            targets = [sock for sock in self.group_clients if sock is not exclude]

        dead: list[socket.socket] = []
        with self.group_send_lock:
            for sock in targets:
                try:
                    self._send_line(sock, text)
                except Exception:
                    dead.append(sock)

        for sock in dead:
            self._remove_group_client(sock)

    def _remove_group_client(self, sock: socket.socket, username: str | None = None):
        with self.group_clients_lock:
            user = username or self.group_clients.pop(sock, None)
            if sock in self.group_clients:
                del self.group_clients[sock]

        try:
            sock.close()
        except Exception:
            pass

        if user:
            ts = datetime.now().strftime("%H:%M:%S")
            self.root.after(0, lambda u=user: self.log_group(f"[{ts}] [LEAVE] '{u}' đã rời phòng Group Chat.", "leave"))
            self.root.after(0, self.refresh_group_members)
            self._group_broadcast(f"[{ts}] [HỆ THỐNG] '{user}' đã rời phòng.")

    # ----- Helpers -----
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
    app = UnifiedServerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
