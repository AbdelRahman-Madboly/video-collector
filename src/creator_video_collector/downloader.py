from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional


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


def ensure_tool_exists(tool_name: str) -> bool:
    return shutil.which(tool_name) is not None


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
    )


def fetch_metadata(url: str, allow_playlist: bool) -> VideoMetadata:
    command = ["yt-dlp", "-J", "--skip-download", *playlist_args(allow_playlist), url]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"yt-dlp check failed with exit code {result.returncode}")
    return parse_metadata(json.loads(result.stdout))


def build_download_command(
    url: str,
    target_folder: Path,
    *,
    allow_playlist: bool,
    download_video: bool,
    download_audio: bool,
    download_subtitles: bool,
    clean_txt: bool,
    download_thumbnail: bool,
    download_description: bool,
    download_info_json: bool,
    selected_format: Optional[str],
    fallback_resolution: str,
    subtitle_languages: str,
) -> List[str]:
    output_template = str(target_folder / "%(title).120B [%(id)s].%(ext)s")
    command = ["yt-dlp", url, "-o", output_template, "--newline", *playlist_args(allow_playlist)]

    if download_audio and not download_video:
        command.extend(["--extract-audio", "--audio-format", "mp3", "--audio-quality", "0"])
    elif download_video:
        command.extend([
            "-f", selected_format or resolution_to_format(fallback_resolution),
            "--merge-output-format", "mp4",
            "--remux-video", "mp4",
        ])
    else:
        command.append("--skip-download")

    if download_subtitles or clean_txt:
        command.extend([
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs", subtitle_languages,
            "--sub-format", "vtt",
        ])

    if download_thumbnail:
        command.extend(["--write-thumbnail", "--convert-thumbnails", "jpg"])
    if download_description:
        command.append("--write-description")
    if download_info_json:
        command.append("--write-info-json")

    command.append("--no-part")
    return command


def run_command_stream(command: List[str], on_line: Callable[[str], None]) -> int:
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    assert process.stdout is not None
    for line in process.stdout:
        on_line(line.rstrip())
    return process.wait()
