"""locales/zh_cn.py — 简体中文。母表是 zh_tw.py，key 必須完全一致。

⚠ 這裡只放介面文字。字幕內容、SRT 規格、檔名、ffmpeg 參數、Gemini prompt
都是資料，不在這個檔裡（見 zh_tw.py 開頭說明）。
"""

from __future__ import annotations

STRINGS: dict[str, str] = {
    # ── 视窗与区块标题 ──
    "gui.win.title":            "Gemini 视频字幕翻译工具",
    "gui.frame.file":           " 视频文件 ",
    "gui.frame.progress":       " 处理进度 ",
    "gui.frame.retry":          " 失败段落 ",

    # ── 按钮与勾选 ──
    "gui.btn.pick_file":        "选择视频",
    "gui.btn.show_key":         "显示",
    "gui.btn.start":            "▶  开始翻译",
    "gui.btn.retry":            "重试所选段落",
    "gui.btn.apply":            "应用",
    "gui.btn.cancel":           "取消",
    "gui.chk.remember_key":     "记住",
    "gui.chk.segment":          "第 {index} 段",

    # ── 标签与说明 ──
    "gui.lbl.api_notice":       "🔒 API Key 仅储存于本机 .env 文件，请勿将 Key 提供给他人。",
    "gui.lbl.theme":            "配色主题",
    "gui.lbl.failed_hint":      "以下段落失败，可勾选后重试：",
    "gui.log.hint":             "选择视频并输入 API Key 后按「开始翻译」。\n",

    # ── 配色主题名 ──
    "theme.light":              "清爽白",
    "theme.dark":               "深色模式",
    "theme.financial":          "金融蓝",

    # ── 对话框 ──
    "gui.dlg.settings_title":   "设置",
    "gui.dlg.pick_file_title":  "请选择视频文件",
    "gui.dlg.error_title":      "错误",
    "gui.dlg.info_title":       "提示",
    "gui.dlg.done_title":       "完成",
    "gui.filetype.video":       "视频文件",
    "gui.filetype.all":         "所有文件",

    # ── 消息 ──
    "gui.msg.no_video":            "请选择有效的视频文件",
    "gui.msg.no_api_key":          "请输入 Gemini API Key",
    "gui.msg.select_one_segment":  "请至少勾选一个失败段落",
    "gui.msg.done":                "已完成：\n{path}",

    # ── 状态栏与进度 ──
    "gui.status.idle":               "等待开始...",
    "gui.status.ready":              "就绪",
    "gui.status.preparing":          "准备中...",
    "gui.status.running":            "执行中，请稍候...",
    "gui.status.retrying":           "重试中，请稍候...",
    "gui.status.done":               "已完成！",
    "gui.status.done_with_failures": "完成，但有 {count} 段失败",
    "gui.status.fatal_label":        "发生错误，请查看上方记录",
    "gui.status.fatal":              "致命错误：{error}",
    "gui.progress.segments":         "{done} / {total} 段完成",

    # ── 画面记录区 ──
    "gui.log.duration":         "视频总时长: {minutes} 分 {seconds} 秒",
    "gui.log.total_segments":   "共 {count} 段，开始处理...",
    "gui.log.segment_start":    "\n-> 正在处理第 {index} 段 (起始时间: {minutes} 分)...",
    "gui.log.segment_retry":    "   第 {index} 段失败，{delay} 秒后重试（第 {attempt} 次）...",
    "gui.log.segment_done":     "   第 {index} 段完成。",
    "gui.log.segment_failed":   "   第 {index} 段重试后仍失败（{error}）",
    "gui.log.failed_list":      "\n以下段落失败：第 {indices} 段",
    "gui.log.output":           "\n字幕已输出: {path}",
    "gui.log.retry_start":      "\n重试第 {indices} 段...",
    "gui.log.ai_ready":         "AI 已就绪，开始翻译 ({model})...",

    # ── 同时推 UI 又落档的消息（落档那条永远是繁中，见 logtext.py）──
    "log.segment_error":        "第{index}段 上传Gemini -> {detail} | 重试 {attempt}/{total}",
    "log.segment_error_final":  "第{index}段 上传Gemini -> {detail} | 重试 {attempt}/{total} 后失败",

    # ── 会显示给使用者看的异常消息 ──
    "err.ffmpeg_failed":        "ffmpeg 音频提取失败，请确认 FFmpeg 已安装并加入系统环境变量（PATH）。",
}
