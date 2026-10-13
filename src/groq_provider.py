"""Cloud-only Groq ASR; source coordinates remain absolute across silence and splits."""
import math
import subprocess
import tempfile
import re
from pathlib import Path

import httpx

MODELS = ('whisper-large-v3', 'whisper-large-v3-turbo')
MAX_BYTES = 24_000_000  # headroom below the documented 25 MB upload limit


class GroqError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(f'Groq HTTP {code}')


class TimestampError(ValueError):
    def __init__(self, start, end, duration):
        self.subtitler_reason = f'timestamp_out_of_range ({start}, {end}; limit {duration})'
        super().__init__(self.subtitler_reason)


def find_silences(path, duration):
    """Conservative -80 dB detector, not speech AI. Do not classify music as silence."""
    result = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(path),
                             '-af', 'silencedetect=noise=-80dB:d=1', '-f', 'null', '-'],
                            capture_output=True, text=True, check=True)
    intervals, start = [], None
    for kind, value in re.findall(r'silence_(start|end): ([0-9.]+)', result.stderr):
        if kind == 'start':
            start = float(value)
        elif start is not None:
            intervals.append((start, float(value)))
            start = None
    if start is not None:
        intervals.append((start, duration))
    return intervals


def audible_window(silences, duration):
    start, end = 0.0, duration
    for left, right in silences:
        if left <= 0.05:
            start = right
        if right >= duration - 0.05:
            end = left
    if start >= end:
        return None
    return max(0, start - 0.25), min(duration, end + 0.25)


def parse_response(data, offset, duration, silences=(), owned_start=None, owned_end=None):
    try:
        return _parse_word_response(data, offset, duration, silences, owned_start, owned_end)
    except (RuntimeError, ValueError, KeyError, TypeError) as word_error:
        segments = data.get('segments') if isinstance(data, dict) else None
        if not segments:
            raise
        # Keep each segment's original text and timestamps; never sort words into
        # a guessed chronology. This is the SAME API response, not another request.
        fallback = {'text': data.get('text', ''), 'words': [
            {'word': segment['text'], 'start': segment['start'], 'end': segment['end']}
            for segment in segments if str(segment.get('text', '')).strip()]}
        try:
            cues = _parse_word_response(fallback, offset, duration, silences, owned_start, owned_end)
        except (RuntimeError, ValueError, KeyError, TypeError) as segment_error:
            segment_error.subtitler_reason = 'word_and_segment_timestamps_invalid'
            raise segment_error from word_error
        for cue in cues:
            cue['timing_source'] = 'segment'
            from .translator import _safe_err
            cue['timing_fallback_reason'] = (
                getattr(word_error, 'subtitler_reason', None) or _safe_err(word_error))
        return cues


def _parse_word_response(data, offset, duration, silences=(), owned_start=None, owned_end=None):
    from .translator import _source_cues
    if not isinstance(data, dict) or not isinstance(data.get('text'), str):
        raise ValueError('Invalid Groq transcription response')
    words = data.get('words')
    if not words:
        if not data['text'].strip():
            return []
        error = ValueError('Groq returned text without requested word timestamps')
        error.subtitler_reason = 'missing_word_timestamps'
        raise error
    parsed = []
    for word in words:
        start, end = float(word['start']), float(word['end'])
        if not math.isfinite(start + end) or start < 0 or end < start or end > duration + 1:
            raise TimestampError(start, end, duration)
        if any(left <= start and end <= right for left, right in silences):
            continue
        for left, right in silences:
            if left <= start < right < end:
                start = right
            if start < left < end <= right:
                end = left
        midpoint = offset + (start + end) / 2
        if owned_start is not None and midpoint < owned_start:
            continue
        if owned_end is not None and midpoint >= owned_end:
            continue
        if owned_start is not None:
            start = max(start, owned_start - offset)
        if owned_end is not None:
            end = min(end, owned_end - offset)
        text = str(word['word']).strip()
        if text:
            parsed.append({'text': text, 'start': start, 'end': end})
    if any(b['start'] < a['start'] - 0.001 for a,b in zip(parsed, parsed[1:])):
        error = RuntimeError('non-monotonic word timestamps')
        error.subtitler_reason = 'non_monotonic_timestamps'
        raise error
    return _source_cues(parsed, offset)


def transcribe_bounded(source, start, duration, extract, recognize, temp_dir,
                       max_bytes=MAX_BYTES, stop_event=None, cache=None, save_piece=None):
    from .translator import StopRequested
    key = f'{start:.6f}:{duration:.6f}'
    if stop_event is not None and stop_event.is_set():
        raise StopRequested()
    if cache is not None and key in cache:
        return cache[key]
    path = Path(temp_dir) / f'{key.replace(":", "-")}.flac'
    try:
        extract(source, start, duration, path)
        if path.stat().st_size > max_bytes:
            if duration <= 1:
                raise ValueError('Audio exceeds upload limit even after splitting')
            half = duration / 2
            return (transcribe_bounded(source, start, half, extract, recognize, temp_dir,
                                      max_bytes, stop_event, cache, save_piece)
                    + transcribe_bounded(source, start + half, duration - half,
                                         extract, recognize, temp_dir, max_bytes,
                                         stop_event, cache, save_piece))
        if stop_event is not None and stop_event.is_set():
            raise StopRequested()
        cues = recognize(path, start, duration)
        if save_piece is not None:
            save_piece(key, cues)
        return cues
    finally:
        path.unlink(missing_ok=True)


class GroqProvider:
    def __init__(self, api_key, model, translation_client=None, language='auto'):
        if model not in MODELS:
            raise ValueError('Unsupported Groq model')
        self.api_key = api_key
        self.model = model
        self.translation_client = translation_client
        self.language = language
        self.identity = f'groq:{model}:{language}:zh-TW:v1'
        self.request_count = 0
        self.uploaded_seconds = 0.0
        self._response_cache = None
        self._save_response = None

    def recognize(self, path, start, duration, owned_start=None, owned_end=None):
        silences = find_silences(path, duration)
        window = audible_window(silences, duration)
        if window is None:
            return []
        left, right = window
        if left > 0 or right < duration:
            with tempfile.TemporaryDirectory(prefix='groq-trim-') as folder:
                trimmed = Path(folder) / 'speech.flac'
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(left),
                                '-t', str(right-left), '-i', str(path), '-c:a', 'flac', str(trimmed)],
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return self._recognize_audio(trimmed, start + left, right-left,
                                             owned_start, owned_end)
        return self._recognize_audio(path, start, duration, owned_start, owned_end)

    def _recognize_audio(self, path, start, duration, owned_start=None, owned_end=None):
        data = {'model': self.model, 'response_format': 'verbose_json',
                'timestamp_granularities[]': ['word', 'segment'], 'temperature': '0'}
        if self.language != 'auto':
            data['language'] = self.language
        cache_key = f'{start:.6f}:{duration:.6f}'
        raw = self._response_cache.get(cache_key) if self._response_cache is not None else None
        if raw is None:
            with path.open('rb') as audio, httpx.Client(timeout=600) as client:
                self.request_count += 1
                self.uploaded_seconds += duration
                response = client.post(
                    'https://api.groq.com/openai/v1/audio/transcriptions',
                    headers={'Authorization': f'Bearer {self.api_key}'},
                    files={'file': (path.name, audio, 'audio/flac')},
                    data=data,
                )
            if response.status_code != 200:
                raise GroqError(response.status_code)
            raw = response.json()
            if self._response_cache is not None:
                self._response_cache[cache_key] = raw
                if self._save_response is not None:
                    self._save_response()
        try:
            return parse_response(raw, start, duration, find_silences(path, duration),
                                  owned_start, owned_end)
        except Exception as exc:
            exc.subtitler_stage = 'timestamp_validation'
            raise

    def transcribe_saved(self, source, index, offset, duration, state, stop_event):
        from . import resume
        cache = state.setdefault('groq_parts', {}).setdefault(str(index), {})
        self._response_cache = state.setdefault('groq_responses', {}).setdefault(str(index), {})
        self._save_response = lambda: resume.save(source, state)

        def extract(source, start, length, out):
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(start),
                            '-t', str(length), '-i', str(source), '-vn', '-ar', '16000',
                            '-ac', '1', '-c:a', 'flac', str(out)],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        def save_piece(key, cues):
            cache[key] = cues
            resume.save(source, state)

        with tempfile.TemporaryDirectory(prefix='subtitler-groq-') as folder:
            start = max(0, offset - 1)
            end = min(state['identity']['duration'], offset + duration + 1)
            def recognize(path, part_start, part_duration):
                return self.recognize(path, part_start, part_duration, offset, offset + duration)
            return transcribe_bounded(source, start, end - start, extract, recognize,
                                     folder, stop_event=stop_event, cache=cache,
                                     save_piece=save_piece)

    def translate(self, cues, source=None, state=None, index=None, stop_event=None):
        from .translator import _translate_cues
        from .prompts import DEFAULT_TARGET_LANGUAGE
        from opencc import OpenCC
        if not cues:
            return []
        text = ''.join(c['text'] for c in cues)
        # Route predominantly Chinese speech to deterministic conversion, never rewrite it.
        cjk = sum(0x4e00 <= ord(ch) <= 0x9fff for ch in text)
        other_script = any(0x3040 <= ord(ch) <= 0x30ff or
                           0xac00 <= ord(ch) <= 0xd7af for ch in text)
        if self.language == 'zh' or (self.language == 'auto' and not other_script
                                    and cjk / max(1, sum(ch.isalpha() for ch in text)) >= 0.5):
            converter = OpenCC('s2twp')
            return [{**cue, 'text': converter.convert(cue['text'])} for cue in cues]
        if self.translation_client is None:
            raise RuntimeError('Gemini API key required for non-Chinese translation')
        if state is not None:
            from . import resume
            cache = state.setdefault('translation_batches', {}).setdefault(str(index), {})
            return _translate_cues(self.translation_client,cues,DEFAULT_TARGET_LANGUAGE,
                                   batch_cache=cache,on_batch_saved=lambda:resume.save(source,state),
                                   stop_event=stop_event)
        return _translate_cues(self.translation_client, cues, DEFAULT_TARGET_LANGUAGE)
