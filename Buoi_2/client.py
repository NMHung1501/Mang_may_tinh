"""💬 MÁY A (CLIENT) - Ứng dụng Chat & Gửi File TCP Socket (Kết nối tới Máy B).

Máy A đóng vai trò CLIENT: Kết nối tới địa chỉ IP của Máy B, gửi/nhận tin nhắn Text và Tệp tin nhị phân.
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
DEFAULT_CONNECT_IP = "127.0.0.1"
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


class MessengerClientGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("💬 MÁY A (CLIENT) - Ứng dụng Chat TCP Socket | Kết nối tới Máy B")
        self.root.geometry("860x720")
        self.root.minsize(720, 560)

        self.is_connected = False
        self.client_sock: socket.socket | None = None
        self.send_lock = threading.Lock()
        self.local_ip = get_local_ip()

        self._build_ui()
        self._show_welcome_guide()

    # ═══════════════════════════════════════════════════
    # BUILD UI
    # ═══════════════════════════════════════════════════
    def _build_ui(self):
        # ── 1. Header ──────────────────────────────────
        header = tk.Frame(self.root, bg="#00875A", padx=16, pady=10)
        header.pack(fill=tk.X)

        tk.Label(
            header, text="💬  MÁY A  —  CLIENT GỬI TIN & TỆP",
            font=("Segoe UI", 14, "bold"), fg="#FFFFFF", bg="#00875A",
        ).pack(anchor=tk.W)
        tk.Label(
            header,
            text="Máy A kết nối vào IP của Máy B để nhắn tin và gửi file. Nhập IP Máy B bên dưới.",
            font=("Segoe UI", 9), fg="#C8FFE7", bg="#00875A",
        ).pack(anchor=tk.W, pady=(1, 0))

        # ── 2. Info Bar (IP máy này) ───────────────────
        info_bar = tk.Frame(self.root, bg="#E6FFF4", padx=12, pady=6)
        info_bar.pack(fill=tk.X)

        tk.Label(info_bar, text="📡 IP Máy A (máy này):",
                 font=("Segoe UI", 9, "bold"), bg="#E6FFF4", fg="#005C3A").pack(side=tk.LEFT)

        self.my_ip_display = tk.Entry(
            info_bar, font=("Segoe UI", 10, "bold"), width=16,
            bd=1, relief=tk.SOLID, fg="#00875A", bg="#FFFFFF", state="readonly",
        )
        self.my_ip_display.pack(side=tk.LEFT, padx=(6, 4), ipady=2)
        self._set_readonly_entry(self.my_ip_display, self.local_ip)

        btn_copy_my_ip = tk.Button(
            info_bar, text="📋 Copy IP", font=("Segoe UI", 8, "bold"),
            bg="#00875A", fg="#FFFFFF", bd=0, padx=8, pady=2,
            activebackground="#006644", activeforeground="#FFFFFF",
            command=self._copy_my_ip,
        )
        btn_copy_my_ip.pack(side=tk.LEFT, padx=(0, 16))
        Tooltip(btn_copy_my_ip, "Sao chép IP máy A của bạn (hữu ích nếu Máy B cần biết IP của bạn).")

        btn_guide = tk.Button(
            info_bar, text="❓ Hướng dẫn", font=("Segoe UI", 8, "bold"),
            bg="#FFF3CD", fg="#856404", bd=1, relief=tk.SOLID, padx=8, pady=2,
            command=self._show_welcome_guide,
        )
        btn_guide.pack(side=tk.RIGHT, padx=4)
        Tooltip(btn_guide, "Xem lại hướng dẫn sử dụng từng bước.")

        # ── 3. Control Bar (IP Máy B + Kết nối) ───────
        cfg_bar = tk.Frame(self.root, bg="#FFFFFF", padx=12, pady=7, bd=1, relief=tk.SOLID)
        cfg_bar.pack(fill=tk.X, padx=10, pady=(6, 3))

        tk.Label(cfg_bar, text="🎯 IP Máy B:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#333333").pack(side=tk.LEFT, padx=(0, 4))
        self.ip_entry = tk.Entry(cfg_bar, font=("Segoe UI", 9), width=14, bd=1, relief=tk.SOLID)
        self.ip_entry.insert(0, DEFAULT_CONNECT_IP)
        self.ip_entry.pack(side=tk.LEFT, padx=(0, 4))
        Tooltip(self.ip_entry, "Nhập địa chỉ IP của máy tính chạy server.py (Máy B).\nNếu cùng 1 máy: dùng 127.0.0.1")

        btn_localhost = tk.Button(
            cfg_bar, text="⚡ Cùng máy",
            font=("Segoe UI", 8, "bold"),
            bg="#EBF4FF", fg="#0068FF", bd=0, padx=6, pady=3,
            command=self._set_localhost,
        )
        btn_localhost.pack(side=tk.LEFT, padx=(0, 8))
        Tooltip(btn_localhost, "Bấm nếu Máy A và Máy B đang cùng chạy trên 1 máy tính.\nTự động điền 127.0.0.1")

        tk.Label(cfg_bar, text="Tên của bạn:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#333333").pack(side=tk.LEFT, padx=(4, 2))
        self.user_entry = tk.Entry(cfg_bar, font=("Segoe UI", 9), width=10, bd=1, relief=tk.SOLID)
        self.user_entry.insert(0, "Máy A")
        self.user_entry.pack(side=tk.LEFT, padx=(0, 10))
        Tooltip(self.user_entry, "Tên hiển thị của bạn trong khung chat.")

        self.btn_connect = tk.Button(
            cfg_bar, text="🔌 KẾT NỐI TỚI MÁY B",
            font=("Segoe UI", 9, "bold"),
            bg="#00875A", fg="#FFFFFF",
            activebackground="#006644", activeforeground="#FFFFFF",
            bd=0, padx=14, pady=5, command=self.toggle_connection,
        )
        self.btn_connect.pack(side=tk.LEFT)
        Tooltip(self.btn_connect, "Bấm để kết nối tới Máy B.\nĐảm bảo Máy B đã chạy server.py trước!")

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
            bd=0, padx=10, pady=5, command=self.open_received_folder,
        )
        self.btn_open_folder.pack(side=tk.RIGHT)
        Tooltip(self.btn_open_folder, "Mở thư mục chứa các tệp đã nhận từ Máy B.")

        # ── 4. Status Bar ──────────────────────────────
        status_frame = tk.Frame(self.root, bg="#F7F9FC", padx=12, pady=3)
        status_frame.pack(fill=tk.X)

        self.status_label = tk.Label(
            status_frame,
            text="🔴 Chưa kết nối. Nhập IP Máy B rồi bấm 'KẾT NỐI TỚI MÁY B'.",
            font=("Segoe UI", 9, "bold"), fg="#E53E3E", bg="#F7F9FC",
        )
        self.status_label.pack(side=tk.LEFT)

        # ── 5. Chat Feed ───────────────────────────────
        chat_card = tk.Frame(self.root, bg="#E8F5EE", bd=1, relief=tk.SOLID)
        chat_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        self.chat_feed = ScrolledText(
            chat_card, wrap=tk.WORD, font=("Segoe UI", 10),
            bg="#F7FBF8", fg="#1C1E21", state=tk.DISABLED,
            bd=0, padx=14, pady=10,
        )
        self.chat_feed.pack(fill=tk.BOTH, expand=True)

        # Tags
        self.chat_feed.tag_config("system",    foreground="#65676B", font=("Segoe UI", 9, "italic"), justify=tk.CENTER)
        self.chat_feed.tag_config("me_tag",    foreground="#00875A", font=("Segoe UI", 10, "bold"), justify=tk.RIGHT)
        self.chat_feed.tag_config("me_msg",    foreground="#000000", font=("Segoe UI", 10),          justify=tk.RIGHT, rmargin=10)
        self.chat_feed.tag_config("peer_tag",  foreground="#0068FF", font=("Segoe UI", 10, "bold"), justify=tk.LEFT)
        self.chat_feed.tag_config("peer_msg",  foreground="#000000", font=("Segoe UI", 10),          justify=tk.LEFT,  lmargin1=10)
        self.chat_feed.tag_config("file_card", foreground="#1565C0", font=("Segoe UI", 9, "bold"))
        self.chat_feed.tag_config("time_lbl",  foreground="#8D949E", font=("Segoe UI", 8),           justify=tk.CENTER)

        # ── 6. Progress Bar ────────────────────────────
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
        prog_frame.pack_forget()
        self._prog_frame = prog_frame

        # ── 7. Bottom Input Bar ────────────────────────
        input_bar = tk.Frame(self.root, bg="#FFFFFF", padx=10, pady=8, bd=1, relief=tk.SOLID)
        input_bar.pack(fill=tk.X, padx=10, pady=(2, 10))

        self.btn_attach = tk.Button(
            input_bar, text="📎 Gửi File",
            font=("Segoe UI", 9, "bold"),
            bg="#E6FFF4", fg="#00875A",
            activebackground="#B3FFD9", bd=0, padx=10, pady=6,
            command=self.send_file_action,
        )
        self.btn_attach.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(self.btn_attach, "Chọn một tệp bất kỳ từ máy tính để gửi sang Máy B.")

        self.msg_entry = tk.Entry(
            input_bar, font=("Segoe UI", 10), bg="#F0F2F5", fg="#1C1E21",
            bd=0, highlightthickness=1, highlightcolor="#00875A",
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
            bg="#00875A", fg="#FFFFFF",
            activebackground="#006644", activeforeground="#FFFFFF",
            bd=0, padx=16, pady=6, command=self.send_text_message,
        )
        self.btn_send.pack(side=tk.RIGHT)
        Tooltip(self.btn_send, "Gửi tin nhắn văn bản sang Máy B.\nPhím tắt: nhấn Enter.")

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
        dlg.title("📖 Hướng dẫn sử dụng — Máy A (Client)")
        dlg.geometry("520x430")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.configure(bg="#FFFFFF")

        hdr = tk.Frame(dlg, bg="#00875A", padx=16, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="📖 Hướng dẫn sử dụng — MÁY A (Client)",
                 font=("Segoe UI", 12, "bold"), fg="#FFFFFF", bg="#00875A").pack(anchor=tk.W)

        body = tk.Frame(dlg, bg="#FFFFFF", padx=16, pady=12)
        body.pack(fill=tk.BOTH, expand=True)

        guide_text = (
            "━━━ VAI TRÒ CỦA BẠN ━━━\n"
            "Bạn đang chạy Máy A (CLIENT).\n"
            "Máy A KẾT NỐI tới Máy B để gửi và nhận tin nhắn, tệp.\n\n"
            "━━━ CÁCH SỬ DỤNG ━━━\n\n"
            "① Đảm bảo Máy B đã chạy server.py trước\n"
            "   → Yêu cầu người dùng Máy B bấm '🚀 BẮT ĐẦU MÁY B'\n\n"
            "② Lấy địa chỉ IP của Máy B\n"
            "   → Hỏi người dùng Máy B IP của họ là bao nhiêu\n"
            "   → Nếu cùng 1 máy: bấm nút '⚡ Cùng máy' (127.0.0.1)\n\n"
            "③ Nhập IP Máy B vào ô 'IP Máy B' rồi bấm 🔌 'KẾT NỐI'\n"
            "   → Khi kết nối thành công, màn hình hiện 🟢\n\n"
            "④ Nhắn tin qua lại\n"
            "   • Gửi tin: Nhập vào ô bên dưới → bấm Enter\n"
            "   • Gửi file: Bấm 📎 Gửi File → chọn file\n"
            "   • Nhận tin: Tin nhắn xuất hiện tự động, có âm thanh\n\n"
            "━━━ LỖI THƯỜNG GẶP ━━━\n"
            "🔴 Không kết nối được → Kiểm tra Máy B đã chạy server.py chưa\n"
            "🔴 Sai IP → Hỏi lại IP của Máy B (bấm 📋 Copy IP ở cửa sổ Máy B)\n"
            "🔴 Cùng mạng LAN mà vẫn lỗi → Tắt Firewall hoặc dùng 127.0.0.1"
        )

        txt = ScrolledText(body, wrap=tk.WORD, font=("Segoe UI", 9),
                           bg="#F7FBF8", fg="#1A1A2E", bd=1, relief=tk.SOLID, padx=10, pady=8)
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert(tk.END, guide_text)
        txt.config(state=tk.DISABLED)

        tk.Button(
            dlg, text="✅  Đã hiểu, Đóng hướng dẫn",
            font=("Segoe UI", 10, "bold"),
            bg="#00875A", fg="#FFFFFF", bd=0, padx=20, pady=8,
            activebackground="#006644", activeforeground="#FFFFFF",
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

    def _copy_my_ip(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.local_ip)
        messagebox.showinfo("Đã sao chép!", f"Đã sao chép IP Máy A: {self.local_ip}")

    def _set_localhost(self):
        self.ip_entry.delete(0, tk.END)
        self.ip_entry.insert(0, "127.0.0.1")

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
            user_lbl = self.user_entry.get().strip() or "Máy A"
            self.chat_feed.insert(tk.END, f"\n[{ts}] Bạn ({user_lbl}):\n", "me_tag")
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
        label   = f"Bạn ({self.user_entry.get().strip() or 'Máy A'})" if is_me else sender

        self.chat_feed.insert(tk.END, f"\n[{ts}] {label} gửi tệp:\n", tag_hdr)
        if caption:
            tag_msg = "me_msg" if is_me else "peer_msg"
            self.chat_feed.insert(tk.END, f"💬 \"{caption}\"\n", tag_msg)

        self.chat_feed.insert(tk.END, f"  📄 {filename}  ({size_str})\n", "file_card")

        if local_path and local_path.exists():
            btn = tk.Button(
                self.chat_feed, text=f"📁 Mở: {filename}",
                font=("Segoe UI", 8, "bold"), bg="#E6FFF4", fg="#00875A",
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
    # CLIENT SOCKET
    # ═══════════════════════════════════════════════════
    def toggle_connection(self):
        if not self.is_connected:
            self.connect()
        else:
            self.disconnect()

    def connect(self):
        if self.is_connected:
            return
        ip = self.ip_entry.get().strip() or DEFAULT_CONNECT_IP

        self.status_label.config(text=f"⏳ Đang kết nối tới Máy B ({ip}:{PORT}) …", fg="#D69E2E")
        self.btn_connect.config(state=tk.DISABLED)
        self.root.update()

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(4.0)
            sock.connect((ip, PORT))
            sock.settimeout(None)

            self.client_sock = sock
            self.is_connected = True

            user_name = self.user_entry.get().strip() or "Máy A"
            self.btn_connect.config(text="❌ NGẮT KẾT NỐI", bg="#E53E3E", activebackground="#C53030", state=tk.NORMAL)
            self.status_label.config(text=f"🟢 Đã kết nối Máy B ({ip}:{PORT}) — Tên: {user_name}. Sẵn sàng nhắn tin!", fg="#00875A")
            self.append_system_msg(f"🟢 Kết nối thành công tới Máy B ({ip}:{PORT})!\n   Bạn có thể nhắn tin và gửi file ngay bây giờ.")

            threading.Thread(target=self._recv_loop, daemon=True).start()

        except ConnectionRefusedError:
            self.btn_connect.config(state=tk.NORMAL)
            self.status_label.config(text=f"🔴 Không thể kết nối {ip}:{PORT}", fg="#E53E3E")
            messagebox.showerror(
                "❌ Kết nối thất bại",
                f"Không thể kết nối tới Máy B ({ip}:{PORT}).\n\n"
                "Hãy kiểm tra:\n"
                "  ① Máy B đã chạy server.py và bấm '🚀 BẮT ĐẦU MÁY B' chưa?\n"
                "  ② IP bạn nhập có đúng không? (Xem IP ở cửa sổ Máy B)\n"
                "  ③ Hai máy có cùng mạng WiFi/LAN không?\n\n"
                "Nếu test trên cùng 1 máy → bấm nút '⚡ Cùng máy'"
            )
        except TimeoutError:
            self.btn_connect.config(state=tk.NORMAL)
            self.status_label.config(text=f"🔴 Hết thời gian chờ kết nối {ip}", fg="#E53E3E")
            messagebox.showerror(
                "❌ Hết thời gian kết nối",
                f"Không nhận được phản hồi từ {ip}:{PORT} sau 4 giây.\n\n"
                "Nguyên nhân thường gặp:\n"
                "  • IP sai hoặc Máy B chưa chạy\n"
                "  • Firewall chặn kết nối\n"
                "  • Hai máy không cùng mạng"
            )
        except Exception as exc:
            self.btn_connect.config(state=tk.NORMAL)
            self.status_label.config(text=f"🔴 Lỗi kết nối: {exc}", fg="#E53E3E")
            messagebox.showerror("Lỗi kết nối", f"Lỗi không xác định:\n{exc}")

    def disconnect(self):
        self.is_connected = False
        if self.client_sock:
            try:
                self.client_sock.close()
            except Exception:
                pass
            self.client_sock = None
        self.btn_connect.config(text="🔌 KẾT NỐI TỚI MÁY B", bg="#00875A", activebackground="#006644", state=tk.NORMAL)
        self.status_label.config(text="🔴 Đã ngắt kết nối.", fg="#E53E3E")
        self.append_system_msg("❌ Đã ngắt kết nối tới Máy B.")

    def _recv_loop(self):
        while self.is_connected and self.client_sock:
            try:
                line = self._readline(self.client_sock)
                if not line:
                    break

                pkt = json.loads(line)
                p_type = pkt.get("type")
                sender = pkt.get("sender", "Máy B (Server)")

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
                            chunk = self.client_sock.recv(chunk_len)
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

        if self.is_connected:
            self.root.after(0, lambda: (
                self.disconnect(),
                self._hide_progress(),
                messagebox.showwarning("Mất kết nối", "Máy B đã ngắt kết nối hoặc xảy ra lỗi mạng.\n\nBạn có thể kết nối lại khi Máy B sẵn sàng.")
            ))

    # ═══════════════════════════════════════════════════
    # SENDING LOGIC
    # ═══════════════════════════════════════════════════
    def send_text_message(self):
        if not self.is_connected or not self.client_sock:
            messagebox.showinfo(
                "Chưa kết nối",
                "Bạn chưa kết nối tới Máy B.\n\n"
                "Hướng dẫn:\n"
                "  ① Nhập IP Máy B vào ô 'IP Máy B'\n"
                "  ② Bấm nút 🔌 'KẾT NỐI TỚI MÁY B'"
            )
            return
        text = self.msg_entry.get().strip()
        if not text or text == self._PLACEHOLDER:
            return
        user_name = self.user_entry.get().strip() or "Máy A"
        pkt = {"type": "text", "sender": user_name, "content": text}
        try:
            self._send_pkt(self.client_sock, pkt)
            self.append_chat_msg(user_name, text, is_me=True)
            self.msg_entry.delete(0, tk.END)
        except Exception as exc:
            messagebox.showerror("Lỗi gửi", f"Không thể gửi tin nhắn:\n{exc}")

    def send_file_action(self):
        if not self.is_connected or not self.client_sock:
            messagebox.showinfo(
                "Chưa kết nối",
                "Bạn chưa kết nối tới Máy B.\n\nBấm 🔌 'KẾT NỐI TỚI MÁY B' trước."
            )
            return
        file_path = filedialog.askopenfilename(
            title="Chọn tệp để gửi sang Máy B",
            filetypes=[("Tất cả tệp", "*.*"), ("Ảnh", "*.png;*.jpg;*.jpeg"), ("Văn bản", "*.txt;*.pdf;*.docx")],
        )
        if not file_path:
            return
        selected  = Path(file_path)
        user_name = self.user_entry.get().strip() or "Máy A"
        caption   = self.msg_entry.get().strip()
        if caption == self._PLACEHOLDER:
            caption = ""
        self.msg_entry.delete(0, tk.END)
        self.btn_attach.config(state=tk.DISABLED)
        threading.Thread(target=self._send_file_worker, args=(selected, user_name, caption), daemon=True).start()

    def _send_file_worker(self, file_path: Path, user_name: str, caption: str = ""):
        try:
            file_size = file_path.stat().st_size
            header    = {"type": "file_header", "sender": user_name, "filename": file_path.name, "size": file_size, "caption": caption}

            self.root.after(0, lambda: self._show_progress(0, f"Đang gửi: {file_path.name} …"))
            with self.send_lock:
                self._send_pkt(self.client_sock, header)
                sent = 0
                with file_path.open("rb") as f_in:
                    while True:
                        chunk = f_in.read(BUFFER_SIZE)
                        if not chunk:
                            break
                        self.client_sock.sendall(chunk)
                        sent += len(chunk)
                        pct = sent / file_size * 100
                        self.root.after(0, lambda p=pct, s=sent, t=file_size: self._show_progress(
                            p, f"Đang gửi: {s/1024:.0f} KB / {t/1024:.0f} KB  ({p:.0f}%)"
                        ))

            self.root.after(0, self._hide_progress)
            self.root.after(0, lambda fn=file_path.name, sz=file_size, p=file_path, cap=caption: (
                self.append_file_msg("Bạn", fn, sz, is_me=True, local_path=p, caption=cap),
                self.append_system_msg(f"📤 Đã gửi tệp '{fn}' sang Máy B thành công!")
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
    app = MessengerClientGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
