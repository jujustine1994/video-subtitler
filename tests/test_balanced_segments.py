import pytest

from src import resume, translator


@pytest.mark.parametrize('duration,expected', [
    (6000, [(0,1500),(1500,1500),(3000,1500),(4500,1500)]),
    (3900, [(0,1300),(1300,1300),(2600,1300)]),
    (7200, [(0,1800),(1800,1800),(3600,1800),(5400,1800)]),
])
def test_new_jobs_balance_without_exceeding_target(duration, expected):
    assert resume.segment_plan({'identity': {'duration': duration,'chunk_seconds':1800},
                                'split_strategy': 'balanced'}) == expected


def test_old_checkpoint_keeps_fixed_boundaries():
    assert resume.segment_plan({'identity': {'duration':3900,'chunk_seconds':1800}}) == [
        (0,1800), (1800,1800), (3600,300)]


def test_new_plan_survives_restart_and_old_results_are_not_repartitioned(tmp_path, monkeypatch):
    monkeypatch.setattr(resume, 'INDEX_PATH', tmp_path/'index.json')
    source = tmp_path/'source.mp4'
    source.write_bytes(b'video')
    state = resume.create(source, 3900, 1800, 'model')
    assert resume.segment_plan(state) == [(0,1300),(1300,1300),(2600,1300)]
    restored = resume.load(source,3900,1800,'model')
    assert resume.segment_plan(restored) == [(0,1300),(1300,1300),(2600,1300)]
    state.pop('split_plan')
    state.pop('split_strategy')
    resume.record_segment(source, state, 0, 'old subtitle')
    restored = resume.load(source,3900,1800,'model')
    assert resume.segment_plan(restored) == [(0,1800),(1800,1800),(3600,300)]
    assert restored['segments']['0'] == 'old subtitle'


def test_balanced_plan_covers_fractional_duration_without_gaps():
    state = {'identity':{'duration':5663.559578,'chunk_seconds':1800}, 'split_strategy':'balanced'}
    plan = resume.segment_plan(state)
    assert len(plan) == 4
    assert sum(length for start,length in plan) == pytest.approx(5663.559578)
    assert all(length <= 1800 for start,length in plan)
    assert all(a+length == pytest.approx(b) for (a,length),(b,_) in zip(plan,plan[1:]))


def test_duplicate_word_times_do_not_fail_entire_segment():
    words = [{'text':'one.', 'start':1.0, 'end':2.0},
             {'text':'two.', 'start':1.0, 'end':2.0},
             {'text':'three.', 'start':2.0, 'end':3.0}]
    cues = translator._source_cues(words, 1800)
    assert len(cues) == 2
    assert cues[0]['text'] == 'one. two.'
    assert all(a['end'] <= b['start'] for a,b in zip(cues,cues[1:]))


def test_all_failed_does_not_overwrite_existing_subtitle(app_factory, tmp_path):
    app, _, _ = app_factory('zh_tw')
    video = tmp_path / 'failed.mp4'
    video.write_bytes(b'video')
    subtitle = video.with_suffix('.srt')
    subtitle.write_text('existing',encoding='utf-8')
    app._video_path = str(video)
    app._segments = {0:None,1:None}
    app._finish_run()
    assert subtitle.read_text(encoding='utf-8') == 'existing'
