import threading

import pytest

from src import resume, translator
from src import gui


def test_translation_failure_keeps_transcript_across_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(resume, 'INDEX_PATH', tmp_path / 'index.json')
    video = tmp_path / 'video.mp3'
    video.write_bytes(b'audio')
    state = resume.create(video, 12, 1800, translator.MODEL_NAME)
    cues = [{'start': 1.0, 'end': 2.0, 'text': 'hello'}]
    monkeypatch.setattr(translator, 'transcribe_segment', lambda *a, **k: cues)
    def fail(*args):
        raise RuntimeError('quota exhausted')
    monkeypatch.setattr(translator, '_translate_cues', fail)
    with pytest.raises(RuntimeError):
        translator.process_saved_segment(None, video, 'sample.mp3', 0, 0, state)
    restored = resume.load(video, 12, 1800, translator.MODEL_NAME)
    def never_transcribe(*args, **kwargs):
        pytest.fail('saved transcript was retranscribed')
    monkeypatch.setattr(translator, 'transcribe_segment', never_transcribe)
    monkeypatch.setattr(translator, '_translate_cues', lambda client, cues, lang: [
        {**cues[0], 'text': '你好'}])
    result = translator.process_saved_segment(None, video, 'sample.mp3', 0, 0, restored)
    assert '你好' in result
    assert restored['transcripts']['0'][0]['text'] == 'hello'


def test_stop_after_asr_saves_before_translation(tmp_path, monkeypatch):
    monkeypatch.setattr(resume, 'INDEX_PATH', tmp_path / 'index.json')
    video = tmp_path / 'v.mp3'
    video.write_bytes(b'audio')
    state = resume.create(video, 12, 1800, translator.MODEL_NAME)
    stop = threading.Event()
    def transcribe(*args):
        stop.set()
        return [{'start': 1, 'end': 2, 'text': 'hello'}]
    monkeypatch.setattr(translator, 'transcribe_segment', transcribe)
    with pytest.raises(translator.StopRequested):
        translator.process_saved_segment(None, video, 'a.mp3', 0, 0, state, stop)
    assert resume.load(video, 12, 1800, translator.MODEL_NAME)['transcripts']['0'][0]['text'] == 'hello'


def test_close_waits_for_saved_worker_result(app_factory, monkeypatch):
    app, win, _ = app_factory('zh_tw')
    app.is_running = True
    monkeypatch.setattr(gui.messagebox, 'askyesno', lambda *a, **k: True)
    app._on_close()
    assert win.winfo_exists()
    assert app._stop_event.is_set()
    assert app._close_pending
    app._done(None, [])
    app._poll_queue()
    assert not win.winfo_exists()


def test_cancel_close_keeps_processing(app_factory, monkeypatch):
    app, win, _ = app_factory('zh_tw')
    app.is_running = True
    monkeypatch.setattr(gui.messagebox, 'askyesno', lambda *a, **k: False)
    app._on_close()
    assert win.winfo_exists()
    assert not app._stop_event.is_set()


def test_old_checkpoint_remains_usable(tmp_path, monkeypatch):
    monkeypatch.setattr(resume, 'INDEX_PATH', tmp_path / 'index.json')
    video = tmp_path / 'old.mp3'
    video.write_bytes(b'audio')
    state = resume.create(video, 12, 1800, translator.MODEL_NAME)
    state.pop('transcripts')
    resume.record_segment(video, state, 0, 'old subtitle')
    restored = resume.load(video, 12, 1800, translator.MODEL_NAME)
    assert translator.process_saved_segment(None, video, None, 0, 0, restored) == 'old subtitle'
