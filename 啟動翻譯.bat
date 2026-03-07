@echo off
title Gemini 影片字幕翻譯工具
echo 正在啟動程式，請稍候...
cd /d "%~dp0"
call venv\Scripts\activate
python main.py

if exist __pycache__ rmdir /s /q __pycache__

pause
