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
| `src/gui.py` | Tkinter UI：主畫面、主題、queue 輪詢、失敗段補跑邏輯、首次啟動選語言 |
| `src/translator.py` | 純邏輯：ffmpeg 擷取、Gemini 呼叫（含 retry）、SRT 格式處理函式，不含 print/input |
| `src/i18n.py` | 介面文字查表核心（`t()`、`LANGUAGES`、`set_lang()`） |
| `src/locales/*.py` | 四個語言檔（`zh_tw` 母表 / `zh_cn` / `en` / `ja`），各 53 條，只匯出 `STRINGS` |
| `src/config.py` | 讀寫 `.tool_config.json`（`language` / `theme`），缺的 key 補預設值 |
| `src/logtext.py` | `logs/app.log` 的訊息字串，**固定繁中**不跟介面語言走 |
| `src/prompts.py` | 送給 Gemini 的 prompt 與**字幕語言**——資料，永不翻譯 |
| `tests/` | pytest 測試（95 條），含四道 i18n 防退化測試 |
| `requirements_test.txt` | 測試套件清單（`pytest`） |
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

## venv 位置

**venv 不在專案資料夾裡**，而是在：

```
%USERPROFILE%\venvs\video-subtitler\
```

實際路徑：`C:\Users\CTH\venvs\video-subtitler\`

**為什麼要搬出去**：這個專案在 `Documents\Code` 底下，Google Drive 桌面版正在
備份整個 `Documents\Code`（2026-09-21 從
`%LOCALAPPDATA%\Google\DriveFS\root_preference_sqlite.db` 的 `roots` 表確認，
`root_id=4`）。venv 跟著被同步會出事：

- `site-packages` 底下的目錄被設成唯讀 → uv 換套件版本時 `RemoveDirectory`
  一律回 `ERROR_ACCESS_DENIED`（`os error 5 存取被拒`），套件更新整個失敗
- 產生大量 `xxx (1).py` 影子檔（同步工具的衝突命名）
- 套件被切成兩半（實測 `idna` 被刪到只剩影子檔，變成 namespace package，
  `idna.__file__` 是 `None`）

Drive 桌面版**不支援排除子資料夾**，只能整個資料夾勾或不勾，而 `Documents\Code`
底下有一半專案沒有 git remote、Drive 是它們唯一的備份，所以不能關掉備份，
只能把 venv 搬到同步範圍外。完整說明見 `windows-tool.md`「venv 位置」。

**新機器或重裝時什麼都不用做**：`launcher.ps1` 會自己建。手動建的指令：

```powershell
uv venv "$env:USERPROFILE\venvs\video-subtitler" --python 3.13
uv pip install -r requirements.txt --python "$env:USERPROFILE\venvs\video-subtitler\Scripts\python.exe"
```

要跑測試再補這一行（`launcher.ps1` 只裝 `requirements.txt`，不裝
`requirements_test.txt`，避免使用者裝到用不到的 pytest）：

```powershell
uv pip install -r requirements_test.txt --python "$env:USERPROFILE\venvs\video-subtitler\Scripts\python.exe"
```


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

## 免費額度用盡後續跑

每支影片的已完成段落會立即存成影片旁的
`<影片檔名>.<副檔名>.subtitler.resume.json`。這不是字幕成品，而是本機工作檔，
已列入 `.gitignore`。

- 每段 Gemini 呼叫成功後，`resume.record_segment()` 以「寫入暫存檔後 replace」的方式原子更新 checkpoint；程式意外關閉不會毀掉上一段的進度。
- `_run_segments()` 偵測到 HTTP `429`、`RESOURCE_EXHAUSTED` 或 quota 類錯誤時，會停止後續段落並保留 checkpoint，不輸出殘缺字幕。
- 再次選擇**同一路徑、未變動**的影片並按開始時，`resume.load()` 會跳過已完成段落，從第一個未完成段繼續。
- checkpoint 會核對絕對路徑、檔案大小、修改時間、影片時長、切段秒數與模型名稱；任一不同即拒絕沿用，避免混入不同影片或模型的結果。
- 完整成功並寫出 `.srt` 後才刪除 checkpoint。一般段落失敗也會保留已完成進度，供後續重跑或重新開始使用。
- 專案根目錄的 `.subtitler_resume_index.json` 只記錄 checkpoint 的絕對路徑與最後更新時間（同樣不版控）。啟動時會驗證清單，提示最近一份有效工作；使用者確認後自動填入來源檔案欄位，仍須按「開始翻譯」才會呼叫 API。

---

## 關鍵設定變數

| 變數 | 位置 | 說明 |
|------|------|------|
| `CHUNK_DURATION` | `src/translator.py` | 每段處理長度，預設 `1800`（30 分鐘） |
| `RETRY_DELAYS` | `src/translator.py` | 段落級 retry 指數後退秒數 `(5, 15, 45)` |
| `RETRYABLE_MARKERS` | `src/translator.py` | 判斷例外是否可重試的關鍵字清單 |
| `GEMINI_API_KEY` | `.env` | Gemini API Key，GUI 啟動自動帶入欄位，按「開始」時寫回 |
| `max_seconds` | `enforce_max_duration()` | 字幕最長顯示秒數，預設 `5` 秒 |
| 轉錄模型 | `translator._call_gemini()` | `gemini-3.5-transcribe`；回傳詞級時間戳 |
| 翻譯模型 | `translator._translate_cues()` | `gemini-3.5-flash-lite`；只能改字幕文字，不可改時間戳 |
| GUI 主題 | `.tool_config.json` | `light` / `dark` / `financial`，由設定視窗寫入 |
| 介面語言 | `.tool_config.json` | `language` 欄位：`zh_tw` / `zh_cn` / `en` / `ja`。**預設空字串**＝還沒選過，首次啟動會問 |
| 字幕語言 | `src/prompts.py` | `DEFAULT_TARGET_LANGUAGE`，目前固定繁體中文。**與介面語言無關** |
| 續跑 checkpoint | `src/resume.py` | `<影片>.<副檔名>.subtitler.resume.json`；僅保存成功段的 SRT 結果 |

---

## 架構重點

**薄 BAT + launcher.ps1**：BAT 只有 3 行，所有中文訊息與邏輯都在 PS1（PowerShell 原生 UTF-8，無亂碼問題）。launcher.ps1 必須存為 **UTF-8 with BOM**，否則 Windows PowerShell 5.x 會亂碼。背後 console 黑框保留不隱藏，方便看 crash log。

**邏輯與 UI 分離**：`src/translator.py` 不含任何 `print`/`input`，所有進度透過 callback（`on_log`/`on_retry`）回報；`src/gui.py` 負責執行緒、queue、UI 渲染。方便未來若要加 CLI 模式或寫測試，不需碰 UI 程式碼。

**google-genai SDK（新版）**：使用 `genai.Client` 初始化。音訊以 Files API 上傳後交給 `client.interactions.create()` 的 `gemini-3.5-transcribe`；翻譯才使用 `client.models.generate_content()`。舊版 `google-generativeai` 已棄用，不可混用。

**時間軸與翻譯分離**：只從 Gemini Transcribe 的 `word_info` annotations 建立 cue 的起迄時間；翻譯模型只收到 cue id 與文字，回傳缺 id、重複 id 或空文字就拒絕輸出。`_validate_cues()` 會拒絕零長度與重疊時間軸，合併時仍再跑 `enforce_max_duration()` + `renumber_srt()`。

**多語言（i18n）**：介面文字全部走 `i18n.t("key")`，語言檔在 `src/locales/`。
啟動時 `SubtitlerApp.__init__` 先 `set_lang()` 再建 widget——`t()` 是建置時查一次表，
設晚了介面會停在預設語言。**重開才生效，刻意不做即時切換**（即時切換要建 widget
登記表逐一 `config(text=...)`，漏一個就是中英混雜，改動幅度大好幾倍）。
語言選單在設定視窗最上方一列，標籤固定英文 `Language:`、選項用各語言自稱。
首次啟動的選語言視窗全英文——那時還不知道使用者要哪個語言，用任一種當說明都在賭。

**★ 字幕語言 ≠ 介面語言（本工具最容易搞混的一條）**：
字幕的內容跟著**影片音訊**走，不跟介面語言走。切介面語言不會、也不該改變辨識輸出。
所以送給 Gemini 的 prompt 與 `DEFAULT_TARGET_LANGUAGE` 住在 `src/prompts.py`，
是**資料**不是介面文字，永不進語言檔。同樣是資料的還有：SRT 格式規格
（`-->`、`HH:MM:SS,mmm`）、輸出檔名 `<影片檔名>.srt`、暫存檔名 `temp_seg_<n>.mp3`、
ffmpeg 參數、模型代號、`THEMES` 的鍵（存進設定檔的機器碼）。
`tests/test_subtitle_language_is_data.py` 是這條規則的永久守門員。

**log 固定繁中**：`logs/app.log` 的字串在 `src/logtext.py`，不跟介面語言走——
log 是給維護者除錯用的，跟著使用者語言變等於自廢。同一條訊息要同時推 UI 又落檔時，
用 `_log(ui_msg, level, log_msg=None)` 一個呼叫吃兩邊：UI 那條走 `t()`、落檔那條走
`LOG_TEXT`。**`log_msg` 預設 None＝不落檔（fail-closed）**，要落檔就得明講。

**段落級容錯**：單段失敗不影響整體輸出，跑完即合併現有成功段；GUI 提供失敗段勾選補跑，避免長影片因單段問題整部重跑。

**額度用盡是暫停而非一般失敗**：`translator.is_quota_error()` 將 HTTP 429 與 quota 訊息分流為 `QuotaExhaustedError`。GUI 顯示「進度已儲存」並停止工作；下一次完整開始流程會從 checkpoint 回復，避免免費額度已消耗的段落再次上傳。
