# tests/test_i18n.py
"""i18n 的防退化測試。

1. 四個語言檔的 key 集合必須完全一致（漏翻當場紅燈）
2. placeholder 必須一致（譯文打錯 {index} 會讓 t() 靜默吐出未格式化的字串）
3. 專案的 .py 不得再出現寫死的中日文字面（防止日後功能開發時悄悄退化）
4. 不得有任何名稱遮蔽 i18n.t

第 3、4 條是**永久**的：它們擋的不是這次遷移，是下一次。新增功能時順手寫一個
中文按鈕標籤最自然不過，沒有它三個月後就又回到全部寫死的狀態。
"""

import ast
import re
from pathlib import Path

import pytest

from src import i18n
from src.logtext import LOG_TEXT

ROOT = Path(__file__).resolve().parent.parent
CJK = re.compile(r"[一-鿿぀-ヿ]")
PLACEHOLDER = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")
FORMAT_SPEC = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*[:!][^}]*\}")

LANGS = [code for code, _, _ in i18n.LANGUAGES]


def _strings(lang: str) -> dict:
    return i18n._strings(lang)


# ── 1. key 集合一致 ────────────────────────────────────────────────────────

def test_every_language_has_the_same_keys():
    """任一語言少一條就紅燈。靠人眼比對五十幾條不可能可靠，這條就是替代品。"""
    base = set(_strings(i18n.FALLBACK_LANG))
    assert base, "繁中母表是空的，locale 載入壞了"
    for lang in LANGS:
        keys = set(_strings(lang))
        missing = sorted(base - keys)
        extra = sorted(keys - base)
        assert not missing, f"{lang} 少了 {len(missing)} 條：{missing[:10]}"
        assert not extra, f"{lang} 多了 {len(extra)} 條（母表沒有）：{extra[:10]}"


def test_no_language_table_is_empty():
    for lang in LANGS:
        assert _strings(lang), f"{lang} 的 STRINGS 是空的"


# ── 2. placeholder 一致 ───────────────────────────────────────────────────

def test_placeholders_match_across_languages():
    """譯文的 {index} 打錯或漏掉，t() 會 format 失敗並吐出未格式化的原字串——
    畫面上看到 {index} 殘留，不會 crash 所以特別容易漏掉。"""
    base = _strings(i18n.FALLBACK_LANG)
    for lang in LANGS:
        if lang == i18n.FALLBACK_LANG:
            continue
        table = _strings(lang)
        for key, zh in base.items():
            if key not in table:      # 缺 key 由上一條測試負責報告
                continue
            want = set(PLACEHOLDER.findall(zh))
            got = set(PLACEHOLDER.findall(table[key]))
            assert want == got, (
                f"{lang} / {key} 的 placeholder 不一致："
                f"母表 {sorted(want)}、譯文 {sorted(got)}"
            )


def test_no_format_spec_leaks_into_the_tables():
    """`{seconds:.1f}` 這種格式規格不可以進譯文：翻譯者一改成 `:.0f`
    數字就變了，而且完全不會報錯。呼叫端先算好字串再餵進來。"""
    for lang in LANGS:
        for key, val in _strings(lang).items():
            assert not FORMAT_SPEC.search(val), f"{lang} / {key} 含格式規格：{val!r}"
    for key, val in LOG_TEXT.items():
        assert not FORMAT_SPEC.search(val), f"LOG_TEXT / {key} 含格式規格：{val!r}"


def test_placeholders_are_named_not_positional():
    """`{0}` 這種位置參數翻譯時語序一變就錯位。"""
    for lang in LANGS:
        for key, val in _strings(lang).items():
            assert not re.search(r"\{\d+\}", val), f"{lang} / {key} 用了位置參數：{val!r}"


# ── 3. 不得寫死中日文 ─────────────────────────────────────────────────────
#
# 豁免清單。每一條都要有理由——沒理由的豁免等於把這條測試關掉。
ALLOWLIST = {
    # 語言選單的顯示名（「繁體中文」「日本語」）本來就該用各語言自稱，
    # 而且它們住在 i18n.py 自己身上，沒有更上層可以查。
    "i18n.py",
    # logs/app.log 的內容依設計永遠繁中：log 是給維護者除錯用的，跟著使用者
    # 語言變等於自廢。這個檔存在的目的就是把那些字串集中起來，好讓 gui.py /
    # translator.py 能被本條測試涵蓋。
    "logtext.py",
    # 送給 Gemini 的 prompt 與**字幕語言**。這是資料不是介面文字：它決定字幕
    # 檔的內容，跟著影片音訊走，翻了等於使用者換介面語言就把辨識結果換掉。
    "prompts.py",
}


def _hardcoded_cjk(path: Path) -> list:
    """回傳 (行號, 字串)。docstring 與註解不算——那些是寫給人看的說明。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docs.add(id(body[0].value))
    hits = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and CJK.search(node.value) and id(node) not in docs):
            hits.append((node.lineno, node.value))
    return sorted(hits)


def _scannable() -> list:
    """⚠ 掃 ROOT 不是只掃 src/：本專案的 main.py 在根目錄。寫死成某個子目錄
    很容易掃到空 list，parametrize 收集 0 個 case——測試「通過」但什麼都沒檢查。"""
    skip_dirs = {"venv", ".venv", "locales", "tests", "__pycache__", ".git", "docs"}
    return [p for p in sorted(ROOT.rglob("*.py"))
            if not skip_dirs & set(p.parts)
            and p.name not in ALLOWLIST]


@pytest.mark.parametrize("path", _scannable(), ids=lambda p: p.name)
def test_no_hardcoded_cjk(path):
    """介面文字一律走 t()。真的需要豁免就加進 ALLOWLIST，但要寫清楚理由。"""
    hits = _hardcoded_cjk(path)
    assert not hits, (
        f"{path.name} 有 {len(hits)} 條寫死的中日文字串，請改走 i18n.t()：\n"
        + "\n".join(f"  行 {ln}: {v[:60]!r}" for ln, v in hits[:10])
    )


def test_scannable_actually_covers_the_gui():
    """豁免清單一旦寫太寬，上面那條就等於沒跑。釘住主程式一定在掃描範圍內，
    而且真的收集到檔案（不是空 list）。"""
    files = _scannable()
    assert len(files) > 0, "掃描範圍是空的，上面那條測試等於沒跑"
    names = {p.name for p in files}
    assert {"gui.py", "translator.py", "config.py", "main.py"} <= names, \
        f"主程式不在掃描範圍：{sorted(names)}"


# ── 4. 不得有任何名稱遮蔽 i18n.t ─────────────────────────────────────────

def test_nothing_shadows_the_translation_function():
    """區域變數／參數叫 `t` 會遮蔽 `from .i18n import t`，同一個 scope 裡的
    `t("gui.x")` 就變成對 dict 取值或對 Thread 呼叫——而且只有那條路徑被走到
    時才炸，靜態看不出來。

    本專案動手前有三個：`_apply_theme` 的主題 dict、`_start` 與 `_retry_selected`
    的 threading.Thread。已改名為 theme / worker，這條測試釘住不要走回頭路。
    """
    offenders = []
    for path in _scannable():
        if path.name == "i18n.py":       # t() 的家
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "t":
                    offenders.append(f"{path.name}:{node.lineno} def t()")
                for a in (node.args.args + node.args.kwonlyargs
                          + node.args.posonlyargs):
                    if a.arg == "t":
                        offenders.append(f"{path.name}:{node.lineno} "
                                         f"{node.name}() 的參數 t")
            if (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
                    and node.id == "t"):
                offenders.append(f"{path.name}:{node.lineno} 賦值給 t")
    assert not offenders, "有名稱遮蔽 i18n.t：\n  " + "\n  ".join(offenders)


# ── t() 的行為 ────────────────────────────────────────────────────────────

def test_unknown_key_returns_the_key_itself():
    """查不到不回空字串——空白按鈕看不見，key 看得見。"""
    i18n.set_lang("zh_tw")
    assert i18n.t("gui.btn.does_not_exist") == "gui.btn.does_not_exist"


def test_falls_back_to_traditional_chinese(monkeypatch):
    monkeypatch.setitem(i18n._cache, "ja", {})
    i18n.set_lang("ja")
    try:
        assert i18n.t("gui.btn.start") == _strings("zh_tw")["gui.btn.start"]
    finally:
        i18n._cache.pop("ja", None)
        i18n.set_lang("zh_tw")


def test_unknown_lang_falls_back_to_default():
    try:
        assert i18n.set_lang("kl_ingon") == i18n.DEFAULT_LANG
        assert i18n.set_lang(None) == i18n.DEFAULT_LANG
        assert i18n.set_lang("") == i18n.DEFAULT_LANG
    finally:
        i18n.set_lang("zh_tw")


def test_format_failure_returns_the_unformatted_string():
    """譯文的 placeholder 打錯不該讓程式當掉。"""
    i18n.set_lang("zh_tw")
    got = i18n.t("gui.progress.segments", done=1)      # 少給 total
    assert "{total}" in got


def test_t_never_raises_and_never_returns_empty():
    for lang in LANGS:
        i18n.set_lang(lang)
        for key in _strings(i18n.FALLBACK_LANG):
            assert i18n.t(key) != ""
    i18n.set_lang("zh_tw")


def test_ui_font_follows_language():
    """微軟正黑體缺日文假名字形，真的要指定字型時日文必須換。
    （本工具目前不呼叫 ui_font，維持既有外觀——見 i18n.py 的說明。）"""
    assert i18n.ui_font("ja") != i18n.ui_font("zh_tw")
    assert i18n.ui_font("ja") == "Yu Gothic"


def test_language_menu_is_generated_from_the_registry():
    """下拉選單的選項不是寫死的——新增語言只改 LANGUAGES 一行。"""
    codes = [c for c, _ in i18n.available_languages()]
    assert codes == LANGS
    assert len(codes) >= 4


# ── log 檔永遠繁中 ────────────────────────────────────────────────────────

def test_log_text_never_changes_with_the_ui_language():
    """log 是給維護者除錯用的：跟著使用者語言變等於自廢。

    ⚠ 這裡**不能**寫成「LOG_TEXT 的值不得出現在語言檔裡」——同一句話推 UI
    又落檔時兩邊字面本來就一樣（segment_error 就是），重疊是設計不是 bug。
    """
    snapshot = dict(LOG_TEXT)
    for lang in LANGS:
        i18n.set_lang(lang)
        assert dict(LOG_TEXT) == snapshot, f"切到 {lang} 之後 LOG_TEXT 被改掉了"
    i18n.set_lang("zh_tw")
    for key, val in LOG_TEXT.items():
        assert CJK.search(val), f"LOG_TEXT / {key} 不是中文了：{val!r}"


def test_log_text_and_locale_keys_do_not_collide():
    """兩張表的 key 命名空間要分開，才不會有人以為改一邊就兩邊都改到。"""
    for lang in LANGS:
        assert not (set(LOG_TEXT) & set(_strings(lang))), \
            f"{lang} 與 LOG_TEXT 有同名 key"


# ── 機器鍵不得被翻譯 ──────────────────────────────────────────────────────
#
# 這些字串會被寫進檔案、餵給外部程式，或拿去跟 dict 的鍵比對。翻了會靜默改掉
# 使用者的輸出檔名、讓設定檔對不起來，或直接讓 ffmpeg / Gemini 失敗。

MACHINE_VALUES = [
    "light", "dark", "financial",              # THEMES 的鍵＝存進設定檔的值
    "zh_tw", "zh_cn", "en", "ja",              # 語言代號＝存進設定檔的值
    ".srt", "temp_seg_", ".mp3",               # 檔名樣板與副檔名
    "ffmpeg", "ffprobe", "libmp3lame", "-vn",  # 外部程式參數
    "gemini-flash-latest",                     # 模型代號
    "GEMINI_API_KEY",                          # .env 的鍵名
    "srt_content",                             # Gemini 回傳 JSON 的欄位名
    "-->",                                     # SRT 規格
]


@pytest.mark.parametrize("lang", LANGS)
def test_machine_values_are_not_in_any_locale(lang):
    table = _strings(lang)
    for v in MACHINE_VALUES:
        assert v not in table, f"{lang} 把機器鍵 {v!r} 放進語言檔當 key 了"
        assert v not in table.values(), f"{lang} 把機器鍵 {v!r} 當成譯文了"


@pytest.mark.parametrize("lang", LANGS)
def test_theme_keys_are_machine_codes(lang):
    """THEMES 的鍵是存進 .tool_config.json 的值，name 欄放的才是 i18n key。"""
    from src import gui
    assert set(gui.THEMES) == {"light", "dark", "financial"}
    table = _strings(lang)
    for key, info in gui.THEMES.items():
        assert info["name"] in table, f"{info['name']} 不是合法的 i18n key"
        assert not CJK.search(key)
