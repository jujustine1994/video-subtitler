# I18N_RESUME — 多語言遷移進度（feat/i18n 分支）

**每完成一個 commit 就更新本檔。**全部做完後改寫成完成紀錄。

參考資料（動手前依序讀完）：

1. `C:\Users\CTH\Documents\Code\_i18n_migration\i18n_lessons.md`（前面專案踩出來的坑，最重要）
2. `C:\Users\CTH\.claude\project-rules\windows-tool\tkinter-ui\pattern_i18n.py`（完整食譜）
3. `C:\Users\CTH\.claude\project-rules\general.md`「資料與顯示文字必須分離」
4. `C:\Users\CTH\.claude\project-rules\windows-tool.md`「多語言」「執行紀錄（log）」
5. 參考實作（**唯讀**）：`C:\Users\CTH\Documents\Code\Video-Combiner` 的 `feat/i18n` 分支

---

## 現在停在哪

**批次 4 完成。gui.py / translator.py / config.py / main.py 的寫死中日文全部歸零**
（只剩 ALLOWLIST 的三個檔：i18n.py 語言自稱、logtext.py log 母語言、prompts.py Gemini prompt）。

**下一步：批次 5 — 简中／英／日譯文（各 59 條），從 `locales/zh_tw.py` 翻。**

## 已完成的 commit

分支起點 `8e870b8`（main 最後一筆）。

| hash | 內容 |
|---|---|
| `4e51871` | docs: TODO 補「校正專案 MD」（分支起點就有的既有改動，與 i18n 無關） |
| `dd41655` | 前置：消除三個會遮蔽 `i18n.t` 的區域變數（`theme` / `worker` × 2） |
| `94d109a` | 批次 1 前半：`src/i18n.py` |
| `e73b726` | 本檔初版 |
| `fa883e3` | docs: TODO 補多語言待辦與兩項既有問題 |
| `1ff2989` | 批次 1 後半：`src/config.py`、`src/locales/`（四個空表）、首次啟動選語言、設定視窗語言列、重啟提示 |
| `80fe88b` | 批次 2-1：`logtext.py` + `prompts.py`（純常數，未接線） |
| `f108763` | 批次 2-2：translator/gui 接上 logtext 與 prompts，`_log` 改 fail-closed |
| `75c1773` | 批次 3：gui.py 43 處介面文字改走 `t()`，zh_tw 母表 55 條 |

**分支未合併、未 push。**

---

## 剩下的批次

### 批次 2（進行中）— log 字串抽 `logtext.py`、prompt 抽 `prompts.py`

落檔字串共 5 條，已全部進 `LOG_TEXT`：
`task_start_full` / `task_start_retry` / `task_ok` / `task_fail` /
`segment_error` / `segment_error_final`。

`_log()` 形狀照 lessons 第 13 條：`_log(ui_msg, level="INFO", log_msg=None)`，
參數名統一用 `log_msg`，**預設不落檔**（fail-closed）。
現況：gui 的呼叫幾乎都是 `to_file=False`，唯一同時推 UI 又落檔的是
`_run_segments` 傳給 translator 的 `on_error`。

### 批次 3 — GUI 介面文字（**一個檔一個 commit**）

`src/gui.py` 74 條寫死中日文（f-string 碎片要**整句重組**成一條帶具名 placeholder 的 key）。
⚠ `THEMES` 是模組層級常數表，`t()` 不可在 import 時求值 → `name` 欄改放 i18n key
（lessons 12），**鍵 `light` / `dark` / `financial` 不可動**（存進 `.tool_config.json`）。

### 批次 4 — 錯誤訊息

`messagebox` 的標題與內文；`src/translator.py` 的
`RuntimeError("ffmpeg 音訊擷取失敗…")`（會經 `_fatal()` 顯示給使用者 → 是介面文字）。

### 批次 5 — 简中／英／日譯文

### 批次 6 — 測試（本專案目前 **0 條測試**，`tests/` 從零建）

pytest 9.1.1 已裝進 venv（`uv pip install pytest --python venv\Scripts\python.exe`；
此 venv **沒有 pip**）。要寫 `requirements_test.txt`。

- ALLOWLIST 只放 `i18n.py`（語言自稱）、`logtext.py`（log 母語言）、`prompts.py`（Gemini prompt）
- 掃描範圍掃 ROOT 排除 `venv`/`tests`/`locales`/`__pycache__`/`docs`，`assert len(files) > 0`，
  並釘住 `gui.py`、`translator.py` 在範圍內（lessons 4/5）
- ✔ 本專案的 `SubtitlerApp(root)` **接受外部傳入的 root**（不是 `class App(tk.Tk)`），
  所以 lessons 6-b 的子行程方案**用不到**，用 conftest 的 session 級 `tk_root` + `Toplevel` 即可
- GUI smoke 要涵蓋 `ScrolledText`（`get("1.0","end")`）與 `Combobox.values`；本專案沒有 Treeview
- 首次啟動視窗測試用 `after()` 排模擬點擊，不可用 `wait_window` 卡住
- 門檻不要寫死絕對值（lessons 6-d）
- **不要**寫「LOG_TEXT 的值不得出現在語言檔裡」（lessons 13 反向提醒，重疊是設計）
- ★ 本專案特有：切介面語言後，字幕語言設定與送給 Gemini 的 prompt 完全不變

---

## ★ 字幕語言設定怎麼處理（本專案最關鍵一項）

**現況：沒有 GUI 選項、沒有存進 config。**它是 `translate_segment()` 的預設參數，
呼叫端從未傳值，實際上永遠是「繁體中文」。

**決定：判成資料，不翻、不接介面語言。**已抽成 `src/prompts.py` 的
`DEFAULT_TARGET_LANGUAGE` 與 `TRANSLATE_PROMPT`（純常數，列入 ALLOWLIST，字面逐字不變）。
字幕跟著**影片音訊**走——使用者把介面切成日文，字幕不該變成日文。

**已知缺陷（刻意沒動，寫在 docs/TODO.md）**：它存的是中文字面「繁體中文」而不是機器碼。
目前不落檔所以還沒污染，但日後做成可存設定時必須改存機器碼 + `_display()`/`_stored()`。
**不要順手做成 GUI 選項**，那是邏輯變更。

---

## 判定為「資料」不翻的清單

| 項目 | 位置 |
|---|---|
| 送給 Gemini 的整段 prompt、`target_language` | `src/prompts.py` |
| 字幕檔內容（辨識出來的逐字稿） | Gemini 回傳 |
| SRT 格式規格：`-->`、`HH:MM:SS,mmm`、序號 | `translator` 的 regex 與 f-string |
| 輸出檔名 `<影片檔名>.srt`、暫存檔名 `temp_seg_<n>.mp3` | `gui` |
| ffmpeg / ffprobe 參數、`MODEL_NAME` | `translator` |
| `THEMES` 的鍵 `light`/`dark`/`financial`、`GEMINI_API_KEY` | `gui` |
| `RETRYABLE_MARKERS`（拿去比對 API 錯誤訊息） | `translator` |
| `logs/app.log` 的內容 | `src/logtext.py` |

灰色地帶：`THEMES` 的 `name` 欄是純顯示文字 → **要翻**（批次 3）；主題**鍵**不翻。

---

## 驗收狀態

| # | 項目 | 狀態 |
|---|---|---|
| 1 | 完整測試綠燈（原本 0 條） | 未做（批次 6） |
| 2 | 四語各建置 GUI、殘留 key 0 | 未做 |
| 3 | 輸出基準四語相同且與改前逐字一致 | **每個 commit 都在跑，目前全綠** |
| 4 | 四語 key 集合 + placeholder 一致 | 未做 |
| 5 | 首次啟動語言視窗 | 手動驗過「已選過就不跳」；自動化測試未做 |
| 6 | ★ 切介面語言不影響字幕語言設定 | 未做（要寫成永久測試） |

輸出基準腳本在
`C:\Users\CTH\AppData\Local\Temp\claude\C--Users-CTH--claude\11685c65-ace7-4e37-bd93-14b32e0e66c9\scratchpad\baseline.py`
（臨時目錄，可能被清）。邏輯：mock 掉 ffmpeg/Gemini，設 `app._video_path` 與 `app._segments`
後呼叫 `app._merge_and_write()`，記下輸出檔名、字幕檔完整內容、`translate_segment` 組出的 prompt。
已知基準：`示範 影片 sample.mp4` → `示範 影片 sample.srt`（同目錄）。

---

## 譯文待校對的術語

| 繁中 | 備註 |
|---|---|
| 「段」／「第 N 段」 | 影片切成 30 分鐘一段，英文建議 `segment`，日文 `セグメント` |
| 「補跑」 | 失敗段重跑，英文建議 `Retry failed segments` |
| 「清爽白」「深色模式」「金融藍」 | 主題自訂稱呼，直譯 |
| 「影片總時長」 | duration |

---

## 重掃寫死中日文的指令

```python
import ast, re
from pathlib import Path
CJK = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff]")
skip = {"venv", "__pycache__", ".git", "docs", "tests", "locales"}
for p in sorted(Path(".").rglob("*.py")):
    if skip & set(p.parts):
        continue
    tree = ast.parse(p.read_text(encoding="utf-8"))
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and CJK.search(n.value):
            print(p, n.lineno, repr(n.value[:60]))
```

（docstring 要排除，做法見 pattern_i18n.py 第 7 段的 `_hardcoded_cjk`。）
⚠ 搬字串一律 **AST 逐節點取代**，切字串**在 bytes 上做**（`col_offset` 是 UTF-8 位元組偏移）。
