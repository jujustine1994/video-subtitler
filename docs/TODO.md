# TODO 清單

## 多語言（i18n，feat/i18n 分支進行中，批次 1 只做完 i18n.py 即中斷）

詳細交接見根目錄 `I18N_RESUME.md`（全部完成後刪除該檔）。

- [ ] 批次 1 剩餘：`src/locales/`、`src/config.py`（設定檔是根目錄 `.tool_config.json`，
      `DEFAULT_CONFIG = {"language": "", "theme": "light"}`）、首次啟動選語言、
      設定視窗語言列、重啟提示
- [ ] 批次 2：`src/logtext.py`（5 條落檔字串固定繁中）＋ `gui._log()` 改成
      `_log(ui_msg, log_msg=None)`（`gui.py` `_run_segments` 的 `on_error` 是唯一
      同時推 UI 又落檔的路徑）
- [ ] 批次 3：`src/gui.py` 74 條寫死中文（f-string 碎片要整句重組）；
      `THEMES` 的 `name` 欄改放 i18n key，**鍵 `light`/`dark`/`financial` 不可動**（存進設定檔）
- [ ] 批次 4：錯誤訊息，含 `src/translator.py` L60 `RuntimeError("ffmpeg 音訊擷取失敗…")`
- [ ] 批次 5：简中／英／日譯文；術語待校對：「段」「補跑」「配色主題」與三個主題名
- [ ] 批次 6：`tests/`（本專案目前 **0 條測試**），含防退化三道 +
      `test_nothing_shadows_the_translation_function` + GUI smoke（要掃 `ScrolledText`）+
      輸出基準四語比對 + ★「切介面語言不影響字幕語言」永久測試

### 順手發現、刻意沒動的既有問題

- [ ] `src/translator.py` L159 `translate_segment(target_language="繁體中文")`：字幕語言目前是
      **中文字面的預設參數**，不是機器碼，且沒有 GUI 選項、呼叫端從未傳值。
      目前不落檔所以還沒造成污染，但**日後若做成可選設定存進 `.tool_config.json`，
      必須存機器碼（`zh-TW`/`en`/`ja`），顯示名另走 `_display()`/`_stored()`**，
      不可直接存「繁體中文」。改成設定屬邏輯變更，這次刻意不動。
- [ ] `src/translator.py` L169-185 的 Gemini prompt 待抽成 `src/prompts.py`（純常數模組，
      抽出時字面必須逐字不變；它是資料不是介面文字，測試要列入 ALLOWLIST）

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
