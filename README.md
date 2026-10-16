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
- **手動檢查更新**：設定視窗「版本更新」區塊可手動檢查 GitHub 上的新版本並一鍵安裝，安裝完需自行關閉重開程式生效（不會自動觸發、不會自動重啟）

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
- **Quota-safe resume**: Each completed segment is checkpointed beside the video. If Gemini free-tier quota is exhausted, choose the same unchanged video later and processing resumes from the first unfinished segment
- **Precise timestamp alignment**: Timestamps are anchored to `00:00:00,000` and merge seamlessly across segments
- **Subtitle duration control**: Each subtitle displays for a maximum of 5 seconds; long dialogues are automatically split into multiple entries
- **Noise filtering**: Background music, ambient noise, and non-speech sounds (laughter, crying) are skipped automatically
- **API Key memory**: Saved after first entry and reused on subsequent runs
- **Multilingual UI**: Traditional Chinese / Simplified Chinese / English / Japanese. Picked once on first launch, changeable later in Settings
- **Accepted source files**: MP4, MKV, AVI, MOV, WMV, MP3, WAV, M4A, AAC, FLAC, OGG, Opus, and WebM. Other FFmpeg-readable inputs can be selected through “All files”

### How to Use

1. Install [FFmpeg](https://ffmpeg.org/) and add it to your system PATH
2. Get a [Google Gemini API Key](https://aistudio.google.com/app/apikey) (free tier works)
3. Copy `.env.example`, rename it to `.env`, and fill in your Gemini API Key
4. Run `啟動翻譯.bat`
5. **On first launch you are asked to pick a UI language** (changeable later via the ⚙ Settings window; takes effect after a restart)
6. Read the instructions and press Enter, then select your video file
7. Enter or confirm your API Key
8. Wait for processing to finish — the `.srt` file will appear next to the video

### Gemini / Groq selection

The translation model has its own selector: `gemini-3.5-flash-lite` (default)
or `gemini-3.6-flash`. Availability/free quota depends on your account.
Gemini speech recognition still uses the specialized `gemini-3.5-transcribe`;
text models are not interchangeable with that transcription endpoint.

After a failure, change the recognition service/model or translation model,
select the failed segments, and click Retry. The retry rebuilds the client but
preserves completed segments and original segment boundaries. Saved transcripts
are reused for translation, and translation batches are isolated by model.
Failure rows show stage/model and a safe reason (quota, permission, malformed
JSON, truncated output, timestamps, etc.); raw responses and keys are not shown.
Content/safety blocks are reported rather than bypassed by switching models.
The unfinished-job list restores the latest retry settings after restart.

When every segment succeeds and the SRT is written, Open source media appears.
Click it to launch the original file in your Windows default player. It does not
autoplay on completion; automatic SRT loading depends on your player settings.

New jobs now use balanced segments of at most 10 minutes (both providers).
Valid existing checkpoints retain their original segment boundaries when resumed.
Audio slices use per-run system temporary directories, removed on success, errors
and normal stop/close. Forced termination/power loss may leave temporary files.
Resume JSON is retained for unfinished work; it is not an audio slice.

The main window's Unfinished jobs section lists all indexed checkpoints across
folders, including progress, provider/model and update time. Select a job and
click Resume selected to restore its settings and continue. Startup only loads
the list; it does not call an API. Missing/changed source files are shown but
blocked from resuming, and their saved progress is retained. Restore the original
file and refresh. Successfully exported jobs leave the list automatically.

Both providers split output cues longer than 30 characters, preferably at
punctuation or whitespace. Short cues stay short; text is not summarized.
Split cues divide the original time interval proportionally by text length;
these internal boundaries are estimates, not a new speech-alignment pass.

Long-file validation: a 136-minute Japanese MP4 completed all five balanced
segments and produced 1,175 cues, with no invalid time ranges or overlaps.
This checks the pipeline and timestamp structure, not human-reviewed lip sync.
Translation runs in batches of at most 50 cues with a structured JSON response.
Successful translation batches are checkpointed; retrying a failed translation
reuses the saved transcript and batches without uploading the audio again.

API keys, segment length and source audio language are now in Settings → Processing
settings. The main screen keeps only file selection, service/model and progress.
Failure messages include the stage and a sanitized error type/HTTP code; numeric
timestamp errors include the offending bounds. Logs never include API keys.

Select the service manually; the app never switches providers automatically.
For Groq, `whisper-large-v3` is the default quality option; Turbo is also available.
Choose 10 or 30 minutes per segment (default 30). Groq extracts 16 kHz mono FLAC,
adds one-second context around segment boundaries, and halves oversized uploads
until they are below 24 MB. Completed subparts are checkpointed too.

New jobs calculate `ceil(total duration / target)` segments and divide the duration
equally. For example, 100 minutes becomes four 25-minute segments, not 30+30+30+10.
The actual segment ranges are saved in the checkpoint. Older unfinished jobs keep
their fixed boundaries; the new policy never reassigns their already saved subtitles.
If all segments fail, the app retains the checkpoint and does not write or overwrite
an empty SRT. Duplicate-start subtitle cues are merged before timestamp validation.

If Groq word timestamps go backwards, valid segment timestamps from the same
response are used instead, with an on-screen notice. This does not switch services
or upload audio again. Raw transcription responses are checkpointed before parsing
so a failed parse can be retried without another API request. Invalid segment
timestamps still stop that segment. Segment-timed captions can last over five seconds;
the app preserves their ends instead of silently cutting them short.

Set the Groq audio language to `zh` for Chinese recordings, `en` for English,
`ja` for Japanese, or `ko` for Korean; `auto` can misdetect long silent recordings.
Chinese uses local OpenCC text conversion (no local AI). Other languages still
need a Gemini key for Traditional Chinese translation.

Both keys are stored only in the ignored local `.env`. Groq jobs use separate
checkpoint files per model and source-language setting; Gemini checkpoints remain
compatible. Changing service starts/resumes that service's own job.

Groq can hallucinate words during silence. The app rejects out-of-range timestamps
and excludes words in near-digital-silence intervals detected by FFmpeg (-80 dB).
Music and quiet speech still require review. The short validation sample passed;
an artificial two-hour sparse timeline also passed, but a complete real film has not
been validated. Near-digital-silence-only chunks are now skipped without API calls.
Leading/trailing silence is trimmed before upload, with its original start offset
preserved. This uses FFmpeg, not local AI.

### Resuming an unfinished job

Transcription and translation are saved separately. If translation fails, the next run
reuses the saved original text and timestamps without uploading audio again. Use
“Stop and save” to stop at the next saved stage. Closing the window during processing
asks whether to wait for the current request to finish and save before exiting.
Force quitting or powering off can still lose the request that has not returned.

You can close the app at any time after a segment has completed. On the next launch,
the app lists all indexed unfinished jobs. Select one and click Resume selected
to restore its settings and continue from the first
unfinished segment. The video must remain at the same path and be unchanged.

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
- **API quota**: Free-tier Gemini has a daily request limit. When quota is exhausted, progress is kept in `<video>.subtitler.resume.json`; select the same unchanged video later and click Start to continue. The checkpoint is removed after a fully successful run
- **Safety filtering**: Explicit or sensitive content may be blocked by Google's safety filters
- **Internet required**: Audio is uploaded to the manually selected Gemini or Groq service
- **Privacy**: Free-tier usage may be used by Google to improve their services
- **Quality**: Speech recognition can still mishear names and technical terminology. Review important subtitles, especially finance, medical, legal, or technical recordings
