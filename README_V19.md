# PO Intelligence Hub v1.9

Giải nén toàn bộ ZIP vào thư mục có quyền ghi, rồi mở **RUN_WINDOWS.bat**. Bản Windows ZIP kèm Python 3.12 và thư viện chuẩn; không cần cài Python riêng. App mở ở http://127.0.0.1:8765. Đóng cửa sổ server để dừng app.

## Nghiên cứu

1. Chọn **Nghiên cứu mới**, nhập câu hỏi; có thể đính kèm CSV.
2. Chọn **Codex Auto** hoặc **ChatGPT Manual**. Lựa chọn được ghi nhớ trên trình duyệt.
3. Bấm **Nghiên cứu**. Câu trả lời, tiến độ, nguồn và lỗi cập nhật cùng trang.

**Auto:** Cài Codex CLI, đăng nhập bằng ChatGPT, kiểm tra và bật cho phép trong Settings. Một lần bấm chạy cả lập scope/discovery strategy, thu thập, đánh giá và phân tích. App không chuyển sang Manual khi Auto lỗi. JSON sai hợp đồng được yêu cầu AI sửa một lần; nếu vẫn lỗi, evidence được giữ lại và có Thử lại bước lỗi.

**Manual:** App tự chuẩn bị evidence. Bấm Copy dữ liệu sang ChatGPT, dán vào ChatGPT rồi dán JSON trả về vào app. Không có bước copy planner riêng.

Phạm vi trong câu hỏi được ưu tiên. Mặc định US, 30 ngày gần nhất so với 30 ngày trước. Phạm vi thực tế luôn hiển thị trên kết quả. Scope Manual dựa trên bộ nhận diện câu hỏi tại local; Auto có thêm AI hiểu chủ đề và đề xuất truy vấn. Với câu hỏi mơ hồ, hãy ghi rõ chủ đề trong câu hỏi và kiểm tra scope hiển thị.

## Dữ liệu và giới hạn

- CSV dùng parser hiện có cho export Top Apps PoP/YoY: cần ID, category, platform, GEO và kỳ có thể xác định từ dữ liệu/tên file. Không có dữ liệu Sensor Tower đóng gói sẵn.
- Dataset gắn với research tự được kiểm tra; dữ liệu sai GEO/OS/kỳ/chủ đề bị loại và có lý do. Tên chứa chủ đề nhưng thiếu mô tả được ghi là **có thể liên quan**, cần xác minh.
- Filter, sort và Top N ở Data Library chỉ thay đổi bảng. **Phân tích tập đang chọn** mới tạo phiên có tập evidence giới hạn rõ ràng.
- Apple Search trả tối đa 25 kết quả/truy vấn; Google Play collector hiện có trả tối đa 15. Đây là độ phủ search, không phải toàn bộ thị trường. Mọi ứng viên thu về đều được đánh giá; không còn cắt ngầm 70 ứng viên.
- AI packet có ngân sách 180.000 ký tự cho evidence, ưu tiên thứ tự evidence đã lưu. Số dùng/chưa dùng được công bố; không tự suy rộng phần chưa đưa vào AI.
- Google Play là connector tùy chọn; nếu chưa cài, app báo thiếu coverage. Bản ZIP kèm thư viện chuẩn Python, chưa kèm connector này. RSS hiện có được giữ lại làm context.
- Một snapshot listing không đủ kết luận trending. Chỉ tính thay đổi với kỳ CSV/snapshot so sánh phù hợp. Downloads ước tính/reviews không chứng minh UA có lợi nhuận.

## Nâng cấp dữ liệu cũ

Source hiện hữu đã được cập nhật mà không ghi vào database đang dùng. Khi chạy server mới lần đầu, app sao lưu SQLite vào **data/backups/research-pre-v19-*.sqlite3**, rồi thêm bảng mới; giữ ID và dữ liệu v1.5–v1.8.

ZIP là bản sạch, không có database riêng của bạn. Nếu dùng ZIP để thay app cũ, dừng app cũ trước, sao lưu cả thư mục cũ, rồi giữ/copy thư mục **data** của bản cũ vào bản đã giải nén trước khi chạy. Không copy database khi server còn chạy.

Research cũ mở trong giao diện mới với dữ liệu nguyên trạng. Chưa có kết quả v1.9 sẽ được ghi rõ; không tự tạo insight thay thế. API cũ và các tài nguyên cũ vẫn có để tương thích. Link report/analysis cũ mở bản chụp lịch sử. Action từ v1.9 trỏ đúng phiên/finding/evidence.

Kết quả từng phiên và evidence được lưu trong SQLite. Có Hủy, Thử lại bước lỗi, Chạy lại (giữ lịch sử), đổi tên ngắn và xuất JSON. Sau khi server bị dừng giữa lượt, mở lại và bấm Thử lại để tiếp tục; Manual đang chờ nhập kết quả vẫn được giữ.
