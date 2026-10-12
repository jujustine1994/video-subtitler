"""Opt-in short real-API test through the app's Start/worker/queue/export flow."""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import gui, resume
from src.groq_provider import MODELS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--seconds', type=int, default=40)
    parser.add_argument('--padding', type=int, default=0)
    parser.add_argument('--language', default='zh')
    parser.add_argument('--model', choices=MODELS, default=MODELS[0])
    parser.add_argument('--timeline2h', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.seconds <= 120 or not 0 <= args.padding <= 90:
        raise ValueError('Short validation only: speech <=120s, padding <=90s')
    project = Path(__file__).resolve().parent.parent
    output = project / 'validation_outputs'
    output.mkdir(exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='workflow-', dir=output))
    clip = run / ('timeline2h.flac' if args.timeline2h else 'sample.mp3')
    command = ['ffmpeg', '-v', 'error', '-y', '-ss', '7', '-t', str(args.seconds),
               '-i', args.source, '-vn', '-ar', '16000', '-ac', '1']
    if args.padding:
        command += ['-af', f'adelay={args.padding*1000}:all=1']
    if args.timeline2h:
        command = ['ffmpeg', '-v', 'error', '-y', '-ss', '7', '-t', '40', '-i', args.source,
                   '-filter_complex',
                   'anullsrc=r=16000:cl=mono:d=7200[base];'
                   '[0:a]aresample=16000,aformat=channel_layouts=mono,asplit=2[a][b];'
                   '[a]adelay=1790000:all=1[a1];[b]adelay=5400000:all=1[b1];'
                   '[base][a1][b1]amix=inputs=3:duration=first:normalize=0[out]',
                   '-map', '[out]', '-c:a', 'flac', str(clip)]
        subprocess.run(command, check=True)
    else:
        subprocess.run(command + ['-c:a', 'libmp3lame', str(clip)], check=True)
    config = run / 'config.json'
    config.write_text('{"language":"zh_tw","theme":"light"}', encoding='utf-8')
    gui.CONFIG_PATH = str(config)
    resume.INDEX_PATH = run / 'index.json'
    # Only modal notifications are suppressed; all app processing remains real.
    gui.messagebox.showinfo = lambda *a, **k: None
    gui.messagebox.showerror = lambda *a, **k: None
    gui.messagebox.askyesno = lambda *a, **k: False
    window = tk.Tk()
    window.withdraw()
    app = gui.SubtitlerApp(window)
    app.provider_var.set('Groq')
    app.groq_model_var.set(args.model)
    app._refresh_model_choices()
    app.audio_language_var.set(args.language)
    app.save_key_var.set(False)
    app.file_var.set(str(clip))
    app._start()
    deadline = time.monotonic() + 600
    stopping = False
    while app.is_running and time.monotonic() < deadline:
        window.update()
        if args.timeline2h and not stopping and app._segments.get(0) is not None:
            app._request_stop()
            stopping = True
        time.sleep(0.05)
    window.update()
    prior_requests = 0
    prior_seconds = 0
    checkpoint_saved = False
    if args.timeline2h:
        checkpoint_saved = resume.checkpoint_path(clip, app._model_identity).exists()
        prior_requests = app._client.request_count
        prior_seconds = app._client.uploaded_seconds
        original_segment = app._segments.get(0)
        app._on_close()
        window = tk.Tk()
        window.withdraw()
        app = gui.SubtitlerApp(window)
        app.provider_var.set('Groq')
        app.groq_model_var.set(args.model)
        app._refresh_model_choices()
        app.audio_language_var.set(args.language)
        app.save_key_var.set(False)
        app.file_var.set(str(clip))
        app._start()
        deadline = time.monotonic() + 600
        while app.is_running and time.monotonic() < deadline:
            window.update()
            time.sleep(0.05)
        window.update()
        assert app._segments.get(0) == original_segment, 'Completed segment changed during resume'
    failed = [i for i, text in app._segments.items() if text is None]
    success = bool(app._segments) and not failed and not app.is_running
    path = clip.with_suffix('.srt')
    text = path.read_text(encoding='utf-8') if path.exists() else ''
    rows = re.findall(r'(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)', text)
    def seconds(parts):
        return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2]) + int(parts[3])/1000
    times = [(seconds(row[:4]), seconds(row[4:])) for row in rows]
    report = {'success': success, 'model': args.model, 'language': args.language,
              'speech_seconds': args.seconds, 'padding_seconds': args.padding,
              'cues': len(times), 'failed_segments': failed,
              'first_start': times[0][0] if times else None,
              'last_end': times[-1][1] if times else None,
              'invalid_ranges': sum(b <= a for a,b in times),
              'overlaps': sum(a[1] > b[0] for a,b in zip(times, times[1:])),
              'silence_cues': sum(a < args.padding-1 for a,b in times),
              'expected_term': Path(args.source).stem in text,
              'checkpoint_after_stop': checkpoint_saved,
              'initial_requests': prior_requests,
              'uploaded_seconds_before_stop': round(prior_seconds, 2),
              'resumed_requests': app._client.request_count,
              'uploaded_seconds_after_resume': round(app._client.uploaded_seconds, 2),
              'run_folder': str(run.relative_to(project))}
    if args.timeline2h:
        report['source_duration'] = 7200
        report['boundary_1800_cues'] = sum(a < 1800 < b for a,b in times)
        report['hour90_cues'] = sum(5400 <= a < 5441 for a,b in times)
        report['unexpected_region_cues'] = sum(not (1789 <= a < 1831 or 5399 <= a < 5441)
                                               for a,b in times)
        report['checkpoint_removed_after_success'] = not resume.checkpoint_path(
            clip, app._model_identity).exists()
    (run / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True), flush=True)
    if not success:
        # UI messages are sanitized stage diagnostics, but never emit full fatal text.
        print('Stage diagnostics:')
        for line in app.log_text.get('1.0', 'end').splitlines():
            if ' / ' in line:
                print(line.encode('ascii', 'backslashreplace').decode())
    window.destroy()
    if not success or report['invalid_ranges'] or report['overlaps'] or report['silence_cues']:
        sys.exit(1)
    if args.timeline2h:
        if (not checkpoint_saved or report['unexpected_region_cues']
                or not report['hour90_cues'] or not report['checkpoint_removed_after_success']):
            sys.exit(1)


if __name__ == '__main__':
    main()
