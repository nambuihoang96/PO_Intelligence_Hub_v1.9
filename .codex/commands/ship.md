# Ship — dây chuyền 4 agent tuần tự

Nhận yêu cầu tính năng do người dùng cung cấp. Project skill $ship nạp hướng dẫn này cho agent cha; không phải slash command /ship.

## Trước khi chạy
1. Đọc AGENTS.md và xác định ROOT đúng repo hiện tại. Kiểm tra Git branch; main/master/detached phải dừng trước mọi ghi file.
2. Kiểm tra phiên có thể tạo custom agent đúng model. Chạy helper preflight (chỉ đọc); lấy model/reasoning/instructions trực tiếp từ bốn TOML; preflight chỉ xuất tóm tắt, dispatch xuất instructions của đúng một vai trò. Không dùng bảng model riêng. Không có model hoặc công cụ spawn: dừng, không giả vờ tuần tự bằng một model khác. Không tạo chat người dùng mới.
3. Chỉ sau khi preflight và host capability hợp lệ mới start. Dùng Python >=3.11 có sẵn (repo này có runtime/python.exe). Chạy `python .codex/commands/ship_guard.py start --request "<yêu cầu>"`. Có thể dùng --request-file khi yêu cầu dài. Helper chỉ xóa bốn báo cáo cũ đúng tên, giữ baseline/nen và các file khác.
4. Đọc JSON trả về: RUN_ID, branch, next_role. Không khởi động lượt mới khi lượt cũ chưa dừng. Không tự thay đổi luot-chay.json hoặc baseline. Nếu cần bỏ lượt, người dùng phải yêu cầu dừng; dùng helper halt --reason để ghi lý do.

## Bốn chặng
Chỉ có MỘT agent con đang làm việc tại một thời điểm. Đợi agent hoàn tất, chạy helper `check <role>` và đọc next_role trước khi gọi chặng tiếp. Không chỉ chờ thấy file tồn tại.

- Planner: giao ROOT, RUN_ID, branch, yêu cầu và profile planner. Chỉ được ghi ke-hoach.md. `check planner` kiểm tra header/status/phạm vi; nếu CAN_LAM_RO đưa câu hỏi cho người dùng và dừng. Nếu sẵn sàng helper chụp baseline các file kế hoạch vào nen/<RUN_ID>/files.
- Coder: chỉ giao yêu cầu, bàn giao và các file liên quan; không truyền cả lịch sử chat. Sau khi hoàn tất chạy `check coder`. Chưa hoàn tất hoặc có sửa ngoài phạm vi thì next_role=reviewer; không gọi Tester.
- Tester: sau Coder hợp lệ, giao đúng profile tester. Các lệnh test phải đi qua helper `test -- <argv>` theo PHAM_VI_JSON.commands. Khi test thất bại Tester vẫn ghi report, rồi cha `check tester` và giao Reviewer. Không sửa hoặc chạy vòng lặp.
- Reviewer: luôn chạy khi có báo cáo Tester, kể cả KHONG_DAT/CHUA_KIEM_TRA; cũng chạy khi helper ghi vi phạm của chặng trước. Chỉ đọc code và ghi danh-gia.md. Sau đó `check reviewer`; helper không cho CHOT nếu gate chưa đạt.

Trước mỗi lần spawn, cha chạy `python .codex/commands/ship_guard.py dispatch` (không thêm tên role) để nhận ROOT, RUN_ID, branch, role, request, profile và guard_python. Dispatch chỉ đọc, kiểm tra profile còn nguyên so với đầu lượt. Không gửi toàn bộ lịch sử chat.

Mỗi lần spawn phải chọn đúng profile native. Nếu host có explicit spawn hỗ trợ cả model và reasoning, đọc TOML và truyền nguyên developer_instructions + đúng model/reasoning, fresh context, ROOT/RUN_ID; ghi rõ cơ chế này trong bàn giao. Không hỗ trợ đúng reasoning hoặc không chứng minh profile native được áp dụng thì dừng, không suy đoán mặc định. Khi explicit spawn, truyền nguyên developer_instructions vào nhiệm vụ con và fresh context (fork_turns=none nếu API hỗ trợ). Quyền giữ nguyên từ cha.

Cha tự chờ agent hoàn tất (không polling chỉ dựa file report), ghi agent ID và tham chiếu sự kiện spawn/model/reasoning từ host trong kết quả cuối; có transcript/log host thì dẫn đường dẫn. Không dùng header MODEL của report làm bằng chứng thực thi, không tạo log model giả. Chạy check rồi dùng next_role trả về để quyết định. Đóng agent đã xong nếu host có API close để tránh hết slot, không xóa lịch sử. Không truyền model khác. Giới hạn vai trò là instruction + hậu kiểm, không sandbox riêng.

## Gate và lỗi
- Báo cáo thiếu/rỗng/sai lượt/sai model/sai vai trò: dừng tại chặng, không chạy chặng tiếp hoặc đọc bản cũ. Báo rõ lỗi và dùng helper halt --reason; không tự làm thay báo cáo.
- Model lỗi/quyền bị từ chối: dừng, ghi lý do bằng halt nếu còn quyền; không tự xin thêm quyền cho agent con, đổi model hoặc giả báo cáo.
- Vi phạm phạm vi: giữ nguyên thay đổi để người dùng xem, không rollback; giao Reviewer nếu helper cho phép. Không kết luận CHOT.
- Branch/HEAD/index bị đổi trong lượt: dừng và báo, không reset/checkout/commit.
- Snapshot chỉ gồm Git-visible source (loại runtime/data/secret) và file kế hoạch. Không quét SQLite/CSV hoặc gửi payload database vào AI. Nếu yêu cầu đòi sửa dữ liệu bị bảo vệ, dừng để làm rõ ngoài workflow này.

## Kết thúc
Hiển thị task, RUN_ID, trạng thái bốn vai trò, files changed theo helper diff, test/exit code/log, Reviewer verdict, findings và việc người dùng cần quyết định. Vai trò bị bỏ qua ghi CHUA_CHAY cùng lý do. Dẫn đường dẫn bàn giao và log spawn thực tế. Không commit/stage/push/merge/PR. Nếu có model lỗi hoặc gate không đạt, nói rõ dây chuyền CHƯA hoàn tất. Con người đọc, quyết định và tự gộp nhánh.
