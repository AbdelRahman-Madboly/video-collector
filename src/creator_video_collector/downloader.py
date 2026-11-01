from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional


@dataclass(frozen=True)
class QualityChoice:
    label: str
    selector: str


@dataclass(frozen=True)
class VideoMetadata:
    title: str
    qualities: List[QualityChoice]
    manual_subtitles: List[str]
    auto_subtitles: List[str]
    uploader: str = ""
    source: str = ""
    duration: str = ""
    is_playlist: bool = False
    playlist_count: int = 0
    video_id: str = ""
    url: str = ""
    upload_date: str = ""                      # YYYY-MM-DD
    entries: tuple = ()                        # links of a playlist's videos
    thumbnail: str = ""                        # link of the thumbnail picture


def resolution_to_format(resolution: str) -> str:
    if resolution.lower() == "best":
        return (
            "bv*[vcodec^=avc1][ext=mp4]+ba[ext=m4a]/"
            "bv*[vcodec!=none][ext=mp4]+ba[ext=m4a]/"
            "bv*[vcodec!=none]+ba/"
            "b[vcodec!=none][ext=mp4]/b[vcodec!=none]"
        )

    height = int(resolution)
    return (
        f"bv*[height<={height}][vcodec^=avc1][ext=mp4]+ba[ext=m4a]/"
        f"bv*[height<={height}][vcodec!=none][ext=mp4]+ba[ext=m4a]/"
        f"bv*[height<={height}][vcodec!=none]+ba/"
        f"b[height<={height}][vcodec!=none][ext=mp4]/"
        f"b[height<={height}][vcodec!=none]/"
        "bv*[vcodec!=none]+ba/b[vcodec!=none]"
    )


def format_id_to_selector(format_id: str) -> str:
    # Never fall back to the bare video-only format ID for video downloads.
    # If audio cannot be merged, the download should fail instead of producing a silent MP4.
    return f"{format_id}+ba[ext=m4a]/{format_id}+ba"


def playlist_args(allow_playlist: bool) -> List[str]:
    return ["--yes-playlist"] if allow_playlist else ["--no-playlist"]


def _quality_sort_key(choice: QualityChoice) -> int:
    match = re.match(r"(\d+)p", choice.label)
    return int(match.group(1)) if match else 0


def parse_metadata(raw: dict) -> VideoMetadata:
    is_playlist = "entries" in raw and bool(raw.get("entries"))
    playlist_count = 0
    info = raw
    if is_playlist:
        entries = [entry for entry in raw.get("entries") or [] if entry]
        playlist_count = len(entries)
        info = entries[0] if entries else raw

    title = info.get("title") or "Unknown title"
    choices: List[QualityChoice] = []
    seen = set()

    for item in info.get("formats") or []:
        format_id = str(item.get("format_id") or "").strip()
        vcodec = item.get("vcodec") or "none"
        height = item.get("height")
        ext = item.get("ext") or ""
        if not format_id or vcodec == "none" or not height:
            continue

        note = item.get("format_note") or ""
        fps = item.get("fps")
        acodec = item.get("acodec") or "none"
        audio_note = "with audio" if acodec != "none" else "+ best audio"
        label = re.sub(r"\s+", " ", f"{height}p {ext} {note} {audio_note} | id {format_id}").strip()
        key = (height, ext, vcodec, fps, audio_note)
        if key in seen:
            continue
        seen.add(key)
        selector = format_id if acodec != "none" else format_id_to_selector(format_id)
        choices.append(QualityChoice(label=label, selector=selector))

    qualities = sorted(choices, key=_quality_sort_key, reverse=True)[:30]
    return VideoMetadata(
        title=title,
        qualities=qualities,
        manual_subtitles=sorted((info.get("subtitles") or {}).keys()),
        auto_subtitles=sorted((info.get("automatic_captions") or {}).keys()),
        uploader=info.get("uploader") or info.get("channel") or "",
        source=info.get("extractor_key") or info.get("extractor") or "",
        duration=info.get("duration_string") or "",
        is_playlist=is_playlist,
        playlist_count=playlist_count,
        video_id=str(info.get("id") or ""),
        thumbnail=(info.get("thumbnail") or "") if is_web_link(info.get("thumbnail") or "") else "",
        url=info.get("webpage_url") or info.get("original_url") or "",
        upload_date=_iso_day(info.get("upload_date") or ""),
        entries=tuple(e.get("webpage_url") or e.get("url") or "" for e in (raw.get("entries") or []) if e)
        if is_playlist else (),
    )


def _iso_day(yyyymmdd: str) -> str:
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}" if len(yyyymmdd) == 8 else ""


def is_web_link(url: str) -> bool:
    """Only http(s) links reach yt-dlp: anything else could be read as an option or a local file."""
    return bool(re.match(r"^https?://[^\s]+$", url or ""))


def require_web_link(url: str) -> str:
    if not is_web_link(url):
        raise ValueError(f"Not a web link: {url[:80]}")
    return url


def fetch_metadata(url: str, allow_playlist: bool, runner=None) -> VideoMetadata:
    """One video's details, or with allow_playlist a playlist's video links (read flat: only the list)."""
    from . import procs
    flat = ["--flat-playlist"] if allow_playlist else []
    command = ["yt-dlp", "-J", "--skip-download", *playlist_args(allow_playlist), *flat, "--", require_web_link(url)]
    result = (runner or procs.run)(command, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"yt-dlp check failed with exit code {result.returncode}")
    return parse_metadata(json.loads(result.stdout))


def run_command_stream(command: List[str], on_line: Callable[[str], None]) -> int:
    from . import procs
    return procs.stream(command, on_line)


def build_job_command(url: str, folder: Path, missing: set, *, format_selector: Optional[str],
                      fallback_resolution: str, subtitle_languages: str) -> List[str]:
    """yt-dlp for one video into its library folder, asking only for the parts still missing.
    Parts: video, audio, thumbnail, subs (into raw/), info_json (into raw/)."""
    folder = Path(folder)
    require_web_link(url)
    command = ["yt-dlp", "--no-playlist", "--newline", "--no-part", "--no-overwrites"]
    if "audio" in missing:
        command += ["-o", str(folder / "audio.%(ext)s"),
                    "--extract-audio", "--audio-format", "mp3", "--audio-quality", "0"]
    elif "video" in missing:
        command += ["-o", str(folder / "video.%(ext)s"),
                    "-f", format_selector or resolution_to_format(fallback_resolution),
                    "--merge-output-format", "mp4", "--remux-video", "mp4"]
    else:
        command += ["-o", str(folder / "video.%(ext)s"), "--skip-download"]
    if "thumbnail" in missing:
        command += ["-o", f"thumbnail:{folder / 'thumbnail.%(ext)s'}", "--write-thumbnail", "--convert-thumbnails", "jpg"]
    if "subs" in missing:
        command += ["-o", f"subtitle:{folder / 'raw' / 'sub.%(ext)s'}", "--write-subs", "--write-auto-subs",
                    "--sub-langs", subtitle_languages, "--sub-format", "vtt",
                    "--sleep-subtitles", "2"]          # YouTube answers 429 to quick subtitle requests
    if "info_json" in missing:
        command += ["-o", f"infojson:{folder / 'raw' / 'info'}", "--write-info-json"]
    return command + ["--", url]                 # after "--" the link can never be read as an option
