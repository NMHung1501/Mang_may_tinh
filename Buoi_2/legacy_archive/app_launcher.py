"""Khởi chạy ứng dụng Zalo/Messenger Socket TCP Hợp nhất."""

import tkinter as tk
from app import ZaloMessengerApp

if __name__ == "__main__":
    root = tk.Tk()
    app = ZaloMessengerApp(root)
    root.mainloop()

