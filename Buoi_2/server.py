"""🖥️ MÁY B (SERVER) - Ứng dụng Chat & Gửi File TCP Socket (Cổng 5000).

Máy B đóng vai trò SERVER: Lắng nghe kết nối từ Máy A, nhận/gửi tin nhắn Text và Tệp tin nhị phân.
"""

import json
import os
import socket
import sys
import threading
import winsound
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Project paths
BASE_DIR = Path(__file__).resolve().parent
SAVE_DIR = BASE_DIR / "received_files"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# Connection defaults
HOST = "0.0.0.0"
PORT = 5000
ENCODING = "utf-8"
BUFFER_SIZE = 64 * 1024


def get_local_ip() -> str:
    """Lấy địa chỉ IP LAN của máy tính này."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def play_notify():
    """Phát âm thanh thông báo khi nhận tin nhắn (Windows)."""
    try:
        winsound.MessageBeep(winsound.MB_OK)
    except Exception:
        pass


class Tooltip:
    """Tooltip hiện ra khi di chuột vào widget."""
    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self.tip_window: tk.Toplevel | None = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _event=None):
        if self.tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(
            tw, text=self.text, justify=tk.LEFT,
            background="#FFFBCC", relief=tk.SOLID, borderwidth=1,
            font=("Segoe UI", 8), padx=6, pady=3, wraplength=300,
        )
        lbl.pack()

    def hide(self, _event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class MessengerServerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🖥️ MÁY B (SERVER) - Ứng dụng Chat TCP Socket | Cổng 5000")
        self.root.geometry("860x720")
        self.root.minsize(720, 560)

        self.is_running = False
        self.server_sock: socket.socket | None = None
        self.active_client_sock: socket.socket | None = None
        self.send_lock = threading.Lock()
        self.local_ip = get_local_ip()

        self._build_ui()
        self._show_welcome_guide()
        # Auto-start server on launch
        self.root.after(300, self.start_server)

    # ═══════════════════════════════════════════════════
    # BUILD UI
    # ═══════════════════════════════════════════════════
    def _build_ui(self):
        # ── 1. Header ──────────────────────────────────
        header = tk.Frame(self.root, bg="#0068FF", padx=16, pady=10)
        header.pack(fill=tk.X)

        tk.Label(
            header, text="🖥️  MÁY B  —  SERVER NHẬN TIN & TỆP",
            font=("Segoe UI", 14, "bold"), fg="#FFFFFF", bg="#0068FF",
        ).pack(anchor=tk.W)
        tk.Label(
            header,
            text="Máy B lắng nghe Cổng 5000. Máy A kết nối vào IP bên dưới để nhắn tin và gửi file.",
            font=("Segoe UI", 9), fg="#C8DEFF", bg="#0068FF",
        ).pack(anchor=tk.W, pady=(1, 0))

        # ── 2. Info Bar (IP + Port) ────────────────────
        info_bar = tk.Frame(self.root, bg="#EBF4FF", padx=12, pady=6)
        info_bar.pack(fill=tk.X)

        tk.Label(info_bar, text="📡 IP Máy B (dùng để Máy A kết nối):",
                 font=("Segoe UI", 9, "bold"), bg="#EBF4FF", fg="#1A3A6B").pack(side=tk.LEFT)

        self.ip_display = tk.Entry(
            info_bar, font=("Segoe UI", 10, "bold"), width=16,
            bd=1, relief=tk.SOLID, fg="#0068FF", bg="#FFFFFF",
            state="readonly",
        )
        self.ip_display.pack(side=tk.LEFT, padx=(6, 4), ipady=2)
        self._set_readonly_entry(self.ip_display, self.local_ip)

        btn_copy_ip = tk.Button(
            info_bar, text="📋 Copy IP", font=("Segoe UI", 8, "bold"),
            bg="#0068FF", fg="#FFFFFF", bd=0, padx=8, pady=2,
            activebackground="#0052CC", activeforeground="#FFFFFF",
            command=self._copy_ip,
        )
        btn_copy_ip.pack(side=tk.LEFT, padx=(0, 16))
        Tooltip(btn_copy_ip, "Sao chép IP này và chia sẻ với người dùng Máy A để họ nhập vào.")

        tk.Label(info_bar, text="Cổng:", font=("Segoe UI", 9, "bold"),
                 bg="#EBF4FF", fg="#1A3A6B").pack(side=tk.LEFT)
        tk.Label(info_bar, text=str(PORT), font=("Segoe UI", 10, "bold"),
                 bg="#EBF4FF", fg="#E53E3E").pack(side=tk.LEFT, padx=(4, 0))

        btn_guide = tk.Button(
            info_bar, text="❓ Hướng dẫn", font=("Segoe UI", 8, "bold"),
            bg="#FFF3CD", fg="#856404", bd=1, relief=tk.SOLID, padx=8, pady=2,
            command=self._show_welcome_guide,
        )
        btn_guide.pack(side=tk.RIGHT, padx=4)
        Tooltip(btn_guide, "Xem lại hướng dẫn sử dụng từng bước.")

        # ── 3. Control Bar ─────────────────────────────
        cfg_bar = tk.Frame(self.root, bg="#FFFFFF", padx=12, pady=7, bd=1, relief=tk.SOLID)
        cfg_bar.pack(fill=tk.X, padx=10, pady=(6, 3))

        self.btn_toggle = tk.Button(
            cfg_bar, text="🚀 BẮT ĐẦU MÁY B (Lắng nghe)",
            font=("Segoe UI", 9, "bold"),
            bg="#2E7D32", fg="#FFFFFF",
            activebackground="#1B5E20", activeforeground="#FFFFFF",
            bd=0, padx=14, pady=5, command=self.toggle_server,
        )
        self.btn_toggle.pack(side=tk.LEFT)
        Tooltip(self.btn_toggle, "Bấm để bắt đầu chờ Máy A kết nối.\nKhi đang chạy, bấm lại để dừng.")

        btn_clear = tk.Button(
            cfg_bar, text="🗑️ Xóa chat",
            font=("Segoe UI", 9), bg="#F0F2F5", fg="#444444",
            bd=0, padx=10, pady=5, command=self._clear_chat,
        )
        btn_clear.pack(side=tk.LEFT, padx=(8, 0))
        Tooltip(btn_clear, "Xóa toàn bộ lịch sử tin nhắn trên màn hình.")

        self.btn_open_folder = tk.Button(
            cfg_bar, text="📁 Xem File Đã Nhận",
            font=("Segoe UI", 9, "bold"),
            bg="#F0F2F5", fg="#1C1E21",
            bd=0, padx=10, pady=5,
            command=self.open_received_folder,
        )
        self.btn_open_folder.pack(side=tk.RIGHT)
        Tooltip(self.btn_open_folder, "Mở thư mục chứa các tệp đã nhận từ Máy A.")

        # ── 4. Status Bar ──────────────────────────────
        status_frame = tk.Frame(self.root, bg="#F7F9FC", padx=12, pady=3)
        status_frame.pack(fill=tk.X)

        self.status_label = tk.Label(
            status_frame,
            text="🔴 Máy B chưa chạy. Bấm 'BẮT ĐẦU MÁY B' để lắng nghe kết nối từ Máy A.",
            font=("Segoe UI", 9, "bold"), fg="#E53E3E", bg="#F7F9FC",
        )
        self.status_label.pack(side=tk.LEFT)

        # ── 5. Chat Feed ───────────────────────────────
        chat_card = tk.Frame(self.root, bg="#E8ECF0", bd=1, relief=tk.SOLID)
        chat_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        self.chat_feed = ScrolledText(
            chat_card, wrap=tk.WORD, font=("Segoe UI", 10),
            bg="#F7F9FC", fg="#1C1E21", state=tk.DISABLED,
            bd=0, padx=14, pady=10,
        )
        self.chat_feed.pack(fill=tk.BOTH, expand=True)

        # Tags
        self.chat_feed.tag_config("system",   foreground="#65676B", font=("Segoe UI", 9, "italic"), justify=tk.CENTER)
        self.chat_feed.tag_config("me_tag",   foreground="#0068FF", font=("Segoe UI", 10, "bold"),  justify=tk.RIGHT)
        self.chat_feed.tag_config("me_msg",   foreground="#000000", font=("Segoe UI", 10),           justify=tk.RIGHT, rmargin=10)
        self.chat_feed.tag_config("peer_tag", foreground="#2E7D32", font=("Segoe UI", 10, "bold"),  justify=tk.LEFT)
        self.chat_feed.tag_config("peer_msg", foreground="#000000", font=("Segoe UI", 10),           justify=tk.LEFT,  lmargin1=10)
        self.chat_feed.tag_config("file_card",foreground="#1565C0", font=("Segoe UI", 9, "bold"))
        self.chat_feed.tag_config("time_lbl", foreground="#8D949E", font=("Segoe UI", 8),            justify=tk.CENTER)
        self.chat_feed.tag_config("guide",    foreground="#1A3A6B", font=("Segoe UI", 9),            lmargin1=10, lmargin2=20, background="#EBF4FF")

        # ── 6. Progress Bar (file transfer) ───────────
        prog_frame = tk.Frame(self.root, bg="#FFFFFF", padx=10, pady=2)
        prog_frame.pack(fill=tk.X, padx=10)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            prog_frame, variable=self.progress_var, maximum=100,
            mode="determinate", length=200,
        )
        self.progress_bar.pack(side=tk.LEFT)
        self.progress_label = tk.Label(
            prog_frame, text="", font=("Segoe UI", 8),
            fg="#444444", bg="#FFFFFF",
        )
        self.progress_label.pack(side=tk.LEFT, padx=6)
        prog_frame.pack_forget()   # Ẩn cho đến khi cần
        self._prog_frame = prog_frame

        # ── 7. Bottom Input Bar ────────────────────────
        input_bar = tk.Frame(self.root, bg="#FFFFFF", padx=10, pady=8, bd=1, relief=tk.SOLID)
        input_bar.pack(fill=tk.X, padx=10, pady=(2, 10))

        self.btn_attach = tk.Button(
            input_bar, text="📎 Gửi File",
            font=("Segoe UI", 9, "bold"),
            bg="#EBF4FF", fg="#0068FF",
            activebackground="#D0E2FF", bd=0, padx=10, pady=6,
            command=self.send_file_action,
        )
        self.btn_attach.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(self.btn_attach, "Chọn một tệp bất kỳ từ máy tính\nđể gửi sang Máy A.")

        self.msg_entry = tk.Entry(
            input_bar, font=("Segoe UI", 10), bg="#F0F2F5", fg="#1C1E21",
            bd=0, highlightthickness=1, highlightcolor="#0068FF",
            highlightbackground="#CCCCCC",
        )
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6), ipady=7)
        self.msg_entry.bind("<Return>", lambda e: self.send_text_message())
        self.msg_entry.insert(0, "Nhập tin nhắn rồi bấm Enter hoặc nút Gửi →")
        self.msg_entry.config(fg="#AAAAAA")
        self.msg_entry.bind("<FocusIn>",  self._clear_placeholder)
        self.msg_entry.bind("<FocusOut>", self._restore_placeholder)

        self.btn_send = tk.Button(
            input_bar, text="Gửi 📤",
            font=("Segoe UI", 9, "bold"),
            bg="#0068FF", fg="#FFFFFF",
            activebackground="#0052CC", activeforeground="#FFFFFF",
            bd=0, padx=16, pady=6, command=self.send_text_message,
        )
        self.btn_send.pack(side=tk.RIGHT)
        Tooltip(self.btn_send, "Gửi tin nhắn văn bản sang Máy A.\nPhím tắt: nhấn Enter.")

    # ═══════════════════════════════════════════════════
    # PLACEHOLDER HELPERS
    # ═══════════════════════════════════════════════════
    _PLACEHOLDER = "Nhập tin nhắn rồi bấm Enter hoặc nút Gửi →"

    def _clear_placeholder(self, _e=None):
        if self.msg_entry.get() == self._PLACEHOLDER:
            self.msg_entry.delete(0, tk.END)
            self.msg_entry.config(fg="#1C1E21")

    def _restore_placeholder(self, _e=None):
        if not self.msg_entry.get():
            self.msg_entry.insert(0, self._PLACEHOLDER)
            self.msg_entry.config(fg="#AAAAAA")

    # ═══════════════════════════════════════════════════
    # WELCOME GUIDE
    # ═══════════════════════════════════════════════════
    def _show_welcome_guide(self):
        """Hiện hộp thoại hướng dẫn sử dụng cho người mới."""
        dlg = tk.Toplevel(self.root)
        dlg.title("📖 Hướng dẫn sử dụng — Máy B (Server)")
        dlg.geometry("520x420")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.configure(bg="#FFFFFF")

        # Header
        hdr = tk.Frame(dlg, bg="#0068FF", padx=16, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="📖 Hướng dẫn sử dụng — MÁY B (Server)",
                 font=("Segoe UI", 12, "bold"), fg="#FFFFFF", bg="#0068FF").pack(anchor=tk.W)

        body = tk.Frame(dlg, bg="#FFFFFF", padx=16, pady=12)
        body.pack(fill=tk.BOTH, expand=True)

        guide_text = (
            "━━━ VAI TRÒ CỦA BẠN ━━━\n"
            "Bạn đang chạy Máy B (SERVER).\n"
            "Máy B LẮNG NGHE kết nối và nhận tin nhắn, tệp từ Máy A gửi sang.\n\n"
            "━━━ CÁCH SỬ DỤNG ━━━\n\n"
            "① Bấm nút 🚀 'BẮT ĐẦU MÁY B'\n"
            "   → Máy B bắt đầu chờ Máy A kết nối\n\n"
            "② Chia sẻ địa chỉ IP của Máy B cho Máy A\n"
            f"   → IP Máy B của bạn: {self.local_ip}\n"
            "   → Bấm 📋 Copy IP để sao chép nhanh\n\n"
            "③ Chờ Máy A chạy client.py và nhập IP vào\n"
            "   → Khi kết nối thành công, màn hình hiện 🟢\n\n"
            "④ Nhắn tin qua lại\n"
            "   • Nhận tin: Tin nhắn xuất hiện tự động\n"
            "   • Gửi tin: Nhập vào ô bên dưới → bấm Enter\n"
            "   • Gửi file: Bấm 📎 Gửi File\n\n"
            "━━━ LỖI THƯỜNG GẶP ━━━\n"
            "🔴 'Cổng 5000 đang bận' → Tắt chương trình khác đang dùng cổng 5000\n"
            "🔴 Máy A không kết nối được → Kiểm tra Firewall hoặc dùng 127.0.0.1 (cùng máy)"
        )

        txt = ScrolledText(body, wrap=tk.WORD, font=("Segoe UI", 9),
                           bg="#F7F9FC", fg="#1A1A2E", bd=1, relief=tk.SOLID, padx=10, pady=8)
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert(tk.END, guide_text)
        txt.config(state=tk.DISABLED)

        tk.Button(
            dlg, text="✅  Đã hiểu, Đóng hướng dẫn",
            font=("Segoe UI", 10, "bold"),
            bg="#0068FF", fg="#FFFFFF", bd=0, padx=20, pady=8,
            activebackground="#0052CC", activeforeground="#FFFFFF",
            command=dlg.destroy,
        ).pack(pady=(0, 14))

    # ═══════════════════════════════════════════════════
    # UI HELPERS
    # ═══════════════════════════════════════════════════
    def _set_readonly_entry(self, entry: tk.Entry, value: str):
        entry.config(state=tk.NORMAL)
        entry.delete(0, tk.END)
        entry.insert(0, value)
        entry.config(state="readonly")

    def _copy_ip(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.local_ip)
        messagebox.showinfo("Đã sao chép!", f"Đã sao chép IP: {self.local_ip}\n\nGửi địa chỉ này cho Máy A để họ nhập vào ô 'IPv4 Máy B'.")

    def open_received_folder(self):
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(SAVE_DIR)
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không thể mở thư mục:\n{exc}")

    def _clear_chat(self):
        if messagebox.askyesno("Xóa lịch sử?", "Bạn có chắc muốn xóa toàn bộ lịch sử tin nhắn?"):
            self.chat_feed.config(state=tk.NORMAL)
            self.chat_feed.delete("1.0", tk.END)
            self.chat_feed.config(state=tk.DISABLED)

    def _show_progress(self, value: float, label: str = ""):
        self._prog_frame.pack(fill=tk.X, padx=10, before=self.chat_feed.master)
        self.progress_var.set(value)
        self.progress_label.config(text=label)

    def _hide_progress(self):
        self._prog_frame.pack_forget()
        self.progress_var.set(0)
        self.progress_label.config(text="")

    def append_system_msg(self, text: str):
        self.chat_feed.config(state=tk.NORMAL)
        ts = datetime.now().strftime("%H:%M:%S")
        self.chat_feed.insert(tk.END, f"\n─────── {ts} ───────\n", "time_lbl")
        self.chat_feed.insert(tk.END, f"{text}\n", "system")
        self.chat_feed.see(tk.END)
        self.chat_feed.config(state=tk.DISABLED)

    def append_chat_msg(self, sender: str, text: str, is_me: bool):
        self.chat_feed.config(state=tk.NORMAL)
        ts = datetime.now().strftime("%H:%M")
        if is_me:
            self.chat_feed.insert(tk.END, f"\n[{ts}] Bạn (Máy B):\n", "me_tag")
            self.chat_feed.insert(tk.END, f"{text}\n", "me_msg")
        else:
            self.chat_feed.insert(tk.END, f"\n[{ts}] {sender}:\n", "peer_tag")
            self.chat_feed.insert(tk.END, f"{text}\n", "peer_msg")
        self.chat_feed.see(tk.END)
        self.chat_feed.config(state=tk.DISABLED)

    def append_file_msg(self, sender: str, filename: str, file_size: int, is_me: bool,
                        local_path: Path | None = None, caption: str = ""):
        self.chat_feed.config(state=tk.NORMAL)
        ts = datetime.now().strftime("%H:%M")
        size_str = f"{file_size / 1024:.1f} KB" if file_size >= 1024 else f"{file_size} Bytes"
        tag_hdr = "me_tag" if is_me else "peer_tag"
        label   = "Bạn (Máy B)" if is_me else sender

        self.chat_feed.insert(tk.END, f"\n[{ts}] {label} gửi tệp:\n", tag_hdr)
        if caption:
            tag_msg = "me_msg" if is_me else "peer_msg"
            self.chat_feed.insert(tk.END, f"💬 \"{caption}\"\n", tag_msg)

        self.chat_feed.insert(tk.END, f"  📄 {filename}  ({size_str})\n", "file_card")

        if local_path and local_path.exists():
            btn = tk.Button(
                self.chat_feed, text=f"📁 Mở: {filename}",
                font=("Segoe UI", 8, "bold"), bg="#EBF4FF", fg="#0068FF",
                bd=1, padx=6, pady=2,
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
            messagebox.showerror("Lỗi mở file", f"Không thể mở {path.name}:\n{exc}")

    # ═══════════════════════════════════════════════════
    # SERVER SOCKET
    # ═══════════════════════════════════════════════════
    def toggle_server(self):
        if not self.is_running:
            self.start_server()
        else:
            self.stop_server()

    def start_server(self):
        if self.is_running:
            return
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if sys.platform != "win32":
                self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind((HOST, PORT))
            self.server_sock.listen(5)

            self.is_running = True
            self.btn_toggle.config(text="🛑 DỪNG MÁY B", bg="#E53E3E", activebackground="#C53030")
            self.status_label.config(
                text=f"🟢 Máy B đang lắng nghe Cổng {PORT} — IP: {self.local_ip} — Đang chờ Máy A kết nối...",
                fg="#2E7D32"
            )
            self.append_system_msg(
                f"🖥️ Máy B (Server) đã khởi chạy!\n"
                f"   • IP Máy B: {self.local_ip}  |  Cổng: {PORT}\n"
                f"   • Chia sẻ IP này cho Máy A để họ kết nối vào."
            )
            threading.Thread(target=self._accept_loop, daemon=True).start()

        except Exception as exc:
            self.is_running = False
            if "10048" in str(exc) or "already in use" in str(exc).lower():
                messagebox.showerror(
                    "❌ Cổng đang bận",
                    f"Cổng {PORT} đang được chương trình khác sử dụng.\n\n"
                    "Cách khắc phục:\n"
                    "1. Tắt chương trình server.py đang chạy ở cửa sổ khác\n"
                    "2. Khởi động lại máy tính\n"
                    "3. Thử chạy lại chương trình này"
                )
            else:
                messagebox.showerror("Lỗi khởi động", f"Không thể lắng nghe Cổng {PORT}:\n{exc}")
            self.status_label.config(text=f"🔴 Lỗi: Không thể mở Cổng {PORT}. Xem thông báo lỗi.", fg="#E53E3E")

    def stop_server(self):
        self.is_running = False
        for s in (self.active_client_sock, self.server_sock):
            if s:
                try:
                    s.close()
                except Exception:
                    pass
        self.active_client_sock = None
        self.server_sock = None
        self.btn_toggle.config(text="🚀 BẮT ĐẦU MÁY B (Lắng nghe)", bg="#2E7D32", activebackground="#1B5E20")
        self.status_label.config(text="🔴 Máy B đã dừng.", fg="#E53E3E")
        self.append_system_msg("🛑 Server Máy B đã dừng dịch vụ.")

    def _accept_loop(self):
        while self.is_running and self.server_sock:
            try:
                client_s, client_addr = self.server_sock.accept()
                if not self.is_running:
                    break
                self.active_client_sock = client_s
                ip, p = client_addr
                self.root.after(0, lambda i=ip, pr=p: (
                    self.status_label.config(text=f"🟢 Đã kết nối với Máy A ({i}:{pr}) — Sẵn sàng nhắn tin!", fg="#2E7D32"),
                    self.append_system_msg(f"🟢 Máy A ({i}:{pr}) đã kết nối thành công!")
                ))
                # Send welcome
                welcome = {"type": "text", "sender": "Máy B (Server)", "content": "👋 Xin chào! Kết nối thành công. Bạn có thể gửi tin nhắn và file rồi đó!"}
                self._send_pkt(self.active_client_sock, welcome)
                self._recv_loop(self.active_client_sock)
            except Exception:
                if self.is_running:
                    break

    def _recv_loop(self, sock: socket.socket):
        while True:
            try:
                line = self._readline(sock)
                if not line:
                    break

                pkt = json.loads(line)
                p_type = pkt.get("type")
                sender = pkt.get("sender", "Máy A")

                if p_type == "text":
                    content = pkt.get("content", "")
                    self.root.after(0, lambda s=sender, c=content: (
                        self.append_chat_msg(s, c, is_me=False),
                        play_notify()
                    ))

                elif p_type == "file_header":
                    filename  = pkt.get("filename", "file_nhan")
                    file_size = int(pkt.get("size", 0))
                    caption   = pkt.get("caption", "")

                    out_path = SAVE_DIR / Path(filename).name
                    counter, stem, suffix = 1, out_path.stem, out_path.suffix
                    while out_path.exists():
                        out_path = SAVE_DIR / f"{stem}_{counter}{suffix}"
                        counter += 1

                    received = 0
                    self.root.after(0, lambda fn=filename: self._show_progress(0, f"Đang nhận: {fn} …"))
                    with out_path.open("wb") as f_out:
                        while received < file_size:
                            chunk_len = min(BUFFER_SIZE, file_size - received)
                            chunk = sock.recv(chunk_len)
                            if not chunk:
                                raise ConnectionError("Ngắt kết nối khi đang nhận file.")
                            f_out.write(chunk)
                            received += len(chunk)
                            pct = received / file_size * 100
                            self.root.after(0, lambda p=pct, r=received, t=file_size: self._show_progress(
                                p, f"Đang nhận: {r/1024:.0f} KB / {t/1024:.0f} KB  ({p:.0f}%)"
                            ))

                    self.root.after(0, self._hide_progress)
                    self.root.after(0, lambda s=sender, fn=out_path.name, sz=file_size, p=out_path, cap=caption: (
                        self.append_file_msg(s, fn, sz, is_me=False, local_path=p, caption=cap),
                        self.append_system_msg(f"✅ Nhận tệp '{fn}' thành công → xem trong thư mục received_files!"),
                        play_notify()
                    ))

            except Exception:
                break

        self.root.after(0, lambda: (
            self.status_label.config(text="🔴 Máy A đã ngắt kết nối.", fg="#E53E3E"),
            self.append_system_msg("⚠️ Máy A đã ngắt kết nối."),
            self._hide_progress()
        ))

    # ═══════════════════════════════════════════════════
    # SENDING LOGIC
    # ═══════════════════════════════════════════════════
    def send_text_message(self):
        if not self.active_client_sock:
            messagebox.showinfo("Chưa có Máy A", "Chưa có Máy A nào kết nối.\n\nHãy chờ Máy A chạy client.py và kết nối vào.")
            return
        text = self.msg_entry.get().strip()
        if not text or text == self._PLACEHOLDER:
            return
        pkt = {"type": "text", "sender": "Máy B", "content": text}
        try:
            self._send_pkt(self.active_client_sock, pkt)
            self.append_chat_msg("Máy B", text, is_me=True)
            self.msg_entry.delete(0, tk.END)
        except Exception as exc:
            messagebox.showerror("Lỗi gửi", f"Không thể gửi tin nhắn:\n{exc}")

    def send_file_action(self):
        if not self.active_client_sock:
            messagebox.showinfo("Chưa có Máy A", "Chưa có Máy A nào kết nối.\n\nHãy chờ Máy A chạy client.py và kết nối vào.")
            return
        file_path = filedialog.askopenfilename(
            title="Chọn tệp để gửi sang Máy A",
            filetypes=[("Tất cả tệp", "*.*"), ("Ảnh", "*.png;*.jpg;*.jpeg"), ("Văn bản", "*.txt;*.pdf;*.docx")],
        )
        if not file_path:
            return
        selected = Path(file_path)
        caption  = self.msg_entry.get().strip()
        if caption == self._PLACEHOLDER:
            caption = ""
        self.msg_entry.delete(0, tk.END)
        self.btn_attach.config(state=tk.DISABLED)
        threading.Thread(target=self._send_file_worker, args=(selected, caption), daemon=True).start()

    def _send_file_worker(self, file_path: Path, caption: str = ""):
        try:
            file_size = file_path.stat().st_size
            header    = {"type": "file_header", "sender": "Máy B", "filename": file_path.name, "size": file_size, "caption": caption}

            self.root.after(0, lambda: self._show_progress(0, f"Đang gửi: {file_path.name} …"))
            with self.send_lock:
                self._send_pkt(self.active_client_sock, header)
                sent = 0
                with file_path.open("rb") as f_in:
                    while True:
                        chunk = f_in.read(BUFFER_SIZE)
                        if not chunk:
                            break
                        self.active_client_sock.sendall(chunk)
                        sent += len(chunk)
                        pct = sent / file_size * 100
                        self.root.after(0, lambda p=pct, s=sent, t=file_size: self._show_progress(
                            p, f"Đang gửi: {s/1024:.0f} KB / {t/1024:.0f} KB  ({p:.0f}%)"
                        ))

            self.root.after(0, self._hide_progress)
            self.root.after(0, lambda fn=file_path.name, sz=file_size, p=file_path, cap=caption: (
                self.append_file_msg("Máy B", fn, sz, is_me=True, local_path=p, caption=cap),
                self.append_system_msg(f"📤 Đã gửi tệp '{fn}' sang Máy A thành công!")
            ))
        except Exception as exc:
            self.root.after(0, lambda e=exc: messagebox.showerror("Lỗi gửi file", f"Thất bại:\n{e}"))
            self.root.after(0, self._hide_progress)
        finally:
            self.root.after(0, lambda: self.btn_attach.config(state=tk.NORMAL))

    # ═══════════════════════════════════════════════════
    # PROTOCOL HELPERS
    # ═══════════════════════════════════════════════════
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
    app = MessengerServerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
