# Creator Video Collector

<p align="center">
  <strong>A Linux desktop app for downloading videos, covers, subtitles, and clean TXT transcripts with yt-dlp.</strong>
</p>

<p align="center">
  <a href="#features">Features</a> ·
  <a href="#requirements">Requirements</a> ·
  <a href="#installation">Installation</a> ·
  <a href="#usage">Usage</a> ·
  <a href="#development">Development</a>
</p>

Creator Video Collector is a creator-focused GUI around [`yt-dlp`](https://github.com/yt-dlp/yt-dlp). It helps you collect video assets, cover images, subtitle files, and clean plain-text transcripts from YouTube and other `yt-dlp` supported websites.

The app is designed for content creators, researchers, editors, and anyone who wants usable transcripts without manually cleaning `.vtt` / `.srt` subtitle files.

## Features

- Download from YouTube and other `yt-dlp` supported websites.
- Check a URL before downloading to detect title, quality options, and subtitle availability.
- Choose real detected video quality or use a fallback quality.
- Download MP4 video with safer video-plus-audio format selection.
- Download clean transcript text as `.clean.txt`.
- Download cover images, descriptions, and `info.json` metadata.
- Download audio-only MP3.
- Optional playlist support, disabled by default to prevent accidental bulk downloads.
- Default subtitle language pattern: `en.*,ar.*`.
- Progress bar, status messages, and copyable logs for debugging.
- Light/dark mode and startup splash screen.
- Desktop launcher, app-menu launcher, and terminal command installer.

## Screenshots

Add screenshots here after publishing the first GitHub release.

```text
assets/screenshots/main-window.png
assets/screenshots/dark-mode.png
```

## Requirements

This project currently targets Ubuntu/Debian-style Linux desktops.

Install system packages:

```bash
sudo apt update
sudo apt install ffmpeg yt-dlp python3 python3-tk -y
```

Install Python requirements:

```bash
pip install -r requirements.txt
```

At the moment, there are no required pip runtime dependencies. Tkinter is provided by the `python3-tk` system package.

## Installation

Clone the repository:

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

Run the installer:

```bash
chmod +x install_youtube_visual_collector.sh
./install_youtube_visual_collector.sh
```

The installer creates:

| Target | Path / Command |
| --- | --- |
| Terminal command | `youtube-visual-collector` |
| Desktop launcher | `~/Desktop/Creator Video Collector.desktop` |
| App menu launcher | `~/.local/share/applications/youtube-visual-collector.desktop` |

## Launch

After installation:

```bash
youtube-visual-collector
```

Run directly from the project folder:

```bash
python3 youtube_visual_collector.py
```

Run as a module:

```bash
python3 -m src.creator_video_collector
```

## Usage

1. Open Creator Video Collector.
2. Paste a video URL.
3. Click `Check URL` to load metadata, qualities, and subtitle availability.
4. Choose a mode:
   - `Video + TXT + Cover`
   - `Video only`
   - `TXT subtitles only`
   - `Audio only MP3`
   - `Everything`
5. Choose a real quality if available, or keep the fallback quality.
6. Set subtitle languages, for example `en.*,ar.*`.
7. Choose the output folder.
8. Click `Start Download`.
9. Use `Open Folder`, `Copy Log`, or `Save Log` after completion.

Clean transcript files are saved beside subtitle files with this suffix:

```text
.clean.txt
```

Example output:

```text
Video Title [video_id].mp4
Video Title [video_id].jpg
Video Title [video_id].en.vtt
Video Title [video_id].en.clean.txt
```

## Project Structure

```text
.
├── assets/
│   └── creator-video-collector.svg
├── docs/
│   └── ARCHITECTURE.md
├── src/
│   └── creator_video_collector/
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py
│       ├── config.py
│       ├── downloader.py
│       └── subtitles.py
├── install_youtube_visual_collector.sh
├── requirements.txt
├── README.md
└── youtube_visual_collector.py
```

## Architecture

The app is split into small modules so the downloader logic can grow independently from the GUI.

| File | Purpose |
| --- | --- |
| `src/creator_video_collector/app.py` | Tkinter GUI, splash screen, theme, events, progress, logs |
| `src/creator_video_collector/downloader.py` | `yt-dlp` metadata parsing and command generation |
| `src/creator_video_collector/subtitles.py` | `.vtt` / `.srt` cleanup into plain `.txt` |
| `src/creator_video_collector/config.py` | App constants, palettes, defaults |
| `youtube_visual_collector.py` | Simple top-level compatibility launcher |

## About `youtube_visual_collector.py`

This file is intentionally kept as a convenience launcher:

```python
from src.creator_video_collector.app import main
```

It lets users run the app with:

```bash
python3 youtube_visual_collector.py
```

The main application code lives in `src/creator_video_collector/`.

## Troubleshooting

### Video downloaded without audio

Update to the latest project version and redownload the video. The downloader is designed to request video plus best audio when video is selected.

### Subtitles are `.vtt`, but no `.clean.txt` appeared

Make sure `Clean TXT` is enabled. You can also click `Clean Subtitle` in the app and select an existing `.vtt` or `.srt` file.

### yt-dlp fails for a website

Update `yt-dlp` through your package manager or install a newer version using your preferred method. Some sites change often and require a recent `yt-dlp` build.

### Login, cookies, region, or age restriction errors

Some videos require authentication or browser cookies. Advanced cookie/auth options are not exposed in the GUI yet.

## Development

Run syntax checks:

```bash
python3 -m py_compile youtube_visual_collector.py src/creator_video_collector/*.py
bash -n install_youtube_visual_collector.sh
```

Recommended local workflow:

```bash
python3 youtube_visual_collector.py
```

Design and architecture notes:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## Roadmap

- Save user preferences for theme, folder, and subtitle languages.
- Add download history.
- Add cancel/pause support.
- Add automated tests for command generation and subtitle cleanup.
- Add advanced `yt-dlp` options for cookies and authentication helpers.
- Add packaged releases for easier installation.

## Contributing

Issues and pull requests are welcome after the repository is published. Please keep changes focused and avoid mixing UI redesigns with downloader behavior changes in the same pull request.

## License

No license has been selected yet. Add a license before publishing publicly. MIT is a good default for a general-purpose open-source utility.
