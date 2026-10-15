@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
if errorlevel 1 (
  echo [ERROR] Cannot open the directory containing this BAT file.
  pause
  exit /b 1
)
where git >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Git is not installed or not in PATH.
  echo Install Git for Windows: https://git-scm.com/downloads/win
  pause
  exit /b 1
)

:MENU
cls
echo =====================================================
echo                 GIT HELPER FOR WINDOWS
echo =====================================================
echo Working folder: %CD%
echo.
echo [1] Initialize Git repository in this folder
echo [2] Connect / change GitHub remote (origin)
echo [3] View status and remote
echo [4] Stage ALL changes and commit
echo [5] Push current branch to GitHub
echo [6] Pull current branch (fast-forward only)
echo [7] Revert a commit (safe: creates new commit)
echo [8] View recent commit history
echo [9] Open Vietnamese Git guide
echo [0] Exit
echo =====================================================
choice /C 1234567890 /N /M "Choose an option: "
if errorlevel 10 goto END
if errorlevel 9 goto HELP
if errorlevel 8 goto LOG
if errorlevel 7 goto REVERT
if errorlevel 6 goto PULL
if errorlevel 5 goto PUSH
if errorlevel 4 goto COMMIT
if errorlevel 3 goto STATUS
if errorlevel 2 goto REMOTE
if errorlevel 1 goto INIT
goto MENU

:INIT
echo.
git rev-parse --is-inside-work-tree >nul 2>&1
if not errorlevel 1 (
  echo This folder is already inside a Git repository.
  call :CHECK_REPO
  goto PAUSE_MENU
)
git init -b main
if errorlevel 1 (
  echo [ERROR] git init failed.
  goto PAUSE_MENU
)
if exist ".gitignore" goto INIT_OK
(
  echo # Dependencies and build outputs
  echo node_modules/
  echo .next/
  echo dist/
  echo build/
  echo coverage/
  echo .venv/
  echo __pycache__/
  echo # Credentials - never commit secrets
  echo .env
  echo .env.*
  echo !.env.example
  echo !.env.sample
  echo *.pem
  echo *.p12
  echo *.key
  echo # Logs and OS files
  echo *.log
  echo .DS_Store
  echo Thumbs.db
) > ".gitignore"
echo Created a starter .gitignore. Review it for your project.
:INIT_OK
echo [OK] Local repository is initialized.
echo NEXT: Create an EMPTY repository on https://github.com/new
 echo Then use option 2 to connect your GitHub URL.
goto PAUSE_MENU

:REMOTE
call :CHECK_REPO
if errorlevel 1 goto PAUSE_MENU
echo.
echo Current remote(s):
git remote -v
echo.
set "REMOTE_URL="
set /p "REMOTE_URL=Paste GitHub URL (https://github.com/USER/REPO.git): "
if not defined REMOTE_URL (
  echo Canceled - no URL provided.
  goto PAUSE_MENU
)
git remote get-url origin >nul 2>&1
if errorlevel 1 goto REMOTE_ADD
echo.
choice /C YN /N /M "origin already exists. Replace its URL? [Y/N]: "
if errorlevel 2 goto PAUSE_MENU
git remote set-url origin "%REMOTE_URL%"
goto REMOTE_FINISH
:REMOTE_ADD
git remote add origin "%REMOTE_URL%"
:REMOTE_FINISH
if errorlevel 1 (
  echo [ERROR] Could not configure origin.
  goto PAUSE_MENU
)
echo [OK] Remote origin:
git remote -v
goto PAUSE_MENU

:STATUS
call :CHECK_REPO
if errorlevel 1 goto PAUSE_MENU
echo.
echo -- Git status --
git status -sb
echo.
echo -- Remote --
git remote -v
goto PAUSE_MENU

:COMMIT
call :CHECK_REPO
if errorlevel 1 goto PAUSE_MENU
echo.
echo [NOTE] git add -A stages every non-ignored change in this repository.
echo Review .gitignore, .env, tokens and private files BEFORE continuing.
choice /C YN /N /M "Stage all changes now? [Y/N]: "
if errorlevel 2 goto PAUSE_MENU
git add -A
if errorlevel 1 (
  echo [ERROR] git add failed.
  goto PAUSE_MENU
)
git diff --cached --quiet
if not errorlevel 1 (
  echo No staged changes to commit.
  goto PAUSE_MENU
)
echo.
echo -- Staged files --
git diff --cached --name-status
echo.
choice /C YN /N /M "Are these files safe to commit? [Y/N]: "
if errorlevel 2 (
  echo Files remain staged. To unstage: git restore --staged ^<file^>
  goto PAUSE_MENU
)
set "COMMIT_MSG="
set /p "COMMIT_MSG=Commit message (example: feat: add dashboard): "
if not defined COMMIT_MSG (
  echo Commit canceled - empty message. Changes remain staged.
  goto PAUSE_MENU
)
git commit -m "%COMMIT_MSG%"
if errorlevel 1 (
  echo [ERROR] Commit failed. Check git user.name / user.email.
  goto PAUSE_MENU
)
echo [OK] Commit created. Choose option 5 to push.
goto PAUSE_MENU

:PUSH
call :CHECK_REPO
if errorlevel 1 goto PAUSE_MENU
call :GET_BRANCH
if not defined BRANCH (
  echo [ERROR] Detached HEAD: switch to a branch before pushing.
  goto PAUSE_MENU
)
git show-ref --verify --quiet "refs/heads/%BRANCH%"
if errorlevel 1 (
  echo [ERROR] No commit exists yet. Use option 4 first.
  goto PAUSE_MENU
)
git remote get-url origin >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Remote origin is missing. Use option 2 first.
  goto PAUSE_MENU
)
echo.
echo Pushing branch: %BRANCH%
git push -u origin "%BRANCH%"
if errorlevel 1 (
  echo [ERROR] Push did not complete. Your local commits are kept.
  echo If GitHub already contains a README commit, see the Git guide.
  goto PAUSE_MENU
)
echo [OK] Push completed.
goto PAUSE_MENU

:PULL
call :CHECK_REPO
if errorlevel 1 goto PAUSE_MENU
call :GET_BRANCH
if not defined BRANCH (
  echo [ERROR] Detached HEAD: switch to a branch before pulling.
  goto PAUSE_MENU
)
call :CHECK_CLEAN
if errorlevel 1 goto PAUSE_MENU
git remote get-url origin >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Remote origin is missing. Use option 2 first.
  goto PAUSE_MENU
)
echo.
echo Pulling origin/%BRANCH% (fast-forward only)...
git pull --ff-only origin "%BRANCH%"
if errorlevel 1 (
  echo [ERROR] Pull stopped without rewriting your history.
  echo Inspect divergence using: git fetch origin
  echo Then run: git log --oneline --graph --all -15
  goto PAUSE_MENU
)
echo [OK] Pull completed.
goto PAUSE_MENU

:REVERT
call :CHECK_REPO
if errorlevel 1 goto PAUSE_MENU
call :CHECK_CLEAN
if errorlevel 1 goto PAUSE_MENU
echo.
echo -- Recent commits --
git log --oneline -8
if errorlevel 1 goto PAUSE_MENU
echo.
set "TARGET_COMMIT="
set /p "TARGET_COMMIT=Commit hash to revert (press Enter for HEAD): "
if not defined TARGET_COMMIT set "TARGET_COMMIT=HEAD"
git rev-parse --verify --quiet "%TARGET_COMMIT%" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Unknown commit reference.
  goto PAUSE_MENU
)
echo.
echo This creates a NEW commit that reverses %TARGET_COMMIT%.
echo It does NOT erase prior Git history.
choice /C YN /N /M "Confirm revert? [Y/N]: "
if errorlevel 2 goto PAUSE_MENU
git revert --no-edit "%TARGET_COMMIT%"
if errorlevel 1 (
  echo [WARNING] Revert did not finish, possibly due to a conflict.
  echo Run git status. After fixing files: git add -A, then git revert --continue
  echo To cancel the in-progress revert: git revert --abort
  goto PAUSE_MENU
)
echo [OK] Revert commit created. Use option 5 to push it.
goto PAUSE_MENU

:LOG
call :CHECK_REPO
if errorlevel 1 goto PAUSE_MENU
echo.
git log --oneline --decorate --graph -15
if errorlevel 1 echo No commits yet.
goto PAUSE_MENU

:HELP
if exist "%~dp0Git_Guide_VI.md" (
  start "" notepad.exe "%~dp0Git_Guide_VI.md"
) else (
  echo Could not find Git_Guide_VI.md next to this BAT file.
)
goto PAUSE_MENU

:CHECK_REPO
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Not a Git repository. Use option 1 first.
  exit /b 1
)
set "GIT_ROOT="
for /f "delims=" %%R in ('git rev-parse --show-toplevel 2^>nul') do set "GIT_ROOT=%%R"
if not defined GIT_ROOT (
  echo [ERROR] Could not find Git repository root.
  exit /b 1
)
set "GIT_ROOT=%GIT_ROOT:/=\%"
if /I not "%CD%"=="%GIT_ROOT%" (
  echo [ERROR] This BAT file is not in the Git repository ROOT.
  echo Git root: %GIT_ROOT%
  echo BAT folder: %CD%
  echo Move both helper files to Git root, then try again.
  exit /b 1
)
exit /b 0

:GET_BRANCH
set "BRANCH="
for /f "delims=" %%B in ('git symbolic-ref --quiet --short HEAD 2^>nul') do set "BRANCH=%%B"
exit /b 0

:CHECK_CLEAN
set "DIRTY="
for /f "delims=" %%D in ('git status --porcelain 2^>nul') do set "DIRTY=1"
if defined DIRTY (
  echo [ERROR] The working tree has uncommitted or untracked changes.
  echo Commit changes first, or use git stash -u if appropriate.
  git status -sb
  exit /b 1
)
exit /b 0

:PAUSE_MENU
echo.
pause
goto MENU

:END
endlocal
exit /b 0
