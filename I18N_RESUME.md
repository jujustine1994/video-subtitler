# I18N — 多語言遷移完成紀錄（feat/i18n 分支）

2026-08-16 完成。六個批次全數做完，95 條測試全綠。
**本檔留作日後維護的參考**（決策理由與踩過的坑），不是待辦清單——待辦在 `docs/TODO.md`。

分支起點 `8e870b8`。**未合併回 main、未 push。**

---

## commit 列表

| hash | 內容 |
|---|---|
| `4e51871` | docs: TODO 補「校正專案 MD」（分支起點就有的既有改動，與 i18n 無關，先獨立保存） |
| `dd41655` | 前置：消除三個會遮蔽 `i18n.t` 的區域變數（`theme` / `worker` × 2） |
| `94d109a` | 批次 1 前半：`src/i18n.py` |
| `e73b726` | 本檔初版 |
| `fa883e3` | docs: TODO 補多語言待辦與兩項既有問題 |
| `1ff2989` | 批次 1 後半：`config.py`、`locales/`、首次啟動選語言、設定視窗語言列、重啟提示 |
| `80fe88b` | 批次 2-1：`logtext.py` + `prompts.py`（純常數，未接線） |
| `f108763` | 批次 2-2：translator/gui 接上 logtext 與 prompts，`_log` 改 fail-closed |
| `75c1773` | 批次 3：gui.py 43 處介面文字改走 `t()`，zh_tw 母表 |
| `a5f1cae` | 批次 4：translator.py 錯誤與進度訊息改走 `t()`（全專案 CJK 歸零） |
| `e86f04b` | 批次 5：简中／英文／日文譯文（各 53 條） |
| `cc3246b` | 批次 6：防退化測試從零建起（0 → 95 條） |
| `08c18e1` | docs: README / ARCHITECTURE / CHANGELOG / TODO 補多語言說明 |

---

## ★ 這個專案最關鍵的一條：字幕語言 ≠ 介面語言

**字幕的內容跟著影片音訊走。**使用者把介面切成日文，辨識出來的字幕不會、也不該
跟著變成日文——那等於換個介面配色就把辨識結果整個換掉。

現況：字幕語言**沒有 GUI 選項、沒有存進設定檔**。它是 `translate_segment()` 的預設
參數，呼叫端從未傳值，實際上永遠是繁體中文。

**處理方式**：連同整段 prompt 抽成 `src/prompts.py` 的 `DEFAULT_TARGET_LANGUAGE`
與 `TRANSLATE_PROMPT`（純常數、列入測試 ALLOWLIST、字面逐字不變）。
判成**資料**，永不進語言檔。`tests/test_subtitle_language_is_data.py` 是永久守門員：

- 四語下送給 Gemini 的 prompt 逐字相同
- 字幕語言那串字永遠不會出現在 `.tool_config.json`
- 呼叫端沒有開始傳 `target_language`（一傳就得先處理「存機器碼」那件事）
- prompt 與字幕語言沒進過任何語言檔

**已知缺陷（刻意沒動，寫在 `docs/TODO.md`）**：它的值是中文字面「繁體中文」而不是
機器碼。目前不落檔所以還沒污染，但日後做成可選設定時必須改存機器碼 +
`_display()` / `_stored()`。**不要順手做成 GUI 選項**，那是邏輯變更。

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

`THEMES` 的 `name` 欄是純顯示文字 → **有翻**（改放 i18n key，顯示端才 `t()`）；
主題**鍵**不翻。灰色地帶清單見 `docs/TODO.md`。

---

## 驗收結果

| # | 項目 | 結果 |
|---|---|---|
| 1 | 完整測試綠燈 | 0 → **95 條全綠**，連跑 6 次無 flake |
| 2 | 四語各建置 GUI、殘留 key 0 | 四語各 32 條 widget 文字、殘留 key **0** |
| 3 | 輸出基準四語相同且與改前逐字一致 | 檔名／目錄／字幕內容四語完全相同，且與 `8e870b8` 逐字相同 |
| 4 | 四語 key 集合 + placeholder 一致 | 各 53 條，集合與 placeholder 完全一致 |
| 5 | 首次啟動語言視窗 | 開得起來、點下去有存檔、第二次不跳、關掉也存、不洗掉既有主題 |
| 6 | ★ 切介面語言不影響字幕語言 | 四語 prompt 逐字相同；已寫成永久測試 |

**額外驗證**：繁中 widget 文字對 `8e870b8` 逐字比對——既有 27 條全部相同，
只多了新增語言列的 5 條（`Language:` + 四個語言自稱）。

**負向驗證**（都確認會紅，再還原）：

| 破壞 | 抓到的測試 |
|---|---|
| 在 gui.py 塞一條寫死中文 | `test_no_hardcoded_cjk[gui.py]` |
| 從 ja.py 刪一個 key | `test_every_language_has_the_same_keys` |
| 塞一個叫 `t` 的區域變數 | `test_nothing_shadows_the_translation_function` |
| 把字幕語言綁上介面語言 | `test_prompt_is_byte_identical_in_every_ui_language` 等 3 條 |
| 把 en.py 的 placeholder 打錯 | `test_placeholders_match_across_languages` |

---

## 維護須知

- **新增介面文字**：一定走 `t("key")`，並在**四個**語言檔都加。漏了會被
  `test_every_language_has_the_same_keys` 當場抓到。
- **新增落檔訊息**：字面放 `src/logtext.py`（固定繁中），呼叫
  `_log(ui_msg, level, log_msg=...)`。`log_msg` 不給就不落檔（fail-closed）。
- **不要在模組層級 `t()`**：語言是讀完設定檔才設的，會凍結在預設語言。
  常數表就放 key（如 `THEMES` 的 `name`），顯示端才查。
- **不要建名字叫 `t` 的變數／參數／函式**，有測試釘住。
- **字型維持預設**：`i18n.ui_font()` 存在但**刻意不呼叫**——指定字型會改變繁中的
  既有外觀。實測到日文豆腐時才只對 `ja` 套用。
- 測試套件：`uv pip install -r requirements_test.txt --python venv\Scripts\python.exe`
  （此 venv **沒有 pip**）。跑法：`venv\Scripts\python.exe -m pytest tests -q`。

---

## 參考資料

1. `C:\Users\CTH\Documents\Code\_i18n_migration\i18n_lessons.md`（前面專案踩出來的坑）
2. `C:\Users\CTH\.claude\project-rules\windows-tool\tkinter-ui\pattern_i18n.py`（完整食譜）
3. `C:\Users\CTH\.claude\project-rules\general.md`「資料與顯示文字必須分離」
4. `C:\Users\CTH\.claude\project-rules\windows-tool.md`「多語言」「執行紀錄（log）」
5. 參考實作：`C:\Users\CTH\Documents\Code\Video-Combiner` 的 `feat/i18n` 分支
