"""Bài 2 - GUI Server Nhận Tệp TCP (Dành cho MÁY B - FILE SERVER NHẬN TỆP)."""

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
PORT = 5001
ENCODING = "utf-8"
BUFFER_SIZE = 64 * 1024
SAVE_DIR = Path(__file__).resolve().parent / "received_files"


class FileServerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MÁY B: FILE SERVER NHẬN TỆP (Cổng 5001)")
        self.root.geometry("680x580")
        self.root.minsize(580, 480)

        self.server_sock: socket.socket | None = None
        self.is_running = False
        self.listen_thread: threading.Thread | None = None

        SAVE_DIR.mkdir(parents=True, exist_ok=True)

        self._build_ui()
        self.refresh_files_list()
        # Auto-start file server on launch
        self.root.after(300, lambda: self.start_server(is_manual=False))

    def _build_ui(self):
        # Header Banner
        header = tk.Frame(self.root, bg="#2C7A7B", padx=12, pady=10)
        header.pack(fill=tk.X)

        tk.Label(header, text="📥 MÁY B: FILE SERVER NHẬN TỆP (PORT 5001)", font=("Segoe UI", 13, "bold"), fg="#FFFFFF", bg="#2C7A7B").pack(anchor=tk.W)
        tk.Label(header, text="Máy B đóng vai trò SERVER NHẬN TỆP - Lưu trữ các tệp nhị phân truyền từ Máy A (Client)", font=("Segoe UI", 9), fg="#E6FFFA", bg="#2C7A7B").pack(anchor=tk.W, pady=(2, 0))

        # Controls & Config
        ctrl_frame = tk.Frame(self.root, bg="#F7FAFC", padx=10, pady=8)
        ctrl_frame.pack(fill=tk.X)

        tk.Label(ctrl_frame, text="Host:", font=("Segoe UI", 9, "bold"), bg="#F7FAFC").grid(row=0, column=0, sticky=tk.W)
        self.host_entry = tk.Entry(ctrl_frame, font=("Segoe UI", 9), width=10)
        self.host_entry.insert(0, HOST)
        self.host_entry.grid(row=0, column=1, padx=4)

        tk.Label(ctrl_frame, text="Port:", font=("Segoe UI", 9, "bold"), bg="#F7FAFC").grid(row=0, column=2, sticky=tk.W, padx=(8, 0))
        self.port_entry = tk.Entry(ctrl_frame, font=("Segoe UI", 9), width=6)
        self.port_entry.insert(0, str(PORT))
        self.port_entry.grid(row=0, column=3, padx=4)

        self.btn_toggle = tk.Button(ctrl_frame, text="🚀 BẮT ĐẦU LẮNG NGHE", font=("Segoe UI", 9, "bold"), bg="#38A169", fg="#FFFFFF", activebackground="#2F855A", activeforeground="#FFFFFF", padx=8, command=self.toggle_server)
        self.btn_toggle.grid(row=0, column=4, padx=8)

        self.btn_open_folder = tk.Button(ctrl_frame, text="📁 Mở thư mục received_files", font=("Segoe UI", 9, "bold"), bg="#EDF2F7", fg="#2D3748", activebackground="#CBD5E0", command=self.open_received_folder)
        self.btn_open_folder.grid(row=0, column=5, padx=4)

        # Status Label
        status_frame = tk.Frame(self.root, bg="#EDF2F7", padx=10, pady=5, bd=1, relief=tk.SOLID)
        status_frame.pack(fill=tk.X, padx=10, pady=4)
        self.status_label = tk.Label(status_frame, text="🔴 File Server đã dừng", font=("Segoe UI", 9, "bold"), fg="#E53E3E", bg="#EDF2F7")
        self.status_label.pack(side=tk.LEFT)

        # Received Files List Frame
        files_frame = tk.LabelFrame(self.root, text=" Tệp Máy B đã nhận từ Máy A (lưu trong received_files) ", font=("Segoe UI", 9, "bold"), fg="#2C7A7B", bg="#F7FAFC", padx=8, pady=6)
        files_frame.pack(fill=tk.X, padx=10, pady=4)

        self.files_tree = ttk.Treeview(files_frame, columns=("name", "size", "time"), show="headings", height=4)
        self.files_tree.heading("name", text="Tên Tệp Đã Nhận")
        self.files_tree.heading("size", text="Dung Lượng")
        self.files_tree.heading("time", text="Thời Gian Lưu")
        self.files_tree.column("name", width=250)
        self.files_tree.column("size", width=120, anchor=tk.E)
        self.files_tree.column("time", width=180, anchor=tk.CENTER)
        self.files_tree.pack(fill=tk.BOTH, expand=True)

        # Log Frame
        log_frame = tk.Frame(self.root, bg="#F7FAFC", padx=10, pady=4)
        log_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(log_frame, text="Nhật ký Nhận Tệp & Xác Nhận Giao Thức (OK / ERROR):", font=("Segoe UI", 9, "bold"), fg="#2B6CB0", bg="#F7FAFC").pack(anchor=tk.W, pady=(2, 4))

        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=("Segoe UI", 9), state=tk.DISABLED, bg="#FFFFFF", fg="#2D3748")
        self.log_area.pack(fill=tk.BOTH, expand=True)

        self.log_area.tag_config("info", foreground="#2B6CB0")
        self.log_area.tag_config("success", foreground="#38A169", font=("Segoe UI", 9, "bold"))
        self.log_area.tag_config("error", foreground="#E53E3E", font=("Segoe UI", 9, "bold"))
        self.log_area.tag_config("system", foreground="#D69E2E", font=("Segoe UI", 9, "bold"))

    def log(self, text: str, tag: str = "normal"):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, text + "\n", tag)
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

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
            self.status_label.config(text=f"🟢 Máy B đang lắng nghe cổng {port}", fg="#38A169")
            self.log(f"[FILE SERVER MÁY B] Đã khởi chạy lắng nghe tại {host}:{port}. Lưu tệp tại: {SAVE_DIR}", "system")

            self.listen_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.listen_thread.start()

        except Exception as exc:
            self.server_sock = None
            if is_manual:
                messagebox.showerror("Lỗi File Server Máy B", f"Không thể bind tại {host}:{port}\n\nCổng {port} đang được sử dụng bởi một ứng dụng/cửa sổ khác!\n\nLỗi chi tiết: {exc}")
            else:
                self.status_label.config(text=f"🟡 Cổng {port} đang được mở bởi File Server khác!", fg="#D69E2E")
                self.log(f"[THÔNG BÁO] Cổng {port} đang có File Server khác mở. Bấm 'Bắt đầu' khi muốn thử lại.", "system")

    def stop_server(self):
        self.is_running = False
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
            self.server_sock = None

        self.btn_toggle.config(text="🚀 BẮT ĐẦU LẮNG NGHE", bg="#38A169", fg="#FFFFFF", activebackground="#2F855A")
        self.status_label.config(text="🔴 File Server đã dừng", fg="#E53E3E")
        self.log("[FILE SERVER MÁY B] Đã dừng server.", "system")

    def _accept_loop(self):
        while self.is_running and self.server_sock:
            try:
                client_sock, client_addr = self.server_sock.accept()
                if not self.is_running:
                    break

                with client_sock:
                    self._handle_client_file(client_sock, client_addr)

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
        self.root.after(0, lambda f=filename, s=size, i=ip, p=port: self.log(f"[BƯỚC 1 HEADER] Nhận '{f}' ({s:,} bytes) từ Máy A ({i}:{p})", "info"))

        # Recv bytes to file
        try:
            received = 0
            remaining = size
            with out_path.open("wb") as f_out:
                while remaining > 0:
                    chunk = client_sock.recv(min(BUFFER_SIZE, remaining))
                    if not chunk:
                        raise ConnectionError("Máy A ngắt kết nối dở dang.")
                    f_out.write(chunk)
                    received += len(chunk)
                    remaining -= len(chunk)

            self.root.after(0, lambda p=out_path.name, r=received: self.log(f"[BƯỚC 2 ĐÃ LƯU] Thành công: {p} ({r:,} bytes)", "success"))

            # Step 3 Response
            ok_line = f"OK|{out_path.name}|{received}\n"
            client_sock.sendall(ok_line.encode(ENCODING))
            self.root.after(0, lambda o=ok_line.strip(): self.log(f"[BƯỚC 3 XÁC NHẬN] Trả về '{o}' cho Máy A", "success"))

            self.root.after(0, self.refresh_files_list)

        except Exception as exc:
            if out_path.exists():
                out_path.unlink(missing_ok=True)
            err_line = f"ERROR|{exc}\n"
            try:
                client_sock.sendall(err_line.encode(ENCODING))
            except Exception:
                pass
            self.root.after(0, lambda e=exc: self.log(f"[LỖI XỬ LÝ] {e} (Đã dọn dẹp tệp dở dang)", "error"))

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
    app = FileServerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
