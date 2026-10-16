TRANG_THAI: HOAN_THANH
LUOT_CHAY: 4418c0f519834cf79a32ac988afa6a57
NHANH: testagent
VAI_TRO: coder
MODEL: gpt-6-luna

Phạm vi coder và file đổi
- Không tạo hoặc sửa file code trong chặng này. `research_workspace.py` trong workspace đã có logic GEO theo kế hoạch; giữ nguyên để không tạo delta code không cần thiết.
- `.bangiao/thay-doi.md` là báo cáo bàn giao theo yêu cầu của lượt chạy.

Lý do và behavior đã xác nhận
- `scope_for(question, saved=None, overrides=None) -> dict` giữ nguyên interface. GEO đầu vào được viết hoa để chuẩn hóa; giá trị `WORLDWIDE` được biểu diễn là `Worldwide`, và các casing Worldwide trong câu hỏi được nhận diện như cùng scope. Mã quốc gia hai chữ cái như US, VN, JP, KR và mã khác được giữ làm mã quốc gia; không ánh xạ Worldwide thành US. Platform `Unified` vẫn giữ nguyên.
- `relevance(row, scope, csv=False) -> (status, reasons)` so GEO sau khi viết hoa mà không sửa row hoặc scope. GEO rỗng/UNKNOWN bị loại; GEO quốc gia khác không khớp bị loại. Các trường topic/category/period không bị thay đổi bởi phần xử lý GEO.
- `launch(s, p) -> run dict` tiếp tục xây scope từ câu hỏi và saved scope hiện hữu; không thay đổi hành vi launch hay schema.
- Không đổi interface hoặc behavior khác.

Giới hạn và nghiệm thu Tester
- Chưa chạy test ở chặng coder. Không khẳng định test nào đã qua.
- Tester sở hữu `tests/test_workspace.py` và `tests/test_answer_engine.py`; cần kiểm tra ma trận casing Worldwide ở scope/relevance/launch/comparisons, bảo toàn mã quốc gia và Unified, không mutation, period boundary, negative Puzzle name+description, lineage import IDs/evidence refs độc lập, cùng launch tái sử dụng saved scope Worldwide/Unified cho ba casing.
- Tester chạy các suite hồi quy intelligence, studio và research theo kế hoạch, kiểm tra kết quả thật và dừng theo quy định nếu có lỗi.
