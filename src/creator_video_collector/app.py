from __future__ import annotations

import queue
import re
import subprocess
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, Optional

import tkinter as tk

from . import __version__
from .config import (
    APP_ICON,
    APP_NAME,
    APP_STATUS_TEXT,
    APP_TAGLINE,
    DARK_PALETTE,
    DEFAULT_DOWNLOAD_PATH,
    DEFAULT_SUBTITLE_LANGS,
    LIGHT_PALETTE,
    MODE_OPTIONS,
    RESOLUTION_OPTIONS,
    SPLASH_DURATION_MS,
)
from .downloader import build_download_command, ensure_tool_exists, fetch_metadata, run_command_stream
from .subtitles import clean_subtitle_file_to_txt, find_subtitle_files


class CreatorVideoCollectorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1120x780")
        self.root.minsize(980, 680)

        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")
        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.quality_formats: Dict[str, str] = {}

        self.url_var = tk.StringVar()
        self.path_var = tk.StringVar(value=str(DEFAULT_DOWNLOAD_PATH))
        self.mode_var = tk.StringVar(value=MODE_OPTIONS[0])
        self.resolution_var = tk.StringVar(value="720")
        self.quality_var = tk.StringVar(value="Auto: 720p or best available")
        self.sub_lang_var = tk.StringVar(value=DEFAULT_SUBTITLE_LANGS)
        self.status_var = tk.StringVar(value="Ready")
        self.meta_title_var = tk.StringVar(value="")
        self.meta_info_var = tk.StringVar(value="")
        self.log_count_var = tk.StringVar(value="")
        self.progress_var = tk.DoubleVar(value=0)
        self.log_has_real_content = False
        self.dark_mode_var = tk.BooleanVar(value=False)
        self.playlist_var = tk.BooleanVar(value=False)

        self.download_video_var = tk.BooleanVar(value=True)
        self.download_audio_var = tk.BooleanVar(value=False)
        self.download_subtitles_var = tk.BooleanVar(value=True)
        self.clean_txt_var = tk.BooleanVar(value=True)
        self.download_thumbnail_var = tk.BooleanVar(value=True)
        self.download_description_var = tk.BooleanVar(value=False)
        self.download_info_json_var = tk.BooleanVar(value=False)

        self.build_ui()
        self.apply_mode_preset()
        self.apply_theme()
        self.root.after(150, self.process_log_queue)

    def build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(4, weight=1)

        header = ttk.Frame(self.root, style="Header.TFrame", padding=(20, 8, 20, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(2, weight=1)

        self.icon_canvas = tk.Canvas(header, width=28, height=28, highlightthickness=0, bd=0)
        self.icon_canvas.grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.draw_header_icon()
        ttk.Label(header, text=APP_NAME, style="HeaderTitle.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(header, text="Video, subtitle & transcript collector", style="HeaderMuted.TLabel").grid(row=0, column=2, sticky="w", padx=(12, 0))
        ttk.Label(header, text=f"v{__version__}", style="Version.TLabel").grid(row=0, column=3, sticky="e", padx=(8, 8))
        ttk.Checkbutton(header, text="Dark", variable=self.dark_mode_var, command=self.apply_theme, style="Switch.TCheckbutton").grid(row=0, column=4, sticky="e")

        source = ttk.LabelFrame(self.root, text="Source", padding=14, style="Panel.TLabelframe")
        source.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 12))
        source.columnconfigure(0, weight=1)

        ttk.Label(source, text="Video URL", style="Field.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(source, textvariable=self.url_var, style="Mono.TEntry").grid(row=1, column=0, sticky="ew", pady=(4, 8))
        self.check_btn = ttk.Button(source, text="Check URL", command=self.start_check_url, style="Primary.TButton")
        self.check_btn.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(4, 8))

        self.meta_frame = ttk.Frame(source, style="Meta.TFrame", padding=(10, 7, 10, 7))
        self.meta_frame.columnconfigure(0, weight=1)
        ttk.Label(self.meta_frame, textvariable=self.meta_title_var, style="MetaTitle.TLabel").grid(row=0, column=0, sticky="ew")
        ttk.Label(self.meta_frame, textvariable=self.meta_info_var, style="MetaMuted.TLabel").grid(row=1, column=0, sticky="ew", pady=(2, 0))
        ttk.Label(self.meta_frame, text="Verified", style="Verified.TLabel").grid(row=0, column=1, rowspan=2, sticky="e", padx=(10, 0))

        ttk.Label(source, text="Download folder", style="Field.TLabel").grid(row=3, column=0, sticky="w")
        ttk.Entry(source, textvariable=self.path_var, style="Mono.TEntry").grid(row=4, column=0, sticky="ew", pady=(4, 0))
        ttk.Button(source, text="Browse", command=self.choose_folder).grid(row=4, column=1, sticky="ew", padx=(10, 0), pady=(4, 0))

        settings = ttk.LabelFrame(self.root, text="Download Settings", padding=14, style="Panel.TLabelframe")
        settings.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 12))
        for col in range(4):
            settings.columnconfigure(col, weight=1)

        self.add_combo(settings, "Mode", self.mode_var, MODE_OPTIONS, 0, 0, on_select=self.apply_mode_preset)
        self.add_combo(settings, "Fallback quality", self.resolution_var, RESOLUTION_OPTIONS, 0, 1)
        self.quality_box = self.add_combo(settings, "Real quality", self.quality_var, [self.quality_var.get()], 0, 2)
        ttk.Label(settings, text="Subtitle languages", style="Field.TLabel").grid(row=0, column=3, sticky="w", padx=(8, 0))
        ttk.Entry(settings, textvariable=self.sub_lang_var, style="App.TEntry").grid(row=1, column=3, sticky="ew", padx=(8, 0), pady=(4, 12))

        options = ttk.Frame(settings, style="App.TFrame")
        options.grid(row=2, column=0, columnspan=4, sticky="ew")
        labels = [
            ("Video MP4", self.download_video_var),
            ("Audio MP3", self.download_audio_var),
            ("Subtitle files", self.download_subtitles_var),
            ("Clean TXT", self.clean_txt_var),
            ("Cover image", self.download_thumbnail_var),
            ("Description", self.download_description_var),
            ("info.json", self.download_info_json_var),
            ("Allow playlists", self.playlist_var),
        ]
        for idx, (label, var) in enumerate(labels):
            style = "Warning.TCheckbutton" if label == "Allow playlists" else "App.TCheckbutton"
            ttk.Checkbutton(options, text=label, variable=var, style=style).grid(row=idx // 4, column=idx % 4, sticky="w", padx=(0, 22), pady=5)

        actions = ttk.Frame(self.root, style="App.TFrame", padding=(20, 0, 20, 10))
        actions.grid(row=3, column=0, sticky="ew")
        actions.columnconfigure(7, weight=1)

        self.download_btn = ttk.Button(actions, text="Start Download", command=self.start_download, style="Primary.TButton")
        self.download_btn.grid(row=0, column=0, padx=(0, 8))
        self.new_download_btn = ttk.Button(actions, text="New Download", command=self.reset_workflow)
        ttk.Button(actions, text="Clean Subtitle", command=self.clean_existing_subtitle_dialog).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(actions, text="Open Folder", command=self.open_folder).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(actions, text="Copy Log", command=self.copy_log).grid(row=0, column=3, padx=(0, 8))
        ttk.Button(actions, text="Save Log", command=self.save_log).grid(row=0, column=4, padx=(0, 8))
        ttk.Button(actions, text="Clear Log", command=self.clear_log).grid(row=0, column=5, padx=(0, 8))
        self.status_label = ttk.Label(actions, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.grid(row=0, column=7, sticky="e")

        self.progress = ttk.Progressbar(actions, variable=self.progress_var, maximum=100, mode="determinate", style="App.Horizontal.TProgressbar")
        self.progress.grid(row=1, column=0, columnspan=8, sticky="ew", pady=(10, 0))

        log_frame = ttk.LabelFrame(self.root, text="Output Log", padding=10, style="Panel.TLabelframe")
        log_frame.grid(row=4, column=0, sticky="nsew", padx=20, pady=(0, 20))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, height=18, wrap="word", undo=True, relief="flat", borderwidth=0, padx=12, pady=10)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.bind("<Control-a>", self.select_all_log)
        self.configure_log_tags()
        self.show_log_placeholder()

    def draw_header_icon(self) -> None:
        self.icon_canvas.delete("all")
        self.icon_canvas.create_rectangle(2, 5, 22, 19, outline="#3b82f6", width=2)
        self.icon_canvas.create_polygon(9, 9, 9, 16, 17, 12, fill="#3b82f6", outline="")
        self.icon_canvas.create_line(13, 19, 13, 26, fill="#22c55e", width=2, capstyle="round")
        self.icon_canvas.create_line(9, 23, 13, 27, 17, 23, fill="#22c55e", width=2, capstyle="round", joinstyle="round")
        self.icon_canvas.create_line(25, 7, 28, 7, fill="#94a3b8", width=1)
        self.icon_canvas.create_line(25, 11, 28, 11, fill="#94a3b8", width=1)
        self.icon_canvas.create_line(25, 15, 28, 15, fill="#94a3b8", width=1)

    def show_metadata(self, title: str, info: str) -> None:
        self.meta_title_var.set(title)
        self.meta_info_var.set(info)
        if not self.meta_frame.winfo_ismapped():
            self.meta_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))

    def hide_metadata(self) -> None:
        self.meta_title_var.set("")
        self.meta_info_var.set("")
        if self.meta_frame.winfo_ismapped():
            self.meta_frame.grid_remove()

    def set_status(self, text: str, state: str = "neutral") -> None:
        self.status_var.set(text)
        self.status_label.configure(style=f"Status.{state}.TLabel")

    def configure_log_tags(self) -> None:
        self.log_text.tag_configure("error", foreground="#ef4444")
        self.log_text.tag_configure("success", foreground="#22c55e")
        self.log_text.tag_configure("info", foreground="#3b82f6")
        self.log_text.tag_configure("warning", foreground="#f59e0b")
        self.log_text.tag_configure("placeholder", foreground="#6b7280")

    def log_tag_for(self, message: str) -> str | None:
        lower = message.lower()
        if "error" in lower or "failed" in lower or "[✗]" in message:
            return "error"
        if "warning" in lower or "hint:" in lower:
            return "warning"
        if "done" in lower or "saved" in lower or "100%" in message or "[✓]" in message:
            return "success"
        if lower.startswith("[info]") or "title:" in lower or "subtitle" in lower:
            return "info"
        return None

    def show_log_placeholder(self) -> None:
        self.log_text.insert("end", "Log output will appear here after checking or downloading.\n", "placeholder")

    def clear_log_content(self) -> None:
        self.log_text.delete("1.0", "end")
        self.log_has_real_content = False
        self.log_count_var.set("")

    def add_combo(self, parent: ttk.Frame, label: str, variable: tk.StringVar, values: list[str], row: int, col: int, on_select=None):
        ttk.Label(parent, text=label, style="Field.TLabel").grid(row=row, column=col, sticky="w", padx=(0 if col == 0 else 8, 0))
        combo = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", style="App.TCombobox")
        combo.grid(row=row + 1, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0), pady=(4, 12))
        if on_select:
            combo.bind("<<ComboboxSelected>>", lambda _event: on_select())
        return combo

    def apply_theme(self) -> None:
        palette = DARK_PALETTE if self.dark_mode_var.get() else LIGHT_PALETTE
        self.root.configure(bg=palette["window"])

        self.style.configure("Header.TFrame", background=palette["window"], bordercolor=palette["border"])
        self.style.configure("App.TFrame", background=palette["window"])
        self.style.configure("Panel.TLabelframe", background=palette["surface"], foreground=palette["text"], bordercolor=palette["border"], relief="solid")
        self.style.configure("Panel.TLabelframe.Label", background=palette["window"], foreground=palette["text"], font=("Arial", 10, "bold"))
        self.style.configure("HeaderTitle.TLabel", background=palette["window"], foreground=palette["text"], font=("Arial", 14, "bold"))
        self.style.configure("HeaderMuted.TLabel", background=palette["window"], foreground=palette["muted"], font=("Arial", 10))
        self.style.configure("Version.TLabel", background=palette["window"], foreground=palette["muted"], font=("Courier", 9), bordercolor=palette["border"], padding=(6, 2))
        self.style.configure("Title.TLabel", background=palette["window"], foreground=palette["text"], font=("Arial", 22, "bold"))
        self.style.configure("Muted.TLabel", background=palette["window"], foreground=palette["muted"], font=("Arial", 10))
        self.style.configure("Field.TLabel", background=palette["surface"], foreground=palette["muted"], font=("Arial", 8, "bold"))
        self.style.configure("Meta.TFrame", background=palette["surface_alt"], bordercolor=palette["border"], relief="solid")
        self.style.configure("MetaTitle.TLabel", background=palette["surface_alt"], foreground=palette["text"], font=("Arial", 10, "bold"))
        self.style.configure("MetaMuted.TLabel", background=palette["surface_alt"], foreground=palette["muted"], font=("Arial", 9))
        self.style.configure("Verified.TLabel", background=palette["surface_alt"], foreground=palette["success"], font=("Arial", 8, "bold"), padding=(7, 2))
        self.style.configure("Status.TLabel", background=palette["window"], foreground=palette["muted"], font=("Courier", 10, "bold"))
        self.style.configure("Status.neutral.TLabel", background=palette["window"], foreground=palette["muted"], font=("Courier", 10, "bold"))
        self.style.configure("Status.checking.TLabel", background=palette["window"], foreground=palette["warning"], font=("Courier", 10, "bold"))
        self.style.configure("Status.downloading.TLabel", background=palette["window"], foreground=palette["accent"], font=("Courier", 10, "bold"))
        self.style.configure("Status.warning.TLabel", background=palette["window"], foreground=palette["warning"], font=("Courier", 10, "bold"))
        self.style.configure("Status.success.TLabel", background=palette["window"], foreground=palette["success"], font=("Courier", 10, "bold"))
        self.style.configure("Status.error.TLabel", background=palette["window"], foreground=palette["error"], font=("Courier", 10, "bold"))
        self.style.configure("App.TCheckbutton", background=palette["surface"], foreground=palette["text"], font=("Arial", 9))
        self.style.configure("Warning.TCheckbutton", background=palette["surface"], foreground=palette["warning"], font=("Arial", 9, "bold"))
        self.style.configure("Switch.TCheckbutton", background=palette["window"], foreground=palette["text"])
        self.style.configure("TButton", padding=(10, 6), background=palette["surface_alt"], foreground=palette["text"], bordercolor=palette["border"])
        self.style.configure("Primary.TButton", padding=(14, 7), background=palette["accent"], foreground="#ffffff", bordercolor=palette["accent"], font=("Arial", 10, "bold"))
        self.style.configure("App.TEntry", fieldbackground=palette["surface_alt"], foreground=palette["text"], bordercolor=palette["border"], insertcolor=palette["text"])
        self.style.configure("Mono.TEntry", fieldbackground=palette["surface_alt"], foreground=palette["text"], bordercolor=palette["border"], insertcolor=palette["text"], font=("Courier", 10))
        self.style.configure("App.TCombobox", fieldbackground=palette["surface_alt"], foreground=palette["text"], bordercolor=palette["border"], arrowcolor=palette["text"])
        self.style.map("App.TCombobox", fieldbackground=[("readonly", palette["surface"])], foreground=[("readonly", palette["text"])])
        self.style.configure("App.Horizontal.TProgressbar", troughcolor=palette["surface_alt"], background=palette["success"], bordercolor=palette["border"])
        self.log_text.configure(bg=palette["log_bg"], fg=palette["log_fg"], insertbackground=palette["log_fg"], selectbackground=palette["accent"], selectforeground="#ffffff", font=("Courier", 10))
        if hasattr(self, "icon_canvas"):
            self.icon_canvas.configure(bg=palette["window"])
            self.draw_header_icon()

    def apply_mode_preset(self) -> None:
        mode = self.mode_var.get()
        self.download_video_var.set(mode in {"Video + TXT + Cover", "Video only", "Everything"})
        self.download_audio_var.set(mode == "Audio only MP3")
        self.download_subtitles_var.set(mode in {"Video + TXT + Cover", "TXT subtitles only", "Everything"})
        self.clean_txt_var.set(mode in {"Video + TXT + Cover", "TXT subtitles only", "Everything"})
        self.download_thumbnail_var.set(mode in {"Video + TXT + Cover", "Everything"})
        self.download_description_var.set(mode == "Everything")
        self.download_info_json_var.set(mode == "Everything")

    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.path_var.get() or str(DEFAULT_DOWNLOAD_PATH))
        if folder:
            self.path_var.set(folder)

    def log(self, message: str) -> None:
        self.log_queue.put(message)

    def process_log_queue(self) -> None:
        try:
            while True:
                message = self.log_queue.get_nowait()
                if not self.log_has_real_content:
                    self.log_text.delete("1.0", "end")
                    self.log_has_real_content = True
                tag = self.log_tag_for(message)
                if tag:
                    self.log_text.insert("end", message + "\n", tag)
                else:
                    self.log_text.insert("end", message + "\n")
                line_count = int(self.log_text.index("end-1c").split(".")[0]) - 1
                self.log_count_var.set(f"{max(line_count, 0)} lines")
                self.log_text.see("end")
        except queue.Empty:
            pass
        self.root.after(150, self.process_log_queue)

    def select_all_log(self, _event=None):
        self.log_text.tag_add("sel", "1.0", "end")
        return "break"

    def clear_log(self) -> None:
        self.clear_log_content()
        self.show_log_placeholder()
        self.progress_var.set(0)
        self.set_status("Log cleared", "neutral")

    def copy_log(self) -> None:
        self.root.clipboard_clear()
        text = "" if not self.log_has_real_content else self.log_text.get("1.0", "end").strip()
        self.root.clipboard_append(text)
        self.set_status("Log copied", "success")

    def save_log(self) -> None:
        target_folder = self.target_folder()
        target_folder.mkdir(parents=True, exist_ok=True)
        log_path = target_folder / "creator_video_collector_log.txt"
        log_text = "" if not self.log_has_real_content else self.log_text.get("1.0", "end")
        log_path.write_text(log_text, encoding="utf-8")
        self.log(f"Log saved: {log_path}")
        self.set_status("Log saved", "success")

    def open_folder(self) -> None:
        target_folder = self.target_folder()
        target_folder.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["xdg-open", str(target_folder)])

    def target_folder(self) -> Path:
        return Path(self.path_var.get().strip() or str(DEFAULT_DOWNLOAD_PATH)).expanduser()

    def validate_common(self, require_ffmpeg: bool) -> Optional[str]:
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Missing URL", "Paste the video URL first.")
            return None
        if not ensure_tool_exists("yt-dlp"):
            messagebox.showerror("yt-dlp not found", "Install it with:\n\nsudo apt install yt-dlp -y")
            return None
        if require_ffmpeg and not ensure_tool_exists("ffmpeg"):
            messagebox.showerror("ffmpeg not found", "Install it with:\n\nsudo apt install ffmpeg -y")
            return None
        return url

    def clean_existing_subtitle_dialog(self) -> None:
        file_path = filedialog.askopenfilename(title="Choose subtitle file", filetypes=[("Subtitle files", "*.vtt *.srt"), ("All files", "*.*")])
        if not file_path:
            return
        try:
            clean_path = clean_subtitle_file_to_txt(Path(file_path))
            self.log(f"Clean TXT: {clean_path}")
            self.set_status("Subtitle cleaned", "success")
            messagebox.showinfo("Done", f"Clean TXT created:\n{clean_path}")
        except Exception as exc:
            self.log(f"ERROR: {exc}")
            messagebox.showerror("Error", str(exc))

    def start_check_url(self) -> None:
        url = self.validate_common(require_ffmpeg=False)
        if not url:
            return
        self.clear_log_content()
        self.hide_metadata()
        self.check_btn.configure(state="disabled")
        self.set_status("Checking URL...", "checking")
        self.progress.configure(mode="indeterminate")
        self.progress.start(10)
        threading.Thread(target=self.check_url_worker, args=(url,), daemon=True).start()

    def check_url_worker(self, url: str) -> None:
        try:
            self.log("=" * 80)
            self.log("Checking URL metadata...")
            metadata = fetch_metadata(url, self.playlist_var.get())
            self.log(f"Title: {metadata.title}")
            info_parts = [part for part in [metadata.uploader, metadata.duration, metadata.source] if part]
            subtitle_count = len(metadata.manual_subtitles) + len(metadata.auto_subtitles)
            info_parts.append(f"{len(metadata.qualities)} qualities")
            info_parts.append(f"{subtitle_count} subtitle sources")
            self.root.after(0, lambda title=metadata.title, info=" · ".join(info_parts): self.show_metadata(title, info))
            if metadata.is_playlist:
                self.log(f"Playlist detected: {metadata.playlist_count} video(s). Showing qualities for the first video.")
            choices = ["Auto: 720p or best available"] + [choice.label for choice in metadata.qualities]
            self.quality_formats = {choice.label: choice.selector for choice in metadata.qualities}
            self.root.after(0, lambda: self.quality_box.configure(values=choices))
            self.root.after(0, lambda: self.quality_var.set(choices[0]))
            self.log(f"Found {len(metadata.qualities)} quality option(s).")
            self.log("Manual subtitles: " + (", ".join(metadata.manual_subtitles[:20]) if metadata.manual_subtitles else "none listed"))
            self.log("Auto subtitles: " + (", ".join(metadata.auto_subtitles[:20]) if metadata.auto_subtitles else "none listed"))
            self.root.after(0, lambda: self.set_status("URL verified - ready to download", "success"))
        except Exception as exc:
            self.log(f"ERROR: {exc}")
            self.root.after(0, lambda: self.set_status("Check failed", "error"))
            self.root.after(0, lambda: messagebox.showerror("Check failed", str(exc)))
        finally:
            self.root.after(0, self.finish_check_ui)

    def finish_check_ui(self) -> None:
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress_var.set(0)
        self.check_btn.configure(state="normal")

    def start_download(self) -> None:
        url = self.validate_common(require_ffmpeg=self.download_video_var.get() or self.download_audio_var.get())
        if not url:
            return
        if not any(var.get() for var in [self.download_video_var, self.download_audio_var, self.download_subtitles_var, self.clean_txt_var, self.download_thumbnail_var, self.download_description_var, self.download_info_json_var]):
            messagebox.showerror("Nothing selected", "Choose at least one thing to download.")
            return

        target_folder = self.target_folder()
        target_folder.mkdir(parents=True, exist_ok=True)
        self.download_btn.configure(state="disabled")
        self.check_btn.configure(state="disabled")
        self.progress.configure(mode="determinate")
        self.progress_var.set(0)
        self.set_status("Running...", "downloading")

        self.log("=" * 80)
        self.log(f"URL: {url}")
        self.log(f"Folder: {target_folder}")
        self.log(f"Mode: {self.mode_var.get()}")
        self.log(f"Real quality: {self.quality_var.get()}")
        self.log(f"Fallback quality: {self.resolution_var.get()}")
        self.log(f"Subtitles: {self.sub_lang_var.get()}")
        self.log(f"Allow playlists: {self.playlist_var.get()}")
        self.log("")

        threading.Thread(target=self.download_worker, args=(url, target_folder), daemon=True).start()

    def reset_workflow(self) -> None:
        self.url_var.set("")
        self.hide_metadata()
        self.quality_formats = {}
        self.quality_box.configure(values=["Auto: 720p or best available"])
        self.quality_var.set("Auto: 720p or best available")
        self.progress_var.set(0)
        self.clear_log_content()
        self.show_log_placeholder()
        self.set_status("Ready", "neutral")

    def selected_format(self) -> Optional[str]:
        return self.quality_formats.get(self.quality_var.get())

    def download_worker(self, url: str, target_folder: Path) -> None:
        start_time = time.time()
        try:
            command = build_download_command(
                url,
                target_folder,
                allow_playlist=self.playlist_var.get(),
                download_video=self.download_video_var.get(),
                download_audio=self.download_audio_var.get(),
                download_subtitles=self.download_subtitles_var.get(),
                clean_txt=self.clean_txt_var.get(),
                download_thumbnail=self.download_thumbnail_var.get(),
                download_description=self.download_description_var.get(),
                download_info_json=self.download_info_json_var.get(),
                selected_format=self.selected_format(),
                fallback_resolution=self.resolution_var.get(),
                subtitle_languages=self.sub_lang_var.get().strip() or DEFAULT_SUBTITLE_LANGS,
            )
            self.log("Running command:")
            self.log(" ".join(command))
            self.log("")
            return_code = run_command_stream(command, self.handle_download_line)
            if return_code != 0:
                raise RuntimeError(f"yt-dlp failed with exit code {return_code}")
            self.log("\nyt-dlp finished.")
            if self.clean_txt_var.get():
                self.clean_downloaded_subtitles(target_folder, start_time)
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self.set_status("Done", "success"))
            self.log("Done.")
        except Exception as exc:
            self.log(f"\nERROR: {exc}")
            self.root.after(0, lambda: self.set_status("Error", "error"))
            self.root.after(0, lambda: messagebox.showerror("Error", str(exc)))
        finally:
            self.root.after(0, lambda: self.download_btn.configure(state="normal"))
            self.root.after(0, lambda: self.check_btn.configure(state="normal"))

    def handle_download_line(self, line: str) -> None:
        self.log(line)
        match = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%", line)
        if match:
            value = float(match.group(1))
            self.root.after(0, lambda: self.progress_var.set(value))
            self.root.after(0, lambda: self.set_status(f"Downloading... {value:.1f}%", "downloading"))
        elif "[Merger]" in line or "[VideoRemuxer]" in line:
            self.root.after(0, lambda: self.set_status("Merging video/audio...", "downloading"))
        elif "[ExtractAudio]" in line:
            self.root.after(0, lambda: self.set_status("Creating MP3...", "downloading"))

    def clean_downloaded_subtitles(self, target_folder: Path, start_time: float) -> None:
        self.log("Cleaning subtitles into plain TXT...")
        subtitle_files = [path for path in find_subtitle_files(target_folder) if path.stat().st_mtime >= start_time - 300]
        if not subtitle_files:
            subtitle_files = find_subtitle_files(target_folder)[:4]
        if not subtitle_files:
            self.log("No subtitle file found for the selected language.")
            self.root.after(0, lambda: self.set_status("Done, but no subtitle found", "warning"))
            return
        for subtitle_path in subtitle_files:
            clean_path = clean_subtitle_file_to_txt(subtitle_path)
            self.log(f"Subtitle file: {subtitle_path}")
            self.log(f"Clean TXT: {clean_path}")


class SplashScreen:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.window = tk.Toplevel(root)
        self.window.overrideredirect(True)
        self.window.configure(bg=DARK_PALETTE["window"])
        self.window.attributes("-topmost", True)

        width, height = 560, 320
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        x = int((screen_w - width) / 2)
        y = int((screen_h - height) / 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

        frame = tk.Frame(self.window, bg=DARK_PALETTE["window"], highlightbackground=DARK_PALETTE["border"], highlightthickness=1)
        frame.pack(fill="both", expand=True, padx=1, pady=1)

        mark = tk.Canvas(frame, width=92, height=92, bg=DARK_PALETTE["window"], highlightthickness=0)
        mark.pack(pady=(42, 18))
        mark.create_rectangle(10, 18, 82, 64, fill=DARK_PALETTE["surface_alt"], outline=DARK_PALETTE["accent"], width=2)
        mark.create_polygon(39, 31, 39, 51, 58, 41, fill="#ffffff", outline="")
        mark.create_line(46, 68, 46, 84, fill=DARK_PALETTE["success"], width=5, capstyle="round")
        mark.create_line(34, 75, 46, 86, 58, 75, fill=DARK_PALETTE["success"], width=5, capstyle="round", joinstyle="round")

        tk.Label(frame, text=APP_NAME, bg=DARK_PALETTE["window"], fg=DARK_PALETTE["text"], font=("Arial", 24, "bold")).pack()
        tk.Label(frame, text=APP_TAGLINE, bg=DARK_PALETTE["window"], fg=DARK_PALETTE["muted"], font=("Arial", 11)).pack(pady=(8, 20))
        tk.Label(frame, text=APP_STATUS_TEXT, bg=DARK_PALETTE["window"], fg=DARK_PALETTE["success"], font=("Arial", 10, "bold")).pack()

        self.window.update_idletasks()

    def close(self) -> None:
        self.window.destroy()


def set_window_icon(root: tk.Tk) -> None:
    if APP_ICON.exists():
        try:
            root.iconphoto(True, tk.PhotoImage(file=str(APP_ICON)))
        except tk.TclError:
            pass


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    set_window_icon(root)
    splash = SplashScreen(root)

    def show_main_window() -> None:
        splash.close()
        root.deiconify()
        CreatorVideoCollectorApp(root)

    root.after(SPLASH_DURATION_MS, show_main_window)
    root.mainloop()
