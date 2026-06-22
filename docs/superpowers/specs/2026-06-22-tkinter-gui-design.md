# video-subtitler：CLI → Tkinter GUI 改版設計

## 背景

目前 `main.py` 是終端機互動程式（`input()` 確認、`print()` 進度），只用 tkinter 開檔案選取視窗。改為完整 GUI 工具，套用 `windows-tool/tkinter-ui` 模板庫。

## 檔案結構

```
src/translator.py   純邏輯：ffmpeg 擷取、Gemini 呼叫（含 retry）、SRT 處理函式，不含 print/input
src/gui.py           tkinter UI（skeleton.py 骨架）
main.py              極簡入口：import 並啟動 gui
docs/ARCHITECTURE.md / CHANGELOG.md / PITFALLS.md / TODO.md   從根目錄搬入 docs/
```

## GUI 主畫面

- 影片路徑欄 + 瀏覽按鈕（`pattern_file_picker`）
- API Key 欄（`pattern_secret_entry`，沿用 `.env` 記憶邏輯：`setup_api_key` 邏輯改為讀取 `.env` 預填欄位，使用者送出時寫回 `.env`）
- 開始按鈕：按下後 disable 自己與輸入欄，啟動背景 thread
- 進度條：依「已完成段數 / 總段數」換算百分比
- log 文字區（monospace `Consolas`，唯讀，自動捲到底）：顯示「正在處理第 N 段」「第 N 段失敗，將略過」等訊息
- 底部 status bar：執行中（灰）/ 完成（綠，含失敗段數提示）/ 致命錯誤（紅）
- 啟動時印 CTH banner 到背後 console（`pattern_cth_banner`），視窗用 `pattern_topmost` 置頂顯示

## 背景執行緒架構

- 套用 skeleton.py 的 queue 架構：背景 thread 跑 `translator.py` 邏輯，透過 `queue.Queue` 把以下訊息丟回主執行緒：
  - `("log", str)` — 一般訊息，附加到 log 區
  - `("progress", done, total)` — 更新進度條
  - `("segment_failed", index)` — 該段失敗
  - `("done", result)` — 全部段落跑完（含成功/失敗段清單、輸出路徑）
  - `("fatal_error", str)` — 不可恢復錯誤（如 ffmpeg 未安裝），中止流程
- 主執行緒用 `after()` 輪詢 queue 更新 UI（沿用 skeleton.py 既有模式）

## translator.py 介面

```python
def get_video_duration(video_path: str) -> float
def extract_audio_segment(video_path: str, start_time: float, duration: float, out_path: str) -> None
def translate_segment(client, audio_path: str, segment_index: int, offset_seconds: float,
                       target_language: str = "繁體中文") -> str
def renumber_srt(srt_text: str) -> str
def enforce_max_duration(srt_text: str, max_seconds: int = 5) -> str
def fix_srt_format(srt_text: str, offset_seconds: float = 0) -> str
```

所有函式維持與現有 `main.py` 同邏輯（直接搬移），只移除 `print`，改為由呼叫端（gui.py 的背景 thread）透過 queue 回報訊息。

## Retry 機制（段落級）

`translate_segment()` 呼叫包一層 retry：

- 只對 **429 / timeout / 連線類錯誤** 重試（字串比對 `"429"`、`"quota"`、`"exhausted"`、`"timeout"`、`requests.exceptions` 連線錯誤類型）
- 重試 3 次，指數後退：5s → 15s → 45s
- 3 次後仍失敗：捕捉例外，回傳 `None`（呼叫端記錄該段失敗，不拋出中止整體流程）
- 非上述錯誤類型（如格式解析錯誤、API key 無效）：不重試，直接視為該段失敗

## 失敗段處理 + 補跑 UI

- 主流程跑完後，把 `dict[index] -> srt_text or None` 中所有非 None 的段合併輸出 `.srt`
- 若有 `None`（失敗段），GUI 在 log 下方顯示：
  - 文字提示「以下段落失敗：第 2、5 段」
  - 每個失敗段一個勾選框（Checkbutton）
  - 「重試所選段落」按鈕
- 按下「重試所選段落」：
  - 只對勾選的段重新執行「擷取音訊 → translate_segment（含上述 retry）」
  - 成功的段更新進、覆蓋 `dict` 中對應結果
  - 重新合併**所有**目前非 None 的段，覆寫輸出 `.srt`
  - 若補跑後仍有失敗段，勾選框列表更新為剩餘失敗段，可重複按「重試」
- GUI 需在記憶體中保留 `video_path`、`duration`、每段 `srt_text` 結果，供補跑使用（僅執行期記憶，不落地存檔）

## 致命錯誤 vs 段落錯誤

- **致命錯誤**（ffmpeg 缺失、影片無法讀取、API Key 完全無效導致首次呼叫即 401/403）：透過 `fatal_error` 訊息，中止整個流程，status bar 顯示紅色錯誤
- **段落錯誤**：不中止，依上述機制略過該段、記錄、可後續補跑

## launcher.ps1/ 啟動方式

- 不變：黑框 console 保留在背後，`launcher.ps1` 照舊呼叫 `python main.py`
- `main.py` 內容改為純粹呼叫 `src/gui.py` 的 `main()`

## 主題

- 套用 skeleton.py 內建三主題（light/dark/financial），字型規範依 windows-tool.md（`Microsoft JhengHei` 主文字、`Consolas` log 區、最小 11pt）
