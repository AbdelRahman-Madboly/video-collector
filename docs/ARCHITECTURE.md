# Architecture

A PySide6 window on top of small modules that hold all the logic. The modules take their programs
(yt-dlp, the summary engine) as injectable runners, so the tests never start a real one.

```text
src/creator_video_collector/
  __main__.py     entry point: python -m creator_video_collector
  config.py       app name, quality options, default subtitle languages
  settings.py     the owner's choices, saved to ~/.config/video-collector/settings.json
  downloader.py   yt-dlp metadata parsing and the per-video yt-dlp command
  subtitles.py    VTT/SRT cleanup into a plain transcript
  library.py      one folder per video, grouped by project; info.md and INDEX.md
  summarize.py    summary prompt and the engine command, run with no tools in an empty folder
  jobs.py         one link becomes one library folder; publishes the Tools Hub summary
  procs.py        every child process goes through here so closing the window can stop them
  ui/window.py    Download, Library and Settings pages; jobs run on a worker thread
  ui/theme.py     light and dark styles
youtube_visual_collector.py  launcher kept for the old command name
tests/            pytest, offscreen Qt, no network
docs/design/      the design and plan for version 2
```

## Rules the code keeps

- Only http(s) links reach yt-dlp, and always after `--`, so a link can never be read as an option.
- Video downloads never fall back to a silent or audio-only file when video was asked for.
- Nothing in a video folder is overwritten; a second run fetches only what is missing.
- info.md is written before the download starts, so a failed download still leaves a readable folder.
- An empty subtitle file means no transcript, and no summary is asked for.
- Values from the internet (titles, channels) are kept to one line in info.md.
- The transcript is untrusted text: the summary engine gets no tools, no MCP servers, no web search, and
  runs in an empty temporary folder.

## Shared data

After each job the collector writes `~/My-Tools/shared-data/video-collector.json` (override with
`MYTOOLS_SHARED`): video count, latest video and library path, read by the Tools Hub.
