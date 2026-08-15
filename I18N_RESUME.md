# I18N_RESUME — 多語言遷移的中斷交接（feat/i18n 分支）

2026-08-15 建立。工作在**批次 1 進行到一半**時因額度中斷，此檔讓接手的人不必重新盤點。
完成後請刪除本檔。

參考資料（動手前依序讀完）：

1. `C:\Users\CTH\.claude\project-rules\windows-tool\tkinter-ui\pattern_i18n.py`（完整食譜）
2. `C:\Users\CTH\.claude\project-rules\general.md`「資料與顯示文字必須分離」
3. `C:\Users\CTH\.claude\project-rules\windows-tool.md`「多語言」「執行紀錄（log）」
4. 參考實作（**唯讀**）：`C:\Users\CTH\Documents\Code\Video-Combiner` 的 `feat/i18n` 分支
   （同樣是影音工具、同樣呼叫 ffmpeg，`config.py` / `logtext.py` / `tests/` 幾乎可直接照抄）

---

## 現在停在哪

**批次 1（i18n 核心 + config schema + 首次啟動選語言 + 語言選單 + 重啟提示）只做完「i18n.py」一項。**

已完成的 commit（分支起點為 `8e870b8`，main 上的最後一筆）：

| hash | 內容 |
|---|---|
| `4e51871` | docs: TODO 補「校正專案 MD」（分支起點就存在的既有改動，與 i18n 無關，先獨立保存） |
| `dd41655` | 前置：消除三個會遮蔽 `i18n.t` 的區域變數 |
| `94d109a` | 批次 1 前半：新增 `src/i18n.py`（**尚未被任何模組 import**） |

工作區乾淨，沒有半成品。`src/i18n.py` 目前是孤立模組，對執行時行為零影響。

**分支未合併、未 push。**

---

## 下一步具體要做什麼

### 批次 1 剩下的（依序）

1. **`src/locales/__init__.py` + `src/locales/zh_tw.py`（先空 `STRINGS = {}`）**
   `i18n._strings()` 用的是 `importlib.import_module(f".locales.{lang}", package=__package__)`，
   所以 locale 必須放在 `src/locales/` 底下、當成 `src` 套件的子模組。
2. **`src/config.py`**（照抄 Video-Combiner 的 `config.py`，只改兩處）
   - `CONFIG_PATH = Path(__file__).resolve().parent.parent / ".tool_config.json"`
     ⚠ 本專案的設定檔**不是** `config.json`，是**專案根目錄**的 `.tool_config.json`
     （`src/gui.py` L20 已定義，已在 `.gitignore`）。不要搬位置，那是行為變更。
   - `DEFAULT_CONFIG = {"language": "", "theme": "light"}`
     `language` 預設**必須是空字串**，才分得出「沒選過」與「選了繁中」。
     `theme` 要留著並保持預設 `"light"`，因為 `gui.SubtitlerApp.__init__` 現在是
     `self._load_config().get("theme", "light")`。
   - `save_config` 包 `except OSError: pass`。
3. **`src/gui.py` 的 `_load_config` / `_save_config` 改成委派給 `config.py`**（行為不變，
   只是把讀寫集中，讓首次啟動的語言視窗在建 App 之前也能讀寫設定）。
4. **`_pick_language_on_first_run(root)`**：模組層級函式，在 `main()` 裡
   `root = tk.Tk()` 之後、`SubtitlerApp(root)` 之前呼叫。視窗**全英文不翻譯**，
   關掉＝接受第一個選項並照樣存檔。
5. **`SubtitlerApp.__init__` 開頭 `i18n.set_lang(self.cfg.get("language"))`**，
   必須在 `self._build_ui()` **之前**（t() 是建置時查一次表）。
6. **語言選單**：本專案**有**設定視窗（`_open_settings`，齒輪鈕），
   照 pattern 第 5 段放在設定視窗**最上方一列**，標籤固定英文 `Language:`，
   選項用各語言自稱。`_selected_lang_code()` 把顯示名換回代號。
   ⚠ 基準值讀 `self.cfg` 不讀 `i18n.get_lang()`（理由見 pattern）。
7. **重啟提示**：`_prompt_restart_for_language()` + `_restart_app()`（`subprocess.Popen`
   不要用 `os.execv`），只有語言真的變更才跳，視窗全英文。
   ⚠ 本專案的入口是 `main.py`（`from src import gui; gui.main()`），
   `subprocess.Popen([sys.executable, *sys.argv])` 剛好正確。

### 批次 2 — log 字串抽 `src/logtext.py`

本工具**不產 Excel/CSV**，字幕檔內容與 SRT 格式規格一律不翻，所以批次 2 改做 log 字串。
`LOG_TEXT` 固定繁中，具名 placeholder，**不放格式規格**（`{elapsed:.1f}` 這種）。
現在會落檔的字串共 5 條，全部在這裡：

| 位置 | 現況字面 |
|---|---|
| `src/gui.py` `_worker_full_run` | `f"轉錄 {basename} \| {MODEL_NAME} \| {n}段"`（`_write_log_header`） |
| `src/gui.py` `_worker_retry` | `f"補跑 {basename} \| {MODEL_NAME} \| {n}段"`（`_write_log_header`） |
| `src/gui.py` `_log_task_result` | `"成功/失敗，耗時 {m}分{s}秒"` |
| `src/translator.py` `translate_segment` | `f"第{i}段 上傳Gemini -> {safe} \| 重試 {a}/{n}"` |
| `src/translator.py` `translate_segment` | 同上 + `" 後失敗"` 版本 |

`src/gui.py` 的 `_log(msg, level, to_file)` 已經是「一個呼叫同時推 UI ＋（可選）落檔」的形狀，
但**同一條字串目前兩邊共用**。要照 lessons 第 13 條改成 `_log(ui_msg, log_msg=None)`：
UI 那條走 `t()`、落檔那條走 `LOG_TEXT`。參數名統一用 `log_msg`。
目前唯一同時推 UI 又落檔的是 `translator` 的 `on_error` callback（`gui.py` `_run_segments` 內）。

### 批次 3 — GUI 介面文字

`src/gui.py` 共 **74 條**寫死中日文字面（f-string 碎片要**整句重組**成一條帶具名
placeholder 的 key，不可逐碎片翻）。重組後估計約 45~50 條 key。清單見下方「附錄」。

⚠ `THEMES` 是模組層級的 `(key, {"name": 中文名, ...})` 表，`t()` 不可在 import 時求值。
照 lessons 第 12 條：**`name` 欄改放 i18n key**（如 `"theme.light"`），
顯示端（`_open_settings` 的 Radiobutton）才 `t(info["name"])`。
**`THEMES` 的鍵 `light` / `dark` / `financial` 是存進 `.tool_config.json` 的值，絕對不可動。**

### 批次 4 — 錯誤訊息

`messagebox.showerror/showinfo` 的標題與內文、`src/translator.py` L60 的
`RuntimeError("ffmpeg 音訊擷取失敗…")`（那條會經 `_fatal()` 顯示給使用者 → 是介面文字）。

### 批次 5 — 简中／英／日譯文

### 批次 6 — 防退化測試（`tests/`，本專案**目前完全沒有測試**）

`requirements_test.txt` 寫 `pytest`（venv 已裝 pytest 9.1.1，用
`uv pip install pytest --python venv\Scripts\python.exe`；此 venv **沒有 pip**）。
直接照抄 Video-Combiner `feat/i18n` 的 `tests/`，改三處：

- `conftest.py` 的 session 級 `tk_root` fixture 照抄（**不可每個測試建 `tk.Tk()`**）。
- 掃描範圍：本專案的 `.py` 在 **`src/`**（`main.py` 在根目錄且只有 3 行）。
  掃 ROOT 並排除 `venv` / `tests` / `locales` / `__pycache__` / `docs`，
  並 `assert len(files) > 0` + 釘住 `gui.py`、`translator.py` 一定在範圍內。
- `ALLOWLIST` 只放 `i18n.py`（語言自稱）、`logtext.py`（log 母語言）、
  `prompts.py`（送給 Gemini 的 prompt，見下節）。

必寫的測試（除了 pattern 的三道）：

- `test_nothing_shadows_the_translation_function`（AST 掃 `def t` / 參數 `t` / 指派 `t`）
- GUI smoke test：四語各建一次（`Toplevel` + `withdraw()`，不進 mainloop），殘留 key 0 條。
  必須涵蓋 **`tk.Text` / `ScrolledText` 的 `get("1.0","end")`**（本專案的初始提示
  「選擇影片並輸入 API Key 後按…」整條住在 `ScrolledText` 裡，`cget("text")` 掃不到）
  與 `ttk.Combobox` 的 `values`。本專案沒有 Treeview。
- 首次啟動語言視窗：`after()` 排模擬點擊，**不可用 `wait_window` 卡住**。
- 輸出基準：四語各產一次字幕檔，檔名／目錄／內容完全相同（見下節）。
- ★ **本專案特有**：切換介面語言後，送給 Gemini 的 prompt 與字幕語言設定**完全不變**。

---

## ★ 「字幕語言設定」現在是怎麼存的、以及怎麼處理（本專案最關鍵一項）

**現況：這個工具目前沒有把字幕語言存進 config，也沒有任何 GUI 選項。**
它是 `src/translator.py` `translate_segment()` 的預設參數，寫死的中文字面：

```python
def translate_segment(client, audio_path, segment_index, offset_seconds,
                      target_language: str = "繁體中文", ...):
    prompt = f"""
    請聽這段音訊，將其內容翻譯為 {target_language}，並輸出標準 SRT 字幕格式。
    ...
```

呼叫端（`src/gui.py` `_run_segments`）**從來沒有傳過這個參數**，所以實際上永遠是「繁體中文」。

**處理方式（已決定，尚未實作）：**

- `target_language` 與整段 prompt 是**資料**，不是介面文字：它被字串內插進 prompt、
  送給外部程式（Gemini），直接決定字幕檔的內容。**絕對不可以跟介面語言綁在一起**——
  使用者把介面切成日文，字幕不會、也不該變成日文（字幕跟著影片音訊走）。
- 實作：把 prompt 樣板與 `DEFAULT_TARGET_LANGUAGE = "繁體中文"` 抽成
  **`src/prompts.py`**（純常數模組，列入測試的 `ALLOWLIST`）。
  這是抽常數不是改邏輯，跟 `logtext.py` 同性質，**不算重構**。
  抽出來的字面必須**逐字不變**——prompt 一個字不同，Gemini 的輸出就可能不同。
- **不要**順手把它做成 GUI 選項（那是邏輯變更）。要做的話見下方 TODO。

**既有的資料污染風險（發現了但刻意沒動）：**
`target_language` 的值是中文字面「繁體中文」而不是機器碼（`zh-TW`）。目前因為它從不落檔、
也不跟任何檔案裡的值比對，所以還沒造成污染。但**日後若把它做成可選設定並存進
`.tool_config.json`，必須存機器碼、顯示名另外走 `_display()` / `_stored()` 一對函式**
（general.md 的第 (2) 個案例），不可以直接把「繁體中文」這串存進去。

---

## 判定為「資料」不翻的清單與理由

| 項目 | 位置 | 理由 |
|---|---|---|
| 送給 Gemini 的整段 prompt | `translator.translate_segment` | 送給外部程式，決定字幕內容 |
| `target_language = "繁體中文"` | 同上 | 字幕語言 ≠ 介面語言，見上一節 |
| 字幕檔內容（辨識出來的逐字稿） | Gemini 回傳 | 跟著影片音訊走 |
| SRT 格式規格：`-->`、`HH:MM:SS,mmm`、序號、`00:00:00,000` | `translator` 的 regex 與 f-string | 規格，翻了播放器直接讀不出來 |
| 輸出檔名 `<影片檔名>.srt`、副檔名 `.srt` | `gui._merge_and_write` | 寫進磁碟 |
| 暫存檔名 `temp_seg_<n>.mp3` | `gui._run_segments` | 寫進磁碟，且 `.gitignore` 有對應規則 |
| ffmpeg / ffprobe 參數（`-acodec`、`libmp3lame`、`-vn`、`format=duration`…） | `translator` | 餵給外部程式 |
| `MODEL_NAME = "gemini-flash-latest"` | `translator` | 餵給外部 API |
| `THEMES` 的鍵 `light` / `dark` / `financial` | `gui` | 存進 `.tool_config.json` |
| `GEMINI_API_KEY`（`.env` 的鍵名） | `gui` | 寫進檔案 |
| `RETRYABLE_MARKERS`（`"429"`、`"quota"`…） | `translator` | 拿去跟 API 回的錯誤訊息比對 |
| `logs/app.log` 的內容 | `logtext.py`（待建） | log 固定母語言 |

灰色地帶（判成資料、但可以再討論）：`THEMES` 的 `name` 欄是純顯示文字 → **要翻**
（做法見批次 3）；主題**鍵**不翻。

---

## 已知還沒過的驗收項目

六項驗收**一項都還沒跑**（批次 1 未完成，測試尚未建立）：

1. 完整測試綠燈 — **本專案原本 0 條測試**，全部要新建
2. 四語各建置一次 GUI，殘留 key 0 條 — 未做
3. 輸出基準比對（檔名／目錄／字幕檔內容四語相同且與改前逐字一致）— 未做
4. 四語 key 集合一致 + placeholder 一致 — 未做
5. 首次啟動語言視窗開得起來／存得了檔／第二次不跳 — 未做
6. ★ 切換介面語言後字幕語言設定值不變 — 未做

**已經跑過並通過的**（可當基準）：

- 改前輸出基準已存檔：
  `C:\Users\CTH\AppData\Local\Temp\claude\C--Users-CTH--claude\11685c65-ace7-4e37-bd93-14b32e0e66c9\scratchpad\baseline_before.json`
  （臨時目錄，可能已被清掉。重建腳本邏輯：mock 掉 ffmpeg/Gemini，
  設 `app._video_path` 與 `app._segments` 後直接呼叫 `app._merge_and_write()`，
  記下輸出檔名、字幕檔完整內容、`translate_segment` 組出來的 prompt。）
  已知基準值：影片 `示範 影片 sample.mp4` → 輸出 `示範 影片 sample.srt`（與影片同目錄）。
- `dd41655` 與 `94d109a` 兩筆 commit 後，上述基準逐字相同。
- AST 掃描：目前專案內**沒有任何名稱叫 `t`**（三個已改名）。

---

## 譯文待校對的 key

批次 5 還沒開始，**目前沒有任何譯文**。翻譯時特別注意這幾個術語，翻完請回頭校對：

| 術語（繁中） | 備註 |
|---|---|
| 「段」／「第 N 段」 | 影片切成 30 分鐘一段，英文建議 `segment`，日文 `セグメント` |
| 「補跑」 | 失敗段重跑，英文建議 `Retry failed segments` |
| 「配色主題」「清爽白」「深色模式」「金融藍」 | 主題名是自訂稱呼，直譯即可 |
| 「字幕」 | subtitle / 字幕（日文同字） |
| 「影片總時長」 | duration |

---

## 附錄：寫死中日文字串的清單（AST 掃出，行號為 commit `94d109a` 當下）

`src/gui.py` 74 條、`src/translator.py` 12 條（含 f-string 碎片，重組後約 50 條 key）。
重掃指令（在專案根目錄，venv 的 python）：

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

⚠ 搬字串一律用 **AST 逐節點取代**，不要字串搜尋；切字串**在 bytes 上做**
（`col_offset` 是 UTF-8 位元組偏移，中文行用字元位置切會整條歪掉且可能還是合法語法）。
