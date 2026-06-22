# ARCHITECTURE

## 工具總覽

**Gemini 影片字幕翻譯工具**
自動為影片產生繁體中文 `.srt` 字幕檔。Tkinter GUI 選檔 → 擷取音訊 → 上傳 Gemini AI → 輸出 SRT，過程中即時顯示進度，失敗段可單獨補跑。

- **版本**: v3.0（Tkinter GUI 改版）
- **技術棧**: Python 3 + Tkinter + FFmpeg + Google Gemini API（google-genai SDK）
- **套件管理**: uv（虛擬環境 `venv/`）

---

## 檔案清單

| 檔案 | 用途 |
|------|------|
| `啟動翻譯.bat` | 入口點，薄 BAT（3 行），呼叫 launcher.ps1 |
| `launcher.ps1` | 啟動邏輯：檢查 Python / FFmpeg / uv / venv，首次安裝說明，啟動 main.py（黑框保留在背後供除錯）；需含 UTF-8 BOM |
| `main.py` | 極簡入口：`from src import gui; gui.main()` |
| `src/gui.py` | Tkinter UI：主畫面、主題、queue 輪詢、失敗段補跑邏輯 |
| `src/translator.py` | 純邏輯：ffmpeg 擷取、Gemini 呼叫（含 retry）、SRT 格式處理函式，不含 print/input |
| `requirements.txt` | `google-genai`、`python-dotenv==1.2.2` |
| `.env` | 儲存 `GEMINI_API_KEY`（gitignore，GUI 執行時自動建立/更新） |
| `.env.example` | API Key 範本，供使用者參考 |
| `.tool_config.json` | GUI 主題等設定（gitignore） |
| `venv/` | Python 虛擬環境（gitignore） |
| `README.md` | 使用說明（中英雙語） |
| `docs/ARCHITECTURE.md` | 本檔，架構總覽 |
| `docs/CHANGELOG.md` | 現狀總覽 + 更新記錄 |
| `docs/TODO.md` | 待辦清單 |
| `docs/PITFALLS.md` | 已知踩坑記錄 |

---

## 執行流程

```
使用者雙擊 啟動翻譯.bat
  └─ launcher.ps1
       ├─ [1/4] 檢查 Python（缺則 winget 安裝 / fallback 直接下載）
       ├─ [2/4] 檢查 FFmpeg（缺則 winget install Gyan.FFmpeg）
       ├─ [3/4] 檢查 uv（缺則 Invoke-RestMethod 安裝）
       ├─ [4/4] 檢查 venv（缺則顯示首次安裝說明 → uv venv + uv pip install）
       └─ python main.py（背後黑框保留）
            └─ src.gui.main()
                 ├─ show_cth_banner()（印在背後 console）
                 ├─ 建立 Tk 視窗，暫時置頂
                 ├─ SubtitlerApp：選影片、API Key（讀/寫 .env）、開始按鈕
                 ├─ 按下開始 → 背景 thread 跑 _worker_full_run()
                 │    ├─ get_video_duration() 算分段數
                 │    └─ _run_segments()：每段
                 │         ├─ extract_audio_segment()（ffmpeg）
                 │         ├─ translator.translate_segment()（含 retry，見下）
                 │         └─ 結果存入 self._segments[i]（成功 str / 失敗 None）
                 ├─ 所有訊息透過 msg_queue 回主執行緒更新 log / 進度條 / status bar
                 ├─ 跑完 → _merge_and_write()：
                 │    ├─ 合併所有非 None 段
                 │    ├─ enforce_max_duration() + renumber_srt()
                 │    └─ 輸出 .srt（存在影片旁邊）
                 └─ 若有失敗段 → GUI 顯示勾選框，可按「重試所選段落」
                      └─ 只重跑勾選段，更新 self._segments，重新合併輸出
```

---

## Retry 機制

`translator.translate_segment()` 內建重試：

- 只對訊息含 `429` / `quota` / `exhausted` / `timeout` / `connection` / `unavailable` / `deadline` 的例外重試（見 `RETRYABLE_MARKERS`）
- 重試 3 次，指數後退 `RETRY_DELAYS = (5, 15, 45)` 秒
- 3 次後仍失敗：拋出最後一次例外，呼叫端（`gui.py` 的 `_run_segments`）捕捉後標記該段為 `None`，不中斷其他段
- 非上述錯誤（格式解析失敗、API Key 無效等）：不重試，直接視為該段失敗

---

## 關鍵設定變數

| 變數 | 位置 | 說明 |
|------|------|------|
| `CHUNK_DURATION` | `src/translator.py` | 每段處理長度，預設 `1800`（30 分鐘） |
| `RETRY_DELAYS` | `src/translator.py` | 段落級 retry 指數後退秒數 `(5, 15, 45)` |
| `RETRYABLE_MARKERS` | `src/translator.py` | 判斷例外是否可重試的關鍵字清單 |
| `GEMINI_API_KEY` | `.env` | Gemini API Key，GUI 啟動自動帶入欄位，按「開始」時寫回 |
| `max_seconds` | `enforce_max_duration()` | 字幕最長顯示秒數，預設 `5` 秒 |
| Gemini 模型 | `translator._call_gemini()` | `gemini-flash-latest` |
| GUI 主題 | `.tool_config.json` | `light` / `dark` / `financial`，由設定視窗寫入 |

---

## 架構重點

**薄 BAT + launcher.ps1**：BAT 只有 3 行，所有中文訊息與邏輯都在 PS1（PowerShell 原生 UTF-8，無亂碼問題）。launcher.ps1 必須存為 **UTF-8 with BOM**，否則 Windows PowerShell 5.x 會亂碼。背後 console 黑框保留不隱藏，方便看 crash log。

**邏輯與 UI 分離**：`src/translator.py` 不含任何 `print`/`input`，所有進度透過 callback（`on_log`/`on_retry`）回報；`src/gui.py` 負責執行緒、queue、UI 渲染。方便未來若要加 CLI 模式或寫測試，不需碰 UI 程式碼。

**google-genai SDK（新版）**：使用 `genai.Client` 初始化，`client.files.upload/get/delete`、`client.models.generate_content`。舊版 `google-generativeai` 已棄用，不可混用。

**SRT 雙重保險**：Gemini 回傳 JSON（`srt_content` 欄位），若解析失敗則直接對原始文字跑 `fix_srt_format()`。合併後再跑 `enforce_max_duration()` + `renumber_srt()`，確保格式正確。

**段落級容錯**：單段失敗不影響整體輸出，跑完即合併現有成功段；GUI 提供失敗段勾選補跑，避免長影片因單段問題整部重跑。
