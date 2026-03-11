# ARCHITECTURE

## 工具總覽

**Gemini 影片字幕翻譯工具**
自動為影片產生繁體中文 `.srt` 字幕檔。擷取音訊 → 上傳 Gemini AI → 輸出 SRT，全程無需手動介入。

- **版本**: v2.0（穩定）
- **技術棧**: Python 3 + FFmpeg + Google Gemini API（google-genai SDK）
- **套件管理**: uv（虛擬環境 `venv/`）

---

## 檔案清單

| 檔案 | 用途 |
|------|------|
| `啟動翻譯.bat` | 入口點，薄 BAT（3 行），呼叫 launcher.ps1 |
| `launcher.ps1` | 啟動邏輯：檢查 Python / FFmpeg / uv / venv，首次安裝說明，啟動 main.py；需含 UTF-8 BOM |
| `main.py` | 主程式：選檔、API Key、音訊擷取、Gemini 翻譯、SRT 合併輸出 |
| `requirements.txt` | `google-genai`、`python-dotenv==1.2.2` |
| `.env` | 儲存 `GEMINI_API_KEY`（gitignore，執行時自動建立） |
| `.env.example` | API Key 範本，供使用者參考 |
| `venv/` | Python 虛擬環境（gitignore） |
| `README.md` | 使用說明（中英雙語） |
| `ARCHITECTURE.md` | 本檔，架構總覽 |
| `CHANGELOG.md` | 現狀總覽 + 更新記錄 |
| `TODO.md` | 待辦清單 |
| `PITFALLS.md` | 已知踩坑記錄 |

---

## 執行流程

```
使用者雙擊 啟動翻譯.bat
  └─ launcher.ps1
       ├─ [1/4] 檢查 Python（缺則 winget 安裝 / fallback 直接下載）
       ├─ [2/4] 檢查 FFmpeg（缺則 winget install Gyan.FFmpeg）
       ├─ [3/4] 檢查 uv（缺則 Invoke-RestMethod 安裝）
       ├─ [4/4] 檢查 venv（缺則顯示首次安裝說明 → uv venv + uv pip install）
       └─ python main.py
            ├─ 顯示說明畫面，按 Enter 確認
            ├─ select_file()：tkinter 選取影片
            ├─ setup_api_key()：讀 .env，詢問沿用或重新輸入，儲存至 .env
            ├─ get_video_duration()：ffprobe 取得總時長
            ├─ 迴圈（每 30 分鐘一段）：
            │    ├─ ffmpeg 擷取音訊 → temp_seg_N.mp3
            │    └─ translate_segment()：
            │         ├─ client.files.upload() 上傳音訊
            │         ├─ 等待 Gemini 處理（輪詢 state）
            │         ├─ client.models.generate_content()（JSON mode）
            │         ├─ client.files.delete() 刪除雲端暫存
            │         └─ fix_srt_format()：修復格式 + 套用時間偏移
            └─ 合併所有分段：
                 ├─ enforce_max_duration()：截斷超過 5 秒的字幕
                 ├─ renumber_srt()：重新編號確保序號連續
                 └─ 輸出 .srt（存在影片旁邊）
```

---

## 關鍵設定變數

| 變數 | 位置 | 說明 |
|------|------|------|
| `CHUNK_DURATION` | `main.py` 第 34 行 | 每段處理長度，預設 `1800`（30 分鐘） |
| `GEMINI_API_KEY` | `.env` | Gemini API Key，第一次輸入後自動儲存 |
| `max_seconds` | `enforce_max_duration()` | 字幕最長顯示秒數，預設 `5` 秒 |
| Gemini 模型 | `translate_segment()` 第 205 行 | `gemini-flash-latest` |

---

## 架構重點

**薄 BAT + launcher.ps1**：BAT 只有 3 行，所有中文訊息與邏輯都在 PS1（PowerShell 原生 UTF-8，無亂碼問題）。launcher.ps1 必須存為 **UTF-8 with BOM**，否則 Windows PowerShell 5.x 會亂碼。

**google-genai SDK（新版）**：使用 `genai.Client` 初始化，`client.files.upload/get/delete`、`client.models.generate_content`。舊版 `google-generativeai` 已棄用，不可混用。

**SRT 雙重保險**：Gemini 回傳 JSON（`srt_content` 欄位），若解析失敗則直接對原始文字跑 `fix_srt_format()`。合併後再跑 `enforce_max_duration()` + `renumber_srt()`，確保格式正確。
