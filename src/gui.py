"""
Gemini 影片字幕翻譯工具 — tkinter GUI
骨架依 C:\\Users\\CTH\\.claude\\project-rules\\windows-tool\\tkinter-ui\\skeleton.py
"""

import ctypes
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

from dotenv import load_dotenv, set_key

from . import i18n, translator
from .config import load_config, save_config
from .i18n import t
from .logtext import LOG_TEXT

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(SCRIPT_DIR, ".tool_config.json")
ENV_PATH = os.path.join(SCRIPT_DIR, ".env")


# ---- 執行紀錄（log）基礎設施 ----
# 規則見 windows-tool.md「執行紀錄」；核心限制：開檔→寫→關檔，不持有 handle（地雷十）。


def _find_project_root() -> str:
    """往上找 launcher.ps1 所在目錄＝專案根目錄。

    不可寫死 os.path.join(SCRIPT_DIR, "..", "logs")：主程式若在根目錄會算到專案外層
    （Documents\\Code\\logs），污染其他專案。此函式對「.py 在根」或「.py 在 src/」都正確，
    日後搬動也不會壞。本專案的 gui.py 在 src/，會往上一層找到根目錄的 launcher.ps1。
    """
    here = os.path.dirname(os.path.abspath(__file__))
    d = here
    while True:
        if os.path.exists(os.path.join(d, "launcher.ps1")):
            return d
        parent = os.path.dirname(d)
        if parent == d:      # 到磁碟根仍沒找到，退回自己所在目錄，至少不寫到專案外
            return here
        d = parent


LOG_DIR = os.path.join(_find_project_root(), "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")


def _write_log(msg: str, level: str = "INFO"):
    """寫一行到 logs/app.log。每次開檔→寫→關檔，不持有 handle（地雷十）。
    log 掛掉不能拖垮主程式；except OSError 也涵蓋兩個實例同時寫撞在一起。"""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] [{level:<5}] {msg}\n")
    except OSError:
        pass


def _write_log_header(msg: str):
    """任務起始行，唯一有完整日期的行。"""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"=== {time.strftime('%Y-%m-%d %H:%M:%S')} {msg} ===\n")
    except OSError:
        pass

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

THEMES = {
    "light": {
        "name": "清爽白", "sv": "light",
        "log_bg": "#F4F4F4", "log_fg": "#333333",
        "frame_title": "#1A6BAF", "label_fg": "",
        "btn_bg": "#0078D4", "btn_fg": "#FFFFFF",
        "win_bg": "#F3F3F3", "card_bg": "#FFFFFF",
        "border": "#D0D0D0", "pbar": "#0078D4",
        "header_bg": "#E8F0FB", "header_fg": "#1A6BAF",
    },
    "dark": {
        "name": "深色模式", "sv": "dark",
        "log_bg": "#1A1A1A", "log_fg": "#C8C8C8",
        "frame_title": "#60AAFF", "label_fg": "",
        "btn_bg": "#3A7BD5", "btn_fg": "#FFFFFF",
        "win_bg": "#202020", "card_bg": "#2A2A2A",
        "border": "#444444", "pbar": "#4A90E2",
        "header_bg": "#2A3A4D", "header_fg": "#60AAFF",
    },
    "financial": {
        "name": "金融藍", "sv": "light",
        "log_bg": "#F0F5FF", "log_fg": "#1B2B45",
        "frame_title": "#1B3A6B", "label_fg": "#1B3A6B",
        "btn_bg": "#1B3A6B", "btn_fg": "#F5C518",
        "win_bg": "#EEF2F8", "card_bg": "#FFFFFF",
        "border": "#BDD0EA", "pbar": "#1B3A6B",
        "header_bg": "#DCE6F5", "header_fg": "#1B3A6B",
    },
}


def show_cth_banner():
    b = "\033[90m"; c = "\033[96m"; y = "\033[93m"; r = "\033[0m"
    print(f"{b}/*  ================================  *\\{r}")
    print(f"{b} *                                    *{r}")
    print(f"{b} *    {c}██████╗████████╗██╗  ██╗{b}        *{r}")
    print(f"{b} *   {c}██╔════╝   ██║   ██║  ██║{b}        *{r}")
    print(f"{b} *   {c}██║        ██║   ███████║{b}        *{r}")
    print(f"{b} *   {c}██║        ██║   ██╔══██║{b}        *{r}")
    print(f"{b} *   {c}╚██████╗   ██║   ██║  ██║{b}        *{r}")
    print(f"{b} *    {c}╚═════╝   ╚═╝   ╚═╝  ╚═╝{b}        *{r}")
    print(f"{b} *                                    *{r}")
    print(f"{b} *          {y}created by CTH{b}            *{r}")
    print(f"{b}\\*  ================================  */{r}")
    print()


class SubtitlerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        # ⚠ 語言必須在建任何 widget 之前設好——t() 是建置時查一次表，
        # 設晚了介面會停在預設語言。
        self.cfg = self._load_config()
        i18n.set_lang(self.cfg.get("language"))

        self.root.title("Gemini 影片字幕翻譯工具")
        self.root.geometry("560x680")
        self.root.resizable(True, True)

        self.msg_queue: queue.Queue = queue.Queue()
        self.is_running = False
        self._current_theme = self.cfg.get("theme", "light")

        # 補跑所需的執行期狀態
        self._video_path = ""
        self._client = None
        self._segments = {}       # index -> srt_text or None
        self._segment_offsets = {}  # index -> start_time
        self._failed_vars = {}    # index -> tk.BooleanVar()
        self._output_path = ""
        self._task_start = 0.0    # 任務計時起點（三段式結果行用）

        self._build_ui()
        self._apply_theme(self._current_theme)
        self._load_api_key()
        self._poll_queue()

    # ---- UI 建置 ----

    def _build_ui(self):
        pad = {"padx": 14, "pady": 6}

        # === 影片檔案 ===
        frame_file = ttk.LabelFrame(self.root, text=" 影片檔案 ", padding=8)
        frame_file.grid(row=0, column=0, sticky="ew", **pad)
        frame_file.columnconfigure(0, weight=1)

        file_row = ttk.Frame(frame_file)
        file_row.pack(fill="x")
        file_row.columnconfigure(0, weight=1)

        self.file_var = tk.StringVar()
        ttk.Entry(file_row, textvariable=self.file_var, state="readonly", width=46).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(file_row, text="選擇影片", command=self._pick_file, width=10).grid(
            row=0, column=1
        )

        # === API Key ===
        frame_api = ttk.LabelFrame(self.root, text=" Gemini API Key ", padding=8)
        frame_api.grid(row=1, column=0, sticky="ew", **pad)

        api_row = tk.Frame(frame_api)
        api_row.pack(anchor="w")
        self.api_var = tk.StringVar()
        self.api_entry = ttk.Entry(api_row, textvariable=self.api_var, width=40, show="•")
        self.api_entry.pack(side="left", padx=(0, 8))
        ttk.Button(api_row, text="顯示", width=5, command=self._toggle_api_show).pack(
            side="left", padx=(0, 8)
        )
        self.save_key_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(api_row, text="記住", variable=self.save_key_var).pack(side="left")

        tk.Label(
            frame_api,
            text="🔒 API Key 僅儲存於本機 .env 檔，請勿將 Key 提供給他人。",
            foreground="gray", font=("Microsoft JhengHei", 11),
        ).pack(anchor="w", pady=(4, 0))

        # === 開始按鈕 ===
        frame_btn = tk.Frame(self.root)
        frame_btn.grid(row=2, column=0, pady=8)
        self.btn_start = ttk.Button(
            frame_btn, text="▶  開始翻譯", command=self._start, width=20
        )
        self.btn_start.pack(side="left", ipady=6)
        ttk.Button(
            frame_btn, text="⚙", command=self._open_settings, width=4
        ).pack(side="left", ipady=6, padx=(8, 0))

        # === 處理進度 ===
        frame_progress = ttk.LabelFrame(self.root, text=" 處理進度 ", padding=8)
        frame_progress.grid(row=3, column=0, sticky="nsew", padx=14, pady=(0, 6))
        frame_progress.columnconfigure(0, weight=1)
        frame_progress.rowconfigure(2, weight=1)

        self.progress_label = ttk.Label(frame_progress, text="等待開始...")
        self.progress_label.grid(row=0, column=0, sticky="w")
        self.progress_bar = ttk.Progressbar(frame_progress, mode="determinate")
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(4, 8))
        self.log_text = scrolledtext.ScrolledText(
            frame_progress, width=60, height=10, state="disabled",
            font=("Consolas", 12)
        )
        self.log_text.grid(row=2, column=0, sticky="nsew")

        # === 失敗段補跑區（預設隱藏，勾選框列表可捲動，固定高度不撐大視窗） ===
        self.frame_retry = ttk.LabelFrame(self.root, text=" 失敗段落 ", padding=8)
        self.retry_label = ttk.Label(self.frame_retry, text="")
        self.retry_label.pack(anchor="w")

        retry_scroll_area = tk.Frame(self.frame_retry, height=110)
        retry_scroll_area.pack(fill="x", pady=(4, 8))
        retry_scroll_area.pack_propagate(False)

        self.retry_canvas = tk.Canvas(retry_scroll_area, highlightthickness=0)
        retry_scrollbar = ttk.Scrollbar(
            retry_scroll_area, orient="vertical", command=self.retry_canvas.yview
        )
        self.retry_canvas.configure(yscrollcommand=retry_scrollbar.set)
        self.retry_canvas.pack(side="left", fill="both", expand=True)
        retry_scrollbar.pack(side="right", fill="y")

        self.retry_checks_frame = tk.Frame(self.retry_canvas)
        self._retry_checks_window = self.retry_canvas.create_window(
            (0, 0), window=self.retry_checks_frame, anchor="nw"
        )
        self.retry_checks_frame.bind(
            "<Configure>",
            lambda e: self.retry_canvas.configure(scrollregion=self.retry_canvas.bbox("all")),
        )
        self.retry_canvas.bind(
            "<Configure>",
            lambda e: self.retry_canvas.itemconfigure(self._retry_checks_window, width=e.width),
        )

        self.btn_retry = ttk.Button(
            self.frame_retry, text="重試所選段落", command=self._retry_selected
        )
        self.btn_retry.pack(anchor="w")
        # frame_retry 預設不 grid，有失敗段時才顯示

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)

        self.log_text.config(state="normal")
        self.log_text.insert("1.0", "選擇影片並輸入 API Key 後按「開始翻譯」。\n")
        self.log_text.config(state="disabled")

        self._build_status_bar()

    def _build_status_bar(self):
        sep = ttk.Separator(self.root, orient="horizontal")
        sep.grid(row=98, column=0, sticky="ew")
        self._status_bar = tk.Label(
            self.root, text="就緒", anchor="w", padx=10, pady=4,
            font=("Microsoft JhengHei", 11), foreground="gray",
        )
        self._status_bar.grid(row=99, column=0, sticky="ew")

    # ---- 主題 ----

    def _apply_theme(self, theme_key: str):
        # 變數名不可叫 t——會遮蔽 i18n.t()，同 scope 的 t("gui.x") 會靜默改成對 dict 取值
        theme = THEMES.get(theme_key, THEMES["light"])
        try:
            import sv_ttk
            sv_ttk.set_theme(theme["sv"])
        except ImportError:
            pass

        from tkinter import font as tkfont
        for fname in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            tkfont.nametofont(fname).configure(family="Microsoft JhengHei", size=12)

        style = ttk.Style()
        font = ("Microsoft JhengHei", 12)
        label_fg = theme["label_fg"]

        style.configure("TButton", font=font)
        style.configure("TEntry", font=font)
        style.configure("TLabelframe.Label", font=font, foreground=theme["frame_title"])
        for w in ("TLabel", "TCheckbutton", "TRadiobutton"):
            kw = {"font": font}
            if label_fg:
                kw["foreground"] = label_fg
            style.configure(w, **kw)

        self.log_text.config(bg=theme["log_bg"], fg=theme["log_fg"],
                             insertbackground=theme["log_fg"])
        self._current_theme = theme_key

    # ---- 設定視窗（僅外觀） ----

    def _open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("設定")
        win.resizable(False, False)
        win.grab_set()
        self.settings_win = win

        self._build_language_row(win)

        frame = ttk.Frame(win, padding=16)
        frame.pack()
        ttk.Label(frame, text="配色主題").pack(anchor="w", pady=(0, 10))

        theme_var = tk.StringVar(value=self._current_theme)
        for key, info in THEMES.items():
            ttk.Radiobutton(frame, text=info["name"], variable=theme_var, value=key).pack(
                anchor="w", pady=4
            )

        def _apply():
            self._apply_theme(theme_var.get())
            new_lang = self._selected_lang_code()
            lang_changed = new_lang != self._lang_saved_code
            # theme 的值是機器碼（light/dark/financial），language 是語言代號，
            # 兩者都不是畫面上顯示的字——顯示名走 i18n，存檔值永遠固定。
            self._save_config({"theme": theme_var.get(), "language": new_lang})
            win.destroy()
            # 只有語言真的變更才打擾使用者——改主題不該跳重啟視窗
            if lang_changed:
                self._prompt_restart_for_language()

        btn_row = ttk.Frame(win)
        btn_row.pack(pady=(0, 16))
        ttk.Button(btn_row, text="套用", command=_apply, width=10).pack(side="left", padx=4, ipady=4)
        ttk.Button(btn_row, text="取消", command=win.destroy, width=10).pack(side="left", padx=4, ipady=4)

    # ---- 語言 ----

    def _build_language_row(self, popup):
        """設定視窗最上方的語言列。選項由 i18n.LANGUAGES 動態生成，
        新增語言時這裡一個字都不必改。

        標籤固定英文 "Language:"、選項用各語言自稱——任何語言下都認得出來。
        """
        lang_frame = ttk.Frame(popup)
        lang_frame.pack(anchor="w", padx=16, pady=(14, 0))
        ttk.Label(lang_frame, text="Language:").pack(side="left", padx=(0, 8))

        self._lang_choices = i18n.available_languages()
        # ⚠ 讀 config 不讀 i18n.get_lang()：set_lang() 只在 __init__ 跑一次，
        # 使用者選了新語言但按「稍後」不重啟時，runtime 語言還是舊的。用 runtime
        # 值當基準的話，下次開設定按套用會把他的選擇默默寫回去。
        saved = self.cfg.get("language", "")
        self._lang_saved_code = saved if i18n.is_supported(saved) else i18n.DEFAULT_LANG
        names = [name for _, name in self._lang_choices]
        current = next((n for c, n in self._lang_choices if c == self._lang_saved_code),
                       names[0])
        self.settings_lang_var = tk.StringVar(value=current)
        self.settings_lang_combo = ttk.Combobox(
            lang_frame, textvariable=self.settings_lang_var,
            values=names, width=14, state="readonly",
        )
        self.settings_lang_combo.pack(side="left")

    def _selected_lang_code(self) -> str:
        """把下拉選單顯示的名稱換回代號。取不到就維持原設定，不亂改。"""
        chosen = self.settings_lang_var.get()
        for code, name in self._lang_choices:
            if name == chosen:
                return code
        return self._lang_saved_code

    def _prompt_restart_for_language(self):
        """語言變更後問是否重啟。

        視窗全英文：此刻介面還是舊語言、使用者要的是新語言，用任一方都尷尬，
        英文最中立。**重開才生效，不做即時切換**（規則見 windows-tool.md）。
        """
        if messagebox.askyesno(
            "Language Changed",
            "Restart the app to apply the new language.\n\nRestart now?",
        ):
            self._restart_app()

    def _restart_app(self):
        """起一個新行程再關掉自己。

        不用 os.execv：Windows 上它會就地覆寫當前行程，tkinter 還沒釋放的視窗
        handle 可能殘留，看起來像關不掉的殭屍視窗。
        """
        try:
            subprocess.Popen([sys.executable, *sys.argv], close_fds=True)
        except OSError:
            # 起不了新行程就什麼都不做——使用者下次自己開一樣會生效，
            # 這裡把舊視窗關掉反而讓人以為程式壞了
            return
        self.root.destroy()

    # ---- 設定檔 ----

    def _load_config(self) -> dict:
        """讀設定。實作在 config.py——首次啟動的語言視窗在 App 建立**之前**就要
        讀寫設定，所以讀寫邏輯必須住在模組層級而不是這個類別裡。"""
        return load_config(CONFIG_PATH)

    def _save_config(self, data: dict):
        cfg = self._load_config()
        cfg.update(data)
        self.cfg = cfg
        save_config(cfg, CONFIG_PATH)

    # ---- API Key ----

    def _toggle_api_show(self):
        self.api_entry.config(show="" if self.api_entry.cget("show") else "•")

    def _load_api_key(self):
        load_dotenv(ENV_PATH)
        key = os.getenv("GEMINI_API_KEY", "")
        if key:
            self.api_var.set(key)

    # ---- 檔案選取 ----

    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="請選擇影片檔案",
            filetypes=[("影片檔案", "*.mp4 *.mkv *.avi *.mov *.wmv"), ("所有檔案", "*.*")],
        )
        if path:
            self.file_var.set(path)

    # ---- 執行：開始翻譯 ----

    def _start(self):
        video_path = self.file_var.get().strip()
        if not video_path or not os.path.isfile(video_path):
            messagebox.showerror("錯誤", "請選擇有效的影片檔案")
            return

        api_key = self.api_var.get().strip()
        if not api_key:
            messagebox.showerror("錯誤", "請輸入 Gemini API Key")
            return
        if self.save_key_var.get():
            set_key(ENV_PATH, "GEMINI_API_KEY", api_key)

        self.frame_retry.grid_remove()
        for w in self.retry_checks_frame.winfo_children():
            w.destroy()
        self._failed_vars = {}

        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")
        self.progress_bar["value"] = 0
        self.progress_label.config(text="準備中...")
        self.is_running = True
        self.btn_start.config(state="disabled")
        self._set_status("執行中，請稍候...", "info")

        self._video_path = video_path
        self._client = translator.make_client(api_key)
        self._segments = {}
        self._segment_offsets = {}

        worker = threading.Thread(target=self._worker_full_run, daemon=True)
        worker.start()

    def _worker_full_run(self):
        self._task_start = time.time()
        try:
            duration = translator.get_video_duration(self._video_path)
            self._log(f"影片總時長: {int(duration // 60)} 分 {int(duration % 60)} 秒")

            num_segments = int(duration // translator.CHUNK_DURATION) + 1
            indices = []
            for i in range(num_segments):
                start_time = i * translator.CHUNK_DURATION
                if start_time >= duration:
                    break
                indices.append(i)
                self._segment_offsets[i] = start_time

            # ---- 任務起始：一行，關鍵設定（模型、段數）塞同一行 ----
            _write_log_header(LOG_TEXT["task_start_full"].format(
                name=os.path.basename(self._video_path),
                model=translator.MODEL_NAME, count=len(indices),
            ))
            self._log(f"共 {len(indices)} 段，開始處理...")
            self._run_segments(indices, len(indices))
            self._finish_run()
        except Exception as e:
            # UI 可見完整錯誤（ephemeral）；落檔只記型別，絕不寫 str(e)（可能挾帶金鑰 URL）
            self._log(f"\n[ERROR] {type(e).__name__}", "FAIL")
            self._log_task_result(ok=False)
            self._fatal(str(e))

    def _run_segments(self, indices, total_for_progress):
        done_count = 0
        for i in indices:
            start_time = self._segment_offsets[i]
            self._log(f"\n-> 正在處理第 {i + 1} 段 (起始時間: {int(start_time // 60)} 分)...")
            temp_audio = os.path.join(SCRIPT_DIR, f"temp_seg_{i}.mp3")
            try:
                translator.extract_audio_segment(
                    self._video_path, start_time, translator.CHUNK_DURATION, temp_audio
                )
                srt_seg = translator.translate_segment(
                    self._client, temp_audio, i, start_time,
                    # 一般進度訊息只推 UI，不落檔
                    on_log=lambda m: self._log(m),
                    on_retry=lambda attempt, delay, idx=i: self._log(
                        f"   第 {idx + 1} 段失敗，{delay} 秒後重試（第 {attempt} 次）..."
                    ),
                    # 已消毒的錯誤摘要（型別 + status code + 重試次數）：
                    # ui_msg 推畫面、log_msg 落檔為 ERROR 行（固定繁中）
                    on_error=lambda ui_msg, log_msg: self._log(
                        ui_msg, "ERROR", log_msg=log_msg),
                )
                self._segments[i] = srt_seg
                self._log(f"   第 {i + 1} 段完成。")
            except Exception as e:
                self._segments[i] = None
                # ERROR 行已由 translator 的 on_error 落檔（含 status code）；此處只推 UI，不寫 str(e)
                self._log(f"   第 {i + 1} 段重試後仍失敗（{type(e).__name__}）")
            finally:
                if os.path.exists(temp_audio):
                    os.remove(temp_audio)
            done_count += 1
            self._set_progress(done_count, total_for_progress, f"{done_count} / {total_for_progress} 段完成")

    def _finish_run(self):
        self._merge_and_write()
        failed = sorted(i for i, v in self._segments.items() if v is None)
        if failed:
            self._log(f"\n以下段落失敗：第 {', '.join(str(i + 1) for i in failed)} 段")
            self._set_status(f"完成，但有 {len(failed)} 段失敗", "error")
        else:
            self._set_status("已完成！", "success")
        # ---- 任務結束：成功/失敗 + 耗時 ----
        self._log_task_result(ok=not failed)
        self._done(self._output_path, failed)

    def _log_task_result(self, ok: bool):
        elapsed = int(time.time() - getattr(self, "_task_start", time.time()))
        _write_log(
            LOG_TEXT["task_ok" if ok else "task_fail"].format(
                minutes=elapsed // 60, seconds=elapsed % 60),
            "OK" if ok else "FAIL",
        )

    def _merge_and_write(self):
        ordered = [self._segments[i] for i in sorted(self._segments) if self._segments[i] is not None]
        merged = translator.renumber_srt(translator.enforce_max_duration("\n".join(ordered)))
        self._output_path = os.path.splitext(self._video_path)[0] + ".srt"
        with open(self._output_path, "w", encoding="utf-8") as f:
            f.write(merged)
        self._log(f"\n字幕已輸出: {self._output_path}")

    # ---- 失敗段補跑 ----

    def _retry_selected(self):
        selected = [i for i, var in self._failed_vars.items() if var.get()]
        if not selected:
            messagebox.showinfo("提示", "請至少勾選一個失敗段落")
            return

        self.btn_retry.config(state="disabled")
        self.is_running = True
        self.btn_start.config(state="disabled")
        self._set_status("重試中，請稍候...", "info")
        self._log(f"\n重試第 {', '.join(str(i + 1) for i in selected)} 段...")

        worker = threading.Thread(target=self._worker_retry, args=(selected,), daemon=True)
        worker.start()

    def _worker_retry(self, selected):
        self._task_start = time.time()
        # ---- 任務起始：補跑，關鍵設定塞同一行 ----
        _write_log_header(LOG_TEXT["task_start_retry"].format(
            name=os.path.basename(self._video_path),
            model=translator.MODEL_NAME, count=len(selected),
        ))
        try:
            self._run_segments(selected, len(selected))
            self._finish_run()
        except Exception as e:
            self._log(f"\n[ERROR] {type(e).__name__}", "FAIL")
            self._log_task_result(ok=False)
            self._fatal(str(e))

    # ---- 執行緒安全 UI 更新 ----

    def _log(self, ui_msg: str, level: str = "INFO", log_msg: str | None = None):
        """一個呼叫同時推 UI queue +（可選）寫檔，避免維護兩套呼叫而漏記。

        ui_msg 走 i18n（跟著介面語言）、log_msg 走 logtext（**固定繁中**）——
        log 是給維護者除錯用的，跟著使用者語言變等於自廢。

        **預設不落檔（fail-closed）**：要落檔就明確給 log_msg。進度訊息
        （上傳中、切割完成）對 debug 沒用，只推 UI；落檔的只有任務起始
        （另走 _write_log_header）、錯誤、任務結果三種。
        """
        if log_msg is not None:
            _write_log(log_msg, level)
        self.msg_queue.put(("log", ui_msg))

    def _set_progress(self, current, total, label):
        self.msg_queue.put(("progress", (current, total, label)))

    def _set_status(self, msg, level="info"):
        self.msg_queue.put(("status", (msg, level)))

    def _done(self, output_path, failed_indices):
        self.msg_queue.put(("done", (output_path, failed_indices)))

    def _fatal(self, msg):
        self.msg_queue.put(("fatal", msg))

    def _poll_queue(self):
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()
                if msg_type == "log":
                    self.log_text.config(state="normal")
                    self.log_text.insert("end", data + "\n")
                    self.log_text.see("end")
                    self.log_text.config(state="disabled")
                elif msg_type == "progress":
                    current, total, label = data
                    self.progress_bar["maximum"] = total
                    self.progress_bar["value"] = current
                    self.progress_label.config(text=label)
                elif msg_type == "status":
                    msg, level = data
                    colors = {"info": "gray", "success": "#2E7D32", "error": "#C62828"}
                    self._status_bar.config(text=msg, foreground=colors.get(level, "gray"))
                elif msg_type == "done":
                    output_path, failed_indices = data
                    self.is_running = False
                    self.btn_start.config(state="normal")
                    self.btn_retry.config(state="normal")
                    self._show_failed_segments(failed_indices)
                    if not failed_indices:
                        messagebox.showinfo("完成", f"已完成：\n{output_path}")
                elif msg_type == "fatal":
                    self.is_running = False
                    self.btn_start.config(state="normal")
                    self.progress_label.config(text="發生錯誤，請查看上方記錄")
                    self._set_status(f"致命錯誤：{data}", "error")
                    messagebox.showerror("錯誤", data)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _show_failed_segments(self, failed_indices):
        for w in self.retry_checks_frame.winfo_children():
            w.destroy()
        self._failed_vars = {}

        if not failed_indices:
            self.frame_retry.grid_remove()
            return

        self.retry_label.config(text=f"以下段落失敗，可勾選後重試：")
        for i in failed_indices:
            var = tk.BooleanVar(value=True)
            self._failed_vars[i] = var
            ttk.Checkbutton(
                self.retry_checks_frame, text=f"第 {i + 1} 段", variable=var
            ).pack(anchor="w")
        self.frame_retry.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 6))


def _pick_language_on_first_run(root) -> None:
    """首次啟動時問一次語言，選完寫進設定檔，之後不再出現。

    視窗刻意**不翻譯**：這時候還不知道使用者要哪個語言，用任一種當說明都
    在賭。只有一個英文抬頭，其餘全是各語言的自稱，看得懂哪個就點哪個。

    直接關掉視窗＝接受第一個選項並**照樣存檔**——需求是「選完就記住不要再
    跳」，關掉還一直跳才是煩人。選錯了在設定視窗隨時能改。
    """
    cfg = load_config(CONFIG_PATH)
    if i18n.is_supported(cfg.get("language", "")):
        return                      # 選過了，直接進主畫面（不建任何 widget）

    choices = i18n.available_languages()
    chosen = {"code": choices[0][0]}

    dlg = tk.Toplevel(root)
    dlg.title("Language")
    dlg.resizable(False, False)
    dlg.attributes("-topmost", True)

    ttk.Label(dlg, text="Select your language",
              font=("", 12, "bold")).pack(padx=28, pady=(20, 4))
    ttk.Label(dlg, text="You can change this later in Settings.",
              foreground="#555555").pack(padx=28, pady=(0, 14))

    def _choose(code: str) -> None:
        chosen["code"] = code
        dlg.destroy()

    for code, name in choices:
        ttk.Button(dlg, text=name, width=20,
                   command=lambda c=code: _choose(c)).pack(padx=28, pady=3)
    ttk.Frame(dlg, height=10).pack()

    dlg.update_idletasks()
    x = root.winfo_rootx() + (root.winfo_width() - dlg.winfo_width()) // 2
    y = root.winfo_rooty() + (root.winfo_height() - dlg.winfo_height()) // 3
    dlg.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    dlg.grab_set()
    dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)   # 關掉＝用預設值，照樣存
    root.wait_window(dlg)

    cfg["language"] = chosen["code"]
    save_config(cfg, CONFIG_PATH)


def main():
    show_cth_banner()
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.update()
    root.attributes("-topmost", False)
    _pick_language_on_first_run(root)
    SubtitlerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
