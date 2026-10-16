# Báo cáo v1.9.2

## Source và chức năng
Sửa trực tiếp D:\AI\PO Analysis\PO_Intelligence_Hub_v1.9, nhánh testagent; không commit, không đổi nhánh. Hợp đồng mới theo câu hỏi; bỏ title cố định; giữ đọc report cũ. Auto/Manual chung schema; nguồn web chưa xác minh không được dùng cho claim. Claim/app/metric giữ evidence IDs, kiểm tra app identity. Có hỏi tiếp và lịch sử. Overview dùng direct_answer. CSV thêm Worldwide/Unified, scope metadata và YoY; Top N chỉ đổi cách xem.

## Kiểm thử fixture và regression
123 test Python qua; 28 browser regression qua (17 Research + 11 dashboard); hai bộ parser Node qua. Kiểm tra live trong Edge: app cụ thể, không heading trend bắt buộc, panel evidence, hỏi tiếp, mobile không tràn, không lỗi JavaScript. Migration chạy lặp trên bản sao database thu gọn giữ 10 dòng. 10 dòng mẫu thật gồm 5 PoP + 5 YoY, đối chiếu phép cộng ngược downloads/delta thành công. Fixture kiểm thử riêng, không đưa vào screenshot live hay release database.

## Live và mức trả lời được
Ba câu Auto public-only đã hoàn tất, dùng database test riêng; không dùng CSV riêng.
- Top app drama: 6 app có căn cứ listing/báo cáo, 10 claim; 2 nguồn web xác minh được. Trả shortlist, chưa đạt ranking định lượng đầy đủ theo download/revenue/GEO/kỳ.
- So sánh ReelShort/DramaBox: 2 app, 5 claim; 3 nguồn web xác minh được. Có khác biệt mô tả sản phẩm, subscription và đề xuất benchmark. Chưa phải kiểm thử trong app hay chứng minh app nào tốt hơn.
- Benchmark app drama mới: 6 app, 9 claim; 3 nguồn web xác minh được. Gợi ý kiểm tra mở khóa/tập tiếp theo, discovery, player và quay lại; đề xuất được tách khỏi quan sát.

Lượt đầu câu top lỗi vì trích nguồn chưa xác minh; đã sửa packet và thử lại với evidence lưu sẵn. Câu benchmark bị gián đoạn do server test khởi động, sau đó retry hoàn tất. Không che các lần lỗi này bằng trạng thái cuối.
Nguồn 403/PDF/quote không đối chiếu được bị loại khỏi căn cứ. Không bảo đảm mọi claim ngôn ngữ tự nhiên đã được kiểm chứng ngữ nghĩa tự động; backend kiểm tra cấu trúc, ID, nguồn và điều kiện metric, cần người dùng mở nguồn khi quyết định.

## Dữ liệu và giới hạn còn lại
Backup đầy đủ: data/research-before-reset-20261016-043758.sqlite3. Database hoạt động giữ 10 dòng; research/job/result cũ đã dọn. Không gửi database vào AI.
Còn 7 cấu hình RSS trỏ tới project đã xóa. Bộ duyệt tự động chặn xóa vì phải giữ cấu hình; đang chờ lựa chọn của người dùng. SQLite quick_check đạt, nhưng foreign_key_check của database source báo 7 liên kết RSS này. Không coi database source đã sạch hoàn toàn. ZIP dùng database mẫu sạch, không kèm các cấu hình/backup cá nhân và phải đạt foreign_key_check khi smoke test.

## Bàn giao
ZIP có Python Windows; smoke test sau giải nén bằng interpreter đi kèm. Ảnh overview/research/evidence lấy từ lượt live, không phải fixture. File LIVE_ANSWERS_V192.json lưu câu trả lời và tình trạng nguồn để tự kiểm tra chất lượng.
