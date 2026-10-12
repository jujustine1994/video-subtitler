import re

from src import translator


def test_long_cue_splits_at_punctuation_and_preserves_content_and_range():
    text = '甲' * 18 + '，' + '乙' * 18 + '。'
    source = f'1\n00:00:10,000 --> 00:00:20,000\n{text}\n'
    result = translator.split_long_subtitles(source)
    blocks = result.strip().split('\n\n')
    assert len(blocks) == 2
    assert blocks[0].splitlines()[2] == '甲' * 18 + '，'
    assert ''.join(b.splitlines()[2] for b in blocks) == text
    assert '00:00:10,000 --> 00:00:15,000' in blocks[0]
    assert '00:00:15,000 --> 00:00:20,000' in blocks[1]


def test_short_cue_is_not_padded_or_split():
    source = '1\n00:00:01,000 --> 00:00:02,000\n好。\n'
    assert translator.split_long_subtitles(source) == source


def test_without_punctuation_hard_limit_and_positive_millisecond_ranges():
    source = '1\n00:00:00,000 --> 00:00:00,003\n' + '甲' * 61
    result = translator.split_long_subtitles(source)
    blocks = result.strip().split('\n\n')
    assert [len(b.splitlines()[2]) for b in blocks] == [30, 30, 1]
    assert len(re.findall('-->', result)) == 3
    assert '00:00:00,002 --> 00:00:00,003' in result


def test_impossibly_short_cue_rejects_without_losing_text():
    import pytest
    source = '1\n00:00:00,000 --> 00:00:00,001\n' + '甲' * 61
    with pytest.raises(ValueError):
        translator.split_long_subtitles(source)
