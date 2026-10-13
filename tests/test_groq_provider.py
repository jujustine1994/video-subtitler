from types import SimpleNamespace

import pytest

from src import resume


def test_groq_timestamps_keep_long_silence_and_empty_is_valid():
    from src.groq_provider import parse_response
    data = {'text': 'hello', 'words': [{'word': 'hello', 'start': 590, 'end': 591}],
            'segments': [{'start': 590, 'end': 591, 'text': 'hello', 'no_speech_prob': 0.01}]}
    cues = parse_response(data, 1800, 1800)
    assert cues == [{'start': 2390.0, 'end': 2391.0, 'text': 'hello'}]
    assert parse_response({'text': '', 'words': [], 'segments': []}, 1800, 1800) == []
    with pytest.raises(ValueError):
        parse_response({'text': 'hello'}, 0, 10)


def test_size_split_preserves_origins_and_stays_below_limit(tmp_path):
    from src.groq_provider import transcribe_bounded
    origins = []
    def extract(source, start, duration, out):
        out.write_bytes(b'x' * int(duration * 10))
    def recognize(path, start, duration):
        origins.append((start, duration))
        return [{'start': start, 'end': start + 1, 'text': 'hi'}]
    cues = transcribe_bounded('source', 100, 20, extract, recognize, tmp_path, max_bytes=110)
    assert origins == [(100, 10.0), (110.0, 10.0)]
    assert [c['start'] for c in cues] == [100, 110]
    assert list(tmp_path.iterdir()) == []


def test_digital_silence_hallucinations_do_not_become_subtitles():
    from src.groq_provider import parse_response
    data = {'text': 'phantom hello', 'words': [
        {'word': 'phantom', 'start': 29, 'end': 59},
        {'word': 'hello', 'start': 60.5, 'end': 61}], 'segments': []}
    assert parse_response(data, 1800, 100, silences=[(0, 60)]) == [
        {'start': 1860.5, 'end': 1861.0, 'text': 'hello'}]


def test_provider_checkpoints_do_not_overwrite_each_other(tmp_path, monkeypatch):
    monkeypatch.setattr(resume, 'INDEX_PATH', tmp_path / 'index.json')
    source = tmp_path / 'video.mp4'
    source.write_bytes(b'video')
    gem = resume.create(source, 100, 1800, 'gemini-model')
    resume.record_segment(source, gem, 0, 'gem')
    groq = resume.create(source, 100, 1800, 'groq:whisper-large-v3')
    resume.record_segment(source, groq, 0, 'groq')
    assert resume.load(source, 100, 1800, 'gemini-model')['segments']['0'] == 'gem'
    assert resume.load(source, 100, 1800, 'groq:whisper-large-v3')['segments']['0'] == 'groq'


def test_overlap_word_ownership_does_not_repeat_boundary_words():
    from src.groq_provider import parse_response
    data = {'text': 'a b', 'words': [
        {'word': 'a', 'start': 0.2, 'end': 0.6},
        {'word': 'b', 'start': 1.2, 'end': 1.6}], 'segments': []}
    cues = parse_response(data, 1799, 3, owned_start=1800, owned_end=1802)
    assert cues == [{'start': 1800.2, 'end': 1800.6, 'text': 'b'}]


def test_chinese_conversion_works_without_gemini_key():
    from src.groq_provider import GroqProvider
    provider = GroqProvider('unused', 'whisper-large-v3', language='zh')
    assert provider.translate([{'start': 1, 'end': 2, 'text': '硅晶圆'}]) == [
        {'start': 1, 'end': 2, 'text': '矽晶圓'}]


def test_ui_exposes_manual_service_model_and_duration(app_factory):
    app, _, _ = app_factory('zh_tw')
    assert tuple(app.provider_box['values']) == ('Gemini', 'Groq')
    assert app.groq_model_var.get() == 'whisper-large-v3'
    assert app.chunk_var.get() == '30'


def test_service_switch_selects_recommended_model_without_sending_label(app_factory):
    app, win, _ = app_factory('zh_tw')
    assert app.groq_model_box.get() == 'gemini-3.5-transcribe（建議）'
    app.provider_var.set('Groq')
    app.provider_box.event_generate('<<ComboboxSelected>>')
    win.update()
    assert app.groq_model_box.get() == 'whisper-large-v3（建議）'
    app.groq_model_box.current(1)
    app.groq_model_box.event_generate('<<ComboboxSelected>>')
    win.update()
    assert app.groq_model_var.get() == 'whisper-large-v3-turbo'
    app.provider_var.set('Gemini')
    app.provider_box.event_generate('<<ComboboxSelected>>')
    win.update()
    assert tuple(app.groq_model_box['values']) == ('gemini-3.5-transcribe（建議）',)


def test_keys_and_advanced_options_live_in_settings(app_factory):
    app, win, _ = app_factory('zh_tw')
    def entries(widget):
        found = []
        for child in widget.winfo_children():
            if child.winfo_class() == 'TEntry':
                found.append(child)
            found.extend(entries(child))
        return found
    assert len(entries(win)) == 1  # only source file on the main screen
    app._open_settings()
    assert len(entries(app.settings_win)) == 2
    app.chunk_var.set('10')
    # Invoke the native close protocol, which has the same cancel semantics as the button.
    app.settings_win.tk.call(app.settings_win.protocol('WM_DELETE_WINDOW'))
    assert app.chunk_var.get() == '30'


def test_timestamp_diagnostic_is_numeric_and_no_request_secret():
    from src.groq_provider import parse_response
    from src.translator import _safe_err
    with pytest.raises(ValueError) as caught:
        parse_response({'text': 'x', 'words': [{'word':'x', 'start':1, 'end':90}]}, 0, 10)
    detail = _safe_err(caught.value)
    assert 'timestamp_out_of_range' in detail
    assert 'limit 10' in detail


def test_leading_trailing_silence_keeps_original_window_offsets():
    from src.groq_provider import audible_window
    assert audible_window([(0, 60), (90, 100)], 100) == (59.75, 90.25)
    assert audible_window([(0, 1800)], 1800) is None
    assert audible_window([], 40) == (0, 40)


def test_half_hour_of_digital_silence_needs_no_cloud_request(tmp_path, monkeypatch):
    from src import groq_provider
    provider = groq_provider.GroqProvider('unused', 'whisper-large-v3')
    monkeypatch.setattr(groq_provider, 'find_silences', lambda path, duration: [(0, duration)])
    assert provider.recognize(tmp_path / 'unused.flac', 3600, 1800) == []
    assert provider.request_count == 0
    assert provider.uploaded_seconds == 0


def test_reversed_word_times_use_valid_segment_times_without_reupload():
    from src.groq_provider import parse_response
    data = {'text':'one. two.', 'words':[
        {'word':'one.', 'start':4, 'end':5},
        {'word':'two.', 'start':1, 'end':2}],
        'segments':[{'start':1, 'end':5, 'text':'one. two.'}]}
    cues = parse_response(data, 3600, 10)
    assert cues[0]['start'] == 3601
    assert cues[0]['end'] == 3605
    assert cues[0]['text'] == 'one. two.'
    assert cues[0]['timing_source'] == 'segment'


def test_both_word_and_segment_times_invalid_still_refuse_output():
    from src.groq_provider import parse_response
    data = {'text':'bad', 'words':[{'word':'bad','start':20,'end':21}],
            'segments':[{'start':20,'end':21,'text':'bad'}]}
    with pytest.raises(ValueError):
        parse_response(data, 0, 10)


def test_fallback_exposes_word_failure_reason_without_text():
    from src.groq_provider import parse_response
    data = {'text': 'hi', 'words': [{'word': 'a', 'start': 2, 'end': 3},
                                   {'word': 'b', 'start': 1, 'end': 2}],
            'segments': [{'text': 'hi', 'start': 1, 'end': 3}]}
    cues = parse_response(data, 1800, 10)
    assert cues[0]['timing_fallback_reason'] == 'non_monotonic_timestamps'
    assert cues[0]['start'] == 1801


def test_segment_fallback_end_is_not_truncated_to_five_seconds(app_factory, tmp_path):
    app, _, _ = app_factory('zh_tw')
    app._video_path = str(tmp_path/'fallback.mp4')
    app._resume_state = {'segments': {}}
    app._segments = {0:'1\n00:00:01,000 --> 00:00:12,000\nlong dialogue\n'}
    app._merge_and_write()
    assert '00:00:12,000' in (tmp_path/'fallback.srt').read_text(encoding='utf8')


def test_parse_failure_reuses_saved_raw_response_instead_of_reupload(tmp_path, monkeypatch):
    from src import groq_provider
    from src.groq_provider import GroqProvider
    class Response:
        status_code = 200
        def json(self):
            return {'text':'bad','words':[{'word':'bad','start':20,'end':21}], 'segments':[]}
    class Client:
        def __init__(self, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, *args, **kwargs):
            return Response()
    monkeypatch.setattr(groq_provider.httpx, 'Client', Client)
    monkeypatch.setattr(groq_provider, 'find_silences', lambda *args: [])
    path = tmp_path/'audio.flac'
    path.write_bytes(b'audio')
    provider = GroqProvider('unused','whisper-large-v3')
    source = tmp_path/'source.mp4'
    source.write_bytes(b'source')
    monkeypatch.setattr(resume, 'INDEX_PATH', tmp_path/'index.json')
    state = resume.create(source,10,1800,provider.identity)
    provider._response_cache = state.setdefault('groq_responses', {}).setdefault('0', {})
    provider._save_response = lambda: resume.save(source, state)
    for _ in range(2):
        with pytest.raises(ValueError):
            provider.recognize(path,0,10)
    assert provider.request_count == 1
    restored = resume.load(source,10,1800,provider.identity)
    restarted = GroqProvider('unused','whisper-large-v3')
    restarted._response_cache = restored['groq_responses']['0']
    with pytest.raises(ValueError):
        restarted.recognize(path,0,10)
    assert restarted.request_count == 0
