# tests/test_subtitle_language_is_data.py
"""★ 本專案特有：**字幕語言 ≠ 介面語言**。

字幕的內容跟著**影片音訊**走。使用者把介面切成日文，辨識出來的字幕不會、
也不該跟著變成日文——那等於換個介面配色就把辨識結果整個換掉。

所以這支測試釘住三件事：

1. 切換介面語言後，送給 Gemini 的 prompt（含字幕語言）**逐字不變**
2. 存進 .tool_config.json 的值只有機器碼（語言代號、主題代號），
   字幕語言那串**永遠不會被寫進設定檔**
3. 字幕語言與 prompt 從來沒有進過任何語言檔

這是 general.md「存進設定檔的預設分類名被翻譯」那個資料污染案例在本專案的
對應版本，也是整個多語言遷移最容易踩壞的一項。
"""

import json

import pytest

from src import gui, i18n, prompts, translator

LANGS = [code for code, _, _ in i18n.LANGUAGES]


def _captured_prompt():
    """跑真正的 translate_segment，攔下它組出來的 prompt。Gemini 全程 mock。"""
    box = {}

    def _fake_call(client, audio_path, prompt, offset_seconds, on_log):
        box["prompt"] = prompt
        return "ok"

    original = translator._call_gemini
    translator._call_gemini = _fake_call
    try:
        translator.translate_segment(None, "a.mp3", 0, 0)
    finally:
        translator._call_gemini = original
    return box["prompt"]


# ── 1. prompt 與字幕語言不跟著介面語言變 ─────────────────────────────────

def test_prompt_is_byte_identical_in_every_ui_language():
    prompts_seen = {}
    for lang in LANGS:
        i18n.set_lang(lang)
        prompts_seen[lang] = _captured_prompt()
    i18n.set_lang("zh_tw")

    assert len(set(prompts_seen.values())) == 1, \
        "送給 Gemini 的 prompt 隨介面語言變了——字幕內容會跟著被改掉"
    assert prompts.DEFAULT_TARGET_LANGUAGE in prompts_seen["ja"], \
        "日文介面下字幕語言被換掉了"


@pytest.mark.parametrize("lang", LANGS)
def test_target_language_constant_never_changes(lang):
    i18n.set_lang(lang)
    try:
        assert prompts.DEFAULT_TARGET_LANGUAGE == "繁體中文"
        assert translator.translate_segment.__defaults__[0] == \
            prompts.DEFAULT_TARGET_LANGUAGE
    finally:
        i18n.set_lang("zh_tw")


def test_caller_never_passes_a_target_language():
    """呼叫端一旦開始傳值，就必須同時處理「存機器碼」那件事（見 docs/TODO.md）。
    這條測試是那個提醒的守門員。"""
    import ast
    import inspect
    import textwrap
    src = textwrap.dedent(inspect.getsource(gui.SubtitlerApp._run_segments))
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                assert kw.arg != "target_language", (
                    "呼叫端開始傳 target_language 了：請先讀 docs/TODO.md 的"
                    "「字幕語言存的是中文字面不是機器碼」再動")


# ── 2. 字幕語言永遠不會被寫進設定檔 ──────────────────────────────────────

@pytest.mark.parametrize("lang", LANGS)
def test_saving_settings_never_writes_the_subtitle_language(lang, app_factory):
    """四語各存一次設定，設定檔裡只能有機器碼，不能出現字幕語言那串字。"""
    app, win, cfg_path = app_factory(lang)
    app._open_settings()
    try:
        app._save_config({"theme": "dark", "language": app._selected_lang_code()})
    finally:
        app.settings_win.destroy()

    raw = cfg_path.read_text(encoding="utf-8")
    saved = json.loads(raw)
    assert saved["language"] == lang
    assert saved["theme"] == "dark"
    assert prompts.DEFAULT_TARGET_LANGUAGE not in raw, \
        "字幕語言被寫進設定檔了——一旦跟介面語言綁在一起就是資料污染"
    assert set(saved) <= {"language", "theme"}, \
        f"設定檔多了預期外的欄位：{sorted(set(saved) - {'language', 'theme'})}"


def test_every_ui_language_stores_the_same_subtitle_language(app_factory):
    """四語各跑一次完整流程，實際生效的字幕語言必須是同一個值。"""
    effective = {}
    for lang in LANGS:
        app, win, cfg_path = app_factory(lang)
        effective[lang] = _captured_prompt()
        assert json.loads(cfg_path.read_text(encoding="utf-8"))["language"] == lang
    assert len(set(effective.values())) == 1, \
        f"不同介面語言下字幕語言不一樣：{ {k: v[:40] for k, v in effective.items()} }"


# ── 3. prompt 與字幕語言從來沒進過語言檔 ─────────────────────────────────

@pytest.mark.parametrize("lang", LANGS)
def test_prompt_text_is_not_in_any_locale(lang):
    table = i18n._strings(lang)
    assert prompts.DEFAULT_TARGET_LANGUAGE not in table.values(), \
        f"{lang} 把字幕語言當成介面文字翻譯了"
    for key in table:
        assert not key.startswith("prompt."), \
            f"{lang} 有 prompt.* 的 key（{key}）——prompt 是資料不進語言檔"
    # prompt 本體的特徵句也不該出現在任何譯文裡
    assert not any("srt_content" in v for v in table.values()), \
        f"{lang} 的譯文裡出現了 Gemini 回傳欄位名"


def test_prompt_template_keeps_its_only_placeholder():
    """prompt 只能有 {target_language} 一個 placeholder：多一個就會在
    .format() 時 KeyError，少一個代表字幕語言被寫死了。"""
    import re
    found = set(re.findall(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}", prompts.TRANSLATE_PROMPT))
    assert found == {"{target_language}"}, found
