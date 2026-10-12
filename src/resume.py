"""持久化字幕工作進度，讓 API 額度用完後可從已完成段落繼續。"""

from __future__ import annotations

import json
import os
import time
import math
from pathlib import Path

SCHEMA_VERSION = 1
INDEX_PATH = Path(__file__).parent.parent / ".subtitler_resume_index.json"


def checkpoint_path(video_path: str | Path, model=None) -> Path:
    path = Path(video_path)
    if model and model.startswith('groq:'):
        import hashlib
        tag = hashlib.sha256(model.encode()).hexdigest()[:10]
        return path.with_suffix(path.suffix + f'.{tag}.subtitler.resume.json')
    return path.with_suffix(path.suffix + ".subtitler.resume.json")


def _identity(video_path: str | Path, duration: float, chunk_seconds: int, model: str) -> dict:
    path = Path(video_path)
    stat = path.stat()
    return {"path": str(path.resolve()), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
            "duration": duration, "chunk_seconds": chunk_seconds, "model": model}


def load(video_path: str | Path, duration: float, chunk_seconds: int, model: str) -> dict | None:
    """讀取且驗證 checkpoint；影片或處理設定改變時絕不誤用舊結果。"""
    try:
        data = json.loads(checkpoint_path(video_path, model).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if data.get("schema") != SCHEMA_VERSION or not isinstance(data.get("segments"), dict):
        return None
    return data if data.get("identity") == _identity(video_path, duration, chunk_seconds, model) else None


def create(video_path: str | Path, duration: float, chunk_seconds: int, model: str) -> dict:
    state = {"schema": SCHEMA_VERSION,
             "identity": _identity(video_path, duration, chunk_seconds, model), "segments": {},
             "transcripts": {}, "split_strategy": "balanced"}
    state['split_plan'] = segment_plan(state)
    save(video_path, state)
    try:
        register(video_path, model)
    except OSError:
        pass
    return state


def segment_plan(state):
    """New jobs balance; old checkpoints retain their original fixed boundaries."""
    identity = state['identity']
    duration, target = float(identity['duration']), float(identity['chunk_seconds'])
    if not math.isfinite(duration) or duration <= 0 or not math.isfinite(target) or target <= 0:
        raise ValueError('Invalid segment duration')
    if 'split_plan' in state:
        plan = [(float(start), float(length)) for start, length in state['split_plan']]
        end = 0.0
        for start, length in plan:
            if not math.isfinite(start + length) or abs(start-end) > 0.001 or not 0 < length <= target+0.001:
                raise ValueError('Invalid saved segment plan')
            end = start + length
        if abs(end-duration) > 0.001:
            raise ValueError('Saved segment plan does not cover source')
        return plan
    count = math.ceil(duration/target)
    step = duration/count if state.get('split_strategy') == 'balanced' else target
    return [(i*step, min(step, duration-i*step)) for i in range(count)]


def save(video_path: str | Path, state: dict) -> None:
    """以 replace 原子更新，意外中斷也不會毀掉前次進度。"""
    path = checkpoint_path(video_path, state['identity']['model'])
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


def record_segment(video_path: str | Path, state: dict, index: int, srt: str) -> None:
    state["segments"][str(index)] = srt
    save(video_path, state)
    try:
        register(video_path, state['identity']['model'])
    except OSError:
        pass


def record_transcript(video_path, state, index, cues):
    state.setdefault("transcripts", {})[str(index)] = cues
    save(video_path, state)
    try:
        register(video_path, state['identity']['model'])
    except OSError:
        pass


def discard(video_path: str | Path, model=None) -> None:
    try:
        checkpoint_path(video_path, model).unlink()
    except FileNotFoundError:
        pass
    _remove_from_index(video_path, model)


def _read_index() -> list[dict]:
    try:
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _write_index(entries: list[dict]) -> None:
    temp = INDEX_PATH.with_name(INDEX_PATH.name + ".tmp")
    temp.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, INDEX_PATH)


def register(video_path: str | Path, model=None) -> None:
    """記下 checkpoint 所在處；啟動時才能跨資料夾主動提示使用者。"""
    resolved = str(Path(video_path).resolve())
    entries = [entry for entry in _read_index()
               if not (entry.get('path') == resolved and entry.get('model') == model)]
    entries.append({"path": resolved, "model": model, "updated_at": time.time()})
    _write_index(entries)


def _remove_from_index(video_path: str | Path, model=None) -> None:
    resolved = str(Path(video_path).resolve())
    entries = [entry for entry in _read_index()
               if not (entry.get('path') == resolved and
                       (model is None or entry.get('model') == model))]
    try:
        _write_index(entries)
    except OSError:
        pass


def pending_jobs(model: str | None, *, include_unavailable=False) -> list[dict]:
    """回傳仍有效的未完成工作，並清理失效的索引項目。"""
    jobs = []
    valid_entries = []
    entries = _read_index()
    for entry in entries:
        try:
            video_path = Path(entry["path"])
            state = json.loads(checkpoint_path(video_path, entry.get('model')).read_text(encoding="utf-8"))
            identity = state["identity"]
            valid = (state.get("schema") == SCHEMA_VERSION
                     and identity.get("path") == str(video_path.resolve())
                     and (model is None or identity.get("model") == model)
                     and isinstance(state.get("segments"), dict))
            if not valid:
                if model is not None and identity.get('model') != model:
                    valid_entries.append(entry)
                continue
            total = len(segment_plan(state))
            try:
                stat = video_path.stat()
                status = ('ready' if identity.get('size') == stat.st_size
                          and identity.get('mtime_ns') == stat.st_mtime_ns else 'changed')
            except OSError:
                status = 'missing'
            valid_entries.append(entry)
            if status != 'ready' and not include_unavailable:
                continue
            jobs.append({"path": str(video_path), "completed": len(state["segments"]),
                         "total": total, "status": status,
                         "model": identity['model'], "chunk_seconds": identity['chunk_seconds'],
                         "updated_at": float(entry.get("updated_at", 0))})
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
    if valid_entries != entries:
        try:
            _write_index(valid_entries)
        except OSError:
            pass
    return sorted(jobs, key=lambda job: job["updated_at"], reverse=True)
