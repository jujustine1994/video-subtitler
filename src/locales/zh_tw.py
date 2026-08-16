"""locales/zh_tw.py — 繁體中文（母表）

改這裡的譯文不影響任何邏輯：程式一律用 key 比對。改錯最壞的情況只是
畫面顯示怪怪的。

⚠ 這裡只放**介面文字**。會被寫進檔案、拿去跟檔案裡的值比對、或送給外部
程式（Gemini / ffmpeg）的字串是資料，不進這個檔：
  - 送給 Gemini 的 prompt 與字幕語言 → src/prompts.py
  - logs/app.log 的內容 → src/logtext.py（固定繁中）
  - SRT 格式規格、輸出檔名、暫存檔名、ffmpeg 參數 → 留在原處，永不翻譯
"""

from __future__ import annotations

STRINGS: dict[str, str] = {}
