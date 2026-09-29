from src import gui, resume


def test_checkpoint_round_trip_and_discard(tmp_path, monkeypatch):
    monkeypatch.setattr(resume, "INDEX_PATH", tmp_path / "index.json")
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"video")
    state = resume.create(video, 61.0, 1800, "test-model")
    resume.record_segment(video, state, 0, "1\n00:00:00,000 --> 00:00:01,000\nhello\n")

    loaded = resume.load(video, 61.0, 1800, "test-model")
    assert loaded is not None
    assert loaded["segments"] == {"0": "1\n00:00:00,000 --> 00:00:01,000\nhello\n"}

    resume.discard(video)
    assert resume.load(video, 61.0, 1800, "test-model") is None


def test_checkpoint_is_rejected_if_video_or_settings_changed(tmp_path, monkeypatch):
    monkeypatch.setattr(resume, "INDEX_PATH", tmp_path / "index.json")
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"video")
    state = resume.create(video, 61.0, 1800, "test-model")
    resume.record_segment(video, state, 0, "subtitle")

    assert resume.load(video, 61.0, 900, "test-model") is None
    assert resume.load(video, 61.0, 1800, "another-model") is None

    video.write_bytes(b"changed video")
    assert resume.load(video, 61.0, 1800, "test-model") is None


def test_pending_jobs_lists_only_valid_latest_checkpoints(tmp_path, monkeypatch):
    monkeypatch.setattr(resume, "INDEX_PATH", tmp_path / "index.json")
    first = tmp_path / "first.mp3"
    second = tmp_path / "second.mp3"
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    first_state = resume.create(first, 10.0, 1800, "model")
    resume.record_segment(first, first_state, 0, "one")
    second_state = resume.create(second, 10.0, 1800, "model")
    resume.record_segment(second, second_state, 0, "two")
    second.write_bytes(b"changed")

    jobs = resume.pending_jobs("model")
    assert [job["path"] for job in jobs] == [str(first)]
    assert jobs[0]["completed"] == 1


def test_resume_prompt_selects_the_confirmed_file(app_factory, monkeypatch, tmp_path):
    video = tmp_path / "resume-me.mp3"
    jobs = [{"path": str(video), "completed": 2, "updated_at": 1}]
    monkeypatch.setattr(gui.resume, "pending_jobs", lambda model: jobs)
    monkeypatch.setattr(gui.messagebox, "askyesno", lambda *args, **kwargs: True)

    app, _, _ = app_factory("zh_tw")
    app._offer_pending_resume()

    assert app.file_var.get() == str(video)
