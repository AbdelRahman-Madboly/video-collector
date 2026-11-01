# Changelog

## Unreleased

- Summaries come from one **Summary command** setting: any command that reads a transcript on stdin and
  prints a summary. It is empty (summaries off) until you set it. The two built-in engines are gone.
  An old `engine` value in `settings.json` is ignored.
- The summary command receives untrusted text, so it now runs with a small environment, in an empty
  folder, with a time limit, inside `bwrap` (read-only files, no network) when it is installed, and with
  the option groups listed in `summary_guards` added when missing. Settings shows a warning.
- CI workflow that runs the tests on every push, with Qt offscreen.
- README: a Status section and the summary command.

## 2.0.0 - 2026-11-01

Collector 2: a new PySide6 window around the existing yt-dlp and subtitle core.

- Library on disk: one folder per video, grouped by project, with `info.md` and a project `INDEX.md`.
- Download presets (watch offline, research, everything, audio), quality check per link, playlists
  expanded off the window thread with a confirmation above 10 videos.
- Summaries from a command-line engine with no tools, in an empty folder; long transcripts in parts.
- Library page (play, open folder, open summary, make a summary later) and a Settings page.
- Publishes its status for the Tools Hub.
- Fixed in this release: info.md is written before the download, so a failed download leaves a readable
  folder; an empty subtitle file no longer gives an empty transcript and a summary request.
- Removed an unused download command builder that put the link before `--`.
- Tests for the subtitle cleaner and the metadata parser; 59 tests, none touch the network.
- Design docs moved to `docs/design/`; stale `requirements.txt` removed (`pyproject.toml` is the source).
- MIT license.

## 0.3.0 - 2026-07-04

- Tkinter window: download video, audio, thumbnails, subtitles and clean TXT transcripts with yt-dlp.
