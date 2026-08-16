# tests/test_gui_build.py
"""GUI 建置 smoke test：四種語言各建一次，確認畫面上沒有殘留的 key 字串。

t() 查不到時回 key 本身（`gui.btn.start`），所以「漏翻」的症狀就是畫面上出現
一串點分隔的英文小寫。這支測試把整棵 widget 樹走過一遍去找那種字串——比人眼
開四次程式可靠。

刻意**不進 mainloop**：建好、withdraw()、走訪、destroy。
"""

import re
import tkinter as tk
from tkinter import ttk

import pytest

from src import gui, i18n

LANGS = [code for code, _, _ in i18n.LANGUAGES]

KEY_LIKE = re.compile(r"[a-z][a-z0-9_]*(\.[a-z0-9_]+)+")
# Entry / Spinbox 的 cget("text") 會回 PY_VAR0 這種變數名，是雜訊不是漏翻
VARNAME = re.compile(r"PY_VAR\d+")


def _looks_like_a_key(text: str) -> bool:
    return bool(KEY_LIKE.fullmatch(text.strip()))


def _all_texts(widget, out=None):
    """收集整棵樹上所有會顯示給使用者的字串。

    Treeview 的欄位標題、Combobox 的 values、tk.Text 的內容用 cget("text")
    通通拿不到，要各自另外抓。
    """
    if out is None:
        out = []
    try:
        v = widget.cget("text")
        if isinstance(v, str) and v and not VARNAME.fullmatch(v):
            out.append(v)
    except (tk.TclError, AttributeError):
        pass
    if isinstance(widget, ttk.Combobox):
        out.extend(str(v) for v in widget.cget("values"))
    if isinstance(widget, ttk.Notebook):
        for tab in widget.tabs():
            out.append(widget.tab(tab, "text"))
    if isinstance(widget, ttk.Treeview):
        for col in ("#0",) + tuple(widget.cget("columns") or ()):
            try:
                out.append(widget.heading(col, "text"))
            except tk.TclError:
                pass
    # ⚠ tk.Text / ScrolledText 的內容 cget("text") 完全掃不到。本工具的開場
    # 提示整條住在 ScrolledText 裡，漏掃就等於那塊沒被檢查。
    if isinstance(widget, tk.Text):
        content = widget.get("1.0", "end-1c")
        out.extend(line for line in content.splitlines() if line.strip())
    if isinstance(widget, tk.Listbox):
        out.extend(str(v) for v in widget.get(0, "end"))
    for child in widget.winfo_children():
        _all_texts(child, out)
    return out


def _texts_of_everything(app, win):
    """主視窗 + 設定視窗 + 失敗段清單，一次收齊。"""
    collected = [win.title()] + _all_texts(win)
    app._open_settings()
    settings = app.settings_win
    collected += [settings.title()] + _all_texts(settings)
    settings.destroy()
    app._show_failed_segments([0, 2])
    collected += _all_texts(app.frame_retry)
    return collected


@pytest.mark.parametrize("lang", LANGS)
def test_gui_builds_in_every_language_without_residual_keys(lang, app_factory):
    app, win, _ = app_factory(lang)

    assert i18n.get_lang() == lang, "App 沒有依設定檔設定語言"

    texts = _texts_of_everything(app, win)
    residual = [s for s in texts if _looks_like_a_key(s)]
    assert not residual, f"{lang} 畫面上有殘留的 key：{residual}"

    table = i18n._strings(lang)
    # 譯文真的被套上去了（不是整批退回母表）
    assert win.title() == table["gui.win.title"]
    for key in ("gui.btn.start", "gui.btn.pick_file", "gui.btn.retry",
                "gui.lbl.theme", "theme.financial", "gui.lbl.failed_hint"):
        assert table[key] in texts, f"{lang} 的 {key} 沒吃到譯文"

    # ScrolledText 裡的開場提示必須真的被走訪到（漏掃 tk.Text 是常見死角）
    assert table["gui.log.hint"].strip() in texts, \
        f"{lang} 的 ScrolledText 提示沒被收集到，或沒吃到譯文"


def test_switching_language_actually_changes_the_screen(app_factory):
    """四語建出來的畫面必須真的不一樣——不然上一條測試只是在確認「都沒翻」。

    ⚠ 門檻不寫死絕對值：繁中／简中天生有好幾條一樣（「取消」「提示」「完成」），
    再加上四語刻意相同的條目（產品名、Language:、四個語言自稱）。
    改成「扣掉四語本來就相同的條目後，差異數 ≥ 應該變的條目的一半」動態算。
    """
    per_lang = {}
    for lang in LANGS:
        app, win, _ = app_factory(lang)
        per_lang[lang] = _texts_of_everything(app, win)

    base = per_lang["zh_tw"]
    always_same = set(base)
    for lang in LANGS[1:]:
        always_same &= set(per_lang[lang])
    should_change = [s for s in base if s not in always_same]
    assert should_change, "四語畫面完全一樣，語言根本沒切換"

    for lang in LANGS[1:]:
        diff = sum(1 for s in should_change if s not in set(per_lang[lang]))
        assert diff >= len(should_change) // 2, (
            f"{lang} 只有 {diff}/{len(should_change)} 條跟繁中不同，"
            "語言可能沒真的切換"
        )


@pytest.mark.parametrize("lang", LANGS)
def test_language_row_shows_the_saved_language(lang, app_factory):
    """語言選單顯示的是設定檔存的那個，不是 runtime 值。

    用 runtime 值當基準的話，使用者選了新語言但按「稍後」不重啟時，下次開設定
    按套用會把他的選擇默默寫回舊值。
    """
    app, win, _ = app_factory(lang)
    app._open_settings()
    try:
        expected = dict(i18n.available_languages())[lang]
        assert app.settings_lang_var.get() == expected
        assert app._selected_lang_code() == lang
        assert app._lang_saved_code == lang
    finally:
        app.settings_win.destroy()


def test_language_combobox_lists_every_registered_language(app_factory):
    app, win, _ = app_factory("en")
    app._open_settings()
    try:
        values = list(app.settings_lang_combo.cget("values"))
        assert values == [name for _, name in i18n.available_languages()]
    finally:
        app.settings_win.destroy()


def test_language_label_stays_english(app_factory):
    """標籤固定英文 "Language:"——任何語言下的使用者都認得出這一列是什麼。"""
    for lang in LANGS:
        app, win, _ = app_factory(lang)
        app._open_settings()
        try:
            assert "Language:" in _all_texts(app.settings_win)
        finally:
            app.settings_win.destroy()


@pytest.mark.parametrize("lang", LANGS)
def test_unknown_language_in_config_still_builds(lang, app_factory, tmp_path,
                                                 monkeypatch, tk_root):
    """設定檔被手改成怪值時要退回預設語言，不是整個起不來。"""
    import json
    cfg = tmp_path / "broken.json"
    cfg.write_text(json.dumps({"language": "kl_ingon", "theme": "nope"}),
                   encoding="utf-8")
    monkeypatch.setattr(gui, "CONFIG_PATH", str(cfg))
    monkeypatch.setattr(gui, "ENV_PATH", str(tmp_path / ".env"))
    win = tk.Toplevel(tk_root)
    win.withdraw()
    try:
        app = gui.SubtitlerApp(win)
        assert i18n.get_lang() == i18n.DEFAULT_LANG
        assert not [s for s in _all_texts(win) if _looks_like_a_key(s)]
    finally:
        win.destroy()
        i18n.set_lang("zh_tw")
