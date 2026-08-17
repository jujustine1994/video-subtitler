"""locales/zh_tw.py — 繁體中文（母表）

改這裡的譯文不影響任何邏輯：程式一律用 key 比對。改錯最壞的情況只是
畫面顯示怪怪的。

⚠ 這裡只放**介面文字**。會被寫進檔案、拿去跟檔案裡的值比對、或送給外部
程式（Gemini / ffmpeg）的字串是資料，不進這個檔：
  - 送給 Gemini 的 prompt 與字幕語言 → src/prompts.py
  - logs/app.log 的內容 → src/logtext.py（固定繁中）
  - SRT 格式規格、輸出檔名、暫存檔名、ffmpeg 參數 → 留在原處，永不翻譯

帶變數的訊息一律用**具名** placeholder（`{index}` 不是 `{0}`）——翻譯時語序
一變，位置參數就錯位。且**不放格式規格**（`{sec:.1f}` 這種），呼叫端先算好
再餵進來。
"""

from __future__ import annotations

STRINGS: dict[str, str] = {
    # ── 視窗與區塊標題 ──────────────────────────────────────────────
    "gui.win.title":            "Gemini 影片字幕翻譯工具",
    "gui.frame.file":           " 影片檔案 ",
    "gui.frame.progress":       " 處理進度 ",
    "gui.frame.retry":          " 失敗段落 ",

    # ── 按鈕與勾選 ─────────────────────────────────────────────────
    "gui.btn.pick_file":        "選擇影片",
    "gui.btn.show_key":         "顯示",
    "gui.btn.start":            "▶  開始翻譯",
    "gui.btn.retry":            "重試所選段落",
    "gui.btn.apply":            "套用",
    "gui.btn.cancel":           "取消",
    "gui.chk.remember_key":     "記住",
    "gui.chk.segment":          "第 {index} 段",

    # ── 標籤與說明 ─────────────────────────────────────────────────
    "gui.lbl.api_notice":       "🔒 API Key 僅儲存於本機 .env 檔，請勿將 Key 提供給他人。",
    "gui.lbl.theme":            "配色主題",
    "gui.lbl.failed_hint":      "以下段落失敗，可勾選後重試：",
    "gui.log.hint":             "選擇影片並輸入 API Key 後按「開始翻譯」。\n",

    # ── 配色主題名（鍵 light/dark/financial 是機器碼，不在這裡）──────
    "theme.light":              "清爽白",
    "theme.dark":               "深色模式",
    "theme.financial":          "金融藍",

    # ── 對話框 ─────────────────────────────────────────────────────
    "gui.dlg.settings_title":   "設定",
    "gui.dlg.pick_file_title":  "請選擇影片檔案",
    "gui.dlg.error_title":      "錯誤",
    "gui.dlg.info_title":       "提示",
    "gui.dlg.done_title":       "完成",
    # 檔案類型的說明文字（萬用字元樣式是資料，留在程式碼裡）
    "gui.filetype.video":       "影片檔案",
    "gui.filetype.all":         "所有檔案",

    # ── 訊息 ───────────────────────────────────────────────────────
    "gui.msg.no_video":            "請選擇有效的影片檔案",
    "gui.msg.no_api_key":          "請輸入 Gemini API Key",
    "gui.msg.select_one_segment":  "請至少勾選一個失敗段落",
    "gui.msg.done":                "已完成：\n{path}",

    # ── 狀態列與進度 ───────────────────────────────────────────────
    "gui.status.idle":               "等待開始...",
    "gui.status.ready":              "就緒",
    "gui.status.preparing":          "準備中...",
    "gui.status.running":            "執行中，請稍候...",
    "gui.status.retrying":           "重試中，請稍候...",
    "gui.status.done":               "已完成！",
    "gui.status.done_with_failures": "完成，但有 {count} 段失敗",
    "gui.status.fatal_label":        "發生錯誤，請查看上方記錄",
    "gui.status.fatal":              "致命錯誤：{error}",
    "gui.progress.segments":         "{done} / {total} 段完成",

    # ── 畫面記錄區（只推 UI，不落檔；落檔的在 logtext.py）────────────
    "gui.log.duration":         "影片總時長: {minutes} 分 {seconds} 秒",
    "gui.log.total_segments":   "共 {count} 段，開始處理...",
    "gui.log.segment_start":    "\n-> 正在處理第 {index} 段 (起始時間: {minutes} 分)...",
    "gui.log.segment_retry":    "   第 {index} 段失敗，{delay} 秒後重試（第 {attempt} 次）...",
    "gui.log.segment_done":     "   第 {index} 段完成。",
    "gui.log.segment_failed":   "   第 {index} 段重試後仍失敗（{error}）",
    "gui.log.failed_list":      "\n以下段落失敗：第 {indices} 段",
    "gui.log.output":           "\n字幕已輸出: {path}",
    "gui.log.retry_start":      "\n重試第 {indices} 段...",
    "gui.log.ai_ready":         "AI 已就緒，開始翻譯 ({model})...",

    # ── 同時推 UI 又落檔的訊息 ─────────────────────────────────────
    # ⚠ 這兩條與 logtext.py 的 segment_error / segment_error_final 字面相同，
    #   那是**設計**：同一句話推 UI（跟著介面語言）又落檔（固定繁中），
    #   繁中模式下兩邊本來就一樣。不要為了「去重複」把任何一邊刪掉。
    "log.segment_error":        "第{index}段 上傳Gemini -> {detail} | 重試 {attempt}/{total}",
    "log.segment_error_final":  "第{index}段 上傳Gemini -> {detail} | 重試 {attempt}/{total} 後失敗",

    # ── 會顯示給使用者看的例外訊息 ─────────────────────────────────
    "err.ffmpeg_failed":        "ffmpeg 音訊擷取失敗，請確認 FFmpeg 已安裝並加入系統環境變數（PATH）。",
}
