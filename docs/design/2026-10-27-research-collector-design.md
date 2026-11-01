# Creator Video Collector 2: offline videos and research material for other tools

> Note, 2026-11-02: the two built-in summary engines described here were replaced by one
> **Summary command** setting: any command that reads a transcript on stdin and prints a summary.
> See the README.

Date: 2026-10-27. Rebuilds the window and adds summaries, an organized library and settings around the
existing yt-dlp core (`downloader.py`) and subtitle cleaner (`subtitles.py`), which stay.

## Why

The owner uses it for two things: watching videos offline, and turning videos into R&D material for his
projects and products that other tools can read: a clean transcript, a summary and the thumbnail.
Today it is a dense Tk window with a big log; it has no summaries, files land flat in one folder, and the
download location is not remembered.

## Goals

1. **One folder per video, grouped by project**, under a library root:
   `<library>/<Project>/<YYYY-MM-DD> <Title>/` holding, depending on what was chosen:
   `video.mp4` (or `audio.mp3`), `thumbnail.jpg`, `transcript.txt` (clean), `summary.md`, `info.md`
   (title, channel, link, length, upload date, download date, project) and the raw subtitle files in
   `raw/`. Each project folder has an `INDEX.md`: one line per video with its link and the summary's first
   line, so a command-line tool can be pointed at a project folder and read everything.
2. **What to download**, as presets plus the individual switches behind them:
   - Watch offline: video, thumbnail, transcript.
   - Research: thumbnail, transcript, summary (no video file).
   - Everything: video, thumbnail, transcript, summary, raw subtitles, info.json.
   - Audio: MP3, thumbnail, transcript.
   Quality: the detected qualities after Check, or 360/480/720/1080/Best.
3. **Summaries** of the transcript in Markdown: a short TL;DR, key points, details useful for R&D (numbers,
   parts, tools, steps, prices), and open questions. Written in English even for an Arabic transcript,
   and told the project name so it focuses on what matters to it. Engines: CLI A (`cli-a`,
   default, no API key), CLI B (`cli-b`), or Off. A video without subtitles gets no summary and says so.
   A summary can also be made later for an existing video folder.
4. **Where to save**: a default library folder (`~/Videos/Video Collector`) set in Settings, and a
   Change button on each download for a one-off location. The project list comes from the folders in the
   library; typing a new name creates it.
5. **Several links at once**: paste one or more links (one per line); they are queued and downloaded one
   after another, each with its own progress. Playlists only when the playlist switch is on.
6. **Library page**: every collected video by project, with thumbnail, title and what it has (video,
   transcript, summary); buttons to play, open the folder, open the summary, make a summary.
7. **Settings** (saved in `~/.config/video-collector/settings.json`): library folder, default project,
   default preset, quality, subtitle languages (`en,en-orig,en-US,en-GB,ar,ar-orig`), summary engine, light/dark, and the yt-dlp
   version with an Update button (`pkexec yt-dlp -U`, since it is installed system-wide).
8. The Tools Hub shows its status: the collector publishes `~/My-Tools/shared-data/video-collector.json`
   (videos collected, last one, library path).

## Non-goals

- No editing, cutting or transcoding beyond what yt-dlp does.
- No cloud upload or sharing; no account logins in the app (yt-dlp cookies stay out of scope).
- No speech-to-text for videos without subtitles (a later backlog item).

## Anti-goals

- A failed summary or a missing subtitle loses the download: the video and transcript are kept and the
  summary can be retried.
- Files of two videos mixed in one folder, or a re-download overwriting a summary someone edited.
- The window freezing while downloading or summarizing.

## Decided by the owner

- Summary engine CLI A by default, CLI B as an option.
- Folder per video grouped by project; default location plus a per-download choice.

## Builder's calls (marked)

- PySide6 for the window, like Bills Ledger, Laptop Doctor and Tools Hub (call).
- Default library `~/Videos/Video Collector` (call).
- Folder name `<YYYY-MM-DD> <Title>` with the download date, title cut to 80 characters and made safe for
  the file system; a second download of the same video goes into the same folder (matched by the video id
  in `info.md`) and keeps an existing `summary.md` (call).
- Summaries in English (call).

## Settled after review (builder's calls)

1. **Same video, matched per project.** Each project folder is self-contained for other tools, so the
   same video in two projects gets a folder in each. Inside one project a second download of it reuses the
   folder and only adds files that are missing: nothing existing is overwritten (video, thumbnail,
   transcript, summary).
2. **Playlists** (switch on): every item is its own queue entry, folder and summary. Before queueing more
   than 10 items the window asks to confirm, showing how many summaries that means.
3. **The new window replaces the old one** (`app.py` goes). The old flat folder `~/Downloads/Creator Video
   Collector` does not exist on this machine, so there is nothing to import.
4. **Summaries run without tools**: the transcript is untrusted text, so `cli-a` runs with every tool
   disallowed (and `cli-b` read-only, no network), with a 10 minute limit. A missing CLI, a failure or
   a timeout is written to `info.md` (`Summary: failed, <reason>`) and the Library shows "Make summary" for
   it. Transcripts longer than about 120,000 characters are summarized in parts, then the parts together.
5. **Quality**: one choice per download batch. Check on a single link offers its detected qualities;
   several links use 360/480/720/1080/Best. Research and Audio hide the quality choice.
6. **Project names**: made safe for folder names; matched to an existing project ignoring case; empty means
   `Unsorted`. The default project is optional.

## Left to the builder

Layout details, the summary prompt wording, how long transcripts are split, test structure.
