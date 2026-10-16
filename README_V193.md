# PO Intelligence Hub v1.9.3 — UI/UX refactor

## Chạy Windows
Giải nén toàn bộ ZIP, mở RUN_WINDOWS.bat. Python đi kèm; ứng dụng chỉ mở trên máy này.
Nếu đang mở bản cũ, dừng và mở lại server để tải product.css/product.js mới. Có thể dùng Ctrl+F5 sau khi khởi động lại.

## Giao diện mới
- Sidebar gọn trên desktop, menu drawer trên mobile.
- Research: câu trả lời trực tiếp, bảng ứng dụng, nhận xét, nguồn và hỏi tiếp.
- Bấm citation để xem đoạn trích/URL/kỳ trong panel evidence bên phải. Chi tiết listing nằm trong phần mở rộng khi không cần so sánh trực tiếp.
- Menu dấu ⋯ chứa đổi tên, chạy lại, lịch sử và xuất JSON; Hủy luôn hiện khi đang chạy.
- Bản nháp, focus và vị trí đọc được giữ khi kết quả cập nhật.

UI refactor không đổi hợp đồng phân tích 1.9.2 hay điều kiện bằng chứng. Kết quả public có thể là shortlist khi chưa xác minh được thứ hạng; giao diện không tự tạo số liệu.
ZIP có 10 dòng CSV mẫu (5 PoP + 5 YoY), cấu hình sạch, không kèm backup, kết quả test hay dữ liệu cá nhân. Source tại ổ D giữ nguyên database và 7 cấu hình RSS theo yêu cầu.
Codex Auto cần CLI đã đăng nhập và cho phép trong Settings; Manual giữ một handoff. Không có lượt AI mới nào được chạy chỉ để làm UI.
