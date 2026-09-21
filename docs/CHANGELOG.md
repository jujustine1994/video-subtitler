# CHANGELOG

## 現狀總覽
- **目前狀態**: 穩定版本 (v3.0，Tkinter GUI 改版)
- **既有功能**:
    - Tkinter GUI 主畫面：選檔、API Key 欄、開始按鈕、進度條、即時 log。
    - 分段式處理 (每 30 分鐘一段)，支援超長影片。
    - 使用 ffmpeg/ffprobe 進行高精度切割與擷取。
    - JSON Mode + Regex Fixer 雙重保證字幕格式正確。
    - 自動過濾非語言聲音（呻吟、笑聲、哭聲、雜音、純音樂）。
    - 段落級 Gemini API 失敗自動 retry（429/timeout/連線錯誤，指數後退 5s/15s/45s，重試 3 次）。
    - 重試耗盡的失敗段不中斷流程，跑完後在 GUI 列出失敗段供勾選補跑、重新合併輸出。
    - API Key 記憶功能（儲存於 .env，GUI 啟動自動帶入）。
    - 每條字幕最長 5 秒限制。
    - 三套 GUI 主題（清爽白/深色/金融藍）。
    - 介面多語言（繁中／简中／英文／日文），首次啟動選一次，設定視窗可改，重開生效。
      **字幕語言與介面語言分離**：字幕跟著影片音訊走，切介面不改變辨識輸出。
    - 視窗可手動調整大小，固定初始尺寸不因內容變化（log 變長、失敗段變多）被自動撐大；失敗段勾選清單超出固定高度時可捲動查看。
    - 啟動器架構：薄 BAT（2 行）+ launcher.ps1（UTF-8 BOM），解決中文亂碼問題；背後 console 保留供除錯。
    - SDK 使用 google-genai（新版），取代已棄用的 google-generativeai。
- **檔案結構**: 邏輯搬至 `src/translator.py`（純邏輯）+ `src/gui.py`（UI），`main.py` 僅為入口；MD 文件統一收進 `docs/`。

---

## 更新記錄

### 2026-09-21 — 這一天的來龍去脈（本專案當天的異動一次看完）

CTH 抽查 2026-09-14 那輪「10 個 Windows 工具專案 venv 改用 uv」有沒有做確實，
一路查下去翻出三層問題，本專案當天的異動都是這條線上的：

- **第一層**：9/14 的遷移有些沒做確實。urusai upload 重建後根本沒裝到 pytest
  （`requirements.txt` 只列執行期依賴），測試直接跑不動，而它的 CHANGELOG 還寫著
  「測試 90 條全過」——那是舊 venv 的結果。另外查出 3 個專案（AV Code Rename、
  Excel repair、FanCheck）當初根本沒被納入那輪遷移，還掛在 python.org 版系統 Python 上。
- **第二層**：9/14 有 3 個專案不是乾淨重建，是在舊 `site-packages` 上直接疊裝，
  留下一堆孤兒 `dist-info`（同一套件掛新舊兩份 metadata，`uv pip list` 會列兩次）。
  同時發現 4 個專案有測試卻沒把 pytest 寫進 requirements，只是 venv 還沒重建過所以沒爆。
- **第三層（真正的病根）**：清乾淨重建後幾小時內又被污染。查出 `Documents\Code`
  整個被 Google Drive 桌面版備份（從 `root_preference_sqlite.db` 的 `roots` 表確認，
  `root_id=4`、`state=2`），venv 放專案裡就會被同步，`site-packages` 目錄被設成唯讀、
  產生 `xxx (1).py` 影子檔、套件被切成兩半。清查當下 **13 個專案的 venv 全部**中招。
  所以最後把 venv 全部搬到 `%USERPROFILE%\venvs\` 並改了規則檔 `windows-tool.md`，
  以後新專案一律建在專案外。

**本專案當天的異動**：

1. venv 搬到專案外（commit `68a18a6`）。本專案體檢全部過關，沒有其他要修的

同一輪處理的還有其他 12 個專案，以及全域規則檔 `windows-tool.md`
（新增「venv 位置」章節）、`windows-tool-templates.md`、`windows-tool-pitfalls.md`。


### 2026-09-21 — 維護：venv 搬到專案資料夾外（`%USERPROFILE%\venvs\video-subtitler\`）

`Documents\Code` 整個被 Google Drive 桌面版備份（從
`%LOCALAPPDATA%\Google\DriveFS\root_preference_sqlite.db` 的 `roots` 表確認，
`root_id=4`、`state=2`）。venv 放在專案裡就會跟著被同步，實測災情：

- `site-packages` 底下的目錄被設成唯讀 → uv 換套件版本時 `RemoveDirectory`
  一律回 `ERROR_ACCESS_DENIED`，uv 報 `os error 5 存取被拒`，套件更新整個失敗
- 產生大量 `xxx (1).py` 影子檔（同步工具的衝突命名）
- 套件被切成兩半（實測 `idna` 被刪到只剩影子檔，變成 namespace package）

清查當下 13 個專案的 venv **全部**有唯讀目錄，其中 10 個是 100%；本專案是
283/283 全數唯讀。當天稍早才乾淨重建過的 3 個也已經在被感染中，**幾小時就中**，
所以「清乾淨再重建」這種治標做法沒有用。

Drive 桌面版不支援排除子資料夾，只能整個資料夾勾或不勾；而 `Documents\Code`
底下有一半專案沒有 git remote、Drive 是它們唯一的備份，不能關掉備份。
結論是把 venv 搬到同步範圍外。

改動：

- `launcher.ps1`：新增 `$VenvPath` / `$VenvPython` 兩個變數，venv 存在性檢查、
  `uv venv`、`uv pip install --python`、site-packages 路徑、`Activate.ps1`
  全部改用新路徑；建立前會先 `New-Item` 補出 `%USERPROFILE%\venvs\` 父目錄
- `ARCHITECTURE.md`：新增「venv 位置」章節（為什麼搬、手動重建指令）
- 專案內舊 venv 已刪除（先清唯讀屬性才刪得掉）

`venv` **不能用 `mv` 搬**，`Scripts\*.exe` 內嵌絕對路徑，一定要重建。

規則檔 `windows-tool.md` 同步新增「venv 位置」章節，以後新專案一律建在外面。

驗證：測試 96 條全過，與搬移前一致


### 2026-09-14 — 維護：venv 改用 uv 管理的獨立 Python（不依賴系統 Python）

原本 `venv` 是用 Microsoft Store 版 Python 3.13 建的（沙盒安裝，容易有套件裝了
但其他環境讀不到、資料夾存取受限等問題）。照 `windows-tool.md` 既定規範改用
`uv venv venv --python 3.13`：uv 會自己管理一份獨立的 Python 3.13.12，所有專案
共用同一份，不依賴系統上裝的任何 Python。套件安裝改用
`uv pip install -r requirements.txt --python venv\Scripts\python.exe`。舊 venv
備份搬到專案外 `Documents/Code/_venv_backups/video-subtitler/venv_old_store_20260914/`。
驗證：測試套件 96 條全過，跟改之前一致。

### 2026-08-24 — 設定視窗新增「版本更新」區塊（手動檢查 / 一鍵安裝）
- **新增**: `scripts/check_update.ps1` — git fetch/diff/checkout 純資料層，只印
  一行 JSON（`no_git`/`offline`/`dirty`/`ahead`/`up_to_date`/`update_available`/
  `updated`/`error`），只碰程式碼路徑（`src`、`tests`、`docs`、`scripts`、
  `requirements.txt`、`launcher.ps1`、`README.md`、`*.bat`），不動 `.tool_config.json`
  / `.env` / `logs/` 等使用者本機資料
- **新增**: `src/update_checker.py` — 呼叫子行程並解析 JSON，不碰 tkinter
- **新增**: 設定視窗（`_open_settings`）內新增「版本更新」`LabelFrame` 區塊——
  「檢查更新」按鈕（背景執行緒跑 `git fetch`，`.after(0, ...)` 送回主執行緒，
  包 try/except 防視窗中途關閉炸掉）、有新版本才出現的「一鍵安裝」按鈕、
  安裝前跳確認框列出本次變更摘要、安裝完跳訊息框請使用者手動關閉重開
  （**不自動重啟**，`launcher.ps1` 未加任何自動觸發）
- **新增**: 四個語言檔（zh_tw/zh_cn/en/ja）各補 15 條 `gui.update.*` /
  `gui.btn.check_update` / `gui.btn.install_update` / `gui.frame.update` 字串
- **修改**: `_open_settings` 上方註解由「設定視窗（僅外觀）」改為
  「設定視窗（外觀 + 版本更新）」，反映其範圍已不只外觀設定
- **新增**: `scripts/README.md` — 腳本索引表

### 2026-08-17 — launcher.ps1 拿掉失效的 winget/手動安裝 Python 步驟
`winget install --id Python.Python.3`（不帶次版號）已被上游下架，靜默失效；備援
的手動下載路徑也寫死 `python-3.12.9`，同樣會過期。改成只檢查 uv，
`uv venv venv --python 3.13` 讓 uv 自己下載 Python。步驟從 [1/4]~[4/4] 改成
[1/3]~[3/3]，FFmpeg 的 ARM64 模擬執行提醒維持不動。

### 2026-08-16
- **新增**: 介面多語言（i18n）——繁體中文／简体中文／English／日本語，各 53 條字串
  - 新增 `src/i18n.py`（查表核心）、`src/locales/`（四個語言檔）、`src/config.py`
    （讀寫 `.tool_config.json`，新增 `language` 欄位，預設空字串＝還沒選過）
  - 新增首次啟動選語言視窗（全英文不翻譯）、設定視窗最上方語言列（標籤固定
    英文 `Language:`）、語言變更後的重啟提示。**重開才生效，不做即時切換**
  - `src/gui.py` 43 處、`src/translator.py` 4 處寫死的中日文改走 `t()`；
    f-string 碎片整句重組成帶具名 placeholder 的 key
- **新增**: `src/logtext.py` —— `logs/app.log` 的訊息集中管理且**固定繁中**，
  不跟介面語言走。`_log()` 改成 `_log(ui_msg, level, log_msg=None)`，
  **預設不落檔（fail-closed）**，一個呼叫同時處理 UI 與 log 兩邊
- **新增**: `src/prompts.py` —— 送給 Gemini 的 prompt 與字幕語言抽成純常數。
  **這是資料不是介面文字**：字幕內容跟著影片音訊走，切介面語言不可改變它
- **修正**: 消除三個會遮蔽 `i18n.t` 的區域變數（`_apply_theme` 的主題 dict、
  `_start` / `_retry_selected` 的 `threading.Thread`）——不改名的話 `t("gui.x")`
  會靜默變成對 dict 取值或對 Thread 呼叫，不 crash 也不報錯
- **新增**: `tests/`（本專案原本 0 條測試）——95 條，含四道 i18n 防退化測試、
  GUI 四語建置 smoke test、首次啟動語言視窗、輸出基準比對，以及
  ★「切介面語言不影響字幕語言」的永久測試
- **驗證**: 繁中 widget 文字對導入前的 commit 逐字比對（既有 27 條全同，只多了
  語言列的 5 條）；四語產出的字幕檔名／目錄／內容完全相同且與導入前逐字一致

### 2026-07-17
- **文件修正**: README.md 規則檔宣告改成純文字格式（`規則檔: windows-tool.md`），位置移到 CTH banner 之後，與其他專案一致，避免自動化 grep 漏掃

### 2026-06-22
- **架構**: main.py 終端機互動式改為 Tkinter GUI（`src/gui.py` + `src/translator.py`），依 `windows-tool/tkinter-ui` 模板庫骨架建置
- **新增**: Gemini API 呼叫段落級 retry 機制（429/timeout/連線錯誤才重試，指數後退，3 次後標記該段失敗不中斷流程）
- **新增**: GUI 失敗段補跑功能 — 跑完後列出失敗段勾選框，可單獨重試並重新合併輸出
- **新增**: GUI 三主題（清爽白/深色/金融藍）、status bar、API Key 顯示切換
- **整理**: ARCHITECTURE.md / CHANGELOG.md / PITFALLS.md / TODO.md 搬入 `docs/`，符合 windows-tool.md 目錄規範
- **新增**: 視窗改為可手動調整大小（`resizable(True, True)`），並設定固定初始尺寸 `560x680`，避免內容變化（log 增長、失敗段增多）時被自動撐大
- **新增**: 失敗段勾選清單改為固定高度（110px）+ Canvas/Scrollbar 捲動容器，段數很多時可捲動查看而不裁切、不撐大視窗

### 2026-06-10
- 修正：`winget install Python` 加入 `--override "/quiet PrependPath=1 Include_pip=1"`，確保靜默安裝後 Python 自動加進 PATH

### 2026-03-16
- **新增**: launcher.ps1 加入系統架構偵測（`$isArm64`）
- **修正**: Python fallback 下載從寫死 `amd64.exe` 改為根據架構動態選擇 `amd64` / `arm64`
- **新增**: ARM64 電腦找不到 Python 時顯示警告，引導移除舊版 x64 再重裝
- **新增**: ffmpeg 在 ARM64 安裝完成後提示「x64 版透過模擬執行，功能正常但速度略慢」

### 2026-03-11 (v2.0)
- **架構**: 啟動器改為薄 BAT（2 行）+ launcher.ps1 架構，所有邏輯與中文訊息移至 PS1，徹底解決 BAT 中文亂碼問題
- **架構**: launcher.ps1 加 UTF-8 BOM，確保 Windows PowerShell 5.x 正確解析中文
- **升級**: requirements.txt 將 `google-generativeai`（已棄用）替換為 `google-genai`（新版 SDK）
- **升級**: main.py 遷移至新 SDK API：`genai.Client`、`client.files.upload/get/delete`、`client.models.generate_content`
- **新增**: PITFALLS.md 初始化（供後續累積踩坑記錄）

### 2026-03-11 (v1.5.2)
- **新增**: bat 自動偵測並安裝 Python（winget 優先，fallback 為 PowerShell 下載安裝程式）
- **新增**: bat 自動偵測並安裝 FFmpeg（winget `Gyan.FFmpeg`）
- **新增**: bat 自動從 `.env.example` 建立 `.env`，無需使用者手動複製
- **修改**: bat 步驟編號更新為 [1/4]～[4/4]

### 2026-03-11 (v1.5.1)
- **優化**: 移除 requirements.txt 中未使用的 `moviepy` 依賴，重建 venv 後體積從 331MB 縮減至 176MB（減少 47%）

### 2026-03-07 下午 (v1.5)
- **修復**: Gemini 回傳 JSON 陣列格式時字幕解析失敗問題
- **修復**: 暫存音訊檔改用絕對路徑，避免工作目錄不同導致找不到檔案
- **修復**: ffmpeg 擷取失敗時顯示明確中文錯誤提示
- **新增**: 字幕後處理掃描，自動將超過 5 秒的字幕截斷（修正 Gemini 時間戳錯誤）
- **新增**: bat 啟動時自動檢查 Python 環境與 venv，缺少時引導安裝
- **修復**: bat 中文亂碼問題（加入 chcp 65001）
- **修復**: bat if 區塊內 (Y/N) 括號導致解析錯誤
- **修改**: bat 補齊規範格式（color、cls、橫幅、錯誤處理、timeout）
- **修改**: README 補上規則檔與 .gitignore 規則欄位

### 2026-03-07 下午 (v1.4)
- **新增**: 啟動說明畫面，顯示使用說明與注意事項，按 Enter 同意後才進入選檔
- **新增**: API Key 記憶功能，第一次輸入後儲存至 .env，下次自動沿用
- **新增**: 影片分段數量提示，超過 30 分鐘自動顯示切成幾段處理
- **新增**: 每條字幕最長顯示 5 秒限制，長對話自動拆分
- **新增**: API 用量超限時顯示中文提示，說明需等隔天配額重置
- **新增**: 執行結束後自動清除 __pycache__
- **修復**: 彈出式選檔視窗偶發性不顯示問題（tkinter 初始化時序問題）
- **修復**: Gemini 回傳 JSON 陣列格式時字幕內容解析失敗，導致 SRT 檔包含原始 JSON



### 2026-03-07 下午 (v1.3.1)
- **修改**: 優化內容規則，明確排除「呻吟聲、笑聲、哭聲」的字幕產出。
- **修改**: 更新 README 與 CHANGELOG 文件。

### 2026-03-07 下午 (v1.3)
- **新增**: 導入用戶優化後的「完美版」Prompt 邏輯（時間軸規則最高優先級）。
- **新增**: 導入絕對起點對齊與不可重疊規則。

### 2026-03-07 下午 (v1.2)
- **新增**: 分段處理邏輯 (30 分鐘/段)。
- **修改**: 改為直接調用系統 FFmpeg/ffprobe。
