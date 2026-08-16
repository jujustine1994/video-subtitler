# TODO 清單

## 多語言（i18n）— 已完成（feat/i18n 分支，六個批次全數完成）

- [x] 批次 1：`src/i18n.py`、`src/locales/`、`src/config.py`、首次啟動選語言、設定視窗語言列、重啟提示
- [x] 批次 2：`src/logtext.py`（log 固定繁中）、`src/prompts.py`（Gemini prompt＝資料）、`_log()` 改 fail-closed
- [x] 批次 3：`src/gui.py` 43 處介面文字改走 `t()`
- [x] 批次 4：`src/translator.py` 的錯誤與進度訊息改走 `t()`
- [x] 批次 5：简中／英文／日文譯文（各 53 條）
- [x] 批次 6：`tests/` 從零建起，95 條全綠

### 譯文待校對（拿不準的術語，四語現值）

不影響功能，母語者看到覺得怪再改即可。改譯文不影響任何邏輯（程式一律用 key 比對）。

| key | 繁中 | 简中 | 英文 | 日文 | 疑慮 |
|---|---|---|---|---|---|
| `gui.chk.segment` | 第 {index} 段 | 第 {index} 段 | Segment {index} | セグメント {index} | 影片切段的單位，日文用外來語「セグメント」是否比「区間」自然，沒把握 |
| `gui.btn.retry` | 重試所選段落 | 重试所选段落 | Retry Selected | 選択したセグメントを再実行 | 「補跑」這個中文說法沒有標準英日對應，選了直白版 |
| `theme.financial` | 金融藍 | 金融蓝 | Finance Blue | ファイナンスブルー | 自訂主題名，直譯 |
| `theme.light` / `theme.dark` | 清爽白／深色模式 | 同繁中 | Light / Dark | ライト／ダーク | 英日用業界慣例的單字，沒照字面翻「清爽」 |
| `gui.status.done_with_failures` | 完成，但有 {count} 段失敗 | — | Finished, but {count} segment(s) failed | 完了しましたが {count} 個のセグメントが失敗しました | 英文用 `segment(s)` 迴避單複數，日文無此問題 |
| `log.segment_error` | 第{index}段 上傳Gemini -> … | — | Segment {index} upload to Gemini -> … | セグメント {index} Gemini へのアップロード -> … | 這條同時推 UI 又落檔，落檔那條**永遠是繁中**（`src/logtext.py`），兩邊字面重疊是設計 |

### 判成「資料」不翻、但可以再討論的灰色地帶

- [ ] `" Gemini API Key "` 這個 LabelFrame 標題沒有中日文字，因此不在防退化測試的
      掃描範圍內，目前四語都顯示英文原樣。要不要翻（例如日文「Gemini API キー」）
      可以再決定；現況不算 bug。位置：`src/gui.py` `_build_ui()` 的 `frame_api`。
- [ ] `f"
[ERROR] {type(e).__name__}"`（`src/gui.py` `_worker_full_run` /
      `_worker_retry` 的 except 區塊）同樣沒有中日文，四語都顯示 `[ERROR] XxxError`。
      判成「技術性字串」不翻，但它確實顯示在使用者的畫面上。
- [ ] `show_cth_banner()` 的 ASCII art 與 `created by CTH` 印在背後的 console，
      不算 GUI 文字，未納入 i18n。

## 順手發現、刻意沒動的既有問題

- [ ] **字幕語言存的是中文字面不是機器碼**：`src/prompts.py` 的
      `DEFAULT_TARGET_LANGUAGE = "繁體中文"`（原本在 `translator.translate_segment()`
      的預設參數）。目前它**不落檔、也不跟任何檔案裡的值比對**，所以還沒造成污染，
      呼叫端也從未傳值（`tests/test_subtitle_language_is_data.py` 有測試釘住這點）。
      但**日後若要做成使用者可選的字幕語言並存進 `.tool_config.json`**：
      1. 存進去的必須是機器碼（`zh-TW` / `en` / `ja`），不可以是「繁體中文」這串字
      2. 下拉選單的顯示名可以翻，但顯示與儲存要分兩個變數（`_display()` / `_stored()`）
      3. 它**絕對不可以跟介面語言綁在一起**——字幕跟著影片音訊走
      改成可選設定屬於邏輯變更，這次刻意不動。
- [ ] `src/gui.py` `_save_config()` 現在會把 `DEFAULT_CONFIG` 的所有欄位一起寫回
      設定檔（原本只寫使用者動過的）。行為上無害（值都一樣），但檔案會從
      `{"theme": "light"}` 變成含 `language` 的完整內容。
- [ ] `logs/` 與 `.tool_config.json` 已在 `.gitignore`，但 `requirements_test.txt`
      的 `pytest` 沒有釘版本（目前 9.1.1）。要不要釘版本可再決定。

## 其他

- [ ] 校正專案 MD（依新模板：ARCHITECTURE 補現狀，CHANGELOG 拿掉現狀段）
- [x] 檢查系統是否已安裝 FFmpeg & ffprobe
- [x] 建立 Python 虛擬環境與安裝套件
- [x] 撰寫穩定版擷取音訊腳本 (FFmpeg 直接調用)
- [x] 串接 Gemini API 進行翻譯與 SRT 生成
- [x] 導入 JSON Schema 模式排除廢話
- [x] 導入「專業修理工」自動校正時間軸格式
- [x] 導入「分段處理邏輯」 (30 分鐘/段)，解決長影片偏移與字數限制
- [x] 製作一鍵執行的 BAT 檔案
- [x] 測試長影片 ( > 120 分鐘) 的穩定性
