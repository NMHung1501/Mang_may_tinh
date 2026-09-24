# 💬 DNU Socket TCP Lab — Ứng dụng Chat & Gửi File qua Mạng

Ứng dụng truyền tin Socket TCP giữa **Máy A (Client)** và **Máy B (Server)**, cho phép nhắn tin văn bản và gửi tệp nhị phân qua mạng LAN hoặc trên cùng 1 máy tính.

---

## 📋 Yêu cầu

- Python 3.10 trở lên
- Windows (dùng thư viện `winsound` cho âm thanh thông báo)
- Không cần cài thêm thư viện ngoài

---

## 📂 Cấu trúc Dự án

```
DNU_Buoi2_Socket_Lab/
│
├── 🖥️ server.py              → Chạy trên MÁY B (Server lắng nghe kết nối)
├── 💬 client.py              → Chạy trên MÁY A (Client gửi tin nhắn, file)
│
├── 📂 received_files/        → Thư mục tự động lưu tệp nhận được
├── 📄 generate_pdf_report.py → Script tạo Báo cáo PDF
├── 📑 Bao_Cao_Lab_Socket_TCP.pdf
└── 📁 legacy_archive/        → Code cũ (lưu trữ)
```

---

## 🚀 Hướng dẫn Sử dụng

### Trường hợp 1: Chạy trên 2 máy tính trong cùng mạng LAN

#### Bước 1 — Trên Máy B (Server):
```bash
python server.py
```
- Cửa sổ **MÁY B** mở ra, tự động bắt đầu lắng nghe
- **Chú ý địa chỉ IP hiển thị** (ví dụ: `192.168.1.10`) → gửi cho Máy A

#### Bước 2 — Trên Máy A (Client):
```bash
python client.py
```
- Cửa sổ **MÁY A** mở ra
- Nhập IP của Máy B vào ô **"IP Máy B"**
- Bấm nút **🔌 KẾT NỐI TỚI MÁY B**
- Khi thấy 🟢 → kết nối thành công!

---

### Trường hợp 2: Chạy thử nghiệm trên 1 máy tính

```bash
# Cửa sổ Terminal thứ nhất:
python server.py

# Cửa sổ Terminal thứ hai:
python client.py
```
- Trên cửa sổ Máy A → bấm **⚡ Cùng máy** (tự điền `127.0.0.1`)
- Bấm **🔌 KẾT NỐI TỚI MÁY B**

---

## 💬 Cách Nhắn Tin & Gửi File

| Tính năng | Cách làm |
|-----------|----------|
| **Gửi tin nhắn** | Nhập vào ô phía dưới → nhấn **Enter** hoặc bấm **Gửi 📤** |
| **Gửi file** | Bấm **📎 Gửi File** → chọn file bất kỳ |
| **Xem file đã nhận** | Bấm **📁 Xem File Đã Nhận** hoặc mở thư mục `received_files/` |
| **Xóa lịch sử chat** | Bấm **🗑️ Xóa chat** |
| **Xem hướng dẫn** | Bấm **❓ Hướng dẫn** trong ứng dụng |

---

## ✨ Tính năng Nổi bật

- 🌐 **Hiển thị IP tự động** — Biết ngay IP máy mình mà không cần mở CMD
- 📋 **Nút Copy IP** — Sao chép IP một chạm để chia sẻ với đối phương
- 📊 **Thanh tiến trình** — Xem % tiến độ khi gửi/nhận file lớn
- 🔔 **Âm thanh thông báo** — Nghe tiếng *bíp* khi có tin nhắn hoặc file mới
- 💡 **Tooltip hướng dẫn** — Rê chuột vào bất kỳ nút nào để xem giải thích
- 📖 **Hướng dẫn trong app** — Bấm ❓ bất kỳ lúc nào để xem lại cách dùng
- 🗑️ **Xóa lịch sử chat** — Dọn màn hình khi cần
- ❌ **Thông báo lỗi rõ ràng** — Khi lỗi kết nối, hiện hướng dẫn cụ thể cách khắc phục

---

## 🔧 Xử lý Lỗi Thường Gặp

| Lỗi | Nguyên nhân | Cách khắc phục |
|-----|------------|----------------|
| `Cổng 5000 đang bận` | server.py đang chạy ở cửa sổ khác | Đóng cửa sổ server.py cũ, chạy lại |
| `Kết nối thất bại` | Máy B chưa chạy hoặc sai IP | Kiểm tra Máy B đã bấm "BẮT ĐẦU" chưa |
| `Hết thời gian kết nối` | Firewall chặn hoặc không cùng mạng | Tắt Firewall hoặc kiểm tra mạng LAN |
| Máy A không thấy IP Máy B | — | Trên Máy B, bấm 📋 Copy IP rồi gửi sang |
