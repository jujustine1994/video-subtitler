"""持久化字幕工作進度，讓 API 額度用完後可從已完成段落繼續。"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

SCHEMA_VERSION = 1
INDEX_PATH = Path(__file__).parent.parent / ".subtitler_resume_index.json"


def checkpoint_path(video_path: str | Path) -> Path:
    path = Path(video_path)
    return path.with_suffix(path.suffix + ".subtitler.resume.json")


def _identity(video_path: str | Path, duration: float, chunk_seconds: int, model: str) -> dict:
    path = Path(video_path)
    stat = path.stat()
    return {"path": str(path.resolve()), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
            "duration": duration, "chunk_seconds": chunk_seconds, "model": model}


def load(video_path: str | Path, duration: float, chunk_seconds: int, model: str) -> dict | None:
    """讀取且驗證 checkpoint；影片或處理設定改變時絕不誤用舊結果。"""
    try:
        data = json.loads(checkpoint_path(video_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if data.get("schema") != SCHEMA_VERSION or not isinstance(data.get("segments"), dict):
        return None
    return data if data.get("identity") == _identity(video_path, duration, chunk_seconds, model) else None


def create(video_path: str | Path, duration: float, chunk_seconds: int, model: str) -> dict:
    state = {"schema": SCHEMA_VERSION,
             "identity": _identity(video_path, duration, chunk_seconds, model), "segments": {}}
    try:
        register(video_path)
    except OSError:
        pass
    return state


def save(video_path: str | Path, state: dict) -> None:
    """以 replace 原子更新，意外中斷也不會毀掉前次進度。"""
    path = checkpoint_path(video_path)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


def record_segment(video_path: str | Path, state: dict, index: int, srt: str) -> None:
    state["segments"][str(index)] = srt
    save(video_path, state)
    try:
        register(video_path)
    except OSError:
        pass


def discard(video_path: str | Path) -> None:
    try:
        checkpoint_path(video_path).unlink()
    except FileNotFoundError:
        pass
    _remove_from_index(video_path)


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


def register(video_path: str | Path) -> None:
    """記下 checkpoint 所在處；啟動時才能跨資料夾主動提示使用者。"""
    resolved = str(Path(video_path).resolve())
    entries = [entry for entry in _read_index() if entry.get("path") != resolved]
    entries.append({"path": resolved, "updated_at": time.time()})
    _write_index(entries)


def _remove_from_index(video_path: str | Path) -> None:
    resolved = str(Path(video_path).resolve())
    entries = [entry for entry in _read_index() if entry.get("path") != resolved]
    try:
        _write_index(entries)
    except OSError:
        pass


def pending_jobs(model: str) -> list[dict]:
    """回傳仍有效的未完成工作，並清理失效的索引項目。"""
    jobs = []
    valid_entries = []
    entries = _read_index()
    for entry in entries:
        try:
            video_path = Path(entry["path"])
            state = json.loads(checkpoint_path(video_path).read_text(encoding="utf-8"))
            identity = state["identity"]
            stat = video_path.stat()
            valid = (state.get("schema") == SCHEMA_VERSION
                     and identity.get("path") == str(video_path.resolve())
                     and identity.get("size") == stat.st_size
                     and identity.get("mtime_ns") == stat.st_mtime_ns
                     and identity.get("model") == model
                     and isinstance(state.get("segments"), dict))
            if not valid:
                continue
            jobs.append({"path": str(video_path), "completed": len(state["segments"]),
                         "updated_at": float(entry.get("updated_at", 0))})
            valid_entries.append(entry)
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
    if valid_entries != entries:
        try:
            _write_index(valid_entries)
        except OSError:
            pass
    return sorted(jobs, key=lambda job: job["updated_at"], reverse=True)
