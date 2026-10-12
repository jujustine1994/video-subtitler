"""Run an opt-in cloud smoke test. Never print keys or HTTP request headers."""
import argparse
import json
import sys
import subprocess
import tempfile
import httpx
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import dotenv_values
from src.groq_provider import GroqProvider, parse_response, GroqError, find_silences
from src.translator import _cues_to_srt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--model', default='whisper-large-v3')
    parser.add_argument('--case', choices=['sample', 'silence60'])
    parser.add_argument('--language', default='zh')
    parser.add_argument('--expected-term')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    key = dotenv_values(root / '.env').get('GROQ_API_KEY')
    if not key:
        raise RuntimeError('GROQ_API_KEY missing')
    provider = GroqProvider(key, args.model, language=args.language)
    reports = []
    target = root / 'validation_outputs'
    target.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='groq-validation-') as folder:
        for label, padding in [('sample', 0), ('silence60', 60)]:
            if args.case and label != args.case:
                continue
            audio = Path(folder) / f'{label}.flac'
            command = ['ffmpeg', '-v', 'error', '-y', '-ss', '7', '-t', '40',
                       '-i', args.source, '-vn', '-ar', '16000', '-ac', '1']
            if padding:
                command += ['-af', f'adelay={padding * 1000}:all=1']
            subprocess.run(command + ['-c:a', 'flac', str(audio)], check=True)
            with audio.open('rb') as stream, httpx.Client(timeout=600) as client:
                response = client.post(
                    'https://api.groq.com/openai/v1/audio/transcriptions',
                    headers={'Authorization': f'Bearer {key}'},
                    files={'file': (audio.name, stream, 'audio/flac')},
                    data={'model': args.model, 'response_format': 'verbose_json',
                          'timestamp_granularities[]': ['word', 'segment'], 'temperature': '0',
                          'language': args.language})
            if response.status_code != 200:
                raise GroqError(response.status_code)
            raw = response.json()
            (target / f'{label}.json').write_text(json.dumps(raw, ensure_ascii=False, indent=2),
                                                encoding='utf-8')
            cues = parse_response(raw, 0, 40 + padding, find_silences(audio, 40 + padding))
            translated = provider.translate(cues)
            (target / f'{label}.srt').write_text(_cues_to_srt(translated), encoding='utf-8')
            report = {'case': label, 'cues': len(cues),
                      'first_start': cues[0]['start'] if cues else None,
                      'last_end': cues[-1]['end'] if cues else None,
                      'injected_silence_cues': sum(c['start'] < padding - 1 for c in cues),
                      'contains_expected_term': any((args.expected_term or Path(args.source).stem)
                                                   in c['text'] for c in translated)}
            reports.append(report)
            print(json.dumps(report, ensure_ascii=True), flush=True)
    (target / 'report.json').write_text(json.dumps(reports, indent=2), encoding='utf-8')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Validation failed: {type(exc).__name__}, HTTP {getattr(exc, "code", "unknown")}',
              file=sys.stderr)
        if isinstance(exc, ValueError):
            print(str(exc), file=sys.stderr)
        sys.exit(1)
