"""logs/app.log 的訊息字串——**永遠繁體中文，不跟使用者介面語言走**。

log 是給維護者除錯用的：跟著使用者語言變，等於自己看不懂自己的 log。
所以這些字串刻意不進 i18n，也刻意集中在這個檔——gui.py / translator.py 才能被
tests/test_i18n.py 的「不得寫死中日文」那條測試涵蓋，本檔則列入豁免清單。

用法：
    from .logtext import LOG_TEXT
    _write_log_header(LOG_TEXT["task_start_full"].format(name=..., model=..., count=3))

格式一律具名 placeholder（`{count}` 不是 `{0}`），且**不放格式規格**
（`{elapsed:.1f}` 這種）——呼叫端先算好字串再餵進來，否則改字面時一個
`:.0f` 就把數字改掉，而且不會報錯。

⚠ 這裡的字面與語言檔（locales/）重疊是**正常的**：同一句話推 UI 又落檔時，
繁中模式下兩邊本來就長得一樣。該守住的不變量是「切語言不會改到 LOG_TEXT」，
不是「兩邊字面不得相同」。
"""

from __future__ import annotations

LOG_TEXT: dict[str, str] = {
    # 任務起始行（唯一有完整日期的行，關鍵設定塞同一行）
    "task_start_full":  "轉錄 {name} | {model} | {count}段",
    "task_start_retry": "補跑 {name} | {model} | {count}段",
    # 任務結果行
    "task_ok":          "成功，耗時 {minutes}分{seconds}秒",
    "task_fail":        "失敗，耗時 {minutes}分{seconds}秒",
    # 段落錯誤行。detail 只有 exception 類型 + HTTP status code，
    # **絕不含 str(e)**（google-genai 的例外訊息挾帶帶金鑰的完整 URL）。
    "segment_error":       "第{index}段 上傳Gemini -> {detail} | 重試 {attempt}/{total}",
    "segment_error_final": "第{index}段 上傳Gemini -> {detail} | 重試 {attempt}/{total} 後失敗",
}
