# Gemini 影片字幕翻譯工具 啟動器

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$host.UI.RawUI.WindowTitle = "Gemini 影片字幕翻譯工具"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Clear-Host
Write-Host "[INFO] Starting Gemini 影片字幕翻譯工具..." -ForegroundColor Green
Write-Host ""

# 偵測系統架構
$isArm64 = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture -eq 'Arm64'

# ======================================
# [1/4] 檢查 Python
# ======================================
Write-Host "[1/4] 檢查 Python 環境..." -ForegroundColor Cyan
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[WARNING] 未偵測到 Python，本程式需要 Python 才能執行。" -ForegroundColor Yellow
    if ($isArm64) {
        Write-Host ""
        Write-Host "  [!] 偵測到您的電腦是 ARM 架構（例如 Snapdragon X 系列筆電）。" -ForegroundColor Yellow
        Write-Host "  [!] 如果您之前已安裝過 Python 但還是看到這個訊息，" -ForegroundColor Yellow
        Write-Host "      請先到「設定 → 應用程式」搜尋 Python 並移除，" -ForegroundColor Yellow
        Write-Host "      移除後重新點兩下啟動檔，我們會自動幫您安裝正確版本。" -ForegroundColor Yellow
        Write-Host ""
    }
    $ans = Read-Host "是否要立即安裝 Python？[Y/n] - 直接按 Enter 代表同意"
    if ($ans -eq "" -or $ans -ieq "Y") {
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            Write-Host "[INFO] 透過 winget 安裝 Python，請稍候..." -ForegroundColor Gray
            winget install --id Python.Python.3 -e --silent --accept-source-agreements --accept-package-agreements
        } else {
            Write-Host "[INFO] 正在下載 Python 安裝程式，請稍候..." -ForegroundColor Gray
            $arch = if ($isArm64) { "arm64" } else { "amd64" }
            $out = "$env:TEMP\python_installer.exe"
            Invoke-WebRequest "https://www.python.org/ftp/python/3.12.9/python-3.12.9-$arch.exe" -OutFile $out
            Start-Process $out -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1' -Wait
            Remove-Item $out -Force -ErrorAction SilentlyContinue
        }
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
        if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
            Write-Host "[INFO] 安裝完成，請關閉視窗後重新點兩下啟動檔。" -ForegroundColor Yellow
            Read-Host "按 Enter 關閉"; exit 0
        }
        Write-Host "[OK] Python 安裝完成。" -ForegroundColor Green
    } else {
        Write-Host "已取消。" -ForegroundColor Gray; Read-Host "按 Enter 關閉"; exit 1
    }
} else {
    $pyVer = python --version 2>&1
    Write-Host "[OK] $pyVer 已安裝。" -ForegroundColor Green
}

# ======================================
# [2/4] 檢查 FFmpeg
# ======================================
Write-Host "[2/4] 檢查 FFmpeg..." -ForegroundColor Cyan
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "[WARNING] 未偵測到 FFmpeg，本程式需要 FFmpeg 才能擷取音訊。" -ForegroundColor Yellow
    $ans = Read-Host "是否要立即安裝 FFmpeg？[Y/n] - 直接按 Enter 代表同意"
    if ($ans -eq "" -or $ans -ieq "Y") {
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            Write-Host "[INFO] 透過 winget 安裝 FFmpeg，請稍候..." -ForegroundColor Gray
            winget install --id Gyan.FFmpeg -e --silent --accept-source-agreements --accept-package-agreements
        } else {
            Write-Host "[ERROR] 找不到 winget，請手動至 https://ffmpeg.org/ 下載安裝後重新執行。" -ForegroundColor Red
            Read-Host "按 Enter 關閉"; exit 1
        }
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
        if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
            Write-Host "[INFO] 安裝完成，請關閉視窗後重新點兩下啟動檔。" -ForegroundColor Yellow
            Read-Host "按 Enter 關閉"; exit 0
        }
        Write-Host "[OK] FFmpeg 安裝完成。" -ForegroundColor Green
        if ($isArm64) {
            Write-Host "  [!] 注意：ffmpeg 目前沒有 Windows ARM 原生版本，" -ForegroundColor Yellow
            Write-Host "      安裝的是 x64 版本，會透過模擬執行，功能正常但速度略慢。" -ForegroundColor Yellow
        }
    } else {
        Write-Host "已取消。" -ForegroundColor Gray; Read-Host "按 Enter 關閉"; exit 1
    }
} else {
    Write-Host "[OK] FFmpeg 已安裝。" -ForegroundColor Green
}

# ======================================
# [3/4] 檢查 uv
# ======================================
Write-Host "[3/4] 檢查 uv 套件管理工具..." -ForegroundColor Cyan
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "[WARNING] 找不到 uv，正在安裝..." -ForegroundColor Yellow
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + $env:PATH
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "[ERROR] uv 安裝失敗，請關閉視窗後重新點兩下啟動檔再試。" -ForegroundColor Red
        Read-Host "按 Enter 關閉"; exit 1
    }
    Write-Host "[OK] uv 安裝完成。" -ForegroundColor Green
} else {
    $uvVer = uv --version
    Write-Host "[OK] $uvVer 已安裝。" -ForegroundColor Green
}

# ======================================
# [4/4] 檢查虛擬環境
# ======================================
Write-Host "[4/4] 檢查虛擬環境..." -ForegroundColor Cyan
if (-not (Test-Path "venv")) {
    Write-Host ""
    Write-Host "  ============================================" -ForegroundColor Cyan
    Write-Host "    Gemini 影片字幕翻譯工具 - 首次安裝說明" -ForegroundColor Cyan
    Write-Host "  ============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  接下來程式會自動幫你安裝以下東西：" -ForegroundColor White
    Write-Host ""
    Write-Host "    1. Python 虛擬環境（venv）" -ForegroundColor Yellow
    Write-Host "       讓這個工具有獨立乾淨的執行空間，不影響電腦其他程式" -ForegroundColor Gray
    Write-Host ""
    Write-Host "    2. google-genai" -ForegroundColor Yellow
    Write-Host "       用來呼叫 Gemini AI 產生字幕的核心套件" -ForegroundColor Gray
    Write-Host ""
    Write-Host "    3. python-dotenv" -ForegroundColor Yellow
    Write-Host "       用來儲存你的 API Key，下次不用重新輸入" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  全程只需要一直按 Enter 同意即可。" -ForegroundColor Green
    Write-Host "  如果有任何疑問，可以把這段說明貼給 AI 詢問。" -ForegroundColor Green
    Write-Host ""
    Write-Host "  ============================================" -ForegroundColor Cyan
    Write-Host ""
    $ans = Read-Host "[WARNING] 找不到虛擬環境，現在建立並安裝套件？[Y/n] - 直接按 Enter 代表同意"
    if ($ans -eq "" -or $ans -ieq "Y") {
        Write-Host "[INFO] 建立虛擬環境中..." -ForegroundColor Gray
        uv venv venv
        Write-Host "[INFO] 安裝套件中..." -ForegroundColor Gray
        uv pip install -r requirements.txt --python venv\Scripts\python.exe
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] 套件安裝失敗，請確認網路連線後重新執行。" -ForegroundColor Red
            Read-Host "按 Enter 關閉"; exit 1
        }
        Write-Host "[OK] 套件安裝完成。" -ForegroundColor Green
    } else {
        Write-Host "已取消。" -ForegroundColor Gray; Read-Host "按 Enter 關閉"; exit 1
    }
} else {
    Write-Host "[OK] 虛擬環境已就緒。" -ForegroundColor Green
}

. ".\venv\Scripts\Activate.ps1"

Write-Host ""
Write-Host "[START] 啟動中，請保持此視窗開啟..." -ForegroundColor Green
Write-Host ""

python main.py
$exitCode = $LASTEXITCODE

if (Test-Path "__pycache__") { Remove-Item -Recurse -Force "__pycache__" }

if ($exitCode -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] 程式意外停止，請回報上方錯誤訊息。" -ForegroundColor Red
    Read-Host "按 Enter 關閉"
} else {
    Write-Host ""
    Write-Host "5 秒後自動關閉..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
}
