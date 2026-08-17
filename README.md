```
/*  ================================  *\
 *                                    *
 *          C  T  H                   *
 *        created by CTH              *
 *                                    *
\*  ================================  */
```

規則檔: windows-tool.md
類型: Windows 工具

# video-subtitler

- **技術棧**: Python, FFmpeg, Google Gemini API
- **.gitignore 規則**: `.env`、`venv/`、`__pycache__/`、`*.pyc`、`*.srt`、`temp_seg_*.mp3`

---

## 中文說明

自動為無字幕影片產生繁體中文 `.srt` 字幕檔。只需選取影片，程式會自動擷取音訊、上傳至 Google Gemini AI 進行語音辨識與翻譯，完成後將字幕檔存在影片旁邊，直接用 PotPlayer 或 VLC 開啟即可自動載入。

### 功能特色

- **全自動流程**：選取影片後全程無需介入，AI 自動辨識語音並翻譯為繁體中文
- **長影片分段處理**：超過 30 分鐘的影片自動切段，每段獨立上傳翻譯後合併，無長度上限
- **字幕時間軸精準對齊**：強制時間軸從 `00:00:00,000` 起算，分段合併後時間戳無縫銜接
- **字幕顯示控制**：每條字幕最長顯示 5 秒，長段對話自動拆分，不會長時間卡在畫面上
- **雜音過濾**：純音樂、背景雜音、非語言聲音（笑聲、哭聲）自動略過，不產生字幕
- **API Key 記憶**：第一次輸入後自動儲存，下次執行直接沿用
- **介面多語言**：繁體中文／简体中文／English／日本語，首次啟動時選一次，之後可在設定視窗更改

### 使用方式

1. 確認已安裝 [FFmpeg](https://ffmpeg.org/) 並加入系統環境變數
2. 準備好 [Google Gemini API Key](https://aistudio.google.com/app/apikey)（免費版即可）
3. 將 `.env.example` 複製並改名為 `.env`，填入你的 Gemini API Key
4. 點擊 `啟動翻譯.bat` 執行程式
5. **首次啟動會問一次介面語言**（之後可在齒輪 ⚙ 設定視窗更改，重開生效）
6. 閱讀說明後按 Enter，選取影片檔案
7. 輸入或確認 API Key
8. 等待處理完成，`.srt` 字幕檔會出現在影片旁邊

### 介面語言與字幕語言是兩回事

> **切換介面語言不會改變字幕的語言。**

- **介面語言**：按鈕、訊息、狀態列的顯示語言。存在 `.tool_config.json` 的 `language` 欄位，
  值是語言代號（`zh_tw` / `zh_cn` / `en` / `ja`）。**重開才生效**（不做即時切換）。
- **字幕語言**：辨識與翻譯出來的字幕內容。它跟著**影片音訊**走，目前固定輸出繁體中文
  （定義在 `src/prompts.py`，是送給 Gemini 的指令的一部分）。把介面切成日文，
  字幕不會、也不該變成日文。

同理，`logs/app.log` 的內容永遠是繁體中文——log 是給維護者除錯用的，
跟著使用者語言變就等於自廢。

### 注意事項

- **30 分鐘規則**：影片以每 30 分鐘為一段上傳處理，90 分鐘影片會分 3 段依序處理（非平行）
- **API 用量限制**：免費版 Gemini 有每日請求上限，超過限額需等隔天重置
- **安全性過濾**：露骨或敏感內容可能被 Google 安全機制過濾，導致該段翻譯失敗
- **網路依賴**：音訊檔需上傳至 Google 雲端，需穩定網路連線
- **隱私權**：免費版內容可能被 Google 用於改進服務

---

## English

Automatically generate Traditional Chinese `.srt` subtitle files for videos without subtitles. Simply select a video file — the program extracts the audio, uploads it to Google Gemini AI for speech recognition and translation, and saves the subtitle file next to the video. Open with PotPlayer or VLC and subtitles load automatically.

### Features

- **Fully automated**: Select a video and the AI handles everything — no manual intervention required
- **Long video support**: Videos longer than 30 minutes are automatically split into segments, processed individually, then merged — no length limit
- **Precise timestamp alignment**: Timestamps are anchored to `00:00:00,000` and merge seamlessly across segments
- **Subtitle duration control**: Each subtitle displays for a maximum of 5 seconds; long dialogues are automatically split into multiple entries
- **Noise filtering**: Background music, ambient noise, and non-speech sounds (laughter, crying) are skipped automatically
- **API Key memory**: Saved after first entry and reused on subsequent runs
- **Multilingual UI**: Traditional Chinese / Simplified Chinese / English / Japanese. Picked once on first launch, changeable later in Settings

### How to Use

1. Install [FFmpeg](https://ffmpeg.org/) and add it to your system PATH
2. Get a [Google Gemini API Key](https://aistudio.google.com/app/apikey) (free tier works)
3. Copy `.env.example`, rename it to `.env`, and fill in your Gemini API Key
4. Run `啟動翻譯.bat`
5. **On first launch you are asked to pick a UI language** (changeable later via the ⚙ Settings window; takes effect after a restart)
6. Read the instructions and press Enter, then select your video file
7. Enter or confirm your API Key
8. Wait for processing to finish — the `.srt` file will appear next to the video

### UI language is not subtitle language

> **Switching the UI language does not change the language of the subtitles.**

- **UI language** — the language of buttons, messages and the status bar. Stored in
  `.tool_config.json` under `language` as a code (`zh_tw` / `zh_cn` / `en` / `ja`).
  Takes effect after a restart (no live switching by design).
- **Subtitle language** — the recognised and translated subtitle text. It follows the
  **audio of the video** and is currently always Traditional Chinese (defined in
  `src/prompts.py` as part of the instruction sent to Gemini). Setting the UI to
  Japanese does not, and should not, turn the subtitles Japanese.

For the same reason `logs/app.log` is always written in Traditional Chinese — the log
is a maintenance tool, so it must not follow the end user's language.

### Limitations

- **30-minute rule**: Audio is uploaded in 30-minute segments. A 90-minute video takes 3 sequential passes (not parallel)
- **API quota**: Free-tier Gemini has a daily request limit — if exceeded, wait until the next day
- **Safety filtering**: Explicit or sensitive content may be blocked by Google's safety filters
- **Internet required**: Audio is uploaded to Google Cloud for processing
- **Privacy**: Free-tier usage may be used by Google to improve their services
