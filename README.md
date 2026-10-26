# Creator Video Collector

Download videos for offline watching and turn them into research material that other tools can
read: a clean transcript, the thumbnail and a summary, in one folder per video, grouped by project.

## Use

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
  subtitle languages, who writes summaries (CLI A, CLI B or off), light or dark, and **Update yt-dlp**.

## What lands on disk

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

Point any tool that reads files at a project folder and it can read everything. A second download of the same link in
the same project adds only what is missing and never overwrites a file (an edited summary is kept).

## Summaries

Written by `cli-a` (default) or `cli-b` from your own login, with no tools at all and in an empty
temporary folder: the transcript is text from the internet and is only ever summarized. Long transcripts are
summarized in parts, then together. A failure keeps the download and is noted in `info.md`.

## Install and develop

```sh
./install_youtube_visual_collector.sh       # uv environment, launcher, menu entry
uv run python -m pytest -q                  # tests never touch the network, yt-dlp or the summary tool
```

Needs `yt-dlp` and `ffmpeg`. Only http(s) links reach yt-dlp, always after `--`.
