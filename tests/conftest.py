# tests/conftest.py
"""共用 fixture。"""

import json
import os
import sys
import tkinter as tk

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import gui, i18n  # noqa: E402


@pytest.fixture(scope="session")
def tk_root():
    """整個測試 session 共用一個隱藏的 Tk root。

    ⚠ 不可以每個測試建一個 tk.Tk()：Microsoft Store 版 Python 在短時間內
    反覆建立／銷毀直譯器時，會間歇性地丟
    `TclError: Can't find a usable init.tcl ... No error`——測試看起來隨機紅
    綠，跟被測程式一點關係都沒有。要另一個視窗就開 Toplevel。

    本專案的 SubtitlerApp 是 `SubtitlerApp(root)`（接受外部傳進來的 root），
    不是 `class App(tk.Tk)`，所以共用 root + Toplevel 這個解法成立，
    不需要「一語言一個子行程」。
    """
    root = tk.Tk()
    root.withdraw()
    yield root
    try:
        root.destroy()
    except tk.TclError:
        pass


@pytest.fixture
def app_factory(tmp_path, monkeypatch, tk_root):
    """用臨時設定檔建 App，不碰使用者真正的 .tool_config.json 與 .env。

    視窗用 Toplevel 不用 tk.Tk()——原因見上面 tk_root。
    """
    created = []

    def _make(lang, theme="light"):
        assert i18n.is_supported(lang), f"{lang} 不是合法語言代號"
        cfg_path = tmp_path / f"config_{lang}.json"
        cfg_path.write_text(json.dumps({"language": lang, "theme": theme}),
                            encoding="utf-8")
        monkeypatch.setattr(gui, "CONFIG_PATH", str(cfg_path))
        # .env 也導到臨時檔：測試絕不該讀寫使用者真正的 API Key
        monkeypatch.setattr(gui, "ENV_PATH", str(tmp_path / ".env"))
        win = tk.Toplevel(tk_root)
        win.withdraw()
        app = gui.SubtitlerApp(win)
        created.append(win)
        return app, win, cfg_path

    yield _make

    for win in created:
        try:
            win.destroy()
        except tk.TclError:
            pass
    i18n.set_lang("zh_tw")
