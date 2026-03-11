@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Gemini 影片字幕翻譯工具
color 0a
cls

cd /d "%~dp0"

echo ========================================================
echo   Gemini 影片字幕翻譯工具
echo   自動為影片產生繁體中文 .srt 字幕檔
echo   Created by CTH
echo ========================================================
echo.

echo [1/4] 檢查 Python 環境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] 未偵測到 Python，本程式需要 Python 才能執行。
    echo.
    set /p INSTALL_PY=是否要立即安裝 Python？[Y/n]（直接按 Enter 代表同意）：
    if "!INSTALL_PY!"=="" set INSTALL_PY=Y
    if /i "!INSTALL_PY!" neq "Y" (
        echo 已取消。請安裝 Python 後重新啟動。
        pause
        exit /b 1
    )
    winget --version >nul 2>&1
    if !errorlevel! equ 0 (
        echo [INFO] 使用 winget 安裝 Python，請稍候...
        winget install --id Python.Python.3 -e --silent --accept-source-agreements --accept-package-agreements
    ) else (
        echo [INFO] 正在下載 Python 安裝程式，請稍候...
        powershell -NoProfile -Command ^
            "$out=\"$env:TEMP\python_installer.exe\";" ^
            "Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe' -OutFile $out;" ^
            "Write-Host '[INFO] 安裝中...';" ^
            "Start-Process $out -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1' -Wait;" ^
            "Remove-Item $out -Force -EA SilentlyContinue"
    )
    for /f "tokens=*" %%i in ('powershell -NoProfile -Command "[System.Environment]::GetEnvironmentVariable(\"PATH\",\"User\")"') do set "PATH=%%i;%PATH%"
    python --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo.
        echo [INFO] 安裝完成！請關閉此視窗，再次點兩下 bat 重新啟動。
        pause
        exit /b 0
    )
    echo [OK] Python 安裝完成。
) else (
    for /f "tokens=*" %%v in ('python --version') do echo [OK] %%v 已安裝。
)

echo [2/4] 檢查 FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] 未偵測到 FFmpeg，本程式需要 FFmpeg 才能擷取音訊。
    echo.
    set /p INSTALL_FF=是否要立即安裝 FFmpeg？[Y/n]（直接按 Enter 代表同意）：
    if "!INSTALL_FF!"=="" set INSTALL_FF=Y
    if /i "!INSTALL_FF!" neq "Y" (
        echo 已取消。請安裝 FFmpeg 並加入 PATH 後重新啟動。
        pause
        exit /b 1
    )
    winget --version >nul 2>&1
    if !errorlevel! equ 0 (
        echo [INFO] 使用 winget 安裝 FFmpeg，請稍候...
        winget install --id Gyan.FFmpeg -e --silent --accept-source-agreements --accept-package-agreements
    ) else (
        echo [ERROR] 找不到 winget，無法自動安裝 FFmpeg。
        echo         請至 https://ffmpeg.org/ 手動下載並加入 PATH，再重新啟動。
        pause
        exit /b 1
    )
    for /f "tokens=*" %%i in ('powershell -NoProfile -Command "[System.Environment]::GetEnvironmentVariable(\"PATH\",\"Machine\")"') do set "PATH=%%i;%PATH%"
    ffmpeg -version >nul 2>&1
    if !errorlevel! neq 0 (
        echo.
        echo [INFO] 安裝完成！請關閉此視窗，再次點兩下 bat 重新啟動。
        pause
        exit /b 0
    )
    echo [OK] FFmpeg 安裝完成。
) else (
    echo [OK] FFmpeg 已安裝。
)

if not exist .env (
    copy .env.example .env >nul
    echo [OK] 已自動建立 .env 設定檔。
)

echo [3/4] 檢查 uv 套件管理工具...
uv --version >nul 2>&1
if !errorlevel! neq 0 (
    echo [WARNING] 找不到 uv，正在安裝...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    for /f "tokens=*" %%i in ('powershell -NoProfile -Command "[System.Environment]::GetEnvironmentVariable(\"PATH\",\"User\")"') do set "PATH=%%i;%PATH%"
    uv --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] uv 安裝失敗，請關閉視窗後重新點兩下 bat 再試。
        pause
        exit /b 1
    )
    echo [OK] uv 安裝完成。
) else (
    for /f "tokens=*" %%v in ('uv --version') do echo [OK] %%v 已安裝。
)

echo [4/4] 檢查虛擬環境...
if not exist venv (
    echo [WARNING] 找不到虛擬環境 - venv
    echo.
    set /p CONFIRM=是否要立即建立虛擬環境並安裝套件？[Y/n] - 直接按 Enter 代表同意:
    if "!CONFIRM!"=="" set CONFIRM=Y
    if /i "!CONFIRM!" neq "Y" (
        echo 已取消。請手動執行 uv venv venv 後再重新啟動。
        pause
        exit
    )
    echo [INFO] 建立虛擬環境中...
    uv venv venv
    echo [INFO] 安裝套件中...
    uv pip install -r requirements.txt --python venv\Scripts\python.exe
) else (
    echo [OK] 虛擬環境已就緒。
)
call venv\Scripts\activate

echo.
echo [START] 啟動中，請保持此視窗開啟...
echo.

python main.py
set EXIT_CODE=%errorlevel%

if exist __pycache__ rmdir /s /q __pycache__  :: 清除 Python 編譯快取，避免殘留

if %EXIT_CODE% neq 0 (
    echo.
    echo [ERROR] 程式意外停止，請回報上方錯誤訊息
    pause
) else (
    echo.
    echo 5 秒後自動關閉...
    timeout /t 5
)
