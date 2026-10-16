---
name: ship
description: Điều phối yêu cầu lập trình qua Planner, Coder, Tester và Reviewer tuần tự, dùng cấu hình và ship guard của repository. Dùng khi người dùng yêu cầu chạy dây chuyền ship.
---

# Ship

Bạn là agent cha điều phối; không tự đóng vai bốn agent. Lấy phần yêu cầu sau $ship làm task, giữ đúng ý người dùng. Nếu chưa có task, hỏi đúng một lần trước khi tạo lượt chạy.

Xác định Git root của repository được người dùng chọn, đọc AGENTS.md áp dụng và [.codex/commands/ship.md](../../../.codex/commands/ship.md) tại root. Đường dẫn tương đối trong tài liệu đó luôn tính từ Git root. Thực hiện trọn quy trình trong tài liệu, tự chạy preflight, start, dispatch và check, không bắt người dùng điều khiển từng bước.

Đọc model, reasoning và instructions trực tiếp từ .codex/agents/<role>.toml qua guard. Không có cấu hình model mặc định trong skill. Chỉ spawn khi host hỗ trợ chính xác cấu hình đó; không giả lập hoặc đổi model/quyền. Một agent con tại một thời điểm; mỗi vai trò một lượt, không Auto Fix Loop, không Task Queue.

Không sửa sản phẩm trong vai agent cha. Không sửa lock/metadata/baseline, không phá lượt đang dở, không commit/push/merge/PR/đổi nhánh hoặc cấu hình toàn máy. Thiếu quyền/model/công cụ: báo lỗi thật rồi dừng.

Kết thúc ngắn gọn: task; RUN_ID; trạng thái từng agent (kể cả chưa chạy); files changed từ delta baseline; tests và đường dẫn log; Reviewer verdict; điều người dùng cần quyết định. Phân biệt log spawn của host với MODEL tự khai trong report: report không chứng minh model thực thi.
