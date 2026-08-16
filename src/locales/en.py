"""locales/en.py — English. 母表是 zh_tw.py，key 必須完全一致。

⚠ 這裡只放介面文字。字幕內容、SRT 規格、檔名、ffmpeg 參數、Gemini prompt
都是資料，不在這個檔裡（見 zh_tw.py 開頭說明）。
"""

from __future__ import annotations

STRINGS: dict[str, str] = {
    # ── Window / section titles ──
    "gui.win.title":            "Gemini Video Subtitle Translator",
    "gui.frame.file":           " Video File ",
    "gui.frame.progress":       " Progress ",
    "gui.frame.retry":          " Failed Segments ",

    # ── Buttons / checkboxes ──
    "gui.btn.pick_file":        "Browse",
    "gui.btn.show_key":         "Show",
    "gui.btn.start":            "▶  Start",
    "gui.btn.retry":            "Retry Selected",
    "gui.btn.apply":            "Apply",
    "gui.btn.cancel":           "Cancel",
    "gui.chk.remember_key":     "Remember",
    "gui.chk.segment":          "Segment {index}",

    # ── Labels ──
    "gui.lbl.api_notice":       "🔒 Your API key is stored only in the local .env file. Never share it.",
    "gui.lbl.theme":            "Color Theme",
    "gui.lbl.failed_hint":      "These segments failed. Tick the ones to retry:",
    "gui.log.hint":             "Choose a video, enter your API key, then click Start.\n",

    # ── Theme names ──
    "theme.light":              "Light",
    "theme.dark":               "Dark",
    "theme.financial":          "Finance Blue",

    # ── Dialogs ──
    "gui.dlg.settings_title":   "Settings",
    "gui.dlg.pick_file_title":  "Select a video file",
    "gui.dlg.error_title":      "Error",
    "gui.dlg.info_title":       "Notice",
    "gui.dlg.done_title":       "Done",
    "gui.filetype.video":       "Video files",
    "gui.filetype.all":         "All files",

    # ── Messages ──
    "gui.msg.no_video":            "Please select a valid video file.",
    "gui.msg.no_api_key":          "Please enter your Gemini API key.",
    "gui.msg.select_one_segment":  "Tick at least one failed segment.",
    "gui.msg.done":                "Finished:\n{path}",

    # ── Status bar / progress ──
    "gui.status.idle":               "Waiting to start...",
    "gui.status.ready":              "Ready",
    "gui.status.preparing":          "Preparing...",
    "gui.status.running":            "Working, please wait...",
    "gui.status.retrying":           "Retrying, please wait...",
    "gui.status.done":               "Finished!",
    "gui.status.done_with_failures": "Finished, but {count} segment(s) failed",
    "gui.status.fatal_label":        "Something went wrong. See the log above.",
    "gui.status.fatal":              "Fatal error: {error}",
    "gui.progress.segments":         "{done} / {total} segments done",

    # ── On-screen log ──
    "gui.log.duration":         "Video length: {minutes} min {seconds} sec",
    "gui.log.total_segments":   "{count} segment(s) in total. Starting...",
    "gui.log.segment_start":    "\n-> Processing segment {index} (starts at {minutes} min)...",
    "gui.log.segment_retry":    "   Segment {index} failed. Retrying in {delay}s (attempt {attempt})...",
    "gui.log.segment_done":     "   Segment {index} done.",
    "gui.log.segment_failed":   "   Segment {index} still failed after retries ({error})",
    "gui.log.failed_list":      "\nFailed segments: {indices}",
    "gui.log.output":           "\nSubtitles written to: {path}",
    "gui.log.retry_start":      "\nRetrying segment(s) {indices}...",
    "gui.log.ai_ready":         "AI is ready, translating ({model})...",

    # ── Shown on screen AND written to the log (the log copy stays
    #    Traditional Chinese by design — see logtext.py) ──
    "log.segment_error":        "Segment {index} upload to Gemini -> {detail} | retry {attempt}/{total}",
    "log.segment_error_final":  "Segment {index} upload to Gemini -> {detail} | failed after {attempt}/{total} retries",

    # ── Exceptions shown to the user ──
    "err.ffmpeg_failed":        "ffmpeg could not extract the audio. Make sure FFmpeg is installed and on your system PATH.",
}
