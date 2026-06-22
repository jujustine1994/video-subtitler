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

CHUNK_DURATION = 1800  # 每段處理長度（秒），30 分鐘

RETRY_DELAYS = (5, 15, 45)  # 指數後退秒數
RETRYABLE_MARKERS = ("429", "quota", "exhausted", "timeout", "timed out",
                      "connection", "unavailable", "deadline")


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
        raise RuntimeError("ffmpeg 音訊擷取失敗，請確認 FFmpeg 已安裝並加入系統環境變數（PATH）。")


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
                       target_language: str = "繁體中文", on_log=None, on_retry=None) -> str:
    """
    上傳音訊並呼叫 Gemini 翻譯成 SRT，失敗時依 RETRYABLE_MARKERS 判斷是否重試。
    on_log(str)：一般進度訊息
    on_retry(attempt, delay)：重試前回報嘗試次數與等待秒數
    成功回傳修復後的 SRT 文字；重試耗盡仍失敗則拋出最後一次例外。
    """
    prompt = f"""
    請聽這段音訊，將其內容翻譯為 {target_language}，並輸出標準 SRT 字幕格式。

    輸出格式：JSON 格式，包含欄位 "srt_content"。僅輸出 JSON，不附任何說明。

    時間軸規則（最高優先級）：
    1. 所有時間戳必須使用 HH:MM:SS,mmm 格式（例如 00:20:37,340），小時位絕對不可省略。
    2. 時間軸從 00:00:00,000 起算，對應音訊的絕對起點。
    3. 每條字幕的結束時間必須早於下一條字幕的開始時間（嚴格遞增，不可重疊）。
    4. 靜默段不需輸出字幕，但下一條字幕的時間戳必須反映真實的音訊位置。
    5. 每條字幕的顯示時間最長不可超過 5 秒（結束時間 - 開始時間 ≤ 5 秒）。若說話內容超過 5 秒，必須拆分為多條字幕。

    內容規則：
    1. 每行字幕最多 15 個中文字，過長請斷句或拆分為多個字幕塊。
    2. 有人聲說話時，無論清晰或模糊，都必須盡力辨識並翻譯，結合前後文補全語意。
    3. 僅在「完全沒有人聲」的片段（純音樂、純雜音、非語言情緒音、呻吟聲、笑聲、哭聲）才略過，不輸出該段字幕。
    """

    last_err = None
    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            return _call_gemini(client, audio_path, prompt, offset_seconds, on_log)
        except Exception as e:
            last_err = e
            if attempt >= len(RETRY_DELAYS) or not _is_retryable(e):
                raise
            delay = RETRY_DELAYS[attempt]
            if on_retry:
                on_retry(attempt + 1, delay)
            time.sleep(delay)
    raise last_err


def _call_gemini(client, audio_path: str, prompt: str, offset_seconds: float, on_log) -> str:
    audio_file = client.files.upload(file=audio_path)
    while audio_file.state.name == "PROCESSING":
        time.sleep(2)
        audio_file = client.files.get(name=audio_file.name)

    if on_log:
        on_log("AI 已就緒，開始翻譯 (gemini-flash-latest)...")

    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
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
