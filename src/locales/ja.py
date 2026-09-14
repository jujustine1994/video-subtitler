"""locales/ja.py — 日本語。母表是 zh_tw.py，key 必須完全一致。

⚠ 這裡只放介面文字。字幕內容、SRT 規格、檔名、ffmpeg 參數、Gemini prompt
都是資料，不在這個檔裡（見 zh_tw.py 開頭說明）。
"""

from __future__ import annotations

STRINGS: dict[str, str] = {
    # ── ウィンドウ・セクション見出し ──
    "gui.win.title":            "Gemini 動画字幕翻訳ツール",
    "gui.frame.file":           " 動画ファイル ",
    "gui.frame.progress":       " 処理状況 ",
    "gui.frame.retry":          " 失敗セグメント ",
    "gui.frame.update":         " バージョン更新 ",

    # ── ボタン・チェックボックス ──
    "gui.btn.pick_file":        "動画を選択",
    "gui.btn.show_key":         "表示",
    "gui.btn.start":            "▶  翻訳開始",
    "gui.btn.retry":            "選択したセグメントを再実行",
    "gui.btn.apply":            "適用",
    "gui.btn.cancel":           "キャンセル",
    "gui.btn.check_update":     "更新を確認",
    "gui.btn.install_update":   "ワンクリックで更新",
    "gui.chk.remember_key":     "記憶",
    "gui.chk.segment":          "セグメント {index}",

    # ── ラベル・説明 ──
    "gui.lbl.api_notice":       "🔒 API キーはローカルの .env ファイルにのみ保存されます。他人に渡さないでください。",
    "gui.lbl.theme":            "配色テーマ",
    "gui.lbl.failed_hint":      "以下のセグメントが失敗しました。再実行するものを選んでください：",
    "gui.log.hint":             "動画を選び、API キーを入力してから「翻訳開始」を押してください。\n",

    # ── テーマ名 ──
    "theme.light":              "ライト",
    "theme.dark":               "ダーク",
    "theme.financial":          "ファイナンスブルー",

    # ── ダイアログ ──
    "gui.dlg.settings_title":   "設定",
    "gui.dlg.pick_file_title":  "動画ファイルを選択",
    "gui.dlg.error_title":      "エラー",
    "gui.dlg.info_title":       "お知らせ",
    "gui.dlg.done_title":       "完了",
    "gui.filetype.video":       "動画ファイル",
    "gui.filetype.all":         "すべてのファイル",

    # ── メッセージ ──
    "gui.msg.no_video":            "有効な動画ファイルを選択してください。",
    "gui.msg.no_api_key":          "Gemini API キーを入力してください。",
    "gui.msg.select_one_segment":  "失敗したセグメントを少なくとも 1 つ選んでください。",
    "gui.msg.done":                "完了しました：\n{path}",

    # ── ステータスバー・進捗 ──
    "gui.status.idle":               "開始待ち...",
    "gui.status.ready":              "準備完了",
    "gui.status.preparing":          "準備中...",
    "gui.status.running":            "実行中です。しばらくお待ちください...",
    "gui.status.retrying":           "再実行中です。しばらくお待ちください...",
    "gui.status.done":               "完了しました！",
    "gui.status.done_with_failures": "完了しましたが {count} 個のセグメントが失敗しました",
    "gui.status.fatal_label":        "エラーが発生しました。上のログを確認してください。",
    "gui.status.fatal":              "致命的なエラー：{error}",
    "gui.progress.segments":         "{done} / {total} セグメント完了",

    # ── 画面のログ表示 ──
    "gui.log.duration":         "動画の長さ: {minutes} 分 {seconds} 秒",
    "gui.log.total_segments":   "全 {count} セグメント。処理を開始します...",
    "gui.log.segment_start":    "\n-> セグメント {index} を処理中 (開始位置: {minutes} 分)...",
    "gui.log.segment_retry":    "   セグメント {index} が失敗しました。{delay} 秒後に再試行します（{attempt} 回目）...",
    "gui.log.segment_done":     "   セグメント {index} が完了しました。",
    "gui.log.segment_failed":   "   セグメント {index} は再試行後も失敗しました（{error}）",
    "gui.log.failed_list":      "\n失敗したセグメント：{indices}",
    "gui.log.output":           "\n字幕を出力しました: {path}",
    "gui.log.retry_start":      "\nセグメント {indices} を再実行します...",
    "gui.log.ai_ready":         "AI の準備ができました。翻訳を開始します ({model})...",

    # ── 画面とログの両方に出るメッセージ（ログ側は設計どおり繁体字のまま。
    #    logtext.py を参照）──
    "log.segment_error":        "セグメント {index} Gemini へのアップロード -> {detail} | 再試行 {attempt}/{total}",
    "log.segment_error_final":  "セグメント {index} Gemini へのアップロード -> {detail} | 再試行 {attempt}/{total} の後に失敗",

    # ── 利用者に表示される例外メッセージ ──
    "err.ffmpeg_failed":        "ffmpeg の音声抽出に失敗しました。FFmpeg がインストールされ、システムの PATH に追加されているか確認してください。",

    # ── バージョン更新（設定ウィンドウの「バージョン更新」セクション）──
    "gui.update.checking":      "確認中...",
    "gui.update.no_git":        "このバージョンは自動更新できません。GitHub ページから最新版をダウンロードしてください。",
    "gui.update.offline":       "GitHub に接続できません。ネットワーク接続を確認してもう一度お試しください。",
    "gui.update.dirty":         "ローカルのコードに手動での変更が検出されたため、スキップしました（変更を上書きしないため）。",
    "gui.update.ahead":         "ローカルに未同期の変更があるため、スキップしました（変更を上書きしないため）。",
    "gui.update.up_to_date":    "既に最新バージョンです。",
    "gui.update.available":     "新しいバージョンがあります（{count} 件の変更）。「ワンクリックで更新」をクリックしてください。",
    "gui.update.confirm_title": "更新の確認",
    "gui.update.confirm_body":  "コードを更新します。反映させるには手動でアプリを再起動する必要があります。\n\n今回の変更：\n{summary}\n\n続けますか？",
    "gui.update.installing":    "インストール中...",
    "gui.update.updated":       "最新バージョン（{commit}）に更新しました。アプリを閉じて再度開いてください。",
    "gui.update.done_body":     "最新バージョンをインストールしました。このウィンドウを閉じて、起動ファイルをもう一度ダブルクリックしてください。",
    "gui.update.error":         "更新の確認に失敗しました：{msg}",
}
