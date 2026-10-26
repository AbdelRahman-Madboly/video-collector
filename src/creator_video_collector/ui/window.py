"""Creator Video Collector window: Download, Library and Settings."""
from __future__ import annotations

import re
import subprocess
import traceback
from dataclasses import replace
from datetime import date
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
                               QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea,
                               QStackedWidget, QVBoxLayout, QWidget)

from .. import jobs, library, settings, summarize
from ..config import APP_NAME, RESOLUTION_OPTIONS
from ..downloader import fetch_metadata, is_web_link
from . import theme

PARTS = [("video", "Video (MP4)"), ("audio", "Audio (MP3)"), ("thumbnail", "Thumbnail"),
         ("transcript", "Transcript"), ("summary", "Summary"), ("raw", "Raw subtitles"),
         ("info_json", "yt-dlp info.json")]
ENGINE_NAMES = {"cli-a": "CLI A", "cli-b": "CLI B", "off": "Off"}
PROGRESS = re.compile(r"\[download\]\s+([\d.]+)%")


def _label(text: str, role: str = "", wrap: bool = False) -> QLabel:
    lab = QLabel(text)
    if role:
        lab.setProperty("role", role)
    lab.setWordWrap(wrap)
    return lab


def _card() -> QFrame:
    f = QFrame()
    f.setProperty("card", True)
    return f


class _Signals(QObject):
    line = Signal(int, str)          # queue row, text
    state = Signal(int, str)         # queue row, status
    progress = Signal(int, float)
    done = Signal(object)


class _Work(QRunnable):
    """Runs fn on the thread pool. Kept alive here until its done signal has been delivered, so a
    window closing mid-task never frees the signals while the worker still uses them."""

    alive: set = set()

    def __init__(self, fn):
        super().__init__()
        self.fn, self.signals = fn, _Signals()
        self.setAutoDelete(False)

    def run(self):
        try:
            result = self.fn(self.signals)
        except Exception as e:                       # shown, never a crash
            result = e
            traceback.print_exc()
        try:
            self.signals.done.emit(result)
        except RuntimeError:                         # the window is gone; nothing to tell
            _Work.alive.discard(self)


class _Page(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName("page")
        self.setWidget(body)
        self.lay = QVBoxLayout(body)
        self.lay.setContentsMargins(24, 18, 24, 24)
        self.lay.setSpacing(14)


# ---------------------------------------------------------------------------------------------- Download
class DownloadPage(_Page):
    def __init__(self, win: "MainWindow"):
        super().__init__()
        self.win = win
        self._library_override: Path | None = None
        self._jobs: list[jobs.Job] = []
        self._running = False
        self._detected: list = []

        self.lay.addWidget(_label("Download", "title"))
        top = QHBoxLayout()
        top.setSpacing(14)

        src = _card()
        sl = QVBoxLayout(src)
        sl.setContentsMargins(16, 14, 16, 14)
        sl.addWidget(_label("Links", "h2"))
        self.links = QPlainTextEdit()
        self.links.setPlaceholderText("Paste one or more video links, one per line (YouTube and any site yt-dlp supports)")
        self.links.setFixedHeight(96)
        sl.addWidget(self.links)
        row = QHBoxLayout()
        self.btn_check = QPushButton("Check link")
        self.btn_check.clicked.connect(self.check)
        self.playlist = QCheckBox("Allow playlists")
        row.addWidget(self.btn_check)
        row.addWidget(self.playlist)
        row.addStretch(1)
        sl.addLayout(row)
        self.preview = QFrame()
        pl = QHBoxLayout(self.preview)
        pl.setContentsMargins(0, 6, 0, 0)
        self.thumb = QLabel()
        self.thumb.setFixedSize(160, 90)
        self.thumb.setStyleSheet("background: #0b0d14; border-radius: 6px;")
        pl.addWidget(self.thumb)
        info = QVBoxLayout()
        self.p_title = _label("", "h2", wrap=True)
        self.p_meta = _label("", "muted", wrap=True)
        info.addWidget(self.p_title)
        info.addWidget(self.p_meta)
        info.addStretch(1)
        pl.addLayout(info, 1)
        self.preview.hide()
        sl.addWidget(self.preview)
        top.addWidget(src, 3)

        opts = _card()
        ol = QGridLayout(opts)
        ol.setContentsMargins(16, 14, 16, 14)
        ol.setVerticalSpacing(10)
        ol.addWidget(_label("Project", "h2"), 0, 0)
        self.project = QComboBox()
        self.project.setEditable(True)
        self.project.setInsertPolicy(QComboBox.NoInsert)
        self.project.lineEdit().setPlaceholderText("Unsorted, or type a new project")
        ol.addWidget(self.project, 0, 1)
        ol.addWidget(_label("Save to", "h2"), 1, 0)
        dest = QHBoxLayout()
        self.dest = _label("", "muted", wrap=True)
        b_change = QPushButton("Change…")
        b_change.clicked.connect(self.change_folder)
        b_reset = QPushButton("Default")
        b_reset.clicked.connect(self.reset_folder)
        dest.addWidget(self.dest, 1)
        dest.addWidget(b_change)
        dest.addWidget(b_reset)
        ol.addLayout(dest, 1, 1)
        ol.addWidget(_label("Get", "h2"), 2, 0, Qt.AlignTop)
        presets = QHBoxLayout()
        self.preset_group = QButtonGroup(self)
        self.preset_btns = {}
        for key, name in jobs.PRESET_NAMES.items():
            b = QPushButton(name)
            b.setCheckable(True)
            b.setProperty("chip", True)
            b.clicked.connect(lambda _=False, k=key: self.apply_preset(k))
            self.preset_group.addButton(b)
            self.preset_btns[key] = b
            presets.addWidget(b)
        presets.addStretch(1)
        get = QVBoxLayout()
        get.addLayout(presets)
        parts = QGridLayout()
        self.part_boxes = {}
        for i, (key, name) in enumerate(PARTS):
            box = QCheckBox(name)
            box.toggled.connect(self._parts_changed)
            self.part_boxes[key] = box
            parts.addWidget(box, i // 4, i % 4)
        get.addLayout(parts)
        ol.addLayout(get, 2, 1)
        self.quality_label = _label("Quality", "h2")
        ol.addWidget(self.quality_label, 3, 0)
        self.quality = QComboBox()
        ol.addWidget(self.quality, 3, 1)
        ol.setColumnStretch(1, 1)
        top.addWidget(opts, 4)
        self.lay.addLayout(top)

        go = QHBoxLayout()
        self.btn_start = QPushButton("Start download")
        self.btn_start.setProperty("primary", True)
        self.btn_start.clicked.connect(self.start)
        self.status = _label("", "muted")
        go.addWidget(self.btn_start)
        go.addWidget(self.status, 1)
        self.lay.addLayout(go)

        q = _card()
        ql = QVBoxLayout(q)
        ql.setContentsMargins(16, 14, 16, 14)
        head = QHBoxLayout()
        head.addWidget(_label("Queue", "h2"))
        head.addStretch(1)
        self.btn_log = QPushButton("Show details")
        self.btn_log.clicked.connect(self._toggle_log)
        head.addWidget(self.btn_log)
        ql.addLayout(head)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        ql.addWidget(self.progress)
        self.queue = QListWidget()
        self.queue.setMinimumHeight(120)
        ql.addWidget(self.queue)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(160)
        self.log.hide()
        ql.addWidget(self.log)
        self.lay.addWidget(q, 1)
        self.reload()

    # -- state from settings and the library
    def reload(self) -> None:
        s = self.win.settings
        current = self.project.currentText()
        self.project.clear()
        projects = sorted({e.project for e in library.scan(self.target_library())} | (
            {s.default_project} if s.default_project else set()), key=str.lower)
        self.project.addItems(projects)
        self.project.setCurrentText(current or s.default_project)
        self.apply_preset(s.preset)
        self._fill_quality([])
        self.dest.setText(str(self.target_library()) + ("   (this batch only)" if self._library_override else ""))

    def target_library(self) -> Path:
        return self._library_override or self.win.settings.library

    def change_folder(self) -> None:
        chosen = self.win.runners["pick_dir"](str(self.target_library()))
        if chosen:
            self._library_override = Path(chosen)
            self.reload()

    def reset_folder(self) -> None:
        self._library_override = None
        self.reload()

    def apply_preset(self, key: str) -> None:
        key = key if key in jobs.PRESETS else "watch"
        for k, b in self.preset_btns.items():
            b.setChecked(k == key)
        for part, box in self.part_boxes.items():
            box.blockSignals(True)
            box.setChecked(part in jobs.PRESETS[key])
            box.blockSignals(False)
        self._parts_changed()

    def chosen_parts(self) -> set:
        return {k for k, box in self.part_boxes.items() if box.isChecked()}

    def _parts_changed(self) -> None:
        parts = self.chosen_parts()
        match = next((k for k, v in jobs.PRESETS.items() if set(v) == parts), None)
        for k, b in self.preset_btns.items():
            b.setChecked(k == match)
        has_video = "video" in parts
        self.quality.setVisible(has_video)
        self.quality_label.setVisible(has_video)
        self.part_boxes["summary"].setEnabled(self.win.settings.engine != "off")

    def _fill_quality(self, detected: list) -> None:
        self._detected = detected
        self.quality.clear()
        for q in detected:
            self.quality.addItem(q.label, q.selector)
        for r in RESOLUTION_OPTIONS:
            self.quality.addItem(f"Up to {r}p" if r != "Best" else "Best available", None)
        default = self.win.settings.quality
        idx = self.quality.findText(f"Up to {default}p" if default != "Best" else "Best available")
        self.quality.setCurrentIndex(0 if detected else max(0, idx))

    def _links(self) -> list[str]:
        return [l.strip() for l in self.links.toPlainText().splitlines() if l.strip()]

    # -- check one link
    def check(self) -> None:
        links = self._links()
        if len(links) != 1:
            self.status.setText("Check works on one link at a time.")
            return
        self.btn_check.setEnabled(False)
        self.status.setText("Checking…")
        fetch = self.win.runners["fetch"]
        self.win.run(lambda sig: fetch(links[0]), self._checked)

    def _checked(self, meta) -> None:
        self.btn_check.setEnabled(True)
        if isinstance(meta, Exception):
            self.status.setText(f"Could not read this link: {meta}")
            return
        self.preview.show()
        self.p_title.setText(meta.title)
        subs = "subtitles: " + (", ".join((meta.manual_subtitles or meta.auto_subtitles)[:6]) or "none")
        self.p_meta.setText(" · ".join(x for x in (meta.uploader, meta.duration, meta.upload_date, subs) if x))
        self._fill_quality(meta.qualities)
        self.status.setText("Ready.")
        thumb = getattr(meta, "thumbnail", "")
        if thumb and self.win.runners.get("thumb"):
            self.win.run(lambda sig: self.win.runners["thumb"](thumb), self._thumb)

    def _thumb(self, data) -> None:
        if isinstance(data, (bytes, bytearray)):
            pix = QPixmap()
            pix.loadFromData(bytes(data))
            self.thumb.setPixmap(pix.scaled(160, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    # -- queue
    def start(self) -> None:
        links = self._links()
        bad = [l for l in links if not is_web_link(l)]
        links = [l for l in links if is_web_link(l)]
        if bad:
            self.status.setText(f"Skipped {len(bad)} line(s) that are not web links (http or https).")
        if not links:
            if not bad:
                self.status.setText("Paste a link first.")
            return
        parts = self.chosen_parts()
        if not parts:
            self.status.setText("Choose at least one thing to get.")
            return
        urls: list[str] = []
        for link in links:
            got = jobs.expand(link, self.playlist.isChecked(), self.win.runners["fetch"])
            if len(got) > 10 and not self.win.runners["confirm"](
                    f"This playlist has {len(got)} videos" + (
                        f", which means {len(got)} summaries" if "summary" in parts else "") + ". Queue them all?",
                    len(got)):
                continue
            urls += got
        if not urls:
            self.status.setText("Nothing queued.")
            return
        s = self.win.settings
        fmt = self.quality.currentData() if len(urls) == 1 and self._detected else None
        quality = s.quality
        m = re.match(r"Up to (\d+)p", self.quality.currentText())
        if m:
            quality = m.group(1)
        elif self.quality.currentText() == "Best available":
            quality = "Best"
        for url in urls:
            self._jobs.append(jobs.Job(url=url, project=self.project.currentText().strip(), parts=set(parts),
                                       quality=quality, format_selector=fmt, library=self.target_library(),
                                       langs=s.subtitle_langs, engine=s.engine))
            QListWidgetItem(f"{url} · Waiting", self.queue)
        self.links.clear()
        self.preview.hide()
        self._next()

    def queue_done(self) -> bool:
        return not self._running and not self._jobs

    def _next(self) -> None:
        if self._running or not self._jobs:
            if not self._jobs and not self._running:
                self.status.setText("All done.")
                self.win.page("Library").refresh_entries()
            return
        job = self._jobs.pop(0)
        row = self.queue.count() - len(self._jobs) - 1
        self._running = True
        self.btn_start.setEnabled(True)
        r = self.win.runners

        def work(sig):
            sig.state.emit(row, "Downloading")

            def on_line(text: str) -> None:
                sig.line.emit(row, text)
                if (m := PROGRESS.search(text)):
                    sig.progress.emit(row, float(m.group(1)))
                elif text.startswith("Writing the summary"):
                    sig.state.emit(row, "Summarizing")
            return jobs.run(job, on_line, fetch=r["fetch"], download=r["download"], summary_runner=r["summary"])

        self.win.run(work, lambda result: self._finished(row, result),
                     on_line=self._line, on_state=self._state, on_progress=lambda _r, p: self.progress.setValue(int(p)))

    def _line(self, row: int, text: str) -> None:
        self.log.appendPlainText(text)

    def _state(self, row: int, state: str) -> None:
        item = self.queue.item(row)
        if item:
            item.setText(item.text().rsplit(" · ", 1)[0] + f" · {state}")

    def _finished(self, row: int, result) -> None:
        self._running = False
        self.progress.setValue(100 if not isinstance(result, Exception) else 0)
        if isinstance(result, Exception):
            self._state(row, "Failed")
            self.log.appendPlainText(f"Failed: {result}")
            self.status.setText(f"A download failed: {result}")
        else:
            item = self.queue.item(row)
            if item:
                item.setText(f"{result.title} → {result.project} · Done")
        self._next()

    def _toggle_log(self) -> None:
        self.log.setVisible(not self.log.isVisible())
        self.btn_log.setText("Hide details" if self.log.isVisible() else "Show details")


# ---------------------------------------------------------------------------------------------- Library
class LibraryPage(_Page):
    def __init__(self, win: "MainWindow"):
        super().__init__()
        self.win = win
        head = QHBoxLayout()
        head.addWidget(_label("Library", "title"))
        head.addStretch(1)
        self.filter = QComboBox()
        self.filter.currentIndexChanged.connect(self._fill)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search titles")
        self.search.textChanged.connect(self._fill)
        b_refresh = QPushButton("Refresh")
        b_refresh.clicked.connect(self.refresh_entries)
        for w in (self.filter, self.search, b_refresh):
            head.addWidget(w)
        self.lay.addLayout(head)
        self.where = _label("", "muted")
        self.lay.addWidget(self.where)
        self.list = QListWidget()
        self.list.setIconSize(QSize(128, 72))
        self.list.setSpacing(4)
        self.list.currentRowChanged.connect(self._sync)
        self.list.itemDoubleClicked.connect(lambda _i: self.play())
        self.lay.addWidget(self.list, 1)
        row = QHBoxLayout()
        self.btn_play = QPushButton("Play")
        self.btn_folder = QPushButton("Open folder")
        self.btn_summary = QPushButton("Open summary")
        self.btn_make = QPushButton("Make summary")
        self.btn_index = QPushButton("Open project INDEX")
        for b, fn in ((self.btn_play, self.play), (self.btn_folder, self.open_folder),
                      (self.btn_summary, self.open_summary), (self.btn_make, self.make_summary),
                      (self.btn_index, self.open_index)):
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        self.state = _label("", "muted")
        row.addWidget(self.state)
        self.lay.addLayout(row)
        self.entries: list[library.Entry] = []
        self.shown: list[library.Entry] = []
        self.refresh_entries()

    def refresh_entries(self) -> None:
        lib = self.win.settings.library
        self.entries = library.scan(lib)
        keep = self.filter.currentText()
        self.filter.blockSignals(True)
        self.filter.clear()
        self.filter.addItem("All projects")
        self.filter.addItems(sorted({e.project for e in self.entries}, key=str.lower))
        self.filter.setCurrentText(keep or "All projects")
        self.filter.blockSignals(False)
        self.where.setText(f"{len(self.entries)} videos in {lib}")
        self._fill()

    def _fill(self) -> None:
        proj, text = self.filter.currentText(), self.search.text().lower()
        self.shown = [e for e in self.entries if (proj in ("", "All projects") or e.project == proj)
                      and text in e.title.lower()]
        self.list.clear()
        for e in self.shown:
            has = [n for n, ok in (("video", e.has_video), ("transcript", e.has_transcript),
                                   ("summary", e.has_summary)) if ok]
            note = f"   summary {e.summary_state}" if e.summary_state.startswith("failed") else ""
            item = QListWidgetItem(f"{e.title}\n{e.project} · {e.day} · {e.channel or '—'} · {', '.join(has) or 'info only'}{note}")
            thumb = e.folder / "thumbnail.jpg"
            if thumb.exists():
                item.setIcon(QIcon(str(thumb)))
            self.list.addItem(item)
        self._sync()

    def current(self) -> library.Entry | None:
        row = self.list.currentRow()
        return self.shown[row] if 0 <= row < len(self.shown) else None

    def _sync(self, *_a) -> None:
        e = self.current()
        self.btn_play.setEnabled(bool(e and e.has_video))
        self.btn_folder.setEnabled(e is not None)
        self.btn_index.setEnabled(e is not None)
        self.btn_summary.setEnabled(bool(e and e.has_summary))
        self.btn_make.setEnabled(bool(e and e.has_transcript and self.win.settings.engine != "off"))

    def _open(self, path: Path) -> None:
        self.win.runners["launch"](["xdg-open", str(path)])

    def play(self) -> None:
        e = self.current()
        if e:
            media = next((p for p in (e.folder / "video.mp4", e.folder / "audio.mp3") if p.exists()), None)
            if media:
                self._open(media)

    def open_folder(self) -> None:
        if (e := self.current()):
            self._open(e.folder)

    def open_summary(self) -> None:
        if (e := self.current()) and e.has_summary:
            self._open(e.folder / "summary.md")

    def open_index(self) -> None:
        if (e := self.current()):
            self._open(library.write_index(e.folder.parent))

    def make_summary(self) -> None:
        e = self.current()
        if not e:
            return
        self.state.setText("Writing the summary…")
        self.btn_make.setEnabled(False)
        engine, runner = self.win.settings.engine, self.win.runners["summary"]
        self.win.run(lambda sig: jobs.make_summary(e.folder, engine, runner), self._made)

    def _made(self, ok) -> None:
        self.state.setText("Summary written." if ok is True else "No summary: see the video's info.md.")
        self.refresh_entries()


# ---------------------------------------------------------------------------------------------- Settings
class SettingsPage(_Page):
    def __init__(self, win: "MainWindow"):
        super().__init__()
        self.win = win
        self.lay.addWidget(_label("Settings", "title"))
        card = _card()
        g = QGridLayout(card)
        g.setContentsMargins(18, 16, 18, 16)
        g.setVerticalSpacing(12)
        s = win.settings
        self.library = QLineEdit(str(s.library))
        b = QPushButton("Browse…")
        b.clicked.connect(self._browse)
        lib_row = QHBoxLayout()
        lib_row.addWidget(self.library, 1)
        lib_row.addWidget(b)
        self.project = QLineEdit(s.default_project)
        self.project.setPlaceholderText("Unsorted")
        self.preset = QComboBox()
        for k, n in jobs.PRESET_NAMES.items():
            self.preset.addItem(n, k)
        self.preset.setCurrentIndex(max(0, self.preset.findData(s.preset)))
        self.quality = QComboBox()
        self.quality.addItems(RESOLUTION_OPTIONS)
        self.quality.setCurrentText(s.quality)
        self.langs = QLineEdit(s.subtitle_langs)
        self.engine = QComboBox()
        for k in summarize.ENGINES:
            self.engine.addItem(ENGINE_NAMES[k], k)
        self.engine.setCurrentIndex(max(0, self.engine.findData(s.engine)))
        self.dark = QCheckBox("Dark")
        self.dark.setChecked(s.dark)
        rows = [("Library folder", lib_row), ("Default project", self.project), ("Default download", self.preset),
                ("Video quality", self.quality), ("Subtitle languages", self.langs),
                ("Summaries written by", self.engine), ("Look", self.dark)]
        for i, (name, w) in enumerate(rows):
            g.addWidget(_label(name, "h2"), i, 0)
            (g.addLayout if isinstance(w, QHBoxLayout) else g.addWidget)(w, i, 1)
        g.addWidget(_label("Videos go to <library>/<project>/<date> <title>/. Summaries run with no tools, "
                           "from your own login.", "muted", wrap=True), len(rows), 0, 1, 2)
        g.setColumnStretch(1, 1)
        self.lay.addWidget(card)
        b_save = QPushButton("Save settings")
        b_save.setProperty("primary", True)
        b_save.clicked.connect(self.save)
        self.saved = _label("", "ok")
        row = QHBoxLayout()
        row.addWidget(b_save)
        row.addWidget(self.saved, 1)
        self.lay.addLayout(row)

        tool = _card()
        tl = QHBoxLayout(tool)
        tl.setContentsMargins(18, 14, 18, 14)
        self.ytdlp = _label("yt-dlp: …")
        b_up = QPushButton("Update yt-dlp")
        b_up.setToolTip("Asks for your password: yt-dlp is installed for the whole system")
        b_up.clicked.connect(self.update_ytdlp)
        tl.addWidget(self.ytdlp, 1)
        tl.addWidget(b_up)
        self.lay.addWidget(tool)
        self.lay.addStretch(1)
        version = self.win.runners["version"]
        self.win.run(lambda sig: version(), lambda v: self.ytdlp.setText(f"yt-dlp version: {v}"))

    def _browse(self) -> None:
        chosen = self.win.runners["pick_dir"](self.library.text())
        if chosen:
            self.library.setText(chosen)

    def save(self) -> None:
        s = replace(self.win.settings, library=Path(self.library.text()).expanduser(),
                    default_project=self.project.text().strip(), preset=self.preset.currentData(),
                    quality=self.quality.currentText(), subtitle_langs=self.langs.text().strip() or "en.*,ar.*",
                    engine=self.engine.currentData(), dark=self.dark.isChecked())
        settings.save(s)
        self.win.apply_settings(s)
        self.saved.setText("Saved.")

    def update_ytdlp(self) -> None:
        self.ytdlp.setText("Updating yt-dlp… (enter your password in the window that opens)")
        runner = self.win.runners.get("run", subprocess.run)
        self.win.run(lambda sig: runner(["pkexec", "/usr/bin/python3", "/usr/local/bin/yt-dlp", "-U"],
                                        capture_output=True, text=True, timeout=600),
                     lambda r: self.ytdlp.setText(f"yt-dlp: {self.win.runners['version']()}" + (
                         "" if getattr(r, "returncode", 1) == 0 else "  (update did not finish)")))


# ---------------------------------------------------------------------------------------------- Window
def _default_runners(win) -> dict:
    def thumb(url: str) -> bytes:
        import urllib.request
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.read()
    return {"fetch": lambda url: fetch_metadata(url, False), "download": None, "summary": subprocess.run,
            "launch": lambda argv: subprocess.Popen(argv, start_new_session=True, stdout=subprocess.DEVNULL,
                                                    stderr=subprocess.DEVNULL),
            "confirm": lambda text, n: QMessageBox.question(win, APP_NAME, text) == QMessageBox.Yes,
            "pick_dir": lambda start: QFileDialog.getExistingDirectory(win, "Choose a folder", start),
            "thumb": thumb, "version": jobs.ytdlp_version}


class MainWindow(QMainWindow):
    PAGES = ("Download", "Library", "Settings")

    def __init__(self, s: settings.Settings, runners: dict | None = None):
        super().__init__()
        self.settings = s
        self.runners = {**_default_runners(self), **(runners or {})}
        self.setWindowTitle(APP_NAME)
        central = QWidget()
        lay = QHBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFixedWidth(180)
        self.nav.addItems(self.PAGES)
        self.stack = QStackedWidget()
        lay.addWidget(self.nav)
        lay.addWidget(self.stack, 1)
        self.setCentralWidget(central)
        self.pages = {}
        for name, cls in zip(self.PAGES, (DownloadPage, LibraryPage, SettingsPage)):
            self.pages[name] = cls(self)
            self.stack.addWidget(self.pages[name])
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)
        self.apply_settings(s)

    def page(self, name: str):
        return self.pages[name]

    def show_page(self, name: str) -> None:
        self.nav.setCurrentRow(self.PAGES.index(name))

    def current_page(self):
        return self.stack.currentWidget()

    def apply_settings(self, s: settings.Settings) -> None:
        self.settings = s
        self.setStyleSheet(theme.DARK if s.dark else theme.LIGHT)
        self.pages["Download"].reload()
        self.pages["Library"].refresh_entries()

    def run(self, fn, done, on_line=None, on_state=None, on_progress=None) -> None:
        """fn(signals) on the thread pool; done(result) back on the window's thread."""
        work = _Work(fn)
        _Work.alive.add(work)
        if on_line:
            work.signals.line.connect(on_line)
        if on_state:
            work.signals.state.connect(on_state)
        if on_progress:
            work.signals.progress.connect(on_progress)

        def finish(result):
            _Work.alive.discard(work)
            done(result)
        work.signals.done.connect(finish)
        QThreadPool.globalInstance().start(work)
