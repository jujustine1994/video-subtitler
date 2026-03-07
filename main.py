import os
import time
import json
import re
import subprocess
import tkinter as tk
from tkinter import filedialog
import google.generativeai as genai
from dotenv import load_dotenv, set_key

# 每段處理的長度（秒），建議 1800 秒 (30 分鐘)
CHUNK_DURATION = 1800 

def setup_api_key():
    load_dotenv()
    existing_key = os.getenv("GEMINI_API_KEY", "")

    if existing_key:
        masked = existing_key[:8] + "..." + existing_key[-4:]
        print(f"偵測到上次使用的 API Key: {masked}")
        choice = input("直接使用上次的 API Key？(直接 Enter 同意，n 重新輸入): ").strip().lower()
        if choice != 'n':
            return existing_key

    new_key = input("請輸入你的 Gemini API Key: ").strip()
    if not new_key:
        if existing_key:
            print("未輸入，沿用上次的 API Key。")
            return existing_key
        print("未輸入 API Key，程式結束。")
        return None

    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    set_key(env_path, "GEMINI_API_KEY", new_key)
    print("API Key 已儲存。")
    return new_key


def select_file():
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', True)
    root.update()
    file_path = filedialog.askopenfilename(
        parent=root,
        title="請選擇影片檔案",
        filetypes=[("影片檔案", "*.mp4 *.mkv *.avi *.mov *.wmv"), ("所有檔案", "*.*")]
    )
    root.destroy()
    return file_path

def get_video_duration(video_path):
    """取得影片總時長（秒）"""
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return float(result.stdout)

def fix_srt_format(srt_text, offset_seconds=0):
    """
    極致強化的 SRT 格式修復工具，並處理時間偏移
    """
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

def translate_segment(audio_path, segment_index, offset_seconds, target_language="繁體中文"):
    print(f"\n   -> 正在處理第 {segment_index+1} 段 (起始時間: {int(offset_seconds//60)} 分)...")
    
    audio_file = genai.upload_file(path=audio_path)
    while audio_file.state.name == "PROCESSING":
        print(".", end="", flush=True)
        time.sleep(2)
        audio_file = genai.get_file(audio_file.name)

    print(f"\n   -> AI 已就緒，開始翻譯 (gemini-flash-latest)...")

    model = genai.GenerativeModel(
        model_name="gemini-flash-latest",
        generation_config={"response_mime_type": "application/json"}
    )
    
    # 套用用戶優化後的「完美版」Prompt
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

    response = model.generate_content([prompt, audio_file])
    genai.delete_file(audio_file.name)
    
    try:
        result = json.loads(response.text)
        if isinstance(result, list):
            result = result[0]
        content = result.get("srt_content", "")
        return fix_srt_format(content, offset_seconds)
    except:
        return fix_srt_format(response.text, offset_seconds)

def main():
    print("="*50)
    print("      Gemini 影片字幕翻譯專業版 (v1.3)      ")
    print("="*50)
    print()
    print("【使用說明】")
    print("  1. 按下確認後，會跳出視窗讓你選取影片檔案")
    print("  2. 程式自動擷取音訊，上傳至 Gemini AI 翻譯")
    print("  3. 完成後，.srt 字幕檔會存在影片旁邊")
    print()
    print("【注意事項】")
    print("  - 需要網路連線（音訊會上傳至 Google 雲端）")
    print("  - 每 30 分鐘影片約需數分鐘處理時間")
    print("  - 敏感內容可能因 Google 安全過濾而失敗")
    print()
    print("="*50)
    confirm = input("確認開始？(直接 Enter 同意，n 取消): ").strip().lower()
    if confirm == 'n':
        print("已取消。")
        return

    video_path = select_file()
    if not video_path: return

    print(f"已選取影片: {os.path.basename(video_path)}")
    print()

    api_key = setup_api_key()
    if not api_key: return
    genai.configure(api_key=api_key)
    print()
    
    try:
        duration = get_video_duration(video_path)
        print(f"影片總時長: {int(duration // 60)} 分 {int(duration % 60)} 秒")

        num_segments = int(duration // CHUNK_DURATION) + 1
        if num_segments > 1:
            print(f"影片超過 30 分鐘，將自動切成 {num_segments} 段分別處理。")
        else:
            print("影片在 30 分鐘以內，將一次處理完畢。")

        full_srt = []
        temp_files = []

        print()
        if num_segments > 1:
            print(f"本影片超過 30 分鐘，將切為 {num_segments} 段處理字幕，開始處理...")
        else:
            print("開始處理字幕...")
        print()

        for i in range(num_segments):
            start_time = i * CHUNK_DURATION
            if start_time >= duration: break
            
            temp_audio = f"temp_seg_{i}.mp3"
            temp_files.append(temp_audio)
            
            # 使用 ffmpeg 擷取
            cmd = [
                'ffmpeg', '-ss', str(start_time), '-t', str(CHUNK_DURATION),
                '-i', video_path, '-vn', '-acodec', 'libmp3lame', '-y', temp_audio
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            srt_seg = translate_segment(temp_audio, i, start_time)
            full_srt.append(srt_seg)
            
            if os.path.exists(temp_audio): os.remove(temp_audio)

        print(f"\n[步驟 3/3] 正在合併並產出最終字幕檔...")
        final_srt_path = os.path.splitext(video_path)[0] + ".srt"
        
        with open(final_srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(full_srt))
        
        print(f"\n恭喜！任務完成。")
        print(f"字幕儲存在: {final_srt_path}")

    except Exception as e:
        err = str(e)
        if "429" in err or "quota" in err.lower() or "exhausted" in err.lower():
            print(f"\n[錯誤] API 免費用量已達上限。")
            print("       請等待配額重置（通常為隔天）後再重新執行。")
        else:
            print(f"\n[錯誤] {e}")
    finally:
        for f in temp_files:
            if os.path.exists(f): os.remove(f)
            
    print("\n" + "="*40)
    input("按 Enter 鍵結束...")

if __name__ == "__main__":
    main()
