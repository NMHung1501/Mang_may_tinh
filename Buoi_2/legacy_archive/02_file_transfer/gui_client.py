"""Bài 2 - GUI Client Truyền Tệp TCP (Dành cho MÁY A - FILE CLIENT GỬI TỆP)."""

import os
import socket
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PORT = 5001
ENCODING = "utf-8"
BUFFER_SIZE = 64 * 1024


class FileClientGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MÁY A: FILE CLIENT GỬI TỆP (GỬI SANG MÁY B SERVER)")
        self.root.geometry("660x550")
        self.root.minsize(560, 450)

        self.selected_file: Path | None = None
        
        # Auto pre-fill IP passed from Chat GUI command-line args if available
        initial_ip = sys.argv[1].strip() if len(sys.argv) > 1 and sys.argv[1].strip() else "127.0.0.1"

        self._build_ui(initial_ip=initial_ip)

    def _build_ui(self, initial_ip: str = "127.0.0.1"):
        # Header Banner
        header = tk.Frame(self.root, bg="#2C7A7B", padx=12, pady=10)
        header.pack(fill=tk.X)

        tk.Label(header, text="📤 MÁY A: FILE CLIENT GỬI TỆP", font=("Segoe UI", 13, "bold"), fg="#FFFFFF", bg="#2C7A7B").pack(anchor=tk.W)
        tk.Label(header, text="Máy A đóng vai trò CLIENT GỬI - Chọn tệp nhị phân và gửi sang Máy B (Server)", font=("Segoe UI", 9), fg="#E6FFFA", bg="#2C7A7B").pack(anchor=tk.W, pady=(2, 0))

        # Connection Config
        conn_frame = tk.Frame(self.root, bg="#F7FAFC", padx=10, pady=8)
        conn_frame.pack(fill=tk.X)

        tk.Label(conn_frame, text="IPv4 Server (Máy B):", font=("Segoe UI", 9, "bold"), bg="#F7FAFC").grid(row=0, column=0, sticky=tk.W)
        self.ip_entry = tk.Entry(conn_frame, font=("Segoe UI", 9), width=13)
        self.ip_entry.insert(0, initial_ip)
        self.ip_entry.grid(row=0, column=1, padx=2)

        btn_local = tk.Button(conn_frame, text="⚡ Localhost", font=("Segoe UI", 8, "bold"), bg="#EDF2F7", fg="#2D3748", command=self.set_localhost)
        btn_local.grid(row=0, column=2, padx=2)

        tk.Label(conn_frame, text="Port:", font=("Segoe UI", 9, "bold"), bg="#F7FAFC").grid(row=0, column=3, sticky=tk.W, padx=(8, 0))
        self.port_entry = tk.Entry(conn_frame, font=("Segoe UI", 9), width=6)
        self.port_entry.insert(0, str(PORT))
        self.port_entry.grid(row=0, column=4, padx=2)

        hint_lbl = tk.Label(conn_frame, text="💡 Gợi ý: Kiểm tra mở File Server (Cổng 5001) trên Máy B trước khi bấm gửi.", font=("Segoe UI", 9, "italic"), fg="#718096", bg="#F7FAFC")
        hint_lbl.grid(row=1, column=0, columnspan=5, sticky=tk.W, pady=(4, 0))

        # File Select Frame
        file_frame = tk.LabelFrame(self.root, text=" Tệp Nhị Phân Cần Truyền ", font=("Segoe UI", 9, "bold"), fg="#2C7A7B", bg="#F7FAFC", padx=10, pady=10)
        file_frame.pack(fill=tk.X, padx=10, pady=6)

        self.btn_browse = tk.Button(file_frame, text="📂 CHỌN TỆP CẦN GỬI...", font=("Segoe UI", 10, "bold"), bg="#2C7A7B", fg="#FFFFFF", activebackground="#234E52", activeforeground="#FFFFFF", padx=10, command=self.browse_file)
        self.btn_browse.grid(row=0, column=0, padx=4, pady=4)

        self.file_label = tk.Label(file_frame, text="Chưa chọn tệp nào.", font=("Segoe UI", 9, "italic"), fg="#718096", bg="#F7FAFC")
        self.file_label.grid(row=0, column=1, sticky=tk.W, padx=8, pady=4)

        self.size_label = tk.Label(file_frame, text="", font=("Segoe UI", 9, "bold"), fg="#2B6CB0", bg="#F7FAFC")
        self.size_label.grid(row=1, column=1, sticky=tk.W, padx=8, pady=2)

        # Send Action Frame
        action_frame = tk.Frame(self.root, bg="#F7FAFC", padx=10, pady=6)
        action_frame.pack(fill=tk.X)

        self.btn_send = tk.Button(action_frame, text="📤 GỬI TỆP SANG MÁY B (TCP)", font=("Segoe UI", 10, "bold"), bg="#38A169", fg="#FFFFFF", activebackground="#2F855A", activeforeground="#FFFFFF", padx=12, command=self.start_send_thread, state=tk.DISABLED)
        self.btn_send.pack(side=tk.LEFT)

        self.progress_bar = ttk.Progressbar(action_frame, orient=tk.HORIZONTAL, mode="determinate")
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        # Log Window
        log_frame = tk.Frame(self.root, bg="#F7FAFC", padx=10, pady=4)
        log_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(log_frame, text="Tiến trình Truyền Tệp & Phản hồi từ Máy B (Server):", font=("Segoe UI", 9, "bold"), fg="#2B6CB0", bg="#F7FAFC").pack(anchor=tk.W, pady=(2, 4))

        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=("Segoe UI", 9), state=tk.DISABLED, bg="#FFFFFF", fg="#2D3748")
        self.log_area.pack(fill=tk.BOTH, expand=True)

        self.log_area.tag_config("info", foreground="#2B6CB0")
        self.log_area.tag_config("success", foreground="#38A169", font=("Segoe UI", 9, "bold"))
        self.log_area.tag_config("error", foreground="#E53E3E", font=("Segoe UI", 9, "bold"))

    def set_localhost(self):
        self.ip_entry.delete(0, tk.END)
        self.ip_entry.insert(0, "127.0.0.1")

    def log(self, text: str, tag: str = "normal"):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, text + "\n", tag)
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Chọn tệp cần gửi sang Máy B",
            filetypes=[("Tất cả tệp", "*.*"), ("Ảnh PNG/JPG", "*.png;*.jpg;*.jpeg"), ("Văn bản", "*.txt;*.pdf;*.docx")]
        )
        if file_path:
            self.selected_file = Path(file_path)
            size_bytes = self.selected_file.stat().st_size
            size_str = self._format_size(size_bytes)
            self.file_label.config(text=f"Tệp: {self.selected_file.name}", fg="#1A202C", font=("Segoe UI", 9, "bold"))
            self.size_label.config(text=f"Kích thước: {size_bytes:,} bytes ({size_str})")
            self.btn_send.config(state=tk.NORMAL)
            self.log(f"[CHỌN TỆP] {self.selected_file.resolve()} ({size_str})", "info")

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"

    def start_send_thread(self):
        if not self.selected_file or not self.selected_file.is_file():
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn tệp hợp lệ.")
            return

        ip = self.ip_entry.get().strip() or "127.0.0.1"
        try:
            port = int(self.port_entry.get().strip() or str(PORT))
        except ValueError:
            messagebox.showerror("Lỗi", "Cổng Port phải là số nguyên.")
            return

        self.btn_send.config(state=tk.DISABLED)
        self.btn_browse.config(state=tk.DISABLED)
        self.progress_bar["value"] = 0

        threading.Thread(target=self._send_file_worker, args=(ip, port), daemon=True).start()

    def _send_file_worker(self, ip: str, port: int):
        file_path = self.selected_file
        file_size = file_path.stat().st_size

        try:
            self.root.after(0, lambda: self.log(f"[CLIENT MÁY A] Đang kết nối tới Máy B ({ip}:{port})...", "info"))
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                client.settimeout(10.0)
                client.connect((ip, port))

                # Step 1 Header
                header_line = f"{file_path.name}|{file_size}\n"
                client.sendall(header_line.encode(ENCODING))
                self.root.after(0, lambda: self.log(f"[BƯỚC 1 HEADER] Đã gửi Header: {file_path.name}|{file_size}", "info"))

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
                        self.root.after(0, lambda p=progress: self._update_progress(p))

                self.root.after(0, lambda s=sent: self.log(f"[BƯỚC 2 DATA] Đã gửi {s:,}/{file_size:,} bytes (100%). Chờ phản hồi từ Máy B...", "info"))

                # Step 3 Response
                client.settimeout(10.0)
                response_line = self._recv_line(client)
                if response_line:
                    if response_line.startswith("OK|"):
                        self.root.after(0, lambda: self._update_progress(100))
                        self.root.after(0, lambda r=response_line: self.log(f"[BƯỚC 3 XÁC NHẬN] Máy B báo: {r}", "success"))
                        self.root.after(0, lambda r=response_line: messagebox.showinfo("Thành công", f"Máy B đã lưu tệp thành công!\n\nPhản hồi: {r}"))
                    else:
                        self.root.after(0, lambda r=response_line: self.log(f"[MÁY B BÁO LỖI] {r}", "error"))
                        self.root.after(0, lambda r=response_line: messagebox.showerror("Lỗi từ Máy B", r))
                else:
                    self.root.after(0, lambda: self.log("[LỖI] Không nhận được phản hồi từ Máy B.", "error"))

        except socket.timeout:
            self.root.after(0, lambda: self.log(f"[LỖI QUÁ THỜI GIAN] Hết thời gian chờ phản hồi từ Máy B ({ip}:{port}). Hãy chắc chắn đã mở File Server (Port 5001).", "error"))
            self.root.after(0, lambda: messagebox.showerror("Lỗi timeout", f"Không có phản hồi từ Cổng {port} trên Máy B ({ip}).\n\n💡 Kiểm tra: Đã khởi chạy File Server (Port 5001) trên Máy B chưa?"))

        except Exception as exc:
            self.root.after(0, lambda e=exc: self.log(f"[LỖI MẠNG] Không kết nối được tới Máy B ({ip}:{port}) - {e}", "error"))
            self.root.after(0, lambda e=exc: messagebox.showerror("Lỗi truyền tệp", f"Thất bại kết nối Máy B ({ip}:{port}): {e}\n\n💡 Mẹo: Bấm 'Localhost' nếu thử trên 1 máy!"))

        finally:
            self.root.after(0, lambda: self.btn_send.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_browse.config(state=tk.NORMAL))

    def _update_progress(self, val: float):
        self.progress_bar["value"] = val
        self.root.update_idletasks()

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
    app = FileClientGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
