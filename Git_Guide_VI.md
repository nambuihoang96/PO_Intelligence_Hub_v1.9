# Hướng dẫn Git & GitHub cho Windows — từ folder tới repository

Dành cho project code trên Windows (ví dụ: PO Intelligence), dùng CMD, PowerShell, Windows Terminal hoặc VS Code Terminal.

## 1. Chuẩn bị (chỉ làm lần đầu)

1. Cài **Git for Windows**: https://git-scm.com/downloads/win
2. Mở terminal, kiểm tra:

   ```bash
   git --version
   ```

3. Cấu hình tên/email để Git ghi tác giả commit (thay bằng của bạn):

   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "you@example.com"
   ```

4. Đăng nhập GitHub trên trình duyệt. Khi `git push` yêu cầu xác thực HTTPS, dùng luồng đăng nhập của **Git Credential Manager** (nếu được cài) hoặc personal access token; mật khẩu GitHub thông thường **không** dùng để xác thực Git qua HTTPS.

## 2. Đẩy folder project lên GitHub lần đầu

**Bước A — tạo repository trên GitHub**

- Mở https://github.com/new, nhập tên, ví dụ `po-intelligence`.
- Chọn **Private** nếu project có code nội bộ, công ty hoặc dữ liệu cần bảo vệ.
- Vì folder đã tồn tại trên máy, hãy để repository mới **trống**: không tick README, `.gitignore` hoặc license lúc tạo. Điều này tránh lệch lịch sử commit ban đầu.
- Bấm **Create repository**, copy URL dạng `https://github.com/USERNAME/po-intelligence.git`.

**Bước B — cách dễ nhất với file BAT**

1. Copy `Git_Helper.bat` và `Git_Guide_VI.md` vào **thư mục gốc** của project (ngang hàng `package.json` nếu có).
2. Nhấp đúp `Git_Helper.bat`.
3. Chọn **1** để `git init` (nếu folder chưa có Git). Script tự tạo `.gitignore` mẫu **chỉ khi chưa tồn tại**.
4. Chọn **2** và paste URL repository GitHub.
5. Chọn **4** để stage và tạo commit đầu tiên. **Kiểm tra file chuẩn bị commit**, nhất là `.env`, token, key, CSV và dữ liệu riêng tư.
6. Chọn **5** để push; xác thực GitHub nếu được hỏi.
7. Refresh trang repository GitHub để kiểm tra source đã xuất hiện.

**Bước C — cách dùng lệnh trực tiếp (không cần BAT)**

Mở terminal **ngay trong folder project**:

```bash
# Chỉ chạy khi folder chưa có repository Git
git init -b main

# Kiểm tra .gitignore trước khi add
git status

git add -A
git status
git commit -m "chore: initial project setup"

git remote add origin https://github.com/USERNAME/po-intelligence.git
git push -u origin main
```

Nếu repo đã có Git (`.git`) thì **không cần** chạy lại `git init`. Kiểm tra `git remote -v`, `git branch --show-current`, và push nhánh hiện có thay vì mặc định `main`.

## 3. Workflow Git hằng ngày

**Trước khi code** (nhất là khi nhiều máy/người cùng làm):

```bash
git status
git pull --ff-only
```

**Sau khi code xong**:

```bash
git status
git diff                 # Xem thay đổi chưa stage
git add -A
git diff --cached --stat # Xem nội dung được stage theo tổng quan
git commit -m "feat: improve analytics dashboard"
git push
```

Lần push đầu tiên của một branch mới, sử dụng `git push -u origin TEN_NHANH`. Sau đó `git push` là đủ.

**Nên nhớ:**

- `git add` = đưa thay đổi vào vùng **staging**.
- `git commit` = lưu phiên bản **trên máy**, chưa lên GitHub.
- `git push` = đưa commit local **lên GitHub**.
- `git fetch` = tải thông tin lịch sử remote, **không nhập vào branch đang làm**.
- `git pull` = fetch + tích hợp thay đổi từ remote vào branch hiện tại; `--ff-only` dừng nếu lịch sử bị phân nhánh, tránh merge bất ngờ.

## 4. Bảng lệnh Git cơ bản

| Nhu cầu | Lệnh | Ghi chú |
|---|---|---|
| Xem trạng thái | `git status -sb` | Đang ở branch nào, file nào thay đổi |
| Xem nội dung sửa | `git diff` | Với các thay đổi chưa stage |
| Xem file được stage | `git diff --cached --name-status` | Trước khi commit |
| Stage tất cả | `git add -A` | Bao gồm file bị xóa; chỉ file không bị ignore |
| Stage một file | `git add duong-dan/file.ts` | An toàn hơn khi muốn commit chọn lọc |
| Tạo commit | `git commit -m "fix: repair chart"` | Lưu local |
| Xem lịch sử | `git log --oneline --graph --decorate -15` | Lấy mã commit để revert |
| Xem remote | `git remote -v` | Kiểm tra URL GitHub |
| Đổi URL remote | `git remote set-url origin URL_MOI` | Nếu đã có origin |
| Cập nhật từ GitHub | `git pull --ff-only` | Khi đã set upstream |
| Đẩy lên GitHub | `git push` | Khi đã set upstream |
| Tạo branch | `git switch -c feature/new-dashboard` | Tách tính năng khỏi main |
| Chuyển branch | `git switch main` | Cẩn thận file chưa commit |
| Xem branch | `git branch -a` | Local + remote-tracking |
| Lưu tạm thay đổi | `git stash push -u -m "WIP"` | Bao gồm untracked, không gồm ignored |
| Khôi phục stash | `git stash pop` | Có thể phát sinh conflict |

## 5. Revert, undo và restore — KHÔNG giống nhau

### A. Đã commit/push rồi, muốn hoàn tác commit mà vẫn giữ lịch sử (khuyên dùng)

```bash
git log --oneline -10
git revert abc1234    # Đảo tác động của commit abc1234, tạo commit mới
git push
```

Hoặc để hoàn tác **commit mới nhất**:

```bash
git revert --no-edit HEAD
git push
```

`git revert` phù hợp nhất khi commit đã lên GitHub hoặc nhiều người đang dùng chung nhánh. Nếu gặp conflict: chỉnh file, `git add -A`, `git revert --continue`; muốn hủy tiến trình thì `git revert --abort`. **Revert một merge commit** cần xử lý thêm, đừng tự đoán tham số `-m`.

### B. Lỡ `git add` nhưng chưa commit — bỏ stage (GIỮ sửa đổi ở file)

```bash
git restore --staged duong-dan/file.ts
# Hoặc unstage toàn bộ:
git restore --staged .
```

### C. Chưa commit, muốn bỏ sửa đổi của 1 file (XÓA sửa đổi local của file đó)

```bash
git diff -- duong-dan/file.ts  # Xem kỹ trước
git restore -- duong-dan/file.ts
```

**Cảnh báo:** `git restore` trên file đã theo dõi sẽ loại bỏ chỉnh sửa chưa commit; khó phục hồi nếu không có bản lưu khác. Nó không xóa file chưa được Git theo dõi (untracked).

### D. Commit cuối chưa push, muốn sửa nội dung hoặc message

```bash
# Chỉ khi CHƯA push và chắc chắn không ai dựa vào commit này
git commit --amend
```

Nếu commit đã push, thường nên tạo commit sửa mới hoặc `git revert` thay vì viết lại lịch sử.

> Tránh dùng `git reset --hard`, `git clean -fd` và `git push --force` nếu chưa hiểu rõ hậu quả. File BAT **không** có các thao tác này.

## 6. Lỗi thường gặp

**`fatal: not a git repository`**: Chưa `git init`, hoặc đang mở terminal sai folder. Chạy `cd` tới thư mục gốc project.

**`Author identity unknown` / `Please tell me who you are`**: Cấu hình `git config --global user.name` và `user.email` như Mục 1.

**`remote origin already exists`**: Dùng `git remote -v`; nếu cần đổi URL, dùng `git remote set-url origin https://github.com/USERNAME/REPO.git`.

**`rejected (non-fast-forward)` khi push**: GitHub có commit mà local chưa có, hoặc lịch sử đã khác. Chạy:

```bash
git fetch origin
git log --oneline --graph --all -20
```

Không `force push`. Nếu GitHub repo mới có README được tạo riêng thì hai bên có thể có **lịch sử không liên quan**; cách dễ nhất trước lần push đầu tiên là tạo repository GitHub **trống**. Với repo có dữ liệu quan trọng, cần xem lịch sử trước khi chọn merge/rebase.

**`fatal: refusing to merge unrelated histories`**: Local và remote có hai lịch sử gốc độc lập. Không tự reset/force; kiểm tra repo, backup nếu cần, rồi xử lý merge có chủ đích hoặc tạo repo trống khác.

**`Authentication failed` hoặc `Permission denied`**: Kiểm tra URL `git remote -v`, quyền repo và tài khoản GitHub đang đăng nhập qua credential manager. HTTPS không dùng mật khẩu GitHub bình thường; có thể dùng Git Credential Manager, GitHub CLI hoặc personal access token.

**`git pull --ff-only` thất bại**: Branch local và remote đã diverge. Kiểm tra bằng `git fetch origin` + `git log --oneline --graph --all -20`; quyết định merge/rebase có chủ đích.

**Push rồi nhưng thiếu file**: Kiểm tra `.gitignore`, `git status`, và `git ls-files`; các file bị ignore sẽ không được add.

## 7. Gợi ý riêng cho project PO Intelligence

- Nếu có dữ liệu AdMob/GA4, file export CSV, khóa API, service account JSON, session/cookie: **không đẩy lên public repository**. `Private` cũng không thay cho việc bảo vệ secrets.
- Nếu project dùng Node/Next.js: ignore `node_modules/`, `.next/`, `dist/`, `.env*` (giữ `.env.example` không chứa bí mật).
- Commit theo nhiệm vụ nhỏ: `feat: add market research flow`, `fix: handle missing AdMob data`, `refactor: split agent orchestration`.
- Nếu làm đa agent/Codex: mỗi task nên làm trên branch riêng, ví dụ `feature/ux-audit`, rồi review trước khi merge vào `main`.
- Script đặt ở **root Git**, không đặt trong folder con.

## 8. Tài liệu chính thức

- GitHub: https://docs.github.com/en/get-started/start-your-journey/creating-an-account-on-github
- GitHub authentication: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github
- Git revert: https://git-scm.com/docs/git-revert
- Git restore: https://git-scm.com/docs/git-restore
- Git pull: https://git-scm.com/docs/git-pull
- Git push: https://git-scm.com/docs/git-push
