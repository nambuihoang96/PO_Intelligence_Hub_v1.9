# Báo cáo triển khai v1.9 — 16/10/2026

## Đã triển khai

- Research Workspace mới với một câu hỏi, CSV tùy chọn, Auto/Manual và phạm vi thu gọn; không có dãy nút bước hoặc iframe quay về Studio/Market cũ.
- Backend điều phối và lưu lượt chạy, bước chạy, preview theo nguồn, bộ evidence, kết quả và lịch sử phiên trong SQLite. Chống lượt chạy trùng trong cùng research; Hủy dừng tiến trình Codex; phục hồi trạng thái gián đoạn sau restart.
- Phân biệt loại sản phẩm/chủ đề. ASMR không tự thêm Puzzle; Utilities và All Apps được kiểm thử độc lập. Auto dùng Codex để hiểu chủ đề và lập seeds; Manual dùng nhận diện local, không có planner handoff riêng.
- Auto có một lượt planner và analysis; chỉ chạy khi đã cho phép trong Settings và CLI đăng nhập ChatGPT hợp lệ. Không âm thầm fallback. Một lần sửa JSON theo validation trước khi báo lỗi; Retry dùng lại evidence đã lưu.
- Câu trả lời có trend, candidate, signals, evidence, gaps và next steps. Phân biệt quan sát / diễn giải AI / chưa đủ bằng chứng. Không suy ra trend từ search count hoặc UA profitability từ downloads.
- Toàn bộ public candidates thu về đều được đánh giá relevance. CSV kiểm tra chủ đề, GEO, OS, kỳ; matching/merge CSV theo ID, OS, GEO và kỳ, không theo tên app. Evidence không đủ xác minh chủ đề chỉ là possible.
- Signals PoP truy về filename/dòng CSV; thay đổi reviews cần snapshot từ hai kỳ nghiên cứu. Tập AI dùng/bỏ vì ngân sách được công bố, không còn cắt ngầm 70 public candidates.
- Data Library có filter/sort trên header, kỳ rõ ràng. Top N không thay đổi kết quả; chỉ Phân tích tập đang chọn tạo scope giới hạn rõ.
- Overview mở kết quả mới nhất; tên ngắn tối đa 80 ký tự, sửa được khi lượt chạy dừng; câu hỏi đầy đủ xuống dòng. Lịch sử và xuất JSON theo đúng phiên.
- Action/Opportunity giữ run/finding/evidence nguồn. Subtask, investigation và experiment có giao diện native; API cũ vẫn giữ. Report/analysis lịch sử mở dữ liệu nguyên trạng.
- Backup SQLite trước migration; thêm workspace_runs, workspace_steps, workspace_links. Source được cập nhật riêng, không ghi vào database thật trong quá trình triển khai.
- ZIP Windows kèm Python 3.12 chuẩn, chạy bằng RUN_WINDOWS.bat. Không chứa database/CSV riêng hoặc dữ liệu thị trường đóng gói sẵn.

## Kiểm thử bằng fixture

- **85 Python tests: PASS**, gồm regression v1.0–v1.8 và kiểm thử v1.9: phạm vi, dedupe, preview/restart, hủy subprocess, source lỗi, Auto lỗi/retry, sửa JSON, ID sai, dữ liệu không phù hợp, snapshot so sánh và lineage quyết định.
- **17 browser acceptance checks: PASS** trên Edge headless, desktop 1440px và mobile 390px. Kiểm tra nội dung câu trả lời và scope ASMR/Utilities; Manual một handoff; Auto không CTA nội bộ; CSV từ câu hỏi và Data Library; filter/Top N; reload; JSON sai giữ input; evidence URL; Action/Opportunity/subtask/investigation/experiment; không JavaScript error.
- CSV parser/core suite: PASS. JavaScript syntax toàn bộ assets: PASS.
- Fixture ghi rõ TEST, dùng database riêng, collector/AI giả lập. Đây không phải kết quả thị trường live.

## Kiểm thử dữ liệu thật

- Migration trên **bản sao** SQLite hiện hữu: **28 bảng / 1.539 dòng cũ được giữ nguyên**, hash nội dung tất cả bảng cũ không đổi; integrity_check = ok. Database gốc không bị sửa.
- Lượt live đầu: 42 candidates, 31 evidence phù hợp dùng cho AI; hoàn tất bằng CLI ChatGPT thực và Apple Search thực.
- Lượt live thứ hai phát hiện next_step thiếu evidence ID; backend chặn đúng. Retry giữ evidence, AI được yêu cầu sửa đúng lỗi một lần, sau đó hoàn tất. Không chuyển Manual và không tạo dữ liệu giả.
- Lượt live cuối trên schema planner v1.9: **33 candidates / 33 đã đánh giá**, 21 relevant, 3 possible, 9 unrelated; AI dùng **24/24** phù hợp. Kết quả **ready**. Nguồn Apple thành công; Android báo connector chưa cài; news 0 kết quả.
- Kết luận live: **chưa đủ lịch sử để xác nhận ASMR trending hoặc app đang scale tốt**. AI đưa Perfect Tidy, Fill The Fridge! và Tanghulu Master thành ứng viên cần xác minh, có URL/snapshot, không khẳng định tăng trưởng hay UA profitability.

## Giới hạn còn hiện hữu

- Public search là mẫu top kết quả, không phải census thị trường. Apple tối đa 25/truy vấn và Google Play collector hiện hữu tối đa 15/truy vấn; giới hạn được hiển thị.
- Máy nghiệm thu chưa cài Android connector; chưa kiểm chứng live Google Play. RSS không trả evidence trong lượt cuối. Chưa có nguồn lịch sử downloads/spend/CPI/retention/ROAS public trong lượt này.
- Không thể kết luận market trend hoặc scale chỉ từ public listing hiện tại. Cần CSV phù hợp hoặc snapshot so sánh và dữ liệu kinh tế UA để trả lời chắc chắn hơn.
- Manual scope và relevance là bộ nhận diện local thận trọng; các chủ đề mơ hồ/đồng nghĩa không có trong mô tả có thể chỉ được phân loại possible hoặc bị loại. Cần ghi câu hỏi cụ thể và kiểm tra scope/reasons.
- Evidence AI có ngân sách 180.000 ký tự. Toàn bộ manifest được lưu; số chưa đưa vào AI được báo. Chưa triển khai tổng hợp nhiều batch AI tự động khi vượt ngân sách.
- Thu thập đang chạy không thể tiếp tục chính xác từ một request mạng bị ngắt giữa chừng; restart đánh dấu interrupted, Retry thu thập lại khi chưa có packet hoàn chỉnh. Evidence đã lưu và các kết quả hoàn tất không mất.
- Cập nhật source không tự thay tiến trình server cũ đang chạy. Cần đóng app cũ và mở RUN_WINDOWS.bat để dùng phiên bản mới.

## Đóng gói và bàn giao

Chi tiết hash ZIP, manifest và kết quả smoke sau giải nén được bàn giao trong release-checks.json bên cạnh ZIP. Báo cáo này chỉ ghi PASS cho các kiểm tra đã thực thi, không coi fixture là kiểm chứng thị trường.
