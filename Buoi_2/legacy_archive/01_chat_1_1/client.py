"""Bài 1 - Client chat 1:1 bằng TCP.

Hỗ trợ Username handshake (REQ-1), gửi tin nhắn, nhận phản hồi tự động /time (REQ-2), /whoami (REQ-3), và chống rỗng / crash (REQ-4).
"""

import socket
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PORT = 5000

ENCODING = "utf-8"


def send_line(sock: socket.socket, text: str) -> None:
    sock.sendall((text + "\n").encode(ENCODING))


def recv_line(sock: socket.socket) -> str | None:
    data = bytearray()
    while True:
        try:
            chunk = sock.recv(1)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            return None
        if not chunk:
            return None if not data else data.decode(ENCODING)
        if chunk == b"\n":
            return data.decode(ENCODING).rstrip("\r")
        data.extend(chunk)


def main() -> None:
    server_ip = input("Nhập IPv4 của server [127.0.0.1]: ").strip() or "127.0.0.1"

    # REQ-1: Nhập Username trước hoặc ngay sau khi kết nối
    username = ""
    while not username:
        username = input("Nhập tên của bạn (Username): ").strip()
        if not username:
            print("Tên không được để rỗng. Vui lòng nhập lại.")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        print(f"[CLIENT] Đang kết nối tới {server_ip}:{PORT} ...")
        client.connect((server_ip, PORT))

        # REQ-1: Gửi Username handshake
        send_line(client, username)

        welcome = recv_line(client)
        if welcome:
            print(f"[SERVER] {welcome}")
        else:
            print("[CLIENT] Không nhận được phản hồi chào từ server.")
            return

        print(f"[CLIENT] Local endpoint : {client.getsockname()[0]}:{client.getsockname()[1]}")
        print(f"[CLIENT] Remote endpoint: {client.getpeername()[0]}:{client.getpeername()[1]}\n")

        while True:
            # REQ-4: Chống gửi tin nhắn rỗng
            try:
                message = input("Bạn > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[CLIENT] Đã thoát.")
                break

            if not message:
                print("Không gửi tin nhắn rỗng. Vui lòng nhập lại.")
                continue

            try:
                send_line(client, message)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
                print("[CLIENT] Mất kết nối tới server khi gửi dữ liệu.")
                break

            response = recv_line(client)
            if response is None:
                print("[CLIENT] Server đã đóng kết nối.")
                break

            print(f"{response}")

            if message.lower() == "/quit":
                print("[CLIENT] Phiên chat kết thúc.")
                break


if __name__ == "__main__":
    try:
        main()
    except ConnectionRefusedError:
        print("Không kết nối được: server chưa chạy, sai IP/cổng, hoặc bị firewall chặn.")
    except OSError as exc:
        print(f"Lỗi mạng: {exc}")

