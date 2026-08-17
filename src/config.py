"""config.py — 讀寫 .tool_config.json。

讀出來的內容一律與 DEFAULT_CONFIG 合併，缺的 key 補上預設值，
呼叫端不必到處寫 `.get(..., 預設)`。

⚠ 設定檔是**專案根目錄**的 `.tool_config.json`（不是 src/config.json）——
既有使用者的主題設定就存在那裡，搬位置等於把他們的設定弄丟。已在 .gitignore。
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

# gui.py 的 SCRIPT_DIR 算的是同一個位置（src/ 的上一層＝專案根目錄）
CONFIG_PATH = Path(__file__).resolve().parent.parent / ".tool_config.json"

DEFAULT_CONFIG: dict = {
    # 介面語言。代號清單見 i18n.LANGUAGES。
    #
    # 預設是**空字串而不是 "zh_tw"**：空字串代表「使用者還沒選過」，
    # gui._pick_language_on_first_run() 靠它決定首次啟動要不要問。填了
    # "zh_tw" 就分不出「他選了繁中」和「他沒選過」，只能再加一個布林值，
    # 而兩個欄位描述同一件事遲早會不同步。
    #
    # 空字串餵給 i18n.set_lang() 會退回預設語言，所以就算問語言那步被跳過，
    # 程式照樣跑得動。
    #
    # ⚠ 這是**介面**語言，跟字幕（辨識輸出）的語言完全無關。字幕語言跟著影片
    # 音訊走，見 src/prompts.py。
    "language": "",
    # 配色主題。值是機器碼（light / dark / financial），**不是**畫面上顯示的
    # 「清爽白」——顯示名走 i18n，存檔值永遠是這三個代號。
    "theme": "light",
}


def load_config(path: Path | str | None = None) -> dict:
    """讀 .tool_config.json，缺的 key 用預設值補齊。檔案壞掉時整份退回預設。"""
    if path is None:
        path = CONFIG_PATH
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return cfg
        if isinstance(data, dict):
            cfg.update(data)
    return cfg


def save_config(cfg: dict, path: Path | str | None = None) -> None:
    """寫回設定檔（UTF-8）。寫不進去不讓主程式掛掉，只是設定沒存成。"""
    if path is None:
        path = CONFIG_PATH
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
