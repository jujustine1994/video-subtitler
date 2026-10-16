import pytest
from src import gui, resume, translator


def test_new_app_overrides_old_thirty_minute_preference(app_factory):
    app, _, _ = app_factory('zh_tw')
    assert app.chunk_var.get() == '10'
    app._open_settings()
    assert tuple(app.chunk_box['values']) == ('10',)
    state = {'identity': {'duration': 7304, 'chunk_seconds': translator.CHUNK_DURATION},
             'split_strategy': 'balanced'}
    plan = resume.segment_plan(state)
    assert len(plan) == 13
    assert max(length for start, length in plan) <= 600


@pytest.mark.parametrize('outcome', ['success', 'error', 'stop'])
def test_gemini_audio_temp_is_removed_on_all_exits(app_factory, tmp_path, monkeypatch, outcome):
    app, _, _ = app_factory('zh_tw')
    app._client = object()
    app._video_path = str(tmp_path / 'source.mp4')
    app._segment_offsets = {0: 0}
    created = []
    def extract(source, start, duration, path):
        from pathlib import Path
        p = Path(path)
        p.write_bytes(b'audio')
        created.append(p)
    def translate(*a, **k):
        if outcome == 'error':
            raise RuntimeError('test failure')
        if outcome == 'stop':
            raise translator.StopRequested()
        return 'subtitle'
    monkeypatch.setattr(translator, 'extract_audio_segment', extract)
    monkeypatch.setattr(translator, 'translate_segment', translate)
    try:
        app._run_segments([0], 1)
    except translator.StopRequested:
        assert outcome == 'stop'
    assert created
    assert not created[0].exists()
    assert not created[0].parent.exists()


def test_existing_checkpoint_keeps_old_boundaries(tmp_path, monkeypatch):
    monkeypatch.setattr(resume, 'INDEX_PATH', tmp_path / 'index.json')
    source = tmp_path / 'video.mp4'
    source.write_bytes(b'media')
    state = resume.create(source, 7304, 1800, translator.MODEL_NAME)
    resume.record_segment(source, state, 0, 'completed')
    restored = resume.load_existing(source, 7304, translator.MODEL_NAME)
    assert restored['identity']['chunk_seconds'] == 1800
    assert resume.segment_plan(restored) == resume.segment_plan(state)
    assert restored['segments']['0'] == 'completed'


@pytest.mark.parametrize('outcome', ['success', 'error', 'stop'])
def test_groq_temp_directory_is_removed_on_all_exits(tmp_path, monkeypatch, outcome):
    from pathlib import Path
    import threading
    from src import groq_provider
    monkeypatch.setattr(resume, 'INDEX_PATH', tmp_path / 'index.json')
    source = tmp_path / 'source.mp4'
    source.write_bytes(b'media')
    provider = groq_provider.GroqProvider('unused', 'whisper-large-v3')
    state = resume.create(source, 10, 600, provider.identity)
    created = []
    def run(command, **kwargs):
        path = Path(command[-1])
        path.write_bytes(b'audio')
        created.append(path)
    def recognize(*args):
        if outcome == 'error':
            raise RuntimeError('test failure')
        if outcome == 'stop':
            raise translator.StopRequested()
        return [{'start': 1, 'end': 2, 'text': 'hello'}]
    monkeypatch.setattr(groq_provider.subprocess, 'run', run)
    monkeypatch.setattr(provider, 'recognize', recognize)
    if outcome == 'success':
        provider.transcribe_saved(source, 0, 0, 10, state, threading.Event())
    else:
        with pytest.raises(translator.StopRequested if outcome == 'stop' else RuntimeError):
            provider.transcribe_saved(source, 0, 0, 10, state, threading.Event())
    assert created and not created[0].exists() and not created[0].parent.exists()
