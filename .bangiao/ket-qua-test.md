TRANG_THAI: DAT
LUOT_CHAY: fb60ee9db8ee482698b37d8924818a32
NHANH: testagent
VAI_TRO: tester
MODEL: gpt-6-luna

## Kết quả kiểm thử

Cả sáu lệnh bắt buộc trong `.bangiao/luot-chay.json` đã chạy tuần tự qua `.codex/commands/ship_guard.py test -- <argv>` và đều có exit code 0. Không có lệnh lỗi; không sửa test sau khi bắt đầu chạy. Bốn runner Python dùng cùng đoạn `-c` isolation runner lấy nguyên văn từ kế hoạch: đặt `TMP`, `TEMP`, `tempfile.tempdir` vào ROOT/.bangiao; chặn duy nhất `Path.mkdir(ROOT/data)` trong lúc import `server`; chuyển `s.DATA` và `s.DBPATH` vào `TemporaryDirectory` dưới `.bangiao` trước khi discover. Thư mục tạm tự được dọn khi runner kết thúc. Hai lệnh Node không nhận đường dẫn dữ liệu.

Các lệnh thực chạy (Python helper được gọi bằng `runtime/python.exe`; `{python}` được truyền nguyên dạng chuỗi có nháy để helper thay bằng `sys.executable`):

1. `runtime/python.exe .codex/commands/ship_guard.py test -- '{python}' -B -c <isolation runner nguyên văn trong commands[0]> test_intelligence.py` — exit 0; log `.bangiao/nen/fb60ee9db8ee482698b37d8924818a32/test-e7ae387011de4ef7b7b1260a949ea7e8.log`; 49 tests PASS.
2. `runtime/python.exe .codex/commands/ship_guard.py test -- '{python}' -B -c <cùng isolation runner> test_workspace.py` — exit 0; log `.bangiao/nen/fb60ee9db8ee482698b37d8924818a32/test-bb69fdaff1794302991c1a5e910b258d.log`; 33 tests PASS.
3. `runtime/python.exe .codex/commands/ship_guard.py test -- '{python}' -B -c <cùng isolation runner> test_studio.py` — exit 0; log `.bangiao/nen/fb60ee9db8ee482698b37d8924818a32/test-083f3d1edab34d0ca5519de67a2f60e3.log`; 6 tests PASS.
4. `runtime/python.exe .codex/commands/ship_guard.py test -- '{python}' -B -c <cùng isolation runner> test_answer_engine.py` — exit 0; log `.bangiao/nen/fb60ee9db8ee482698b37d8924818a32/test-48f21289c64c46448e643252a49a4f88.log`; 10 tests PASS.
5. `runtime/python.exe .codex/commands/ship_guard.py test -- 'D:/Program Files/nodejs/node.exe' 'tests/test_v16_core.cjs'` — exit 0; log `.bangiao/nen/fb60ee9db8ee482698b37d8924818a32/test-73897b90958e47d3b1ffe4aa2b2d333f.log` (`v1.6.1 core tests passed`).
6. `runtime/python.exe .codex/commands/ship_guard.py test -- 'D:/Program Files/nodejs/node.exe' 'tests/test_intelligence_core.cjs'` — exit 0; log `.bangiao/nen/fb60ee9db8ee482698b37d8924818a32/test-493366725e134239996a45f8bb78ec0c.log` (`v1.9.1 CSV day/period/currency/cohort parser tests PASS`).

Các log và SHA-256 được tạo bởi guard trong lượt này. Bốn log Python lần lượt kết thúc `Ran 49/33/6/10 tests ... OK`. Tổng cộng 98 tests Python cùng hai bộ kiểm tra JavaScript đều qua.

## Hành vi đã kiểm tra

- Lineage và số liệu tăng trưởng: refs chỉ lấy từ evidence khai báo; metadata sai kiểu/thiếu/không khớp làm metric không đủ điều kiện, không tự thêm ID; PoP giữ previous suy ra 100000, current 145000, delta 45000, +45% dù baseline mâu thuẫn; unrelated mismatch chỉ chặn và đưa refs thật vào chẩn đoán, còn unrelated bằng giá trị không corroborate hoặc thêm refs. YoY giữ 50000 → 145000, +190%; giảm 100000 → 80000 cho -20%/down; baseline zero cho `percent=None` và `zero_base=True`. Leap-day YoY dùng ngày 28/2 năm trước. Huge integers, phần trăm tràn, aggregate tràn và invalid levels bị xử lý hữu hạn; aggregate không hữu hạn không vào group.
- Scope, identity và daily: Worldwide casing deduplicate tại enrichment, assessment kể cả metric ID legacy khác, và dashboard; giữ GEO gốc ở evidence/output. Conflict cùng identity vẫn bị chặn và union refs. Warning app 142 không chặn app 42, còn exact ID chặn. Missing, sai dạng, ngày compact/week và 2026-09-31 không tạo daily chart; bốn ngày thật có gap vẫn giữ bốn points; unrelated bị loại khỏi daily kể cả khi có public evidence cùng app. Daily warning tuân thủ exact app ID. Các test MR01 Worldwide/Unified và phân tách GEO/OS cũ vẫn qua.
- Snapshot và public answer: test import PoP/YoY thật kiểm tra deep snapshot records trước/sau, cùng deep snapshot evidence trước/sau khi enrichment; hai lineage import và công thức giữ nguyên. Name-only/possible không trở thành growth. Answer Engine chấp nhận metric đủ điều kiện và từ chối diagnostic metric conflict, metric ID hoặc evidence ID không thật.

## Lỗi và phần chưa kiểm tra

Không có lệnh thất bại, exception hoặc test đỏ trong lượt này. Các tình huống âm được mong đợi (metadata sai, warning chính xác, mâu thuẫn baseline, ngày bất khả thi, overflow, growth claim không đủ bằng chứng) được test và xử lý đúng nên tính PASS. Hai lỗi đã được ghi nhận từ lượt trước — ID `CSV:77:4` không được evidence khai báo và ngày `2026-09-31` — có assertion tương ứng trong suite hiện tại và suite Intelligence hiện chạy 49/49 PASS.

Không chạy ngoài sáu lệnh đã định: không test riêng lẻ, không probe/import ứng dụng ngoài isolation runner, không chạy database thật hoặc nguồn RSS. Các đường dẫn JavaScript được kiểm tra bởi hai command đã nêu; UI/browser, API trực tiếp, dữ liệu live và các cấu hình ngoài phạm vi chưa được kiểm tra. Số lần sửa sau lần chạy đầu: 0.
