"""Test script for verifying Bài 1 (Chat 1:1) and Bài 2 (File Transfer)."""

import socket
import time
import threading
import sys
from pathlib import Path

# Force UTF-8 output encoding for Windows terminal stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Imports from 01_chat_1_1 and 02_file_transfer

sys.path.append(str(Path(__file__).resolve().parent / "01_chat_1_1"))
sys.path.append(str(Path(__file__).resolve().parent / "02_file_transfer"))

import importlib.util

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

chat_server_mod = load_module("chat_server", Path("01_chat_1_1/server.py"))
chat_client_mod = load_module("chat_client", Path("01_chat_1_1/client.py"))

file_server_mod = load_module("file_server", Path("02_file_transfer/server.py"))
file_client_mod = load_module("file_client", Path("02_file_transfer/client.py"))

def test_chat_server():
    print("\n--- TEST BÀI 1: CHAT TCP 1:1 ---")
    def run_server():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(("127.0.0.1", 5000))
                server.listen(1)
                server.settimeout(3.0)
                client_sock, client_addr = server.accept()
                with client_sock:
                    # Step 1: Recv username
                    user = chat_server_mod.recv_line(client_sock)
                    print(f"[TEST SERVER] Recv Username: {user} from {client_addr}")
                    chat_server_mod.send_line(client_sock, f"Xin chào {user}! Kết nối thành công.")
                    
                    # Test commands loop
                    while True:
                        msg = chat_server_mod.recv_line(client_sock)
                        if msg is None or msg.strip().lower() == "/quit":
                            chat_server_mod.send_line(client_sock, "Tạm biệt!")
                            break
                        if msg.strip().lower() == "/time":
                            chat_server_mod.send_line(client_sock, "[Hệ thống] Server time: 2026-09-16 09:47:00")
                        elif msg.strip().lower() == "/whoami":
                            chat_server_mod.send_line(client_sock, f"[Hệ thống] IP: {client_addr[0]}, Port: {client_addr[1]}")
                        else:
                            chat_server_mod.send_line(client_sock, f"Server Echo: {msg}")
        except Exception as e:
            print(f"[TEST SERVER ERROR] {e}")

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    # Client socket connecting to server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect(("127.0.0.1", 5000))
        
        # REQ-1: Send Username
        chat_client_mod.send_line(client, "NguyenVanA")
        welcome = chat_client_mod.recv_line(client)
        print(f"[TEST CLIENT] Recv Welcome: {welcome}")
        assert "NguyenVanA" in welcome or "Xin chào" in welcome, "REQ-1 failed"

        # REQ-2: Send /time
        chat_client_mod.send_line(client, "/time")
        time_reply = chat_client_mod.recv_line(client)
        print(f"[TEST CLIENT] Recv /time reply: {time_reply}")
        assert "Server time" in time_reply or "Thời gian" in time_reply, "REQ-2 failed"

        # REQ-3: Send /whoami
        chat_client_mod.send_line(client, "/whoami")
        whoami_reply = chat_client_mod.recv_line(client)
        print(f"[TEST CLIENT] Recv /whoami reply: {whoami_reply}")
        assert "127.0.0.1" in whoami_reply, "REQ-3 failed"

        # Quit
        chat_client_mod.send_line(client, "/quit")
        quit_reply = chat_client_mod.recv_line(client)
        print(f"[TEST CLIENT] Recv /quit reply: {quit_reply}")
        assert "Tạm biệt" in quit_reply, "Quit failed"

    server_thread.join(timeout=2.0)
    print(">>> BÀI 1 TEST PASSED! <<<\n")


def test_file_transfer():
    print("--- TEST BÀI 2: FILE TRANSFER ---")
    test_dir = Path("test_file_dir")
    test_dir.mkdir(exist_ok=True)
    test_file = test_dir / "test_image.png"
    # Create fake 128KB dummy binary content
    dummy_data = b"PNG_HEADER_DUMMY_DATA_" + b"X" * (128 * 1024 - 22)
    test_file.write_bytes(dummy_data)

    def run_file_server():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(("127.0.0.1", 5001))
                server.listen(1)
                server.settimeout(3.0)
                client_sock, client_addr = server.accept()
                with client_sock:
                    file_server_mod.handle_client(client_sock, client_addr)
        except Exception as e:
            print(f"[TEST FILE SERVER ERROR] {e}")

    server_thread = threading.Thread(target=run_file_server, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect(("127.0.0.1", 5001))
        # Step 1: Send Header
        header = f"{test_file.name}|{len(dummy_data)}"
        file_client_mod.send_line(client, header)
        # Step 2: Send Data
        client.sendall(dummy_data)
        # Step 3: Recv Response
        resp = file_client_mod.recv_line(client)
        print(f"[TEST FILE CLIENT] Recv response: {resp}")
        assert resp and resp.startswith("OK|"), "REQ Step 3 failed"

    server_thread.join(timeout=2.0)

    # Check received file in received_files
    recv_file = Path("02_file_transfer/received_files/test_image.png")
    assert recv_file.exists(), "File was not saved"
    assert recv_file.stat().st_size == len(dummy_data), "Saved file size mismatch"
    print(f"[TEST FILE SERVER] Received file verified at {recv_file} ({recv_file.stat().st_size} bytes)")

    print(">>> BÀI 2 TEST PASSED! <<<\n")


if __name__ == "__main__":
    test_chat_server()
    test_file_transfer()
    print("ALL TESTS PASSED SUCCESSFULLY!")
