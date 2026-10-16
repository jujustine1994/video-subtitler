"""Run the real app workflow unattended; print only safe diagnostics, never keys/text."""
import argparse
import json
import re
import sys
import time
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import gui, resume
from src.groq_provider import MODELS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--language', default='ja')
    parser.add_argument('--model', choices=MODELS, default=MODELS[0])
    args = parser.parse_args()
    source = Path(args.source).resolve(strict=True)
    project = Path(__file__).resolve().parent.parent
    reports = project/'validation_outputs'
    reports.mkdir(exist_ok=True)
    config = reports/'unattended-config.json'
    config.write_text('{"language":"zh_tw","theme":"light"}',encoding='utf8')
    gui.CONFIG_PATH = str(config)
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
    app.chunk_var.set('10')
    app.save_key_var.set(False)
    app.file_var.set(str(source))
    original_log = app._log
    def log(message, level='INFO', log_msg=None):
        original_log(message,level,log_msg)
        if level == 'ERROR' and log_msg:
            print(log_msg.encode('ascii','backslashreplace').decode(),flush=True)
    app._log = log
    app._start()
    if not app.is_running:
        window.destroy()
        raise RuntimeError('Could not start; required API keys must be configured')
    last_completed = -1
    next_status = 0
    started = time.monotonic()
    while app.is_running:
        window.update()
        completed = sum(value is not None for value in app._segments.values())
        if completed != last_completed or time.monotonic() >= next_status:
            print(json.dumps({'elapsed_seconds':round(time.monotonic()-started),
                              'completed_segments':completed,
                              'failed_segments':sum(v is None for v in app._segments.values()),
                              'asr_requests':getattr(app._client,'request_count',0),
                              'uploaded_audio_seconds':round(getattr(app._client,'uploaded_seconds',0))}),
                  flush=True)
            next_status = time.monotonic()+30
            last_completed = completed
        time.sleep(0.1)
    window.update()
    failed = [i for i,v in app._segments.items() if v is None]
    checkpoint = resume.checkpoint_path(source,app._model_identity)
    output = source.with_suffix('.srt')
    text = output.read_text(encoding='utf8') if output.exists() else ''
    rows = re.findall(r'(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)',text)
    def seconds(p):
        return int(p[0])*3600+int(p[1])*60+int(p[2])+int(p[3])/1000
    times = [(seconds(row[:4]),seconds(row[4:])) for row in rows]
    report = {'finished':bool(app._segments) and not failed and not checkpoint.exists(),
              'completed_segments':sum(v is not None for v in app._segments.values()),
              'failed_segments':failed,'checkpoint_retained':checkpoint.exists(),
              'cues':len(times),'invalid_ranges':sum(b<=a for a,b in times),
              'overlaps':sum(a[1]>b[0] for a,b in zip(times,times[1:])),
              'first_start':times[0][0] if times else None,
              'last_end':times[-1][1] if times else None,
              'asr_requests':app._client.request_count,
              'uploaded_audio_seconds':round(app._client.uploaded_seconds,2)}
    (reports/'unattended-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report),flush=True)
    window.destroy()
    if not report['finished'] or report['invalid_ranges'] or report['overlaps']:
        sys.exit(2)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Unattended failure: {type(exc).__name__}',file=sys.stderr,flush=True)
        sys.exit(1)
