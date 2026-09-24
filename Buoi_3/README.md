# Buoi 3 - QM Meet

Ung dung hop truc tuyen don gian voi FastAPI, WebSocket va giao dien web tinh.

## Tinh nang

- Vao phong nhanh bang ten hien thi va ma phong.
- Dang ky va dang nhap tai khoan trong bo nho cua ung dung.
- Ho tro ket noi nhieu thanh vien trong cung mot phong.
- Truyen tin hieu WebRTC qua WebSocket de phuc vu hop video.
- Hien thi thong tin thanh vien, avatar va xu ly su kien tham gia/roi phong.

## Cau truc du an

```text
Buoi_3/
|-- Web_cam/
|   |-- main.py
|   |-- requirements.txt
|   `-- static/
|       |-- index.html
|       |-- script.js
|       `-- style.css
|-- Mang_may_tinh_B3.docx
`-- README.md
```

## Yeu cau

- Python 3.9 tro len
- Trinh duyet co ho tro camera, microphone va WebSocket

## Cai dat va chay ung dung

1. Mo PowerShell tai thu muc `Web_cam`:

   ```powershell
   cd Web_cam
   ```

2. Tao moi truong ao va kich hoat:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Cai dat cac thu vien:

   ```powershell
   pip install -r requirements.txt
   ```

4. Khoi dong may chu:

   ```powershell
   python main.py
   ```

5. Mo `http://localhost:8000` tren trinh duyet. De thu hop nhieu nguoi, mo cung dia chi phong tren cac tab hoac thiet bi khac trong cung mang.

## Luu y

- Du lieu tai khoan chi duoc luu tam thoi trong bo nho va se mat khi khoi dong lai may chu.
- Camera va microphone can duoc cap quyen cho trang web.
- Day la ung dung hoc tap; chua co co che xac thuc va ma hoa phu hop cho moi truong production.