# Architecture

Creator Video Collector is intentionally small, but split into clear modules so it can grow without becoming one large script.

```text
src/creator_video_collector/
  app.py          Tkinter GUI, splash screen, theme, events, progress, logs
  config.py       App constants, palettes, defaults
  downloader.py   yt-dlp metadata parsing and command generation
  subtitles.py    VTT/SRT cleanup into plain TXT
  __main__.py     python -m entry point
youtube_visual_collector.py  Backward-compatible launcher
assets/          App icon and future visual assets
docs/            Design and architecture docs
```

## Design Principles

- GUI code calls service modules; service modules do not import Tkinter.
- Video downloads must never fall back to audio-only when video is requested.
- Playlist download is opt-in.
- Logs are visible and copyable for debugging.
- TXT transcripts are plain text, without timestamps, for later AI/content use.
- UI design changes should be tokenized in config.py before being spread across widgets.

## UI Handoff

Keep downloader and subtitle behavior independent from the GUI so future frontends can reuse the same core logic.
