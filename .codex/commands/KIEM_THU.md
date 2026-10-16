# Kiểm thử dây chuyền 4 agent Codex

## Đã cài
Source: D:\AI\PO Analysis\PO_Intelligence_Hub_v1.9, nhánh testagent. Bốn profile native nằm trong .codex/agents; ship.md, README và guard/test nằm trong .codex/commands. Không sửa cấu hình toàn máy, code sản phẩm, database, RSS hoặc lịch sử Git. HEAD sản phẩm giữ 2d97b348a383dd5fb221e5ced56621d266a7e931. Không tạo .bangiao trong repo sản phẩm khi chỉ cài cấu hình; thư mục này sinh ở lượt chạy thực.

## Kiểm thử gate: 27/27 qua
Chạy test_ship_guard.py bằng Python 3.13: 27 test qua. Kiểm tra thêm bằng runtime/python.exe của repo Windows: 2 test tương thích (profile native + happy path/log test thật) qua.
Các nhóm đã kiểm tra: main/master/detached không ghi file; chặng sai; báo cáo thiếu/rỗng/chỉ header/cũ/sai model; câu hỏi mở; baseline dirty; chỉ xóa đúng 4 báo cáo cũ; lượt đang chạy; source/test sửa ngoài phạm vi; file bàn giao lồng thư mục; traversal/protected data; branch/index đổi; snapshot/log bị sửa; argv test không đúng kế hoạch; test fail vẫn tới Reviewer; không rerun sau fail; không DAT thiếu log; không CHOT khi gate chưa đạt; halt khi model/quyền lỗi.
Các tình huống lỗi là fixture/fault injection, không cố tình gọi model sai hoặc gây lỗi tài khoản thật. Giới hạn vai trò là instructions + hậu kiểm, không phải sandbox riêng hoặc chống agent cố tình thay helper/metadata. Không đọc/hash payload database; chỉ kiểm tra metadata của SQLite/RSS store khi chạy gate.

## Smoke native Codex: hoàn tất đủ 4 chặng
CLI: codex-cli 0.162.0-alpha.17.2. Dùng repo tạm feature/ship-smoke, không dùng source/data sản phẩm. Thiết lập fixture có seed commit trước lượt ship; bản thân workflow không commit/stage/push/merge/PR.
- Planner: gpt-6.1-sol / high → SAN_SANG.
- Coder: gpt-6-luna / medium → HOAN_THANH.
- Tester: gpt-6-luna / medium → DAT.
- Reviewer: gpt-6.1-sol / high → CHOT.
Tính năng fixture normalize_label: strip + casefold, TypeError cho non-string, ValueError cho chuỗi rỗng sau normalize. Tester viết 5 unittest bao gồm happy path, Unicode, whitespace và negative cases; chạy qua helper, exit 0. Không vi phạm phạm vi. Các bàn giao native cũng đã được đối chiếu lại bằng validator cuối.
Catalog bundled có cả hai model. debug prompt-input không hiển thị registry custom agent nên không được dùng làm bằng chứng discovery; smoke native mới là phép kiểm tra thực tế. Transcript CLI cuối xác nhận 4 native role/model đúng thứ tự. Không lấy model khác thay thế.

## Cảnh báo quan sát được
CLI smoke exit 0 nhưng stderr có một cảnh báo sandbox filesystem (không nêu path) và ba cảnh báo hook không tìm được transcript cha do phiên --ephemeral. Các report/gate/test hoàn tất; không khẳng định smoke không có cảnh báo hoặc chứng minh sandbox độc lập. Khi chạy bình thường từ phiên Codex tại repo, không cần --ephemeral. Nếu có lỗi quyền/model thực sự chặn thao tác, workflow phải dừng và báo theo ship.md.

## Bàn giao và dùng
Mở Codex tại repo rồi gửi: Đọc .codex/commands/ship.md và chạy dây chuyền cho: [yêu cầu]. Mở phiên mới nếu phiên cũ chưa thấy bốn native profile. Không có lệnh slash /ship tự đăng ký. Phán quyết CHOT chỉ là khuyến nghị; người dùng tự đọc và quyết định gộp nhánh.


## Nâng cấp project skill ship — 2026-10-16

### Phạm vi và cách gọi
- Source trực tiếp trên nhánh testagent tại repository ổ D. Không đổi nhánh/stage/commit/push/merge/PR, không sửa sản phẩm, database, RSS hoặc cấu hình toàn máy.
- Gọi trong phiên Codex mở ở Git root: $ship Sửa lỗi GEO Worldwide. Tải lại phiên nếu skill chưa hiển thị.
- Skill: .agents/skills/ship/SKILL.md. Cha nạp ship.md, tự preflight/start/dispatch/check và chờ bốn vai trò tuần tự. Không Auto Fix Loop hoặc Task Queue.
- Model/reasoning/instructions chỉ đọc TOML. Preflight xuất cấu hình gọn; dispatch xuất đúng vai trò hiện tại. Lượt mới lưu hash TOML và chặn khi profile thay đổi. Không sửa bốn TOML; hash được đối chiếu với manifest.
- Lượt cũ không có hash profile vẫn đọc được; preflight/start không ghi đè lượt còn next_role. Không tự xóa lock hoặc sửa metadata.

### File thêm/sửa
- Thêm .agents/skills/ship/SKILL.md và CODEX_4_AGENTS_GUIDE.md tại Git root.
- Sửa .codex/commands/ship.md, README.md, ship_guard.py, test_ship_guard.py và báo cáo này.
- Guard bảo vệ cả skill ship khỏi allowlist sửa tính năng sản phẩm. Khả năng spawn do host cung cấp, không do Python helper giả lập.

### Regression guard
- .codex/commands/test_ship_guard.py: 32 test PASS, 100.374 giây trên Python runtime đi kèm.
- Sau bổ sung bảo vệ skill và hai case mới: 3 focused test PASS, 3.078 giây.
- Tổng 34 test riêng biệt PASS (một test path protection được chạy lại). Không nói thành một lượt full suite 34.
- Log: D:/AI/PO Analysis/ship-validation-2bf83abdbd/guard-tests.log và guard-tests-final.log.
- Bao gồm allowlist, RUN_ID sai, báo cáo thiếu/rỗng/cũ/sai model, test đỏ vẫn Reviewer, không CHOT khi thiếu/đỏ test, test-log/baseline tamper, nhánh/HEAD/index, active run/lock, legacy metadata, profile thiếu/sai/đổi giữa lượt.
- Fixture unit test nằm trong thư mục tạm riêng, không sửa source nghiệp vụ.

### Nghiệm thu bằng Codex thật
- Repo cô lập: D:/AI/PO Analysis/ship-validation-2bf83abdbd/repo.
- Prompt duy nhất: $ship Implement normalize_label. AGENTS.md fixture mô tả yêu cầu nhỏ, chỉ labels.py và tests/test_labels.py; không chứa hướng dẫn tự gọi từng agent.
- Codex nhận skill trong phiên mới, cha đọc skill rồi tự gọi native planner/coder/tester/reviewer với fresh context. Không cần người dùng chạy guard hoặc prompt từng chặng.
- RUN_ID: 1743f5f21d2e431798da29e074067d8b.
- Planner: gpt-6.1-sol / high / SAN_SANG.
- Coder: gpt-6-luna / medium / HOAN_THANH.
- Tester: gpt-6-luna / medium / DAT; 7 unittest PASS, exit 0, log do guard lưu.
- Reviewer: gpt-6.1-sol / high / CHOT. Đây là review tính năng fixture, không phải review độc lập toàn bộ nâng cấp điều phối.
- Không có vi phạm allowlist. Trình tự spawn được đối chiếu với thời điểm hoàn tất phiên con, không chạy đồng thời.
- Bằng chứng: D:/AI/PO Analysis/ship-validation-2bf83abdbd/host-proof.json. Trích call_id/profile của spawn từ transcript cha và model/effort từ turn_context phiên con; không dựa vào header MODEL tự khai.
- Transcript gốc là log hệ thống Codex trong thư mục sessions của tài khoản, tham chiếu trong host-proof.json; không sao chép source sang ổ C.
- Events/exit log và final: events.jsonl, stderr.log, final.txt cùng thư mục fixture. Bốn báo cáo và test log giữ tại repo/.bangiao.
- Cha từng gọi nhầm dispatch planner, CLI báo unrecognized arguments và không thay đổi trạng thái; cha sửa cách gọi thành dispatch rồi tiếp tục, không bỏ guard. Tài liệu cuối đã nêu rõ dispatch không nhận tên role.
- Lượt native dùng bản trước tối ưu preflight/hash-only metadata và bảo vệ đường dẫn skill. Bản cuối được regression + focused test và kiểm tra read-only toàn bộ header/baseline/test logs của native run; không chạy thêm bốn agent để tiết kiệm quota.

### Giới hạn xác minh
- quick_validate.py của skill-creator không chạy được vì Python hiện có thiếu PyYAML. Không cài thêm package toàn máy. Frontmatter/link đã kiểm tra và Codex phiên mới thực sự nhận, gọi skill thành công; không gọi quick_validate là PASS.
- Native smoke chỉ chứng minh host CLI hiện có. Host khác thiếu đúng model/reasoning/profile hoặc spawn phải dừng thật theo skill, không âm thầm fallback.
- Guard/instructions không phải sandbox riêng chống tác nhân cố ý phá helper. Model/quyền lỗi được báo dừng, không tự sửa hoặc chạy vòng lặp.
- CHOT là khuyến nghị kỹ thuật cho fixture; người dùng vẫn quyết định việc áp dụng/commit thay đổi repository.
