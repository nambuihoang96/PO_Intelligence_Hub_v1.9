# Báo cáo v1.9.1 — 16/10/2026

## Đã triển khai

- Overview dashboard: chỉ số vận hành có drill-down, filter đồng bộ URL, biểu đồ theo research/metric/app, ma trận chủ đề, bảng growth theo nhóm tương đương, coverage/attention, decisions và research gần đây.
- Không dùng review, search-result count hoặc ad count để chấp nhận market growth. Backend kiểm tra metric eligibility trước diễn giải AI.
- Tách market assessment, app growth, UA assessment và related apps. Metric có số trước/sau, kỳ, GEO, OS, đơn vị, định nghĩa, provider và evidence IDs.
- Hai kỳ dùng bar; daily series cần >=4 ngày thật và không nối ngày thiếu. Date export không tự biến thành dữ liệu ngày.
- CSV/public matching không dựa tên hoặc giá trị Unified ID trùng số. Chỉ Store ID được khai báo rõ + OS/GEO phù hợp mới dùng để đối chiếu identity. CSV sai phạm vi hoặc chưa xác minh chủ đề không được đưa vào growth.
- Revenue cần Currency và kỳ phù hợp. UA có thể nhận metric/cohort/mục tiêu qua các cột CSV tùy chọn; chỉ chấm mục tiêu khi cohort đủ tuổi. Không tự đặt chuẩn ROAS/CPI/retention, không kết luận lợi nhuận từ downloads.
- Auto có live web research; verifier lưu URL/nguồn gốc/đoạn trích/thời điểm truy cập, đối chiếu số và phạm vi. Nguồn bị chặn hoặc không đối chiếu được giữ trạng thái chưa xác minh. Research web không nhận CSV riêng.
- Manual giữ một handoff với schema mở rộng new_sources; không có bước planner riêng. Backend kiểm tra nguồn được dán về trước khi tạo metric.
- Panel evidence bên phải trên desktop, full-width trên mobile; deep-link/reload đúng phiên. Research cũ được giữ, không tự nâng cấp thành bằng chứng tăng trưởng.
- Giữ API cũ, thêm GET /api/workspace/dashboard chỉ đọc SQLite, không gọi mạng/AI. Migration thêm intelligence_versions và intelligence_web_evidence, backup trước khi chạy.

## Kiểm thử fixture và regression

- **115 Python tests: PASS**, gồm regression v1.0–v1.9 và 30 test nghiệp vụ v1.9.1.
- **28 browser acceptance checks: PASS**: 11 dashboard và 17 research/workflow. Kiểm tra nội dung, bar/daily chart, không nối ngày thiếu, filter/URL/reload, CSV lineage, panel keyboard/deep-link, scope, Auto/Manual và quyết định. Desktop/mobile không tràn ngang; không JavaScript error.
- Hai suite Node cho parser/core: PASS. Kiểm tra riêng Date export không thành daily, Currency và cohort/target columns.
- Ảnh có app “TEST”, số 100.000 → 145.000 hoặc tên file TEST_SYNTHETIC_ASMR.csv là **dữ liệu giả lập để kiểm thử bố cục**, không phải kết quả thị trường. Các fixture chỉ được tạo bởi server test; production không nạp chúng.

## Migration và CSV thật

- Chỉ migration **bản sao online** database tại D:\AI\PO Analysis\PO_Intelligence_Hub_v1.9\data\research.sqlite3.
- **31 bảng / 20.183 dòng cũ** giữ nguyên hash nội dung; integrity_check=ok, foreign_key_check=ok. Database gốc không bị sửa trong triển khai.
- Database có hai import thật, tổng 20.000 dòng PoP/YoY; sau ghép còn **13.852 record**. GEO của chúng là Worldwide, kỳ 14/09–13/10/2026.
- Kiểm tra local với câu hỏi mặc định US và kỳ 16/09–15/10/2026: loại đúng 13.852 record không phù hợp, không tạo CSV growth metric cho US. Không đưa dữ liệu riêng này vào web research.
- Đây là kiểm thử âm tính bằng CSV thật. Chưa có CSV thật cùng GEO/kỳ/chủ đề được xác minh để nghiệm thu kết luận tăng trưởng dương; trường hợp dương được kiểm thử bằng fixture có lineage rõ ràng.

## Live ASMR

- Đã chạy hai lượt Auto thực bằng CLI ChatGPT và live web search, store/news collectors, sau đó đọc/đối chiếu nguồn bằng verifier.
- Lượt live cuối hoàn tất ready: **41 evidence** gồm 33 store candidates và 8 nguồn web; **6 đoạn trích web đối chiếu được, 2 chưa xác minh**. AI dùng 32 evidence phù hợp, không còn evidence phù hợp bị bỏ vì ngân sách trong lượt này.
- Có nguồn từ Sensor Tower public blog, AppBrain, SocialPeta, App Store và TikTok Creative Center; nguồn lỗi/không đối chiếu được được lưu rõ. Đây là kết quả thu thập thực, không phải dữ liệu Sensor Tower đóng gói sẵn.
- Các thông tin downloads toàn cầu, snapshot rank hoặc creative activity không khớp đầy đủ US/OS/hai kỳ yêu cầu. **Không có comparison metric đủ điều kiện**; bảng app tăng trưởng để trống và UA chưa đánh giá.
- Kết luận trả lời đúng giới hạn: chưa đủ bằng chứng khẳng định thị trường game ASMR US đang tăng trưởng trong hai kỳ đã chọn hoặc app đang scale tốt. App liên quan và nguồn ngữ cảnh vẫn xem được, không bị gọi là app đã scale.

## Giới hạn còn lại

- Public-only có thể không trả lời định lượng nếu thiếu lịch sử cùng scope; thêm web search không tạo ra spend/CPI/retention/ROAS không công khai.
- Google Play connector không có trong runtime nghiệm thu; chưa có live Android collector thành công. Thư viện quảng cáo/Trends có thể cần đăng nhập, bị chặn hoặc không cung cấp lịch sử. Không có connector trả phí bắt buộc.
- Verifier HTML/text/JSON dùng đối chiếu đoạn trích và các trường định lượng thận trọng; chưa có browser extraction/OCR/PDF parser cho nguồn bị JS/paywall. Verified không đồng nghĩa kiểm toán số liệu nguồn.
- CSV thiếu Store ID hoặc mô tả chứng minh chủ đề có thể chỉ là possible; không ghép bằng Unified ID/tên để làm đầy bảng growth.
- Lớn hơn ngân sách AI 180.000 ký tự hoặc hơn 12 nguồn web được công bố giới hạn; chưa tổng hợp nhiều batch tự động.
- Chưa có live cohort UA thật cùng mục tiêu do PO cung cấp; phần UA có mục tiêu được kiểm thử bằng fixture, không có claim UA profitability thực.
- Khi server dừng giữa request mạng, cần Retry sau restart; packet/evidence và kết quả đã lưu được giữ. Chưa resume chính xác request đang dở.

## Bàn giao

Source được cập nhật tại repo v1.9, có backup file trước thay đổi, không sửa .git/.agents/runtime/data hoặc tự commit/push. Cần đóng tiến trình server cũ và mở RUN_WINDOWS.bat để dùng source mới.

ZIP sạch kèm Python; không chứa SQLite/CSV riêng hay data kiểm thử. Hash ZIP, manifest và kết quả smoke sau giải nén ghi trong release-checks-v191.json. Ảnh fixture và live được đặt tên riêng để không nhầm kết quả kiểm thử với bằng chứng thị trường.
