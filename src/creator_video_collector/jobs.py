"""One download job: a link becomes a folder in the library with the parts the owner chose."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

from . import library, subtitles, summarize
from .downloader import VideoMetadata, build_job_command, fetch_metadata, is_web_link, run_command_stream

PRESETS = {
    "watch": ("video", "thumbnail", "transcript"),
    "research": ("thumbnail", "transcript", "summary"),
    "everything": ("video", "thumbnail", "transcript", "summary", "raw", "info_json"),
    "audio": ("audio", "thumbnail", "transcript"),
}
PRESET_NAMES = {"watch": "Watch offline", "research": "Research", "everything": "Everything", "audio": "Audio"}


class JobError(Exception):
    pass


@dataclass
class Job:
    url: str
    project: str
    parts: set
    quality: str
    format_selector: str | None
    library: Path
    langs: str
    summary: object = ""           # summarize.Options, or a plain summary command


def _missing(folder: Path, parts: set) -> set:
    """Download parts yt-dlp still has to fetch; nothing already in the folder is fetched again."""
    need = set()
    if "video" in parts and not (folder / "video.mp4").exists():
        need.add("video")
    if "audio" in parts and not (folder / "audio.mp3").exists():
        need.add("audio")
    if "thumbnail" in parts and not (folder / "thumbnail.jpg").exists():
        need.add("thumbnail")
    raw_subs = subtitles.find_subtitle_files(folder / "raw") if (folder / "raw").exists() else []
    if ("transcript" in parts and not (folder / "transcript.txt").exists() and not raw_subs) \
            or ("raw" in parts and not raw_subs):
        need.add("subs")
    if "info_json" in parts and not list((folder / "raw").glob("*.info.json")):
        need.add("info_json")
    return need


def _tidy_stray_subtitles(folder: Path) -> None:
    """yt-dlp writes subtitles next to the media and moves them into raw/ at the end; a run that stopped
    early leaves them as video.<lang>.vtt. Move them where they belong."""
    for f in list(folder.glob("video.*.vtt")) + list(folder.glob("audio.*.vtt")):
        (folder / "raw").mkdir(exist_ok=True)
        target = folder / "raw" / ("sub." + f.name.split(".", 1)[1])
        if target.exists():
            f.unlink()
        else:
            f.replace(target)


def _pick_subtitle(raw: Path, langs: str) -> Path | None:
    files = subtitles.find_subtitle_files(raw) if raw.exists() else []
    for pattern in [p.strip().rstrip(".*").rstrip("*") for p in langs.split(",") if p.strip()]:
        for f in files:
            lang = f.name.split(".")[-2] if f.name.count(".") >= 2 else ""
            if lang.startswith(pattern):
                return f
    return files[0] if files else None


def _has_text(path: Path) -> bool:
    try:
        return bool(path.read_text(encoding="utf-8", errors="ignore").strip())
    except OSError:
        return False


def shared_dir() -> Path:
    return Path(os.environ.get("MYTOOLS_SHARED") or Path.home() / "My-Tools" / "shared-data")


def publish(lib: Path) -> None:
    """The collector's line in the Tools Hub: how many videos, the latest one, where the library is."""
    entries = library.scan(lib)
    last = entries[0] if entries else None
    body = {"tool": "video-collector", "updated": time.time(), "level": "ok",
            "headline": f"{len(entries)} videos · latest: {last.title}" if last else "No videos collected yet",
            "details": [f"Library: {lib}"] + ([f"{last.project} · {last.day}"] if last else []),
            "data": {"videos": len(entries), "library": str(lib),
                     "projects": sorted({e.project for e in entries})}}
    out = shared_dir() / "video-collector.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(".video-collector.json.tmp")
    tmp.write_text(json.dumps(body, ensure_ascii=False, indent=2))
    tmp.replace(out)


def make_summary(folder: Path, summary, runner=None) -> bool:
    """Write summary.md from transcript.txt; on failure keep everything and note why in info.md."""
    entry = library.read_entry(folder)
    transcript = (folder / "transcript.txt")
    if entry is None or not _has_text(transcript):
        return False
    from . import procs
    try:
        text = summarize.summarize(transcript.read_text(), entry.title, entry.project, summary,
                                   runner=runner or procs.run)
    except summarize.SummaryError as e:
        library.set_summary_state(folder, f"failed, {e}")
        return False
    (folder / "summary.md").write_text(f"# {entry.title}\n\n{text.strip()}\n")
    library.set_summary_state(folder, f"done ({Path(summarize.command(getattr(summary, 'command', summary))[0]).name})")
    library.write_index(folder.parent)
    return True


def expand(url: str, allow_playlist: bool, fetch: Callable[[str], VideoMetadata] | None = None) -> list[str]:
    """A playlist link becomes the links of its videos when playlists are allowed."""
    if not allow_playlist:
        return [url]
    meta = (fetch or (lambda u: fetch_metadata(u, True)))(url)
    return [u for u in meta.entries if is_web_link(u)] if meta.is_playlist and meta.entries else [url]


def run(job: Job, on_line: Callable[[str], None], fetch: Callable[[str], VideoMetadata] | None = None,
        download: Callable | None = None, summary_runner=None, today: date | None = None,
        publish_library: Path | None = None) -> library.Entry:
    """publish_library: the library the Tools Hub counts (the settings one), when this job goes elsewhere."""
    from . import procs
    summary_runner = summary_runner or procs.run
    parts = set(job.parts) | ({"transcript"} if "summary" in job.parts else set())   # a summary needs its transcript
    fetch = fetch or (lambda u: fetch_metadata(u, False))
    download = download or run_command_stream
    meta = fetch(job.url)
    folder = library.video_dir(job.library, job.project, meta.title, meta.video_id, today or date.today())
    on_line(f"Folder: {folder}")
    card = {"title": meta.title, "channel": meta.uploader, "url": meta.url or job.url, "id": meta.video_id,
            "duration": meta.duration, "uploaded": meta.upload_date,
            "downloaded": (today or date.today()).isoformat(), "project": folder.parent.name}
    library.write_info(folder, card)            # written first, so a failed download still leaves a readable folder
    need = _missing(folder, parts)
    if need:
        lines: list[str] = []
        cmd = build_job_command(meta.url or job.url, folder, need, format_selector=job.format_selector,
                                fallback_resolution=job.quality, subtitle_languages=job.langs)

        def keep(line: str) -> None:
            lines.append(line)
            on_line(line)
        if download(cmd, keep) != 0:
            errors = [l for l in lines if l.startswith("ERROR")] or lines[-1:] or ["yt-dlp failed"]
            reason = errors[-1].removeprefix("ERROR:").strip()
            media = {"video": "video.mp4", "audio": "audio.mp3"}
            if any(part in need and not (folder / name).exists() for part, name in media.items()):
                raise JobError(reason)
            on_line(f"Kept going without a part: {reason}")     # a subtitle or thumbnail failed, not the video
        _tidy_stray_subtitles(folder)

    transcript_state = "none"
    transcript = folder / "transcript.txt"
    if transcript.exists() and not _has_text(transcript):
        transcript.unlink()                      # an empty subtitle file is no transcript
    if transcript.exists():
        transcript_state = "yes"
    elif "transcript" in parts and (sub := _pick_subtitle(folder / "raw", job.langs)):
        subtitles.clean_subtitle_file_to_txt(sub, transcript)
        if _has_text(transcript):
            transcript_state = sub.name.split(".")[-2]
        else:
            transcript.unlink()
            on_line("The subtitles have no text: no transcript")
    if "raw" not in parts and (folder / "raw").exists():
        for f in subtitles.find_subtitle_files(folder / "raw"):
            f.unlink()
        if not any((folder / "raw").iterdir()):
            (folder / "raw").rmdir()

    library.write_info(folder, {"transcript": transcript_state})
    if "summary" in parts and not (folder / "summary.md").exists():
        if (folder / "transcript.txt").exists():
            on_line("Writing the summary…")
            make_summary(folder, job.summary, summary_runner)
        else:
            library.set_summary_state(folder, "none, no transcript")
    library.write_index(folder.parent)
    publish(publish_library or job.library)
    return library.read_entry(folder)


def ytdlp_version(runner=subprocess.run) -> str:
    try:
        return runner(["yt-dlp", "--version"], capture_output=True, text=True, timeout=20).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "not installed" if shutil.which("yt-dlp") is None else "unknown"
