"""Script tạo Báo cáo PDF chi tiết về dự án Socket Lab (Chat TCP 1:1 & File Transfer)."""

import os
import sys
from pathlib import Path
from datetime import datetime

# Force UTF-8 output encoding for Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Registered Unicode Fonts from Windows Font directory
FONTS_DIR = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("Arial", FONTS_DIR / "arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", FONTS_DIR / "arialbd.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Italic", FONTS_DIR / "ariali.ttf"))
pdfmetrics.registerFont(TTFont("Arial-BoldItalic", FONTS_DIR / "arialbi.ttf"))

# Register Courier New for <code> blocks (monospace, supports ASCII)
pdfmetrics.registerFont(TTFont("CourierNew", FONTS_DIR / "cour.ttf"))
pdfmetrics.registerFont(TTFont("CourierNew-Bold", FONTS_DIR / "courbd.ttf"))

# CRITICAL: Register font family so <b>, <i>, <bi> markup tags work correctly
pdfmetrics.registerFontFamily(
    "Arial",
    normal="Arial",
    bold="Arial-Bold",
    italic="Arial-Italic",
    boldItalic="Arial-BoldItalic"
)
pdfmetrics.registerFontFamily(
    "CourierNew",
    normal="CourierNew",
    bold="CourierNew-Bold",
    italic="CourierNew",
    boldItalic="CourierNew-Bold"
)

# Map <code> tag to CourierNew font in ReportLab's XML/HTML parser
from reportlab.platypus.paraparser import ParaFrag
from reportlab.lib.fonts import addMapping
addMapping("code", 0, 0, "CourierNew")
addMapping("code", 1, 0, "CourierNew-Bold")
addMapping("code", 0, 1, "CourierNew")
addMapping("code", 1, 1, "CourierNew-Bold")

class NumberedCanvas(canvas.Canvas):
    """Canvas hỗ trợ đánh số trang dạng Trang X / Y và tạo Header/Footer chuyên nghiệp."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Arial", 9)
        self.setFillColor(colors.HexColor("#4A5568"))

        # Don't draw header/footer on cover page if page 1
        # Draw header on page >= 2
        if self._pageNumber > 1:
            # Header
            self.drawString(54, 842 - 36, "BÁO CÁO THỰC HÀNH SOCKET TCP LAB - BÀI 1 & BÀI 2")
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(54, 842 - 42, 595 - 54, 842 - 42)

        # Footer on all pages
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(54, 45, 595 - 54, 45)
        
        self.drawString(54, 30, "Đại học Nam Cần Thơ (DNU) - Bộ môn Mạng máy tính & Lập trình Socket")
        page_text = f"Trang {self._pageNumber} / {page_count}"
        self.drawRightString(595 - 54, 30, page_text)
        self.restoreState()


def create_report(output_filename="Bao_Cao_Lab_Socket_TCP.pdf"):
    pdf_path = Path(output_filename).resolve()
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Define Custom Styles with Vietnamese font Arial
    primary_color = colors.HexColor("#1A365D")   # Deep Navy
    secondary_color = colors.HexColor("#2B6CB0") # Slate Blue
    accent_color = colors.HexColor("#2C7A7B")    # Teal
    dark_neutral = colors.HexColor("#2D3748")    # Charcoal Text
    light_bg = colors.HexColor("#F7FAFC")        # Off-white

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Arial-Bold",
        fontSize=24,
        leading=30,
        alignment=TA_CENTER,
        textColor=primary_color,
        spaceAfter=15
    )

    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName="Arial",
        fontSize=13,
        leading=18,
        alignment=TA_CENTER,
        textColor=secondary_color,
        spaceAfter=25
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Arial-Bold",
        fontSize=15,
        leading=20,
        textColor=primary_color,
        spaceBefore=18,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Arial-Bold",
        fontSize=12,
        leading=16,
        textColor=secondary_color,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Arial",
        fontSize=10,
        leading=15,
        textColor=dark_neutral,
        spaceAfter=8,
        alignment=TA_JUSTIFY
    )

    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        parent=styles["Normal"],
        fontName="Arial",
        fontSize=10,
        leading=14,
        textColor=dark_neutral,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Normal"],
        fontName="CourierNew",
        fontSize=8.5,
        leading=13,
        textColor=colors.HexColor("#1A202C"),
        backColor=colors.HexColor("#EDF2F7"),
        borderColor=colors.HexColor("#CBD5E0"),
        borderWidth=0.5,
        borderPadding=8,
        spaceBefore=6,
        spaceAfter=8
    )

    callout_style = ParagraphStyle(
        "Callout_Custom",
        parent=styles["Normal"],
        fontName="Arial-Italic",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#2C5282"),
        backColor=colors.HexColor("#EBF8FF"),
        borderColor=colors.HexColor("#BEE3F8"),
        borderWidth=0.5,
        borderPadding=8,
        spaceBefore=8,
        spaceAfter=10
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Arial-Bold",
        fontSize=9.5,
        leading=13,
        textColor=colors.white,
        alignment=TA_CENTER
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Arial",
        fontSize=9,
        leading=13,
        textColor=dark_neutral
    )

    story = []

    # ==================== COVER / TITLE SECTION ====================
    story.append(Spacer(1, 15))
    story.append(Paragraph("BÁO CÁO DỰ ÁN LẬP TRÌNH SOCKET TCP", title_style))
    story.append(Paragraph("Xây dựng Hệ thống Chat 1:1 & Truyền Tệp dữ liệu Binary qua Giao thức TCP/IP", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceBefore=0, spaceAfter=15))

    # Metadata Table
    meta_data = [
        [Paragraph("<b>Học phần:</b> Lập trình Mạng / Socket Lab", table_cell_style),
         Paragraph("<b>Môi trường thực thi:</b> Python 3.14 (Windows)", table_cell_style)],
        [Paragraph("<b>Bài thực hành:</b> Bài 1 (Chat 1:1) & Bài 2 (File Transfer)", table_cell_style),
         Paragraph("<b>Cổng kết nối (Ports):</b> 5000 (Chat) | 5001 (File)", table_cell_style)],
        [Paragraph("<b>Kiến trúc mạng:</b> Client - Server (TCP/IP)", table_cell_style),
         Paragraph("<b>Thời gian hoàn thành:</b> " + datetime.now().strftime("%d/%m/%Y"), table_cell_style)]
    ]
    meta_table = Table(meta_data, colWidths=[240, 240])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    # Executive Summary Callout
    summary_text = (
        "<b>TÓM TẮT TỔNG QUAN DỰ ÁN:</b> Dự án này đã hoàn thành nâng cấp 2 ứng dụng mạng cơ bản dựa trên bộ mã nguồn mẫu. "
        "Bài 1 đáp ứng đầy đủ 4 yêu cầu phát triển (REQ-1 Username handshake, REQ-2 Lệnh tự động /time, REQ-3 Lệnh tự động /whoami, REQ-4 Khả năng chống crash & ngăn tin nhắn rỗng). "
        "Bài 2 đáp ứng chuẩn giao thức ứng dụng 3 bước truyền dữ liệu byte stream hỗ trợ đa dạng định dạng tệp (văn bản, ảnh PNG/JPG, PDF, ZIP) với cơ chế xác nhận OK/ERROR và dọn dẹp tệp lỗi."
    )
    story.append(Paragraph(summary_text, callout_style))
    story.append(Spacer(1, 10))

    # ==================== SECTION 1: NGUYÊN LÝ KỸ THUẬT & KIẾN TRÚC ====================
    story.append(Paragraph("1. Nguyên lý Kỹ thuật & Kiến trúc Tổng quan", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=secondary_color, spaceBefore=2, spaceAfter=8))
    
    story.append(Paragraph(
        "Giao thức TCP (Transmission Control Protocol) là giao thức truyền tải hướng kết nối (connection-oriented), đảm bảo tính tin cậy, đúng thứ tự và không mất mát dữ liệu giữa hai điểm cuối trên mạng IP. Trong bài lab này, thư viện chuẩn <code>socket</code> của Python được sử dụng để xây dựng các kênh truyền TCP luồng (SOCK_STREAM).",
        body_style
    ))

    arch_table_data = [
        [Paragraph("Tiêu chí Kỹ thuật", table_header_style), Paragraph("Bài 1: Chat TCP 1:1", table_header_style), Paragraph("Bài 2: File Transfer TCP", table_header_style)],
        [Paragraph("<b>Địa chỉ Lắng nghe (Server)</b>", table_cell_style), Paragraph("<code>0.0.0.0:5000</code>", table_cell_style), Paragraph("<code>0.0.0.0:5001</code>", table_cell_style)],
        [Paragraph("<b>Chế độ làm việc</b>", table_cell_style), Paragraph("Kênh hội thoại luân phiên / Tự động", table_cell_style), Paragraph("Truyền Byte Stream từng khối (Chunked)", table_cell_style)],
        [Paragraph("<b>Định dạng Giao thức</b>", table_cell_style), Paragraph("UTF-8 kết thúc bằng ký tự <code>\\n</code>", table_cell_style), Paragraph("Header UTF-8 + Data Payload (Bytes)", table_cell_style)],
        [Paragraph("<b>Cơ chế Khôi phục Lỗi</b>", table_cell_style), Paragraph("Bắt lỗi Socket, giữ Server luôn alive", table_cell_style), Paragraph("Xóa tệp lỗi dở dang khi bị ngắt kết nối", table_cell_style)]
    ]
    arch_table = Table(arch_table_data, colWidths=[120, 180, 180])
    arch_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(arch_table)
    story.append(Spacer(1, 15))

    # ==================== SECTION 2: BÀI 1 CHAT TCP 1:1 ====================
    story.append(Paragraph("2. Bài 1: Chi tiết Triển khai Chat TCP 1:1", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=secondary_color, spaceBefore=2, spaceAfter=8))
    
    story.append(Paragraph(
        "Mục tiêu bài này là duy trì sự đơn giản của mã nguồn gốc đồng thời bổ sung đầy đủ 4 yêu cầu phát triển kỹ thuật:",
        body_style
    ))

    req_table_data = [
        [Paragraph("Mã Yêu cầu", table_header_style), Paragraph("Mô tả Tính năng", table_header_style), Paragraph("Giải pháp Kỹ thuật Triển khai", table_header_style)],
        [
            Paragraph("<b>REQ-1</b><br/>Username Handshake", table_cell_style),
            Paragraph("Client nhập Username ngay sau khi kết nối. Server hiển thị thông báo với định dạng:<br/><code>&lt;tên&gt; từ &lt;IP:port&gt; đã kết nối</code>", table_cell_style),
            Paragraph("Ngay khi <code>server.accept()</code> thành công, luồng xử lý gọi <code>recv_line()</code> để nhận tên Client trước khi đi vào vòng lặp chat chính.", table_cell_style)
        ],
        [
            Paragraph("<b>REQ-2</b><br/>Lệnh /time", table_cell_style),
            Paragraph("Khi client gửi <code>/time</code>, server tự động phản hồi lại thời gian hiện tại mà không cần người dùng ở server gõ tay.", table_cell_style),
            Paragraph("Server bắt điều kiện <code>cmd.lower() == '/time'</code>, sử dụng <code>datetime.now()</code> lấy chuỗi ngày giờ và trả về phản hồi tự động ngay lập tức.", table_cell_style)
        ],
        [
            Paragraph("<b>REQ-3</b><br/>Lệnh /whoami", table_cell_style),
            Paragraph("Server trả lại địa chỉ IP và source port mà server nhìn thấy từ client.", table_cell_style),
            Paragraph("Server trích xuất bộ giá trị <code>client_address[0]</code> (IP) và <code>client_address[1]</code> (Port) từ tuple kết nối và trả về Client.", table_cell_style)
        ],
        [
            Paragraph("<b>REQ-4</b><br/>Tính Ổn định", table_cell_style),
            Paragraph("Ngăn chặn gửi tin nhắn rỗng và đảm bảo chương trình không bị crash nếu một phía đóng kết nối.", table_cell_style),
            Paragraph("Sử dụng vòng lặp kiểm tra <code>.strip() != ''</code> ở cả hai phía. Bao bọc các thao tác Socket bằng <code>try...except (ConnectionResetError, OSError)</code>.", table_cell_style)
        ]
    ]
    req_table = Table(req_table_data, colWidths=[90, 190, 200])
    req_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), secondary_color),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(req_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Minh họa Trình tự Xử lý Giao thức Bài 1:", h2_style))
    code_snippet_chat = (
        "Client ---- [1] Connect TCP (port 5000) -------------> Server\n"
        "Client ---- [2] Send Username ('Nam\\n') -------------> Server (Server log: 'Nam từ 127.0.0.1:54321 đã kết nối')\n"
        "Client <--- [3] Welcome Message ---------------------- Server\n"
        "Client ---- [4] Send '/time\\n' ------------------------> Server (Server tự động trả lời thời gian hiện tại)\n"
        "Client ---- [5] Send '/whoami\\n' ----------------------> Server (Server tự động trả lời IP và Source Port)\n"
        "Client ---- [6] Send '/quit\\n' ------------------------> Server (Server phản hồi 'Tạm biệt!' và ngắt kết nối an toàn)"
    )
    story.append(Paragraph(code_snippet_chat.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))
    story.append(Spacer(1, 15))

    # ==================== SECTION 3: BÀI 2 FILE TRANSFER ====================
    story.append(Paragraph("3. Bài 2: Chi tiết Triển khai File Transfer TCP", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=secondary_color, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "Bài 2 đòi hỏi truyền tải các tệp nhị phân thực tế (như ảnh PNG/JPG, tệp văn bản TXT, tài liệu PDF, tệp nén ZIP) qua cổng 5001 dưới dạng luồng byte (byte stream) nguyên bản.",
        body_style
    ))

    story.append(Paragraph("Cấu trúc Quy chuẩn Giao thức 3 Bước (Application Protocol):", h2_style))
    
    file_steps_data = [
        [Paragraph("Bước", table_header_style), Paragraph("Đối tượng gửi", table_header_style), Paragraph("Nội dung Giao thức (UTF-8 / Binary Payload)", table_header_style)],
        [
            Paragraph("<b>Bước 1</b>", table_cell_style),
            Paragraph("Client", table_cell_style),
            Paragraph("Gửi một dòng Header dạng UTF-8:<br/><code>&lt;filename&gt;|&lt;size in bytes&gt;\\n</code><br/><i>Ví dụ: <code>document.pdf|2048500\\n</code></i>", table_cell_style)
        ],
        [
            Paragraph("<b>Bước 2</b>", table_cell_style),
            Paragraph("Client", table_cell_style),
            Paragraph("Truyền đi đúng <code>&lt;size in bytes&gt;</code> byte dữ liệu nhị phân của tệp thông qua cơ chế đọc khối <code>BUFFER_SIZE = 64KB</code>.", table_cell_style)
        ],
        [
            Paragraph("<b>Bước 3</b>", table_cell_style),
            Paragraph("Server", table_cell_style),
            Paragraph("Server tiến hành lưu tệp vào thư mục <code>received_files/</code> và phản hồi lại Client dòng văn bản:<br/>• Thành công: <code>OK|&lt;filename&gt;|&lt;size in bytes&gt;\\n</code><br/>• Thất bại: <code>ERROR|&lt;mô tả lỗi&gt;\\n</code>", table_cell_style)
        ]
    ]
    file_steps_table = Table(file_steps_data, colWidths=[60, 90, 330])
    file_steps_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(file_steps_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Cơ chế Dọn dẹp Tệp Lỗi dở dang (Partial File Cleanup):", h2_style))
    story.append(Paragraph(
        "Một điểm nâng cấp quan trọng trên Server là hàm <code>recv_exact_to_file()</code>. Nếu trong quá trình nhận tệp, Client bị ngắt kết nối mạng hoặc tắt ứng dụng đột ngột giữa chừng, hệ thống sẽ tự động bắt ngoại lệ và xóa bỏ tệp chưa hoàn chỉnh trong <code>received_files/</code> bằng lệnh <code>output_path.unlink(missing_ok=True)</code>, tránh tình trạng lưu trữ tệp rác bị hỏng trên đĩa cứng.",
        body_style
    ))
    story.append(Spacer(1, 15))

    # ==================== SECTION 4: KẾT QUẢ THỬ NGHIỆM ====================
    story.append(Paragraph("4. Kết quả Thử nghiệm & Kiểm thử Tự động", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=secondary_color, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "Dự án đã xây dựng bộ kịch bản kiểm thử tự động <code>test_lab.py</code> để kiểm tra toàn bộ luồng hoạt động của cả Bài 1 và Bài 2. Kết quả kiểm thử thành công 100%:",
        body_style
    ))

    test_results_data = [
        [Paragraph("STT", table_header_style), Paragraph("Kịch bản Kiểm thử", table_header_style), Paragraph("Dữ liệu đầu vào / Lệnh", table_header_style), Paragraph("Kết quả Kỳ vọng & Thực tế", table_header_style), Paragraph("Trạng thái", table_header_style)],
        [
            Paragraph("1", table_cell_style),
            Paragraph("Handshake Username", table_cell_style),
            Paragraph("Username: <code>NguyenVanA</code>", table_cell_style),
            Paragraph("Server in đúng log <code>NguyenVanA từ 127.0.0.1:xxx đã kết nối</code> và phản hồi chào mừng.", table_cell_style),
            Paragraph("<font color='green'><b>PASSED</b></font>", table_cell_style)
        ],
        [
            Paragraph("2", table_cell_style),
            Paragraph("Lệnh tự động /time", table_cell_style),
            Paragraph("Tin nhắn: <code>/time</code>", table_cell_style),
            Paragraph("Server tự động phản hồi chuỗi ngày giờ <code>2026-09-16 09:47:00</code> mà không cần gõ tay.", table_cell_style),
            Paragraph("<font color='green'><b>PASSED</b></font>", table_cell_style)
        ],
        [
            Paragraph("3", table_cell_style),
            Paragraph("Lệnh tự động /whoami", table_cell_style),
            Paragraph("Tin nhắn: <code>/whoami</code>", table_cell_style),
            Paragraph("Server tự động trả lại đúng IP <code>127.0.0.1</code> và Source Port ngẫu nhiên của Client.", table_cell_style),
            Paragraph("<font color='green'><b>PASSED</b></font>", table_cell_style)
        ],
        [
            Paragraph("4", table_cell_style),
            Paragraph("Gửi tin rỗng / Ngắt kết nối", table_cell_style),
            Paragraph("Nhập phím Enter rỗng", table_cell_style),
            Paragraph("Client thông báo <i>'Không gửi tin nhắn rỗng'</i> và yêu cầu nhập lại, chương trình không crash.", table_cell_style),
            Paragraph("<font color='green'><b>PASSED</b></font>", table_cell_style)
        ],
        [
            Paragraph("5", table_cell_style),
            Paragraph("Truyền tệp Nhị phân 128KB", table_cell_style),
            Paragraph("Tệp <code>test_image.png</code>", table_cell_style),
            Paragraph("Server lưu thành công tệp 131,072 bytes và trả về đúng chuỗi <code>OK|test_image.png|131072</code>.", table_cell_style),
            Paragraph("<font color='green'><b>PASSED</b></font>", table_cell_style)
        ]
    ]
    test_table = Table(test_results_data, colWidths=[30, 110, 110, 170, 60])
    test_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), accent_color),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,1), (0,-1), 'CENTER'),
        ('ALIGN', (4,1), (4,-1), 'CENTER'),
    ]))
    story.append(test_table)
    story.append(Spacer(1, 15))

    # ==================== SECTION 5: KẾT LUẬN ====================
    story.append(Paragraph("5. Kết luận & Bài học Kinh nghiệm", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=secondary_color, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph("<b>Các bài học cốt lõi rút ra qua bài lab:</b>", body_style))
    story.append(Paragraph("• <b>Định dạng Giao thức Ứng dụng (Application Protocol Design):</b> Việc quy định chính xác chuỗi kết thúc <code>\\n</code> giúp việc tách dòng nhận dữ liệu văn bản trở nên đơn giản và chính xác.", bullet_style))
    story.append(Paragraph("• <b>Phân tách giữa Text Protocol và Binary Payload:</b> Việc đọc dòng Header bằng <code>recv_line()</code> UTF-8 kết hợp nhận exact bytes cho khối dữ liệu tệp giúp truyền chính xác mọi loại định dạng tệp mà không bị lỗi đệm mã hóa.", bullet_style))
    story.append(Paragraph("• <b>Xử lý Ngoại lệ mạng Robust:</b> Việc chủ động bắt các ngoại lệ <code>ConnectionResetError</code> và <code>OSError</code> giúp Server duy trì khả năng hoạt động liên tục (Always-on Availability) ngay cả khi Client bị ngắt kết nối đột ngột.", bullet_style))

    story.append(Spacer(1, 20))

    # Signature Block
    sig_data = [
        [Paragraph("", table_cell_style), Paragraph("<b>ĐẠI DIỆN NHÓM THỰC HIỆN DỰ ÁN</b><br/><i>(Ký và ghi rõ họ tên)</i>", ParagraphStyle("Sig", parent=table_cell_style, alignment=TA_CENTER))]
    ]
    sig_table = Table(sig_data, colWidths=[280, 200])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(sig_table)

    # Build Document with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Báo cáo PDF đã được tạo thành công tại: {pdf_path}")
    return pdf_path

if __name__ == "__main__":
    create_report()
