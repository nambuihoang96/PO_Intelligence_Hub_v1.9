# Ship — một yêu cầu, bốn agent tuần tự

Mở phiên Codex trong repository này (nhánh làm việc hiện tại), tải lại phiên nếu chưa thấy skill, rồi nhập:

    $ship Sửa lỗi GEO Worldwide

Agent cha tự kiểm tra điều kiện, khởi tạo RUN_ID và gọi Planner → Coder → Tester → Reviewer.
Bạn không phải nhập prompt từng chặng hoặc chạy guard thủ công. Model/reasoning/instructions lấy trực tiếp từ bốn TOML trong .codex/agents; không có cấu hình model thứ hai.

Xem [hướng dẫn và xử lý lỗi](.codex/commands/README.md) và [quy trình agent cha](.codex/commands/ship.md).
Kết quả gồm trạng thái từng vai trò, delta file, test/log, phán quyết Reviewer và việc bạn cần quyết định.

Test đỏ vẫn chuyển Reviewer theo guard; không tự sửa hoặc chạy vòng lặp. Model/quyền/host không hỗ trợ thì báo thật và dừng.
Giữ nguyên lượt đang dở. Không tự xóa lock, sửa metadata, commit/push/merge/PR/đổi nhánh hoặc cấu hình toàn máy.
Chưa có Auto Fix Loop hoặc Task Queue.
