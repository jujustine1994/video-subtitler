@echo off
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

echo [1/2] 檢查 Python 環境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 找不到 Python，請至 https://www.python.org/ 下載安裝後重新執行
    pause
    exit
)

echo [2/2] 檢查虛擬環境...
if not exist venv (
    echo [WARNING] 找不到虛擬環境（venv）
    echo.
    set /p CONFIRM=是否要立即建立虛擬環境並安裝套件？(Y/N^):
    if /i "%CONFIRM%" neq "Y" (
        echo 已取消。請手動執行 python -m venv venv 後再重新啟動。
        pause
        exit
    )
    echo [INFO] 建立虛擬環境中...
    python -m venv venv
    call venv\Scripts\activate
    echo [INFO] 安裝套件中...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

echo.
echo [START] 啟動中，請保持此視窗開啟...
echo.

python main.py
set EXIT_CODE=%errorlevel%

if exist __pycache__ rmdir /s /q __pycache__

if %EXIT_CODE% neq 0 (
    echo.
    echo [ERROR] 程式意外停止，請回報上方錯誤訊息
    pause
) else (
    echo.
    echo 5 秒後自動關閉...
    timeout /t 5
)
