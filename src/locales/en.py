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
    "gui.frame.update":         " Software Update ",

    # ── Buttons / checkboxes ──
    "gui.btn.pick_file":        "Browse",
    "gui.btn.show_key":         "Show",
    "gui.btn.start":            "▶  Start",
    "gui.btn.retry":            "Retry Selected",
    "gui.btn.apply":            "Apply",
    "gui.btn.cancel":           "Cancel",
    "gui.btn.check_update":     "Check for Updates",
    "gui.btn.install_update":   "Install Update",
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
    "gui.dlg.resume_title":     "Unfinished Job Found",
    "gui.filetype.video":       "Video files",
    "gui.filetype.audio":       "Audio files",
    "gui.filetype.all":         "All files",

    # ── Messages ──
    "gui.msg.no_video":            "Please select a valid video file.",
    "gui.msg.no_api_key":          "Please enter your Gemini API key.",
    "gui.msg.select_one_segment":  "Tick at least one failed segment.",
    "gui.msg.done":                "Finished:\n{path}",
    "gui.msg.resume_found":        "An unfinished subtitle job was found:\n{name}\n\n{count} segment(s) are complete.\n\nSelect this file automatically, then resume when you click Start?",

    # ── Status bar / progress ──
    "gui.status.idle":               "Waiting to start...",
    "gui.status.ready":              "Ready",
    "gui.status.preparing":          "Preparing...",
    "gui.status.running":            "Working, please wait...",
    "gui.status.retrying":           "Retrying, please wait...",
    "gui.status.done":               "Finished!",
    "gui.status.done_with_failures": "Finished, but {count} segment(s) failed",
    "gui.status.quota_paused":       "Free quota exhausted; progress was saved",
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
    "gui.log.resume_found":     "Previous progress found; skipping {count} completed segment(s).",
    "gui.log.quota_paused":     "Free quota is temporarily exhausted. Progress is saved; select this video and start again later to resume.",
    "gui.log.resume_selected":  "Automatically selected unfinished job: {name}",

    # ── Shown on screen AND written to the log (the log copy stays
    #    Traditional Chinese by design — see logtext.py) ──
    "log.segment_error":        "Segment {index} upload to Gemini -> {detail} | retry {attempt}/{total}",
    "log.segment_error_final":  "Segment {index} upload to Gemini -> {detail} | failed after {attempt}/{total} retries",

    # ── Exceptions shown to the user ──
    "err.ffmpeg_failed":        "ffmpeg could not extract the audio. Make sure FFmpeg is installed and on your system PATH.",

    # ── Software update (Settings dialog "Software Update" section) ──
    "gui.update.checking":      "Checking...",
    "gui.update.no_git":        "This copy can't auto-update. Please download the latest version from GitHub.",
    "gui.update.offline":       "Couldn't reach GitHub. Check your network connection and try again.",
    "gui.update.dirty":         "Local code has manual changes, skipped to avoid overwriting them.",
    "gui.update.ahead":         "Local code has unsynced changes, skipped to avoid overwriting them.",
    "gui.update.up_to_date":    "Already up to date.",
    "gui.update.available":     "New version available ({count} change(s)). Click \"Install Update\" to update.",
    "gui.update.confirm_title": "Confirm Update",
    "gui.update.confirm_body":  "About to update the code. You'll need to restart the app manually for it to take effect.\n\nThis update:\n{summary}\n\nContinue?",
    "gui.update.installing":    "Installing...",
    "gui.update.updated":       "Updated to the latest version ({commit}). Please close and reopen the app.",
    "gui.update.done_body":     "The latest version has been installed. Close this window and double-click the launcher again for it to take effect.",
    "gui.update.error":         "Update check failed: {msg}",
}
