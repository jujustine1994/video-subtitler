"""
影片字幕翻譯核心邏輯：ffmpeg 音訊擷取、Gemini 翻譯（含 retry）、SRT 格式處理。
不含任何 print/input，所有進度回報透過呼叫端傳入的 callback 完成，供 gui.py 的背景執行緒呼叫。
"""

import os
import re
import time
import subprocess
from google import genai
from google.genai import types

from . import prompts
from .i18n import t
from .logtext import LOG_TEXT

CHUNK_DURATION = 1800  # 每段處理長度（秒），30 分鐘
MODEL_NAME = "gemini-flash-latest"  # 供 log 任務起始行標示，翻譯呼叫也共用此常數

RETRY_DELAYS = (5, 15, 45)  # 指數後退秒數
RETRYABLE_MARKERS = ("429", "quota", "exhausted", "timeout", "timed out",
                      "connection", "unavailable", "deadline")


def _safe_err(e: Exception) -> str:
    """回傳「可安全落檔」的錯誤摘要：只有 exception 類型 + HTTP status code。

    google-genai / requests 的例外訊息（str(e)）天生挾帶完整 request URL——URL 裡就有
    ?key=<GEMINI_API_KEY>——以及 response 全文。**絕對不可** f"{e}" 落檔，否則等於把金鑰
    寫上磁碟。要辨識是哪一筆，靠任務起始行的檔名/模型，不靠這裡的 URL。
    """
    name = type(e).__name__
    # google.genai.errors.APIError 用 .code 帶 HTTP status；部分例外用 .status_code
    code = getattr(e, "code", None)
    if code is None:
        code = getattr(e, "status_code", None)
    if code is not None:
        return f"{name}: HTTP {code}"
    return name


def make_client(api_key: str):
    return genai.Client(api_key=api_key)


def get_video_duration(video_path: str) -> float:
    """取得影片總時長（秒）"""
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return float(result.stdout)


def extract_audio_segment(video_path: str, start_time: float, duration: float, out_path: str) -> None:
    """用 ffmpeg 擷取指定時間範圍的音訊到 out_path（mp3）"""
    cmd = [
        'ffmpeg', '-ss', str(start_time), '-t', str(duration),
        '-i', video_path, '-vn', '-acodec', 'libmp3lame', '-y', out_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(out_path):
        # 這條會經 gui._fatal() 顯示給使用者看，是介面文字不是 log
        raise RuntimeError(t("err.ffmpeg_failed"))


def renumber_srt(srt_text: str) -> str:
    """重新編號合併後的 SRT，確保序號連續不重複"""
    counter = 1
    result = []
    number_pattern = re.compile(r'^\d+$')
    for line in srt_text.split('\n'):
        if number_pattern.match(line.strip()):
            result.append(str(counter))
            counter += 1
        else:
            result.append(line)
    return '\n'.join(result)


def enforce_max_duration(srt_text: str, max_seconds: int = 5) -> str:
    """掃描 SRT 內容，將超過 max_seconds 的字幕截斷"""
    lines = srt_text.split('\n')
    result = []
    ts_pattern = re.compile(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})')

    def ts_to_ms(ts):
        h, m, s_ms = ts.split(':')
        s, ms = s_ms.split(',')
        return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)

    def ms_to_ts(ms):
        h = ms // 3600000; ms %= 3600000
        m = ms // 60000; ms %= 60000
        s = ms // 1000; ms %= 1000
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    for line in lines:
        m = ts_pattern.match(line.strip())
        if m:
            start_ms = ts_to_ms(m.group(1))
            end_ms = ts_to_ms(m.group(2))
            if end_ms - start_ms > max_seconds * 1000:
                end_ms = start_ms + max_seconds * 1000
            result.append(f"{ms_to_ts(start_ms)} --> {ms_to_ts(end_ms)}")
        else:
            result.append(line)
    return '\n'.join(result)


def fix_srt_format(srt_text: str, offset_seconds: float = 0) -> str:
    """極致強化的 SRT 格式修復工具，並處理時間偏移"""
    fixed_lines = []
    timestamp_pattern = re.compile(r'(\d{1,2}):(\d{1,2})[:|,. ](\d{1,3})')
    full_timestamp_pattern = re.compile(r'(\d{1,2}):(\d{1,2}):(\d{1,2})[:|,. ](\d{1,3})')

    def add_offset(h, m, s, ms, offset):
        total_ms = (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int(ms)
        total_ms += int(offset * 1000)

        nh = total_ms // 3600000
        total_ms %= 3600000
        nm = total_ms // 60000
        total_ms %= 60000
        ns = total_ms // 1000
        nms = total_ms % 1000
        return f"{nh:02d}:{nm:02d}:{ns:02d},{nms:03d}"

    for line in srt_text.split('\n'):
        line = line.strip()
        if '-->' in line:
            parts = line.split('-->')
            new_parts = []
            for p in parts:
                p = p.strip()
                m_full = full_timestamp_pattern.match(p)
                if m_full:
                    h, m, s, ms = m_full.groups()
                    new_parts.append(add_offset(h, m, s, ms, offset_seconds))
                    continue
                m_short = timestamp_pattern.match(p)
                if m_short:
                    m, s, ms = m_short.groups()
                    new_parts.append(add_offset(0, m, s, ms, offset_seconds))
                    continue
                new_parts.append(p)
            if len(new_parts) == 2:
                fixed_lines.append(f"{new_parts[0]} --> {new_parts[1]}")
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def _is_retryable(err: Exception) -> bool:
    msg = str(err).lower()
    return any(marker in msg for marker in RETRYABLE_MARKERS)


def translate_segment(client, audio_path: str, segment_index: int, offset_seconds: float,
                       target_language: str = prompts.DEFAULT_TARGET_LANGUAGE,
                       on_log=None, on_retry=None, on_error=None) -> str:
    """
    上傳音訊並呼叫 Gemini 翻譯成 SRT，失敗時依 RETRYABLE_MARKERS 判斷是否重試。

    target_language：**字幕**的目標語言。跟著影片音訊走，與介面語言完全無關
                   （見 prompts.py）。呼叫端目前不傳，永遠是繁體中文。
    on_log(str)：一般進度訊息（不落檔）
    on_retry(attempt, delay)：重試前回報嘗試次數與等待秒數（UI 用，不落檔）
    on_error(ui_msg, log_msg)：「已消毒」的錯誤摘要（型別 + status code + 重試次數，
                   絕無金鑰）。ui_msg 給畫面、log_msg 給 logs/app.log（固定繁中）。
                   **不會**傳入 str(e)。
    成功回傳修復後的 SRT 文字；重試耗盡仍失敗則拋出最後一次例外。
    """
    prompt = prompts.TRANSLATE_PROMPT.format(target_language=target_language)

    last_err = None
    n = len(RETRY_DELAYS)
    for attempt in range(n + 1):
        try:
            return _call_gemini(client, audio_path, prompt, offset_seconds, on_log)
        except Exception as e:
            last_err = e
            safe = _safe_err(e)   # 只有型別 + status code，永不含金鑰
            if attempt >= n or not _is_retryable(e):
                if on_error:
                    _report_error(on_error, "segment_error_final",
                                  segment_index + 1, safe, attempt, n)
                raise
            delay = RETRY_DELAYS[attempt]
            if on_error:
                _report_error(on_error, "segment_error",
                              segment_index + 1, safe, attempt + 1, n)
            if on_retry:
                on_retry(attempt + 1, delay)
            time.sleep(delay)
    raise last_err


def _report_error(on_error, key: str, index: int, detail: str, attempt: int, total: int):
    """同一條錯誤同時給 UI 與 log 檔：一個呼叫吃兩邊，不要維護兩套呼叫，
    否則一定會有地方漏記（windows-tool.md）。

    UI 那條走 t()（跟著介面語言），log 那條走 LOG_TEXT（固定繁中）。
    ⚠ 繁中模式下兩者字面一模一樣是**正常的**——重疊是設計不是 bug。
    """
    fmt = dict(index=index, detail=detail, attempt=attempt, total=total)
    on_error(t(f"log.{key}", **fmt), LOG_TEXT[key].format(**fmt))


def _call_gemini(client, audio_path: str, prompt: str, offset_seconds: float, on_log) -> str:
    audio_file = client.files.upload(file=audio_path)
    while audio_file.state.name == "PROCESSING":
        time.sleep(2)
        audio_file = client.files.get(name=audio_file.name)

    if on_log:
        # MODEL_NAME 是資料（餵給 API 的模型代號），只是原樣顯示在畫面上
        on_log(t("gui.log.ai_ready", model=MODEL_NAME))

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt, audio_file],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
    finally:
        client.files.delete(name=audio_file.name)

    import json
    try:
        result = json.loads(response.text)
        if isinstance(result, list):
            result = result[0]
        content = result.get("srt_content", "")
        return fix_srt_format(content, offset_seconds)
    except Exception:
        return fix_srt_format(response.text, offset_seconds)
