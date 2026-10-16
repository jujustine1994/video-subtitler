from types import SimpleNamespace
import threading
import pytest
from src import resume, translator


def test_translation_cache_isolated_and_legacy_retained():
    from src.model_config import translation_cache
    state = {'translation_batches': {'0': {'0:1': ['old']}}}
    assert translation_cache(state, 0, translator.TRANSLATION_MODEL_NAME)['0:1'] == ['old']
    assert translation_cache(state, 0, 'gemini-3.6-flash') == {}
    assert state['translation_batches']['0']['0:1'] == ['old']


def test_switch_only_failed_segment_keeps_original_checkpoint(tmp_path, monkeypatch):
    from src.model_config import GeminiProvider
    monkeypatch.setattr(resume, 'INDEX_PATH', tmp_path/'index.json')
    source = tmp_path/'source.mp4'
    source.write_bytes(b'media')
    state = resume.create(source, 1200, 600, 'groq:whisper-large-v3:ja:zh-TW:v1')
    resume.record_segment(source, state, 1, 'already done')
    resume.record_transcript(source, state, 0, [{'start': 1, 'end': 2, 'text': 'original'}])
    def generate(**kwargs):
        assert kwargs['model'] == 'gemini-3.6-flash'
        return SimpleNamespace(text='{"translations":[{"id":0,"text":"translated"}]}')
    provider = GeminiProvider(SimpleNamespace(models=SimpleNamespace(generate_content=generate)),
                              'gemini-3.6-flash')
    result = translator.process_saved_segment(provider, source, None, 0, 0, state, threading.Event())
    assert 'translated' in result
    restored = resume.load_existing(source, 1200, state['identity']['model'])
    assert restored['segments']['1'] == 'already done'
    assert restored['transcripts']['0'][0]['text'] == 'original'
    assert restored['segment_models']['0']['translation'] == 'gemini-3.6-flash'
    assert restored['identity']['model'].startswith('groq:')


@pytest.mark.parametrize('finish,reason', [('MAX_TOKENS','output_truncated'),('SAFETY','content_blocked')])
def test_translation_finish_reason_is_safe_and_explicit(finish, reason):
    response = SimpleNamespace(text=None,candidates=[SimpleNamespace(finish_reason=finish)])
    client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **k: response))
    with pytest.raises(RuntimeError) as caught:
        translator._translate_batch(client,[{'start':0,'end':1,'text':'x'}],'zh')
    assert caught.value.subtitler_reason == reason


def test_malformed_json_reason_does_not_expose_response():
    client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **k: SimpleNamespace(text='gsk_fake_secret')))
    with pytest.raises(RuntimeError) as caught:
        translator._translate_batch(client,[{'start':0,'end':1,'text':'x'}],'zh')
    assert caught.value.subtitler_reason == 'invalid_translation_response'
    assert 'secret' not in translator._safe_err(caught.value)


def test_new_asr_model_does_not_reuse_old_raw_response(tmp_path, monkeypatch):
    from src.groq_provider import GroqProvider
    from src import groq_provider
    monkeypatch.setattr(resume,'INDEX_PATH',tmp_path/'index.json')
    source=tmp_path/'s.mp4';source.write_bytes(b'media')
    old=GroqProvider('fake','whisper-large-v3',language='ja')
    new=GroqProvider('fake','whisper-large-v3-turbo',language='ja')
    state=resume.create(source,10,600,old.identity)
    state['groq_responses']={'0':{'0.000000:10.000000':{'text':'old raw'}}}
    monkeypatch.setattr(groq_provider,'transcribe_bounded',lambda *a,**k:[])
    new.transcribe_saved(source,0,0,10,state,threading.Event())
    assert new._response_cache == {}
    assert state['groq_responses']['0']['0.000000:10.000000']['text']=='old raw'


def test_reused_original_keeps_original_transcription_provenance(tmp_path,monkeypatch):
    from src.model_config import GeminiProvider
    monkeypatch.setattr(resume,'INDEX_PATH',tmp_path/'index.json')
    source=tmp_path/'s.mp4';source.write_bytes(b'media')
    original='groq:whisper-large-v3:ja:zh-TW:v1'
    state=resume.create(source,10,600,original)
    resume.record_transcript(source,state,0,[{'start':1,'end':2,'text':'hi'}])
    client=SimpleNamespace(models=SimpleNamespace(generate_content=lambda **k:SimpleNamespace(text='{"translations":[{"id":0,"text":"new"}]}')))
    translator.process_saved_segment(GeminiProvider(client),source,None,0,0,state)
    assert state['segment_models']['0']['transcription']==original


def test_known_invalid_timestamp_categories_are_not_unknown():
    from src.errors import classify_error
    error=RuntimeError('duration')
    error.subtitler_reason='non_positive_duration'
    assert classify_error(error)=='invalid_timestamps'
    with pytest.raises(ValueError) as caught:
        translator._offset_seconds('not-a-timestamp')
    assert classify_error(caught.value)=='invalid_timestamps'
