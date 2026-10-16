TRANG_THAI: HOAN_THANH
LUOT_CHAY: fb60ee9db8ee482698b37d8924818a32
NHANH: testagent
VAI_TRO: coder
MODEL: gpt-6-luna

## Thay đổi
- `market_intelligence.py`: thêm helper nội bộ chuẩn hóa GEO chỉ cho identity và phân tích ngày ISO canonical hợp lệ. ID metric giữ nguyên GEO/OS gốc trong output; casing GEO thống nhất khi deduplicate, so baseline, đối chiếu public/web và gom daily/dashboard.
- `market_intelligence.py`: lineage chỉ lấy các evidence ID đã được row khai báo; metadata `field_sources` của delta phải hợp lệ và trỏ tới ID hiện có. PoP tiếp tục dùng previous suy ra từ current trừ delta, baseline khớp khác giá trị chặn tính đủ điều kiện thay vì ghi đè; unrelated cùng phép đo chỉ dùng phát hiện mâu thuẫn, giữ refs được khai báo để chẩn đoán, không corroborate. Warning so app ID đầy đủ.
- `market_intelligence.py`: ngày daily phải là ngày lịch `YYYY-MM-DD`; giá trị thiếu/sai loại/ngày không tồn tại bị bỏ qua an toàn. Số tràn/không hữu hạn bị loại; phần trăm baseline zero giữ `None` và `zero_base=True`. Aggregate không hữu hạn không được đưa vào group.

## Interface và giới hạn
Không đổi public function signatures hoặc schema. Không sửa file test. Mọi output vẫn giữ GEO/OS và evidence gốc. Coder không chạy test, import ứng dụng hay probe theo kế hoạch; chưa có kết quả test để báo.

## Tester cần kiểm tra
Kiểm tra lineage declared refs/metadata không hợp lệ, PoP baseline disagreement và unrelated mismatch (bao gồm refs diagnostic), exact-ID warning, GEO casing qua comparison/assessment/dashboard, daily date invalid và exclusion unrelated/no-ref, ngày leap-day YoY, arithmetic finite/overflow/zero-base, và snapshot không mutate evidence.

