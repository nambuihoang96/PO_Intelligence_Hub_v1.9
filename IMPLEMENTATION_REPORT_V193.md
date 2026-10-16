# UI/UX v1.9.3 — bàn giao

## Source và thiết kế
Sửa trực tiếp tại D:\AI\PO Analysis\PO_Intelligence_Hub_v1.9, nhánh testagent. Giữ thay đổi đã có; không commit hoặc đổi nhánh.
Áp dụng UI/UX Pro Max và Web Design Guidelines, theo hướng được chọn: shell gọn kiểu Linear + nội dung đọc kiểu Notion. Không thêm framework, thư viện, font ngoài hay dịch vụ mới.
`product.css` là lớp token/component cuối sau các stylesheet tương thích. `product.js` quản lý shell, menu, mobile dialog và giữ trạng thái UI. Server chỉ bổ sung hai đường dẫn static; API nghiệp vụ và SQLite không đổi.

## Hoàn thành
- Sáu mục điều hướng giữ nguyên; sidebar desktop 232px, native drawer dưới 768px, Escape/focus hoạt động.
- Typography, màu, spacing, button/form/table/empty/error dùng cùng hệ thống. Composer có nút CSV rõ ràng, Auto/Manual thống nhất và một nút submit.
- Research có câu trả lời trực tiếp, bảng app/căn cứ, mục lục desktop, claim không lặp, citation đánh số theo lần xuất hiện và panel evidence. So sánh giữ facts hiển thị; listing phụ có thể mở rộng.
- Menu ⋯ chứa thao tác phụ; nút Hủy vẫn thấy khi chạy. Hỏi tiếp và Action/Opportunity giữ research/finding/evidence gốc.
- Draft/cursor/focus/menu/scroll được giữ khi cập nhật cùng phiên. Ngày giờ hiển thị theo Intl; kỳ so sánh không chiếm header của câu hỏi không cần growth.
- Overview dùng cùng token, panel phụ không giãn thành khối rỗng lớn; research gần đây có vùng cuộn riêng. Data Library, Decisions, Work Queue, Settings thống nhất component.

## Kiểm thử
- 123 Python regression qua; hai bộ parser Node qua.
- 17 browser regression Research và 11 dashboard qua. Test cập nhật để mở menu thao tác/mobile theo UI mới; nghiệp vụ import, Manual JSON, Auto fixture, Action, Opportunity, reload và deep-link giữ nguyên.
- 10 acceptance UI qua trên bản sao kết quả live đã lưu: app/answer giữ nguyên; claim ID không lặp; citation/evidence; menu keyboard; draft/focus; 1440/1024/390; mobile drawer và sáu màn hình; một submit CTA; labels/contrast CTA >=4.5/reduced motion; không lỗi JavaScript hoặc thay đổi kết quả.
- Regression phát hiện lỗi click form do trùng data-run với delegate cũ; đã đổi thành data-rendered-run. Hủy được giữ ngoài menu sau lần kiểm tra đầu. Các lần kiểm tra cuối đều qua.
- Ảnh trước: research-v192-live-top.png. Ảnh sau: research-v193-desktop.png, research-v193-first-screen.png, research-v193-mobile.png; có ảnh Overview, composer và evidence. Tất cả ảnh sau dùng kết quả đã lưu; không dùng fixture để tạo cảm giác có metric thị trường.
- Không chạy AI/discovery mới cho việc refactor. Chart vẫn phản ánh dữ liệu thật; thiếu dữ liệu vẫn nói rõ.

## Dữ liệu và giới hạn
Không thay đổi database source, không xóa thêm RSS, không migrate hoặc quét lại dataset. ZIP dùng 10 dòng mẫu và cấu hình sạch theo quy trình đóng gói đã có; không mang backup/config cá nhân vào ZIP.
Chất lượng/độ phủ insight vẫn theo báo cáo v1.9.2; refactor UI không tạo thêm ranking hoặc dữ liệu market. Report schema cũ vẫn dùng bộ đọc tương thích, được hưởng shell/design tokens mới.
Smoke test ZIP phải giải nén, chạy Python đi kèm, tải trang và các asset mới; kết quả và SHA-256 ở release-checks-v193.json.
