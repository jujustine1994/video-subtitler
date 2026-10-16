from types import SimpleNamespace
import pytest
from src import model_config, translator
from src.errors import classify_error


def fake_client(*names, actions=('generateContent',)):
    models = [SimpleNamespace(name='models/' + n, supported_actions=list(actions)) for n in names]
    return SimpleNamespace(models=SimpleNamespace(list=lambda: iter(models)))


def test_choices_keep_defaults_first_then_newer_flash_models():
    client = fake_client('gemini-3.8-flash', 'gemini-3.5-flash-lite', 'gemini-3.6-flash',
                         'gemini-3.8-flash-tts', 'gemini-3.1-flash-lite-preview',
                         'gemini-3.1-flash-image', 'gemini-3.7-flash')
    choices = model_config.translation_choices(model_config.available_models(client))
    assert choices == ['gemini-3.5-flash-lite', 'gemini-3.6-flash',
                       'gemini-3.8-flash', 'gemini-3.7-flash']


def test_retired_translation_model_switches_to_first_available():
    client = fake_client(translator.ASR_MODEL_NAME, 'gemini-3.8-flash')
    chosen, choices = model_config.resolve_models(client, 'Gemini', 'gemini-3.5-flash-lite')
    assert chosen == 'gemini-3.8-flash'
    assert choices == ['gemini-3.8-flash']


def test_missing_asr_model_fails_before_any_upload():
    client = fake_client('gemini-3.5-flash-lite')
    with pytest.raises(model_config.ModelUnavailable) as caught:
        model_config.resolve_models(client, 'Gemini', 'gemini-3.5-flash-lite')
    assert classify_error(caught.value) == 'model_unavailable'
    assert translator.ASR_MODEL_NAME in translator._safe_err(caught.value)


def test_groq_does_not_require_gemini_asr_model():
    client = fake_client('gemini-3.5-flash-lite')
    assert model_config.resolve_models(client, 'Groq', 'gemini-3.5-flash-lite')[0] == 'gemini-3.5-flash-lite'


def test_no_translation_model_left_is_explicit():
    with pytest.raises(model_config.ModelUnavailable):
        model_config.resolve_models(fake_client(translator.ASR_MODEL_NAME), 'Gemini', 'gemini-3.5-flash-lite')


def test_providers_accept_dynamic_translation_model():
    from src.groq_provider import GroqProvider
    assert model_config.GeminiProvider(None, 'gemini-3.8-flash').translation_model == 'gemini-3.8-flash'
    assert GroqProvider('k', 'whisper-large-v3', None, 'ja', 'gemini-3.8-flash').translation_model == 'gemini-3.8-flash'
    with pytest.raises(ValueError):
        model_config.GeminiProvider(None, 'gemini-3.8-flash-tts')
