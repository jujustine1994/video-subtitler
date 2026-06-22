"""
Gemini 影片字幕翻譯工具 — tkinter GUI
骨架依 C:\\Users\\CTH\\.claude\\project-rules\\windows-tool\\tkinter-ui\\skeleton.py
"""

import ctypes
import json
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

from dotenv import load_dotenv, set_key

from . import translator

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(SCRIPT_DIR, ".tool_config.json")
ENV_PATH = os.path.join(SCRIPT_DIR, ".env")

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
        self.root.title("Gemini 影片字幕翻譯工具")
        self.root.geometry("560x680")
        self.root.resizable(True, True)

        self.msg_queue: queue.Queue = queue.Queue()
        self.is_running = False
        self._current_theme = self._load_config().get("theme", "light")

        # 補跑所需的執行期狀態
        self._video_path = ""
        self._client = None
        self._segments = {}       # index -> srt_text or None
        self._segment_offsets = {}  # index -> start_time
        self._failed_vars = {}    # index -> tk.BooleanVar()
        self._output_path = ""

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
        t = THEMES.get(theme_key, THEMES["light"])
        try:
            import sv_ttk
            sv_ttk.set_theme(t["sv"])
        except ImportError:
            pass

        from tkinter import font as tkfont
        for fname in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            tkfont.nametofont(fname).configure(family="Microsoft JhengHei", size=12)

        style = ttk.Style()
        font = ("Microsoft JhengHei", 12)
        label_fg = t["label_fg"]

        style.configure("TButton", font=font)
        style.configure("TEntry", font=font)
        style.configure("TLabelframe.Label", font=font, foreground=t["frame_title"])
        for w in ("TLabel", "TCheckbutton", "TRadiobutton"):
            kw = {"font": font}
            if label_fg:
                kw["foreground"] = label_fg
            style.configure(w, **kw)

        self.log_text.config(bg=t["log_bg"], fg=t["log_fg"], insertbackground=t["log_fg"])
        self._current_theme = theme_key

    # ---- 設定視窗（僅外觀） ----

    def _open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("設定")
        win.resizable(False, False)
        win.grab_set()

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
            self._save_config({"theme": theme_var.get()})
            win.destroy()

        btn_row = ttk.Frame(win)
        btn_row.pack(pady=(0, 16))
        ttk.Button(btn_row, text="套用", command=_apply, width=10).pack(side="left", padx=4, ipady=4)
        ttk.Button(btn_row, text="取消", command=win.destroy, width=10).pack(side="left", padx=4, ipady=4)

    # ---- 設定檔 ----

    def _load_config(self) -> dict:
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_config(self, data: dict):
        try:
            cfg = self._load_config()
            cfg.update(data)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

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

        t = threading.Thread(target=self._worker_full_run, daemon=True)
        t.start()

    def _worker_full_run(self):
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

            self._log(f"共 {len(indices)} 段，開始處理...")
            self._run_segments(indices, len(indices))
            self._finish_run()
        except Exception as e:
            self._log(f"\n[ERROR] {e}")
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
                    on_log=self._log,
                    on_retry=lambda attempt, delay, idx=i: self._log(
                        f"   第 {idx + 1} 段失敗，{delay} 秒後重試（第 {attempt} 次）..."
                    ),
                )
                self._segments[i] = srt_seg
                self._log(f"   第 {i + 1} 段完成。")
            except Exception as e:
                self._segments[i] = None
                self._log(f"   第 {i + 1} 段重試 3 次後仍失敗：{e}")
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
        self._done(self._output_path, failed)

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

        t = threading.Thread(target=self._worker_retry, args=(selected,), daemon=True)
        t.start()

    def _worker_retry(self, selected):
        try:
            self._run_segments(selected, len(selected))
            self._finish_run()
        except Exception as e:
            self._log(f"\n[ERROR] {e}")
            self._fatal(str(e))

    # ---- 執行緒安全 UI 更新 ----

    def _log(self, msg: str):
        self.msg_queue.put(("log", msg))

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


def main():
    show_cth_banner()
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.update()
    root.attributes("-topmost", False)
    SubtitlerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
