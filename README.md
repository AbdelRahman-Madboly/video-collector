# Creator Video Collector

Download videos for offline watching and turn them into research material: a clean transcript, the
thumbnail and an optional summary, in one folder per video, grouped by project. A PySide6 window around
[yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Status

2.0.0 plus unreleased changes (see [CHANGELOG.md](CHANGELOG.md)). All tests pass and run in CI; a first
check on a few real videos is still open.

## What it does

Open **Creator Video Collector** from the desktop or the app menu (`youtube-visual-collector` in a terminal).

- **Download:** paste one or more links (one per line), pick or type a **project**, choose what to get, press
  **Start download**. **Check link** shows the title, channel, length, subtitles and the real qualities of a
  single link. **Change…** saves this batch somewhere else; **Default** goes back to the library.
  - Watch offline: video, thumbnail, transcript
  - Research: thumbnail, transcript, summary (no video file)
  - Everything: video, thumbnail, transcript, summary, raw subtitles, info.json
  - Audio: MP3, thumbnail, transcript
- **Library:** every video by project with its thumbnail; play it, open its folder or summary, make a summary
  later, or open the project's `INDEX.md`.
- **Settings:** library folder (default `~/Videos/Video Collector`), default project and download, quality,
  subtitle languages, the summary command, light or dark, and **Update yt-dlp**.

### What lands on disk

```
~/Videos/Video Collector/<Project>/
  INDEX.md                         every video of the project, its link and the summary's first line
  2026-10-27 <Title>/
    video.mp4 | audio.mp3          when chosen
    thumbnail.jpg
    transcript.txt                 clean text from the subtitles
    summary.md                     TL;DR, key points, details for R&D, open questions
    info.md                        title, channel, link, length, dates, project, transcript and summary state
    raw/                           original subtitles and yt-dlp info.json (Everything)
```

Any tool that reads files can be pointed at a project folder. A second download of the same link in the
same project adds only what is missing and never overwrites a file (an edited summary is kept).

### Summaries

Summaries are off until you set **Summary command** in Settings. The summary command is any command that
reads a transcript on stdin and prints a summary on stdout, for example a language model's command-line
tool. The collector sends it a prompt that asks for four Markdown sections, followed by the transcript.

**Warning:** the transcript is untrusted text from the internet and can contain instructions aimed at
the tool that reads it. Use a command that cannot run tools, edit files or browse, or make sure those
features are turned off. The collector limits what the command can do:

- The prompt and transcript go to the command on stdin only, never as an argument.
- The command line is split like a shell line, but no shell runs it.
- It runs in an empty temporary folder, with a 10 minute limit, and with a small environment: `PATH`,
  `HOME`, user, locale and XDG folder variables only. Add other variable names (for example the one that
  holds an API key) to `summary_env` in `settings.json`.
- When `bwrap` (bubblewrap) is installed and **Run it in a sandbox** is on (the default), the command runs
  with the whole file system read-only, a private `/tmp` and no network. Tick **Allow network inside the
  sandbox** for a tool that needs to reach an online service; it can still read your files then, so keep
  its tools turned off. Without `bwrap` the command runs unsandboxed.
- `summary_guards` in `settings.json` maps a program name to the option groups it must always get. The
  collector adds any group that is missing from the command, so a tool that can use tools never runs
  without the options that turn them off:

  ```json
  "summary_guards": {"my-assistant": ["--no-tools", "--sandbox read-only"]}
  ```

Long transcripts are summarized in parts, then together. A failure keeps the download and is noted in
`info.md`.

## What it does not do

- No speech-to-text: a video without subtitles gets no transcript and no summary.
- It does not write summaries by itself: you bring the summary command.
- It cannot recognise every tool that can act on what it reads: the guards are the ones you list.
- Downloads saved to a one-off folder (**Change…**) do not show on the Library page, which reads the
  library folder from Settings.
- It does not update yt-dlp by itself; press **Update yt-dlp** in Settings when sites start failing.
- No cookies or logins: private or age-restricted videos fail with the yt-dlp error.
- Linux only (tested on Ubuntu).

## Install

Needs Python 3.12+, [uv](https://docs.astral.sh/uv/), `yt-dlp` and `ffmpeg`.

```sh
sudo apt install ffmpeg
./install_youtube_visual_collector.sh       # uv environment, launcher, menu entry
```

## Run

```sh
youtube-visual-collector                    # after installing
uv run python youtube_visual_collector.py   # straight from the folder
```

## Develop

```sh
uv run python -m pytest -q                  # tests never touch the network, yt-dlp or a summary command
```

Only http(s) links reach yt-dlp, always after `--`. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for
the modules.

## License

MIT, see [LICENSE](LICENSE).
