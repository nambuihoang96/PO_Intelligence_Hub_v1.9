# PO Intelligence Hub v1.9.1

Giải nén toàn bộ ZIP vào thư mục có quyền ghi, mở **RUN_WINDOWS.bat**. ZIP kèm Python 3.12 và thư viện chuẩn; không cần cài Python riêng. App chạy local tại http://127.0.0.1:8765.

Nếu bản cũ đang chạy, đóng cửa sổ server cũ trước khi mở bản mới. Cập nhật source không thay đổi code đang nằm trong tiến trình cũ.

## Overview

Overview là dashboard từ dữ liệu đã lưu: bốn chỉ số vận hành, biểu đồ, ma trận chủ đề, app có bằng chứng tăng trưởng, vấn đề nguồn, quyết định và research gần đây. Mở dashboard không gọi AI hoặc thu thập mạng.

- Bộ lọc chủ đề/GEO/platform/hoạt động research được lưu và đồng bộ URL. Khoảng 7/30/60/90/180/365 ngày là **thời gian hoạt động research**; kỳ metric được ghi theo từng research, không bị đổi ngầm theo bộ lọc này.
- Hai kỳ tổng hợp dùng cột so sánh. Series ngày cần ít nhất bốn ngày quan sát; không nối qua ngày thiếu. Không tạo lịch sử ngày từ ngày export.
- Không cộng các research trùng dữ liệu hoặc trộn nguồn/đơn vị/OS/GEO/kỳ không tương đương. Dữ liệu mâu thuẫn không được đưa vào thứ hạng tăng trưởng.
- Review và số quảng cáo không tạo market growth. App chỉ đúng chủ đề nằm trong nhóm liên quan, không phải app đã xác nhận tăng trưởng.
- Bấm **Xem căn cứ** mở panel metric → phép so sánh → URL hoặc CSV/dòng nguồn. URL panel hoạt động sau reload.
- Research đang chạy được hiển thị riêng; nếu xem phiên hoàn tất trước thì ghi rõ. Kỳ kết thúc hơn bảy ngày trước được đánh dấu cũ. Report cũ không tự được nâng cấp thành metric đã xác minh.

## Nghiên cứu

Nhập câu hỏi, tùy chọn đính kèm CSV, chọn Codex Auto hoặc ChatGPT Manual rồi bấm **Nghiên cứu**. Scope và kết quả nằm cùng một trang. Mặc định US, 30 ngày gần nhất so với 30 ngày trước.

**Auto:** Settings → kiểm tra CLI đã đăng nhập ChatGPT → cho phép Codex. Lượt chạy gồm planner, store/news collection, live web research, đối chiếu đoạn trích và analysis. Lượt web chỉ nhận câu hỏi/scope và app public; không nhận CSV riêng. Không chuyển Manual khi lỗi. Lỗi một nguồn giữ nguyên nguồn thành công.

**Manual:** chỉ một handoff sang ChatGPT. Packet có schema analysis và `new_sources`, yêu cầu ChatGPT tìm/đọc thêm nguồn nếu có browsing. Dán JSON trở lại app; app kiểm tra cấu trúc, URL, đoạn trích, số, kỳ và nguồn trước khi dùng làm metric. Nếu ChatGPT không có browsing, nêu rõ trong gaps; không bịa nguồn.

Mỗi lượt lưu trong SQLite, có Hủy, Thử lại, Chạy lại giữ lịch sử, tên ngắn, xuất JSON và tạo Action/Opportunity. Các lượt Codex lưu log riêng theo planner/web/analysis trong data/workspace_jobs.

## CSV và ý nghĩa dữ liệu

Giữ parser Top Apps PoP/YoY hiện có. Các cột cơ bản: Unified ID, Unified Name, Downloads (Absolute), Downloads (PoP Growth) hoặc Downloads (YoY Growth). GEO/kỳ lấy từ tên export hoặc các cột kỳ được khai báo.

Các cột tùy chọn mới:

| Mục đích | Cột |
|---|---|
| Đối chiếu đúng store identity | Store ID, hoặc App Store ID, hoặc Package ID |
| Kỳ theo dòng | Period Start, Period End |
| Dữ liệu ngày | Date và Granularity=daily; hoặc Period Start=Period End |
| Revenue | Revenue (Absolute), Currency |
| UA | UA Spend, CPI, Retention (%), ROAS (%), ROAS Target (%) |
| Cohort UA | Cohort Window (ví dụ D7), Cohort Start, Cohort End, Measurement Date |

**Unified ID là namespace riêng**, không tự coi là Store ID dù giá trị số trùng nhau. Không ghép app chỉ bằng tên. CSV chỉ có tên chứa ASMR và category Games có thể cần xác minh chủ đề; Store ID rõ ràng cho phép đối chiếu với public identity phù hợp. Utilities/All Apps có thể xác minh ở cấp category đã yêu cầu.

PoP downloads dùng kỳ liền trước cùng độ dài theo định nghĩa export, không dựng daily timeline. Revenue cần hai kỳ rõ ràng và Currency khớp. Nền bằng 0 không tạo phần trăm vô hạn.

UA chỉ chấm **so với mục tiêu ROAS do người dùng khai báo** khi có đủ metric, đơn vị tiền, GEO/OS, cohort và Measurement Date chứng minh cohort đã đủ tuổi. Nếu thiếu chỉ trình bày dữ liệu; không gọi có lợi nhuận. Ví dụ ROAS (%)=120 nghĩa là 120%, không phải 1,2.

CSV Worldwide hoặc Unified không được ép thành US/iOS/Android. Nếu scope không phù hợp, app báo lý do và không dùng để khẳng định tăng trưởng trong scope đó. Filter/sort/Top N chỉ đổi bảng; Phân tích tập đang chọn mới tạo scope evidence giới hạn rõ ràng.

## Giới hạn public

- Search là mẫu có giới hạn, không phải toàn bộ thị trường. Store collectors hiện có: Apple tối đa 25/truy vấn, Android tối đa 15/truy vấn.
- Google Play connector tùy chọn; ZIP không kèm thư viện bên thứ ba. INSTALL_ANDROID_CONNECTOR.bat cài vào runtime của ZIP khi bạn chọn cài.
- Web research tối đa 12 nguồn/lượt. Verifier đọc HTTPS public, chặn local/private và redirect không hợp lệ; không đăng nhập hoặc vượt paywall. PDF/ảnh/JS không đọc được sẽ ghi chưa xác minh.
- “Verified” ở nguồn web nghĩa là **đoạn trích đã đối chiếu trên trang**, không phải số liệu đã được kiểm toán độc lập. Số liệu web được ghi là do nguồn công bố. Không xác minh được ngày xuất bản thì để trống; vẫn giữ thời điểm truy cập.
- Chỉ tạo metric web khi có đủ số, kỳ, GEO, OS, đơn vị và app tương ứng trong nguồn. Rank, search interest và advertising giữ vai trò riêng.
- Evidence AI có ngân sách 180.000 ký tự. Công bố số dùng/chưa dùng; toàn bộ manifest vẫn lưu. Chưa có xử lý nhiều batch tự động khi vượt ngân sách.

## Nâng cấp và bảo toàn dữ liệu

Trước migration v1.9.1, app sao lưu SQLite vào **data/backups/research-pre-v191-*.sqlite3** rồi thêm bảng phiên bản và evidence web. ID, bảng và dữ liệu cũ giữ nguyên. Report cũ mở được, nhưng không tự được coi là đã qua điều kiện metric mới.

ZIP không chứa database hoặc CSV riêng. Muốn dùng dữ liệu cũ: dừng server, sao lưu thư mục app cũ, giữ/copy thư mục **data** vào bản đã giải nén rồi chạy. Không copy SQLite khi server còn chạy.

Xem IMPLEMENTATION_REPORT_V191.md và release-checks-v191.json được bàn giao bên cạnh ZIP để phân biệt fixture, live, migration và smoke test.
