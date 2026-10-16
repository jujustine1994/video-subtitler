import threading
from types import SimpleNamespace
import pytest
from src import gui, resume, translator
from src.errors import classify_error


@pytest.mark.parametrize('code,reason', [(429,'quota'),(401,'authentication'),(403,'authentication'),
    (404,'model_unavailable'),(400,'invalid_request'),(503,'service_unavailable')])
def test_http_error_categories_do_not_expose_secret(code, reason):
    error = RuntimeError('https://example.test?key=gsk_fake_secret')
    error.code = code
    assert classify_error(error) == reason
    assert 'secret' not in translator._safe_err(error)


def test_selected_retry_rebuilds_client_preserves_completed_and_origin(app_factory,tmp_path,monkeypatch):
    monkeypatch.setattr(resume,'INDEX_PATH',tmp_path/'index.json')
    app,_,_ = app_factory('zh_tw')
    source=tmp_path/'video.mp4'; source.write_bytes(b'media')
    app._video_path=str(source)
    app.file_var.set(str(source))
    app._resume_state=resume.create(source,1200,600,translator.MODEL_NAME)
    resume.record_transcript(source,app._resume_state,0,[{'start':1,'end':2,'text':'hi'}])
    completed='1\n00:10:01,000 --> 00:10:02,000\nalready done\n'
    resume.record_segment(source,app._resume_state,1,completed)
    app._segments={0:None,1:completed}
    app._segment_offsets={0:0,1:600};app._segment_durations={0:600,1:600}
    app._show_failed_segments([0])
    app.translation_model_var.set('gemini-3.6-flash')
    app.api_var.set('fake');app.save_key_var.set(False)
    def generate(**kwargs):
        assert kwargs['model']=='gemini-3.6-flash'
        return SimpleNamespace(text='{"translations":[{"id":0,"text":"new"}]}')
    listed=[SimpleNamespace(name='models/'+n,supported_actions=['generateContent'])
            for n in (translator.ASR_MODEL_NAME,'gemini-3.6-flash')]
    monkeypatch.setattr(translator,'make_client',lambda key:SimpleNamespace(models=SimpleNamespace(
        generate_content=generate,list=lambda:listed)))
    monkeypatch.setattr(gui.threading,'Thread',lambda target,args=(),**k:SimpleNamespace(start=lambda:target(*args)))
    app._retry_selected()
    assert 'new' in app._segments[0]
    assert app._segments[1]==completed
    assert (tmp_path/'video.srt').exists()
    assert app._resume_state['identity']['model']==translator.MODEL_NAME
    assert app._resume_state['processing']['translation_model']=='gemini-3.6-flash'


def test_quota_stop_still_offers_unfinished_segments(app_factory,tmp_path,monkeypatch):
    monkeypatch.setattr(resume,'INDEX_PATH',tmp_path/'index.json')
    app,_,_=app_factory('zh_tw')
    source=tmp_path/'q.mp4';source.write_bytes(b'media')
    app._resume_state=resume.create(source,1200,600,translator.MODEL_NAME)
    app._done(None,[])
    app._poll_queue()
    assert set(app._failed_vars)=={0,1}


def test_success_action_uses_completed_source_not_new_selection(app_factory,tmp_path,monkeypatch):
    app,win,_=app_factory('zh_tw')
    source=tmp_path/'completed.mp4';source.write_bytes(b'media')
    output=tmp_path/'completed.srt';output.write_text('subtitle')
    app._video_path=str(source)
    monkeypatch.setattr(gui.messagebox,'showinfo',lambda *a,**k:None)
    app._done(str(output),[]);app._poll_queue()
    assert app.btn_open_source.winfo_manager()=='pack'
    app.file_var.set(str(tmp_path/'another.mp4'))
    opened=[];monkeypatch.setattr(gui.os,'startfile',lambda path:opened.append(path))
    app._open_completed_source()
    assert opened==[str(source)]
    app._done(str(output),[0]);app._poll_queue()
    assert not app.btn_open_source.winfo_manager()


def test_open_missing_source_is_safe(app_factory,tmp_path,monkeypatch):
    app,_,_=app_factory('zh_tw')
    app._completed_source=str(tmp_path/'missing.mp4')
    notices=[]
    monkeypatch.setattr(gui.messagebox,'showerror',lambda *a,**k:notices.append(a))
    app._open_completed_source()
    assert len(notices)==1


def test_failed_open_is_reported_without_raw_os_error(app_factory,tmp_path,monkeypatch):
    app,_,_=app_factory('zh_tw')
    source=tmp_path/'source.mp4';source.write_bytes(b'media')
    app._completed_source=str(source)
    def fail(path):
        raise OSError('secret details')
    monkeypatch.setattr(gui.os,'startfile',fail)
    notices=[]
    monkeypatch.setattr(gui.messagebox,'showerror',lambda *a:notices.append(a))
    app._open_completed_source()
    assert notices and 'secret' not in str(notices)


def test_failure_is_saved_with_safe_reason_and_models(app_factory,tmp_path,monkeypatch):
    from src.model_config import GeminiProvider
    monkeypatch.setattr(resume,'INDEX_PATH',tmp_path/'index.json')
    app,_,_=app_factory('zh_tw')
    source=tmp_path/'source.mp4';source.write_bytes(b'media')
    app._video_path=str(source)
    app._resume_state=resume.create(source,10,600,translator.MODEL_NAME)
    resume.record_transcript(source,app._resume_state,0,[{'start':1,'end':2,'text':'hi'}])
    app._segment_offsets={0:0};app._segment_durations={0:10}
    def fail(**kwargs):
        error=RuntimeError('https://x?key=secret');error.code=503;raise error
    app._client=GeminiProvider(SimpleNamespace(models=SimpleNamespace(generate_content=fail)))
    monkeypatch.setattr(translator,'RETRY_DELAYS',())
    app._run_segments([0],1)
    restored=resume.load_existing(source,10,translator.MODEL_NAME)
    assert restored['failures']['0']['reason']=='service_unavailable'
    assert restored['failures']['0']['stage']=='translation'
    assert 'secret' not in str(restored['failures'])


def test_history_restores_switched_settings_and_keeps_original_job(app_factory,tmp_path,monkeypatch):
    monkeypatch.setattr(resume,'INDEX_PATH',tmp_path/'index.json')
    source=tmp_path/'source.mp4';source.write_bytes(b'media')
    origin='groq:whisper-large-v3:ja:zh-TW:v1'
    state=resume.create(source,1200,600,origin)
    state['processing']={'provider':'Gemini','model':translator.ASR_MODEL_NAME,
                         'translation_model':'gemini-3.6-flash','language':'ja'}
    resume.save(source,state)
    app,_,_=app_factory('zh_tw')
    app._refresh_pending_jobs();app.pending_tree.selection_set('0')
    monkeypatch.setattr(app,'_start',lambda:None)
    app._resume_pending_job()
    assert app.provider_var.get()=='Gemini'
    assert app.translation_model_var.get()=='gemini-3.6-flash'
    assert app._pending_origin==(str(source),origin)


def test_busy_state_blocks_settings_and_double_retry(app_factory,monkeypatch):
    app,_,_=app_factory('zh_tw')
    app.is_running=True
    app._open_settings()
    app._retry_selected()
    assert not hasattr(app,'settings_win')


def test_safety_block_does_not_offer_model_bypass(app_factory,tmp_path,monkeypatch):
    monkeypatch.setattr(resume,'INDEX_PATH',tmp_path/'index.json')
    source=tmp_path/'s.mp4';source.write_bytes(b'media')
    app,_,_=app_factory('zh_tw');app._video_path=str(source)
    state=resume.create(source,10,600,translator.MODEL_NAME)
    state['failures']={'0':{'reason':'content_blocked'}}
    resume.save(source,state);app._resume_state=state;app._show_failed_segments([0])
    notices=[];monkeypatch.setattr(gui.messagebox,'showwarning',lambda *a:notices.append(a))
    monkeypatch.setattr(app,'_selected_client',lambda *a: (_ for _ in ()).throw(AssertionError('bypass')))
    app._retry_selected()
    assert notices and not app.is_running


def test_retry_subset_after_restart_does_not_discard_other_pending_progress(app_factory,tmp_path,monkeypatch):
    monkeypatch.setattr(resume,'INDEX_PATH',tmp_path/'index.json')
    source=tmp_path/'s.mp4';source.write_bytes(b'media')
    app,_,_=app_factory('zh_tw');app._video_path=str(source)
    app._model_identity=translator.MODEL_NAME
    state=resume.create(source,1200,600,translator.MODEL_NAME)
    subtitle='1\n00:00:01,000 --> 00:00:02,000\ndone\n'
    resume.record_segment(source,state,0,subtitle)
    app._resume_state=state;app._segments={0:subtitle}
    app._finish_run()
    assert resume.checkpoint_path(source).exists()
    assert resume.load_existing(source,1200,translator.MODEL_NAME)['segments']['0']==subtitle


def test_stop_saved_segment_is_included_in_final_export(app_factory,tmp_path,monkeypatch):
    monkeypatch.setattr(resume,'INDEX_PATH',tmp_path/'index.json')
    source=tmp_path/'s.mp4';source.write_bytes(b'media')
    app,_,_=app_factory('zh_tw');app._video_path=str(source);app._model_identity=translator.MODEL_NAME
    state=resume.create(source,1200,600,translator.MODEL_NAME)
    first='1\n00:00:01,000 --> 00:00:02,000\nfirst saved before stop\n'
    second='1\n00:10:01,000 --> 00:10:02,000\nsecond saved after retry\n'
    resume.record_segment(source,state,0,first);resume.record_segment(source,state,1,second)
    app._resume_state=state;app._segments={1:second}
    app._finish_run()
    result=(tmp_path/'s.srt').read_text(encoding='utf-8')
    assert 'first saved before stop' in result and 'second saved after retry' in result
    assert not resume.checkpoint_path(source).exists()


def test_history_locator_is_consumed_and_same_source_can_start_new_job(app_factory,tmp_path,monkeypatch):
    monkeypatch.setattr(resume,'INDEX_PATH',tmp_path/'index.json')
    source=tmp_path/'s.mp4';source.write_bytes(b'media')
    origin='groq:whisper-large-v3:ja:zh-TW:v1'
    state=resume.create(source,10,600,origin)
    resume.record_segment(source,state,0,'1\n00:00:01,000 --> 00:00:02,000\nold\n')
    app,_,_=app_factory('zh_tw');app._video_path=str(source)
    app._model_identity=translator.MODEL_NAME
    app._pending_origin=(str(source),origin)
    app._client=SimpleNamespace(identity=translator.MODEL_NAME,model=translator.ASR_MODEL_NAME,
        translation_model=translator.TRANSLATION_MODEL_NAME,language='ja',
        transcribe_saved=lambda *a:[{'start':1,'end':2,'text':'new'}],
        translate=lambda cues,**k:cues)
    monkeypatch.setattr(translator,'get_video_duration',lambda path:10)
    monkeypatch.setattr(app,'_prepare_models',lambda:None)
    app._worker_full_run()
    assert app._pending_origin is None
    assert not resume.checkpoint_path(source,origin).exists()
    app._model_identity=translator.MODEL_NAME
    app._worker_full_run()
    assert app._resume_state['identity']['model']==translator.MODEL_NAME
    assert 'new' in (tmp_path/'s.srt').read_text(encoding='utf-8')


def test_groq_foreign_audio_without_gemini_key_fails_before_checkpoint(app_factory,tmp_path,monkeypatch):
    from src.groq_provider import GroqProvider
    monkeypatch.setattr(resume,'INDEX_PATH',tmp_path/'index.json')
    source=tmp_path/'s.mp4';source.write_bytes(b'media')
    app,_,_=app_factory('zh_tw');app._video_path=str(source)
    app._client=GroqProvider('gsk_fake','whisper-large-v3',None,'ja')
    app._model_identity=app._client.identity
    monkeypatch.setattr(translator,'get_video_duration',lambda path:pytest.fail('must stop before media work'))
    app._worker_full_run()
    assert not resume.checkpoint_path(source,app._model_identity).exists()
    fatal=[data for kind,data in list(app.msg_queue.queue) if kind=='fatal']
    assert fatal and 'Gemini Key' in fatal[0]


def test_retired_translation_model_is_switched_and_dropdown_refreshed(app_factory):
    from src.model_config import GeminiProvider
    listed=[SimpleNamespace(name='models/'+n,supported_actions=['generateContent'])
            for n in (translator.ASR_MODEL_NAME,'gemini-3.8-flash')]
    app,_,_=app_factory('zh_tw')
    app._client=GeminiProvider(SimpleNamespace(models=SimpleNamespace(list=lambda:listed)),'gemini-3.6-flash')
    app._prepare_models()
    assert app._client.translation_model=='gemini-3.8-flash'
    assert ('translation_models',(['gemini-3.8-flash'],'gemini-3.8-flash')) in list(app.msg_queue.queue)
