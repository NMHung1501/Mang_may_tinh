"""Bài 1 - Server chat 1:1 bằng TCP.

Lắng nghe trên cổng 5000.
Hỗ trợ Username handshake (REQ-1), /time (REQ-2), /whoami (REQ-3), và tính ổn định (REQ-4).
"""

import socket
import sys
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HOST = "0.0.0.0"

PORT = 5000
ENCODING = "utf-8"


def send_line(sock: socket.socket, text: str) -> None:
    """Gửi một thông điệp kết thúc bằng ký tự xuống dòng."""
    sock.sendall((text + "\n").encode(ENCODING))


def recv_line(sock: socket.socket) -> str | None:
    """Nhận đúng một dòng. Trả về None nếu phía bên kia đã đóng kết nối."""
    data = bytearray()
    while True:
        chunk = sock.recv(1)
        if not chunk:
            return None if not data else data.decode(ENCODING)
        if chunk == b"\n":
            return data.decode(ENCODING).rstrip("\r")
        data.extend(chunk)


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(5)

        print(f"[SERVER] Đang lắng nghe tại 0.0.0.0:{PORT}")
        print("[SERVER] Nhấn Ctrl+C để dừng server.\n")

        while True:
            try:
                client_socket, client_address = server.accept()
            except KeyboardInterrupt:
                print("\n[SERVER] Đã dừng server.")
                break
            except Exception as exc:
                print(f"[SERVER] Lỗi accept: {exc}")
                continue

            with client_socket:
                try:
                    # REQ-1: Username Handshake
                    username = recv_line(client_socket)
                    if not username or not username.strip():
                        print(f"[SERVER] Kết nối từ {client_address[0]}:{client_address[1]} không gửi username. Ngắt kết nối.")
                        continue

                    username = username.strip()
                    ip, port = client_address[0], client_address[1]
                    print(f"[SERVER] {username} từ {ip}:{port} đã kết nối")
                    send_line(client_socket, f"Xin chào {username}! Kết nối thành công. Gõ /time, /whoami, hoặc /quit.")

                    # Chat loop
                    while True:
                        message = recv_line(client_socket)
                        if message is None:
                            print(f"[SERVER] Client {username} ({ip}:{port}) đã đóng kết nối.")
                            break

                        text = message.strip()
                        if not text:
                            continue

                        # REQ-4 & Lệnh /quit
                        if text.lower() == "/quit":
                            send_line(client_socket, "Tạm biệt!")
                            print(f"[SERVER] Client {username} đã ngắt kết nối (/quit).")
                            break

                        # REQ-2: Lệnh /time
                        if text.lower() == "/time":
                            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            reply = f"[Hệ thống] Thời gian hiện tại của server: {now_str}"
                            send_line(client_socket, reply)
                            print(f"[SERVER Auto-Reply] Đã gửi /time ({now_str}) tới {username}")
                            continue

                        # REQ-3: Lệnh /whoami
                        if text.lower() == "/whoami":
                            reply = f"[Hệ thống] Địa chỉ IP: {ip}, Source Port: {port}"
                            send_line(client_socket, reply)
                            print(f"[SERVER Auto-Reply] Đã gửi /whoami ({ip}:{port}) tới {username}")
                            continue

                        # Tin nhắn thông thường
                        print(f"{username} > {text}")

                        # Nhập phản hồi từ server, chống tin nhắn rỗng (REQ-4)
                        while True:
                            try:
                                reply = input("Server > ").strip()
                            except (EOFError, KeyboardInterrupt):
                                reply = ""
                                break
                            if reply:
                                break
                            print("Không gửi tin nhắn rỗng. Vui lòng nhập lại.")

                        if not reply:
                            print(f"[SERVER] Đóng phiên chat với {username}.")
                            break

                        send_line(client_socket, reply)

                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as exc:
                    print(f"[SERVER] Client {client_address[0]}:{client_address[1]} đã ngắt kết nối đột ngột ({exc}).")
                except Exception as exc:
                    print(f"[SERVER] Lỗi trong phiên chat với client: {exc}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[SERVER] Đã dừng.")

