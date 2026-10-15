@echo off
setlocal
set "ONECLICK_GIT_SELF=%~f0"
set "ONECLICK_GIT_TARGET=%~1"
title Git One-Click - Initial Commit
powershell.exe -NoLogo -NoProfile -STA -Command "$raw = Get-Content -LiteralPath $env:ONECLICK_GIT_SELF -Raw -Encoding UTF8; $marker = '# === POWERSHELL PAYLOAD START ==='; $start = $raw.LastIndexOf($marker); if ($start -lt 0) { throw 'Embedded script not found' }; & ([scriptblock]::Create($raw.Substring($start + $marker.Length)))"
set "ONECLICK_GIT_RESULT=%ERRORLEVEL%"
echo.
if "%ONECLICK_GIT_RESULT%"=="0" (echo Completed. Press any key to close.) else (echo ERROR - nothing was pushed to GitHub. Press any key to close.)
pause >nul
exit /b %ONECLICK_GIT_RESULT%
# === POWERSHELL PAYLOAD START ===
$ErrorActionPreference = 'Stop'
$gitUser = 'nambuihoang96'
$gitEmail = 'mommeo96@gmail.com'

function Stop-WithMessage([string]$message) {
    Write-Host ''
    Write-Host ('ERROR: ' + $message) -ForegroundColor Red
    exit 1
}

function Run-Git([string[]]$arguments) {
    & git @arguments
    if ($LASTEXITCODE -ne 0) {
        throw ('Git command failed: git ' + ($arguments -join ' '))
    }
}

try {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Stop-WithMessage 'Git is not installed or not present in PATH.'
    }

    $target = $env:ONECLICK_GIT_TARGET
    if ([string]::IsNullOrWhiteSpace($target)) {
        Add-Type -AssemblyName System.Windows.Forms
        $chooser = New-Object System.Windows.Forms.FolderBrowserDialog
        $chooser.Description = 'Select the SOURCE folder to initialize Git and create the first commit'
        $chooser.ShowNewFolderButton = $false
        if ($chooser.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
            Write-Host 'Canceled. No files changed.'
            exit 0
        }
        $target = $chooser.SelectedPath
    }
    if (-not (Test-Path -LiteralPath $target -PathType Container)) {
        Stop-WithMessage ('Folder does not exist: ' + $target)
    }
    $target = (Resolve-Path -LiteralPath $target).ProviderPath
    Write-Host ('Project folder: ' + $target) -ForegroundColor Cyan
    Push-Location -LiteralPath $target
    try {
        # Refuse subfolders of existing repos so the wrong repository is never committed.
        $inside = & git rev-parse --is-inside-work-tree 2>$null
        if ($LASTEXITCODE -eq 0 -and $inside -eq 'true') {
            $root = & git rev-parse --show-toplevel 2>$null
            if ($LASTEXITCODE -ne 0) { throw 'Cannot determine Git root.' }
            $rootPath = (Resolve-Path -LiteralPath $root).ProviderPath.TrimEnd('\', '/')
            if (-not [string]::Equals($rootPath, $target.TrimEnd('\', '/'), [StringComparison]::OrdinalIgnoreCase)) {
                Stop-WithMessage ('You selected a subfolder. Select the Git root instead: ' + $rootPath)
            }
            $head = & git rev-parse --verify HEAD 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host 'This project already has an initial commit. No changes made.' -ForegroundColor Yellow
                & git log -1 --oneline
                exit 0
            }
            Write-Host 'Git exists, but no commit was found. Continuing.'
        } else {
            Run-Git @('init', '-b', 'main')
        }

        Run-Git @('config', '--local', 'user.name', $gitUser)
        Run-Git @('config', '--local', 'user.email', $gitEmail)
        Run-Git @('branch', '-M', 'main')
        Write-Host ('Git identity (local repo): ' + $gitUser + ' <' + $gitEmail + '>')

        # Conservative generic ignore list; never hide dist/ or source data/ by default.
        $ignoreFile = Join-Path $target '.gitignore'
        $markerLine = '# --- One-click Git: personal data and generated files ---'
        $ignoreBlock = @(
            $markerLine,
            '.env',
            '.env.*',
            '!.env.example',
            '!.env.sample',
            'node_modules/',
            '.venv/',
            'venv/',
            '__pycache__/',
            '*.pyc',
            '.pytest_cache/',
            '.cache/',
            'tmp/',
            'backup/',
            'backups/',
            '.codex/',
            '.idea/',
            '.vs/',
            '*.log',
            '*.sqlite',
            '*.sqlite3',
            '*.db',
            '*.pem',
            '*.key',
            '*.p12',
            '*.pfx',
            '*.p8',
            'id_rsa',
            'id_ed25519',
            'auth.json',
            'credentials.json',
            'secrets.json',
            'Thumbs.db',
            '.DS_Store',
            '# --- End of one-click defaults ---'
        ) -join "`r`n"
        if (-not (Test-Path -LiteralPath $ignoreFile)) {
            [System.IO.File]::WriteAllText($ignoreFile, $ignoreBlock + "`r`n", [System.Text.UTF8Encoding]::new($false))
            Write-Host 'Created .gitignore with common sensitive/generated file exclusions.'
        } elseif (-not ([System.IO.File]::ReadAllText($ignoreFile)).Contains($markerLine)) {
            [System.IO.File]::AppendAllText($ignoreFile, "`r`n" + $ignoreBlock + "`r`n", [System.Text.UTF8Encoding]::new($false))
            Write-Host 'Added common exclusions to existing .gitignore (preserved original entries).'
        }

        # Prevent auto-committing filenames that strongly suggest secrets.
        $candidates = @(& git -c core.quotepath=false ls-files --others --exclude-standard)
        if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect files that Git would add.' }
        $suspicious = @($candidates | Where-Object {
            $name = ($_ -replace '\\', '/').ToLowerInvariant()
            $name -match '(^|/)(?:\.env(?:\.|$)(?!example$|sample$)|.*(?:private[-_]?key|api[-_]?key|access[-_]?token|credentials?|secrets?)(?:\.|-|_|$)|id_rsa|id_ed25519)' -or
            $name -match '\.(?:pem|key|p12|pfx|p8|db|sqlite|sqlite3)$'
        })
        if ($suspicious.Count -gt 0) {
            Write-Host 'The following unignored files may contain secrets:' -ForegroundColor Yellow
            $suspicious | Select-Object -First 25 | ForEach-Object { Write-Host ('  ' + $_) }
            Stop-WithMessage 'Initial commit canceled. Add appropriate patterns to .gitignore and run again.'
        }

        Run-Git @('add', '-A')
        $staged = @(& git diff --cached --name-only)
        if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect staged changes.' }
        if ($staged.Count -eq 0) { Stop-WithMessage 'No files are staged for the initial commit.' }
        $secretStage = @($staged | Where-Object {
            $name = ($_ -replace '\\', '/').ToLowerInvariant()
            ($name -match '(^|/)(?:\.env(?:\.|$)(?!example$|sample$)|.*(?:private[-_]?key|api[-_]?key|access[-_]?token|credentials?|secrets?)(?:\.|-|_|$)|id_rsa|id_ed25519)' -or
             $name -match '\.(?:pem|key|p12|pfx|p8|db|sqlite|sqlite3)$')
        })
        if ($secretStage.Count -gt 0) {
            $secretStage | Select-Object -First 25 | ForEach-Object { Write-Host ('  UNSAFE STAGED: ' + $_) -ForegroundColor Red }
            Stop-WithMessage 'Initial commit canceled: suspicious files staged. Review staging / .gitignore manually.'
        }
        Write-Host ('Staged files: ' + $staged.Count)
        $staged | Select-Object -First 30 | ForEach-Object { Write-Host ('  ' + $_) }
        if ($staged.Count -gt 30) { Write-Host ('  ... plus ' + ($staged.Count - 30) + ' more files') }
        Write-Host 'Creating initial commit...' -ForegroundColor Cyan
        Run-Git @('commit', '-m', 'Initial project baseline')
        Write-Host ''
        Write-Host 'SUCCESS: Local Git repository is ready for AI Development Manager.' -ForegroundColor Green
        Write-Host ('Git root: ' + $target)
        Write-Host ('Git user: ' + $gitUser)
        Write-Host ('Git email: ' + $gitEmail)
        Write-Host 'No GitHub remote was created. Nothing was pushed.'
        & git log -1 --oneline
    } finally {
        Pop-Location
    }
} catch {
    Stop-WithMessage $_.Exception.Message
}
