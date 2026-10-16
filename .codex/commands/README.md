# Ship — 4 agent Codex cho repo này

## Cách dùng
Mở Codex trong đúng repo trên nhánh làm việc, rồi gửi:

> $ship Sửa lỗi GEO Worldwide

Project skill .agents/skills/ship/SKILL.md tự nạp quy trình; cha tự chạy guard và gọi agent. Tải lại phiên tại repo ổ D nếu chưa thấy ship. Đây không phải lệnh `/ship` được Codex tự đăng ký. File TOML trong `.codex/agents/` là custom agent native. Nếu phiên đang mở chưa nhận profile mới, mở phiên Codex mới tại repo. Không cần sửa config toàn máy.

Model, reasoning và instructions chỉ lấy từ .codex/agents/<role>.toml; preflight và dispatch trả cấu hình thực tế. TOML giữ nguyên trong lần nâng cấp này.

Agent cha gọi từng vai trò, chờ hoàn tất rồi kiểm tra bàn giao; không spawn song song. Không đổi model ngầm. Nếu host chỉ hỗ trợ explicit spawn(model, reasoning), cha truyền nguyên instructions TOML và đúng model, fresh context; phải nêu rõ cơ chế thực tế. Custom agent và prompt không tạo sandbox riêng: quyền vẫn kế thừa cha.

## Bàn giao có mã lượt
Khi start, helper sinh `.bangiao/luot-chay.json` và RUN_ID. Bốn báo cáo đều có:

```text
LUOT_CHAY: <run_id>
NHANH: <branch>
VAI_TRO: planner|coder|tester|reviewer
MODEL: <model đúng vai trò>
```

Dòng đầu Planner: `TRANG_THAI: SAN_SANG` hoặc `TRANG_THAI: CAN_LAM_RO`.
Dòng đầu Coder: `TRANG_THAI: HOAN_THANH` hoặc `TRANG_THAI: CHUA_HOAN_THANH`.
Dòng đầu Tester: `TRANG_THAI: DAT`, `KHONG_DAT` hoặc `CHUA_KIEM_TRA`.
Dòng đầu Reviewer: đúng một trong `PHAN QUYET: CHOT`, `PHAN QUYET: CAN SUA`, `PHAN QUYET: CHAN`.

Planner có thêm đúng một dòng JSON (đường dẫn file chính xác, không wildcard):

```text
PHAM_VI_JSON: {"code":["module.py"],"tests":["tests/test_module.py"],"commands":[["{python}","-m","unittest","discover","-s","tests","-v"]]}
```

Mục CÂU HỎI CÒN BỎ NGỎ có thể tồn tại với nội dung Không; chỉ `CAN_LAM_RO` mới chặn Coder. Không tự đoán quyết định còn thiếu. Report phải có nội dung cụ thể, không chỉ header.

## Helper và kiểm tra
Yêu cầu Python >=3.11 + Git. Với repo Windows này có thể dùng `runtime/python.exe` thay cho `python` ở các lệnh dưới. Không cài dependency hoặc gọi API riêng.

```text
python .codex/commands/ship_guard.py start --request "Yêu cầu tính năng"
python .codex/commands/ship_guard.py status
python .codex/commands/ship_guard.py check planner
python .codex/commands/ship_guard.py check coder
python .codex/commands/ship_guard.py test -- "{python}" -m unittest discover -s tests -v
python .codex/commands/ship_guard.py check tester
python .codex/commands/ship_guard.py diff
python .codex/commands/ship_guard.py check reviewer
```

Đây là các bước do agent cha/Tester chạy theo ship.md; không phải hướng dẫn bỏ qua agent và tự làm báo cáo. Có thể truyền `--root <repo>` trước subcommand. Yêu cầu dài dùng `start --request-file <file>`.

Chỉ lệnh test khớp argv trong kế hoạch được helper chạy; `{python}` được thay bằng Python đang chạy helper. Trên PowerShell giữ dấu nháy quanh "{python}". Exit code, output và hash log lưu trong `.bangiao/nen/<RUN_ID>/test-*.log`. Helper không cho chạy lại sau lệnh test thất bại. Tester viết report, cha kiểm tra và vẫn giao Reviewer. Negative case xử lý lỗi đúng phải PASS; không cần cố tạo suite đỏ.

## Giữ công việc hiện hữu
- main/master/detached HEAD: dừng trước khi mkdir/xóa báo cáo.
- Nhánh có thay đổi chưa commit vẫn dùng được: baseline là trạng thái hiện có, không reset/stash/stage. `diff` so với bản chụp trước Coder, không gán toàn bộ git diff cũ cho workflow.
- Chỉ xóa bốn báo cáo cũ đúng tên; giữ thư mục nen và các file khác. Lượt đang chạy không bị ghi đè.
- Không sửa code/test/config ngoài allowlist; phát hiện vi phạm thì giữ nguyên để người dùng kiểm tra và chuyển Reviewer, không tự rollback.
- File data/runtime/secrets bị cấm trong kế hoạch; helper không đọc/hash payload dữ liệu. Hậu kiểm có giới hạn, không thay thế phân quyền OS hoặc chống agent cố tình sửa chính helper/metadata. Không chạy công việc khác sửa repo trong lúc ship.
- Reviewer không CHOT khi test bắt buộc thiếu/đỏ, Coder chưa hoàn tất hoặc có vi phạm. CHOT chỉ là khuyến nghị kỹ thuật; con người quyết định merge.
- Báo cáo thiếu/rỗng/sai lượt/model: dừng, không đọc báo cáo cũ hoặc giả kết quả. Model/quyền lỗi cũng dừng, không fallback.
- Không commit, push, merge, tạo PR, đổi nhánh hoặc chỉnh cấu hình Codex toàn máy.

Nếu người dùng yêu cầu bỏ lượt đang kẹt: `python .codex/commands/ship_guard.py halt --reason "Lý do"`. Không tự sửa luot-chay.json, xóa lock hoặc tự bắt đầu lại.

## Tự kiểm tra cấu hình và gate

```text
python .codex/commands/test_ship_guard.py
```

Test tạo Git repo tạm và seed commit để có HEAD cho fixture; không commit repo sản phẩm. Smoke thật và kết quả nhận diện native được ghi trong `KIEM_THU.md` sau khi kiểm tra; không đồng nhất việc TOML parse thành công với model thực sự chạy.

Tham chiếu: https://learn.chatgpt.com/docs/agent-configuration/subagents

Không có Auto Fix Loop hoặc Task Queue. Khi test đỏ vẫn giao Reviewer theo next_role, không sửa/chạy lại test. Header MODEL chỉ là khai báo; log spawn host mới chứng minh vai trò/model thực sự chạy.

Skills: https://learn.chatgpt.com/docs/build-skills
