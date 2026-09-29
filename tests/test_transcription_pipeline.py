from types import SimpleNamespace

import pytest

from src import translator


def _interaction(*annotations):
    content = SimpleNamespace(annotations=list(annotations))
    step = SimpleNamespace(content=[content])
    return SimpleNamespace(steps=[step])


def _word(text, start, end):
    return SimpleNamespace(type="word_info", text=text, start_offset=start, end_offset=end)


def test_word_annotations_drive_cues_and_absolute_timestamps():
    words = translator._extract_words(_interaction(
        _word("你", "0.100s", "0.300s"),
        _word("好", "0.310s", "0.500s"),
        _word("。", "0.510s", "0.600s"),
    ))
    cues = translator._source_cues(words, 1800)

    assert cues == [{"start": 1800.1, "end": 1800.6, "text": "你好。"}]
    assert "00:30:00,100 --> 00:30:00,600" in translator._cues_to_srt(cues)


def test_missing_word_timing_refuses_to_write_subtitles():
    with pytest.raises(ValueError, match="invalid word timestamp"):
        translator._extract_words(_interaction(_word("hello", "", "0.5s")))


def test_cue_normalisation_rejects_zero_duration_and_overlap():
    words = translator._extract_words(_interaction(
        _word("甲", "0.000s", "0.100s"),
        _word("。", "0.100s", "0.100s"),
        _word("乙", "0.200s", "0.300s"),
    ))
    cues = translator._source_cues(words, 0)
    assert all(cue["end"] > cue["start"] for cue in cues)
    assert all(a["end"] <= b["start"] for a, b in zip(cues, cues[1:]))


def test_translation_cannot_change_cue_timing():
    class _Response:
        text = '{"translations": [{"id": 0, "text": "測試字幕"}]}'

    class _Models:
        def generate_content(self, **kwargs):
            assert kwargs["model"] == translator.TRANSLATION_MODEL_NAME
            return _Response()

    cues = [{"start": 1.2, "end": 2.3, "text": "test subtitle"}]
    result = translator._translate_cues(SimpleNamespace(models=_Models()), cues, "繁體中文")

    assert result == [{"start": 1.2, "end": 2.3, "text": "測試字幕"}]
