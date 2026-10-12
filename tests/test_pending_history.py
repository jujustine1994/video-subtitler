from src import gui, resume, translator


def test_history_retains_missing_source_and_recovers_when_restored(tmp_path, monkeypatch):
    monkeypatch.setattr(resume, 'INDEX_PATH', tmp_path / 'index.json')
    video = tmp_path / 'missing.mp4'
    video.write_bytes(b'media')
    state = resume.create(video, 3600, 1800, translator.MODEL_NAME)
    parked = tmp_path / 'parked.mp4'
    video.rename(parked)
    jobs = resume.pending_jobs(None, include_unavailable=True)
    assert jobs[0]['status'] == 'missing'
    assert jobs[0]['total'] == 2
    assert resume.checkpoint_path(video).exists()
    parked.rename(video)
    assert resume.pending_jobs(None, include_unavailable=True)[0]['status'] == 'ready'
    resume.discard(video, state['identity']['model'])
    assert resume.pending_jobs(None, include_unavailable=True) == []


def test_history_lists_all_and_resume_restores_selected_settings(app_factory, tmp_path, monkeypatch):
    monkeypatch.setattr(resume, 'INDEX_PATH', tmp_path / 'index.json')
    for name, model, chunk in [('a', translator.MODEL_NAME, 1800),
                               ('b', 'groq:whisper-large-v3:ja:zh-TW:v1', 600)]:
        video = tmp_path / f'{name}.mp4'
        video.write_bytes(b'media')
        resume.create(video, 3600, chunk, model)
    app, _, _ = app_factory('zh_tw')
    app._refresh_pending_jobs()
    assert len(app.pending_tree.get_children()) == 2
    row = next(key for key, job in app._pending_jobs.items() if job['path'].endswith('b.mp4'))
    app.pending_tree.selection_set(row)
    starts = []
    monkeypatch.setattr(app, '_start', lambda: starts.append(app.file_var.get()))
    app._resume_pending_job()
    assert starts == [str(tmp_path / 'b.mp4')]
    assert app.provider_var.get() == 'Groq'
    assert app.groq_model_var.get() == 'whisper-large-v3'
    assert app.audio_language_var.get() == 'ja'
    assert app.chunk_var.get() == '10'
    app.is_running = True
    app._resume_pending_job()
    assert len(starts) == 1


def test_startup_only_populates_history_without_api(app_factory, monkeypatch):
    monkeypatch.setattr(resume, 'pending_jobs', lambda *a, **k: [])
    app, _, _ = app_factory('zh_tw')
    monkeypatch.setattr(app, '_start', lambda: (_ for _ in ()).throw(AssertionError('API start')))
    app._offer_pending_resume()
    assert app.pending_tree.get_children() == ()


def test_missing_job_cannot_start_and_is_not_deleted(app_factory, tmp_path, monkeypatch):
    monkeypatch.setattr(resume, 'INDEX_PATH', tmp_path / 'index.json')
    video = tmp_path / 'offline.mp4'
    video.write_bytes(b'media')
    resume.create(video, 3600, 1800, translator.MODEL_NAME)
    video.rename(tmp_path / 'offline-parked.mp4')
    app, _, _ = app_factory('zh_tw')
    app._refresh_pending_jobs()
    app.pending_tree.selection_set('0')
    warnings = []
    monkeypatch.setattr(gui.messagebox, 'showwarning', lambda *a: warnings.append(a))
    monkeypatch.setattr(app, '_start', lambda: (_ for _ in ()).throw(AssertionError('API start')))
    app._resume_pending_job()
    assert len(warnings) == 1
    assert len(app.pending_tree.get_children()) == 1
    assert resume.checkpoint_path(video).exists()


def test_changed_job_is_blocked_and_completion_refresh_removes_job(app_factory, tmp_path, monkeypatch):
    monkeypatch.setattr(resume, 'INDEX_PATH', tmp_path / 'index.json')
    video = tmp_path / 'modified.mp4'
    video.write_bytes(b'media')
    resume.create(video, 3600, 1800, translator.MODEL_NAME)
    video.write_bytes(b'different media')
    assert resume.pending_jobs(None, include_unavailable=True)[0]['status'] == 'changed'
    app, _, _ = app_factory('zh_tw')
    app._refresh_pending_jobs()
    assert len(app.pending_tree.get_children()) == 1
    resume.discard(video, translator.MODEL_NAME)
    app._done(None, [])
    app._poll_queue()
    assert app.pending_tree.get_children() == ()
