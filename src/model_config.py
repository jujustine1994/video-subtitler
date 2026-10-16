"""Stage settings independent from durable checkpoint identity."""
import re
import tempfile
from pathlib import Path
from . import translator, resume, prompts
from .errors import reason_error

# Preferred defaults only; the real choices come from the account's model list.
TRANSLATION_MODELS = (translator.TRANSLATION_MODEL_NAME, 'gemini-3.6-flash')
# Stable text models only: excludes -tts / -image / -live / -preview variants.
_TRANSLATION_PATTERN = re.compile(r'^gemini-(\d+(?:\.\d+)?)-flash(-lite)?$')


class ModelUnavailable(RuntimeError):
    def __init__(self, model):
        self.model = model
        self.subtitler_reason = f'model_unavailable ({model})'
        super().__init__(self.subtitler_reason)


def is_translation_model(name):
    return bool(_TRANSLATION_PATTERN.match(name or ''))


def available_models(client):
    """Names usable with generateContent; API errors propagate (bad key, network)."""
    names = set()
    for model in client.models.list():
        actions = getattr(model, 'supported_actions', None) or []
        if 'generateContent' in actions:
            names.add(model.name.removeprefix('models/'))
    return names


def translation_choices(available):
    defaults = [m for m in TRANSLATION_MODELS if m in available]

    def newest_first(name):
        version, lite = _TRANSLATION_PATTERN.match(name).groups()
        return tuple(-int(part) for part in version.split('.')), bool(lite)
    others = sorted((m for m in available if is_translation_model(m) and m not in defaults),
                    key=newest_first)
    return defaults + others


def resolve_models(client, provider, translation_model):
    """Check every Gemini model this run needs before any upload.

    ASR is a dedicated model and is never swapped; a retired translation model
    falls back to the first available choice. Returns (chosen, choices).
    """
    available = available_models(client)
    if provider == 'Gemini' and translator.ASR_MODEL_NAME not in available:
        raise ModelUnavailable(translator.ASR_MODEL_NAME)
    choices = translation_choices(available)
    if not choices:
        raise ModelUnavailable(translation_model)
    return (translation_model if translation_model in choices else choices[0]), choices


def processing_settings(client):
    return {'provider': 'Groq' if client.identity.startswith('groq:') else 'Gemini',
            'model': client.model, 'language': client.language,
            'translation_model': client.translation_model}


def translation_cache(state, index, model):
    if model == translator.TRANSLATION_MODEL_NAME:
        return state.setdefault('translation_batches', {}).setdefault(str(index), {})
    return state.setdefault('translation_models', {}).setdefault(model, {}).setdefault(str(index), {})


def translate_saved(client, cues, model, source, state, index, stop_event):
    if client is None:
        raise reason_error('missing_translation_key')
    return translator._translate_cues(
        client, cues, prompts.DEFAULT_TARGET_LANGUAGE,
        batch_cache=translation_cache(state, index, model) if state is not None else None,
        on_batch_saved=(lambda: resume.save(source, state)) if state is not None else None,
        stop_event=stop_event, model=model)


class GeminiProvider:
    def __init__(self, client, translation_model=translator.TRANSLATION_MODEL_NAME, language='auto'):
        if not is_translation_model(translation_model):
            raise ValueError('Unsupported translation model')
        self.client = client
        self.translation_model = translation_model
        self.model = translator.ASR_MODEL_NAME
        self.language = language
        self.identity = translator.MODEL_NAME

    def transcribe_saved(self, source, index, offset, duration, state, stop_event):
        with tempfile.TemporaryDirectory(prefix='subtitler-gemini-') as folder:
            audio = Path(folder) / 'speech.mp3'
            translator.extract_audio_segment(source, offset, duration, str(audio))
            if stop_event is not None and stop_event.is_set():
                raise translator.StopRequested()
            return translator.transcribe_segment(self.client, str(audio), offset)

    def translate(self, cues, source=None, state=None, index=None, stop_event=None):
        return translate_saved(self.client, cues, self.translation_model, source, state, index, stop_event)
