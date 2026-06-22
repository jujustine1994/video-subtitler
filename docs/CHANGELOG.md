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
    - 視窗可手動調整大小，固定初始尺寸不因內容變化（log 變長、失敗段變多）被自動撐大；失敗段勾選清單超出固定高度時可捲動查看。
    - 啟動器架構：薄 BAT（2 行）+ launcher.ps1（UTF-8 BOM），解決中文亂碼問題；背後 console 保留供除錯。
    - SDK 使用 google-genai（新版），取代已棄用的 google-generativeai。
- **檔案結構**: 邏輯搬至 `src/translator.py`（純邏輯）+ `src/gui.py`（UI），`main.py` 僅為入口；MD 文件統一收進 `docs/`。

---

## 更新記錄

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
