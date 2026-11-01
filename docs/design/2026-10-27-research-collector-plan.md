# Creator Video Collector 2 Implementation Plan

> Note, 2026-11-02: the two built-in summary engines described here were replaced by one
> **Summary command** setting: any command that reads a transcript on stdin and prints a summary.
> See the README.

**Goal:** A PySide6 collector that downloads videos into one folder per video grouped by project, with clean transcripts, thumbnails and command-line summaries, a library page and settings.

**Architecture:** Pure modules (`settings`, `library`, `summarize`, `jobs`) hold the logic and take injectable runners, so tests never call yt-dlp or the summary tool. The window (`ui/`) only drives them on a worker thread. `downloader.py` and `subtitles.py` stay as the yt-dlp and caption core.

**Tech Stack:** Python 3.12, PySide6, uv, pytest, yt-dlp CLI, `cli-a`, `cli-b`.

**Spec:** `docs/design/2026-10-27-research-collector-design.md`

## Global Constraints

- Default library `~/Videos/Video Collector`; settings `~/.config/video-collector/settings.json` (env `VIDEO_COLLECTOR_CONFIG` overrides, tests always set it).
- Folder per video `<library>/<Project>/<YYYY-MM-DD> <Title>/`, title cut to 80 chars, empty project → `Unsorted`.
- Files: `video.mp4` | `audio.mp3`, `thumbnail.jpg`, `transcript.txt`, `summary.md`, `info.md`, `raw/` (subtitles, info.json); `<Project>/INDEX.md`.
- Never overwrite an existing file in a video folder.
- Summaries in English; CLI A default (`cli-a` with all tools disallowed), CLI B option (`cli-b --sandbox read-only`), Off; 10 minute limit; split above 120,000 characters.
- Subtitle languages default `en.*,ar.*`. Shared summary `~/My-Tools/shared-data/video-collector.json` (env `MYTOOLS_SHARED` overrides).
- Tests: `uv run python -m pytest -q` with `QT_QPA_PLATFORM=offscreen`; never touch the network, yt-dlp, the summary tool or real config/library.

## Review Focus

- A link whose video has no subtitles: video and thumbnail kept, info.md says no transcript, no summary attempted (Task 4).
- Summary engine missing, failing or timing out: download kept, `Summary: failed, <reason>` in info.md (Task 3, 4).
- A title with `/`, `:`, emoji or 200 characters: a valid folder name (Task 2).
- The same link downloaded twice into one project: same folder, existing files untouched (Task 2, 4).
- A playlist of more than 10 items: confirm before queueing (Task 5).

---

### Task 1: Project setup and settings

**Files:** Create `pyproject.toml`, `src/creator_video_collector/settings.py`, `tests/conftest.py`, `tests/test_settings.py`.

**Interfaces:** Produces `Settings` dataclass (`library: Path`, `default_project: str = ""`, `preset: str = "watch"`, `quality: str = "720"`, `subtitle_langs: str = "en.*,ar.*"`, `engine: str = "cli-a"`, `dark: bool = True`); `settings.load() -> Settings`, `settings.save(s: Settings) -> None`, `settings.config_path() -> Path`.

- [ ] Test: `load()` with no file returns defaults with `library == Path.home()/"Videos"/"Video Collector"`; `save` then `load` round-trips every field; a corrupt file returns defaults.
- [ ] Run: FAIL. Implement. Run: PASS. conftest autouse sets `VIDEO_COLLECTOR_CONFIG` and `MYTOOLS_SHARED` to tmp.
- [ ] Commit `"Collector 2: project setup and settings"`.

### Task 2: Library: folders, names, info.md, INDEX.md

**Files:** Create `library.py`, `tests/test_library.py`.

**Interfaces:** Produces `project_name(raw: str) -> str`; `project_dir(library: Path, project: str) -> Path` (matches an existing folder ignoring case); `safe_title(title: str) -> str`; `video_dir(library, project, title, video_id, day: date) -> Path` (reuses the folder whose `info.md` has `ID: <video_id>`); `@dataclass Entry(folder, title, url, video_id, channel, duration, project, day, has_video, has_transcript, has_summary, summary_state)`; `write_info(folder, meta: dict) -> None` (fields Title, Channel, Link, ID, Length, Uploaded, Downloaded, Project, Transcript, Summary); `read_entry(folder) -> Entry | None`; `scan(library) -> list[Entry]` newest first; `write_index(project_dir) -> Path`; `set_summary_state(folder, state: str) -> None`.

- [ ] Tests: `safe_title("A/B: c? 🎥 " + "x"*200)` has no `/` or `:` and ≤ 80 chars; `project_name("")=="Unsorted"`; `project_dir` maps "workshop" to an existing "Workshop" folder; two calls of `video_dir` with the same id return the same folder; `write_index` lists every video with its link and the summary's first non-heading line; `scan` reads back what `write_info` wrote.
- [ ] FAIL → implement → PASS → commit `"Collector 2: library layout"`.

### Task 3: Summaries

**Files:** Create `summarize.py`, `tests/test_summarize.py`.

**Interfaces:** Produces `ENGINES = ("cli-a", "cli-b", "off")`; `build_prompt(transcript: str, title: str, project: str) -> str`; `command(engine: str) -> list[str]` (`["cli-a", "-p", "--disallowedTools", "Bash,Edit,Write,Read,WebFetch,WebSearch,Glob,Grep,NotebookEdit,Task"]` or `["cli-b", "exec", "--skip-git-repo-check", "--sandbox", "read-only", "-"]`), prompt on stdin; `class SummaryError(Exception)`; `summarize(transcript, title, project, engine, runner=subprocess.run, limit=120_000) -> str`.

- [ ] Tests (fake runner): prompt contains the project, the title and the headings `TL;DR`, `Key points`, `Details for R&D`, `Open questions`, and asks for English; a 250,000-char transcript makes 3 part calls plus 1 combining call; a missing CLI (`FileNotFoundError`), a non-zero exit and a `TimeoutExpired` each raise `SummaryError` with a plain reason; engine `off` raises `SummaryError("Summaries are off")`.
- [ ] FAIL → implement → PASS → commit `"Collector 2: summaries from a command-line tool"`.

### Task 4: Download jobs

**Files:** Create `jobs.py`, `tests/test_jobs.py`; modify `downloader.py` (add `build_job_command`).

**Interfaces:** Produces `PRESETS = {"watch": {video, thumbnail, transcript}, "research": {thumbnail, transcript, summary}, "everything": {video, thumbnail, transcript, summary, raw, info_json}, "audio": {audio, thumbnail, transcript}}`; `@dataclass Job(url, project, parts: set[str], quality: str, format_selector: str | None, library: Path, langs: str, engine: str)`; `downloader.build_job_command(job, folder, parts_missing) -> list[str]` using typed output templates (`-o <folder>/video.%(ext)s`, `-o thumbnail:<folder>/thumbnail.%(ext)s`, `-o subtitle:<folder>/raw/sub.%(ext)s`, `-o infojson:<folder>/raw/info`); `jobs.run(job, on_line, runner_meta, runner_dl, runner_summary, today) -> Entry` (fetch metadata, choose folder, download only missing parts, clean subtitles into `transcript.txt`, write info.md, summarize when chosen and transcript exists, write INDEX.md, publish).

- [ ] Tests with fakes that create the files yt-dlp would: watch preset gives `video.mp4`, `thumbnail.jpg`, `transcript.txt`, `info.md`; research gives no video and a `summary.md`; a second run skips existing parts (command has `--skip-download` when the video exists) and leaves an edited `summary.md` unchanged; no subtitles → `Transcript: none`, no summary call; summary failure → files kept and `Summary: failed, <reason>`; the shared JSON counts the videos.
- [ ] FAIL → implement → PASS → commit `"Collector 2: download jobs into the library"`.

### Task 5: The window

**Files:** Create `ui/__init__.py`, `ui/window.py`, `ui/pages.py`, `ui/theme.py`, `tests/test_ui.py`; rewrite `__main__.py`, `youtube_visual_collector.py`; delete `app.py`, `config.py` palettes once unused.

**Interfaces:** Produces `MainWindow(settings, runners: dict | None = None)` with pages `Download`, `Library`, `Settings`; Download: multi-line links box, Check (single link: title, channel, length, thumbnail preview, qualities), project combo (editable, from `library.scan`), preset chips + part switches, quality (hidden for research/audio), destination label + Change, Start; queue list with per-item status; Library: entries by project with thumbnail and parts, buttons Play, Folder, Summary, Make summary; Settings: every Settings field, yt-dlp version + Update (`pkexec yt-dlp -U`). Work runs on `QThreadPool`; `confirm` injectable for the >10 items prompt.

- [ ] Tests (offscreen, fake runners): window builds at 1280×800 without horizontal scroll; two links queue two jobs that finish in order; a playlist of 12 calls `confirm` with 12; Settings save persists `library` and `engine`; Library lists a fixture entry and Make summary writes `summary.md`.
- [ ] FAIL → implement → PASS → render each page to PNG and check → commit `"Collector 2: new window"`.

### Task 6: Launcher, Hub and docs

**Files:** Modify `install_youtube_visual_collector.sh` (uv-based launcher), `README.md`; in `~/My-Tools/tools-hub`: `tools.json` status `summary` for `video-collector`, re-run `hub.install`.

- [ ] Installer writes `~/.local/bin/youtube-visual-collector` running `uv run --project <dir> python -m creator_video_collector`; launcher keeps name and the new icon.
- [ ] Launch from the menu; download one short real video in Research preset into a scratch library; check the folder, the summary and the Hub card.
- [ ] Commit in both repos.
