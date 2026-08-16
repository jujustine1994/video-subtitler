# tests/test_output_baseline.py
"""輸出基準：字幕檔的**檔名、目錄、完整內容**四種語言必須完全相同，
而且必須跟導入多語言之前逐字一致。

這些是**資料不是介面文字**：翻了以後同一個使用者切個語言就會存到不同檔名、
或產出格式不同的字幕檔，而且是靜默發生的。

ffmpeg / ffprobe / Gemini 全程 mock，不真的跑外部程式。
"""

import os
import tkinter as tk

import pytest

from src import gui, i18n, translator

LANGS = [code for code, _, _ in i18n.LANGUAGES]

# 兩段假字幕：刻意包含超過 5 秒的字幕、重複的序號、非 ASCII 內容與時間偏移，
# 好讓 enforce_max_duration() 與 renumber_srt() 真的被走到。
SEG0 = """1
00:00:00,000 --> 00:00:12,500
第一句 hello world

2
00:00:12,600 --> 00:00:14,000
第二句
"""
SEG1 = """1
00:30:00,000 --> 00:30:03,000
第三句 テスト

2
00:30:04,000 --> 00:30:20,000
第四句
"""

# ⚠ 這份期望值是從導入多語言**之前**的 commit（8e870b8）實際跑出來的。
# 改動 renumber_srt / enforce_max_duration / _merge_and_write 而讓它變了，
# 就是改到了使用者的輸出，不是「測試過時」。
EXPECTED_SRT = (
    "1\n00:00:00,000 --> 00:00:05,000\n第一句 hello world\n\n"
    "2\n00:00:12,600 --> 00:00:14,000\n第二句\n\n"
    "3\n00:30:00,000 --> 00:30:03,000\n第三句 テスト\n\n"
    "4\n00:30:04,000 --> 00:30:09,000\n第四句\n"
)


def _produce(app, tmp_path):
    """跑真正的合併與檔名組裝，回傳 (輸出路徑, 字幕內容)。"""
    video = str(tmp_path / "示範 影片 sample.mp4")
    app._video_path = video
    app._segments = {0: SEG0, 1: SEG1, 2: None}   # 第三段失敗，不該進輸出
    app._merge_and_write()
    with open(app._output_path, encoding="utf-8") as f:
        return app._output_path, f.read()


@pytest.mark.parametrize("lang", LANGS)
def test_subtitle_file_matches_the_pre_i18n_baseline(lang, app_factory, tmp_path):
    app, _, _ = app_factory(lang)
    out_path, content = _produce(app, tmp_path)

    assert os.path.basename(out_path) == "示範 影片 sample.srt"
    assert os.path.dirname(out_path) == str(tmp_path), "字幕檔要存在影片旁邊"
    assert content == EXPECTED_SRT, f"{lang} 產出的字幕檔跟導入多語言前不一樣"


def test_all_languages_produce_byte_identical_output(app_factory, tmp_path):
    """四語產出的檔名與內容必須完全相同——這條擋的是「某個語言下輸出被翻掉」。"""
    results = {}
    for lang in LANGS:
        app, _, _ = app_factory(lang)
        out_path, content = _produce(app, tmp_path)
        results[lang] = (os.path.basename(out_path), content)
    assert len(set(results.values())) == 1, f"四語輸出不一致：{list(results)}"


@pytest.mark.parametrize("lang", LANGS)
def test_temp_audio_name_is_identical_in_every_language(lang, app_factory,
                                                        tmp_path, monkeypatch):
    """暫存檔名 temp_seg_<n>.mp3 會被寫上磁碟（且 .gitignore 有對應規則），
    是資料不是介面文字。"""
    seen = []

    def _fake_extract(video, start, duration, out_path):
        seen.append(os.path.basename(out_path))
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("")

    monkeypatch.setattr(translator, "extract_audio_segment", _fake_extract)
    monkeypatch.setattr(translator, "translate_segment",
                        lambda *a, **k: SEG0)

    app, _, _ = app_factory(lang)
    app._video_path = str(tmp_path / "v.mp4")
    app._segment_offsets = {0: 0, 1: 1800}
    app._run_segments([0, 1], 2)

    assert seen == ["temp_seg_0.mp3", "temp_seg_1.mp3"]
    # 跑完要清乾淨
    leftovers = [n for n in os.listdir(gui.SCRIPT_DIR) if n.startswith("temp_seg_")]
    assert not leftovers, f"暫存音訊沒清掉：{leftovers}"


@pytest.mark.parametrize("lang", LANGS)
def test_srt_format_helpers_are_language_independent(lang):
    """SRT 的時間碼格式與 `-->` 分隔符是規格，不是介面文字。"""
    i18n.set_lang(lang)
    try:
        assert translator.renumber_srt("7\nx\n9\ny") == "1\nx\n2\ny"
        assert translator.enforce_max_duration(
            "00:00:00,000 --> 00:00:30,000") == "00:00:00,000 --> 00:00:05,000"
        assert translator.fix_srt_format(
            "00:00:01,000 --> 00:00:02,000", 60) == \
            "00:01:01,000 --> 00:01:02,000"
    finally:
        i18n.set_lang("zh_tw")


@pytest.mark.parametrize("lang", LANGS)
def test_ffmpeg_arguments_are_language_independent(lang, monkeypatch, tmp_path):
    """餵給 ffmpeg / ffprobe 的參數翻了會直接失敗。"""
    i18n.set_lang(lang)
    captured = []

    class _Result:
        stdout = b"12.5"

    monkeypatch.setattr(translator.subprocess, "run",
                        lambda cmd, **k: captured.append(cmd) or _Result())
    try:
        translator.get_video_duration("in.mp4")
        assert captured[0] == [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", "in.mp4"]

        out = str(tmp_path / f"a_{lang}.mp3")
        with open(out, "w", encoding="utf-8") as f:
            f.write("")
        translator.extract_audio_segment("in.mp4", 0, 1800, out)
        assert captured[1] == [
            "ffmpeg", "-ss", "0", "-t", "1800",
            "-i", "in.mp4", "-vn", "-acodec", "libmp3lame", "-y", out]
    finally:
        i18n.set_lang("zh_tw")
