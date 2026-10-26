"""The library on disk: one folder per video, grouped by project, readable by people and by other tools.

<library>/<Project>/<YYYY-MM-DD> <Title>/  video.mp4 | audio.mp3, thumbnail.jpg, transcript.txt,
summary.md, info.md, raw/   and   <library>/<Project>/INDEX.md
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

TITLE_MAX = 80
INFO = "info.md"
FIELDS = [("title", "Title"), ("channel", "Channel"), ("url", "Link"), ("id", "ID"), ("duration", "Length"),
          ("uploaded", "Uploaded"), ("downloaded", "Downloaded"), ("project", "Project"),
          ("transcript", "Transcript"), ("summary", "Summary")]


def _clean(text: str) -> str:
    text = re.sub(r"[/\\:*?\"<>|\x00-\x1f]+", " - ", text)
    text = re.sub(r"[^\w\s\-.,()&'+!#\[\]]", "", text)        # emoji and other symbols
    text = re.sub(r"(\s*-\s*)+", " - ", text)
    return re.sub(r"\s+", " ", text).strip(" .-")


def safe_title(title: str) -> str:
    return _clean(title)[:TITLE_MAX].rstrip(" .-") or "Untitled"


def project_name(raw: str) -> str:
    return _clean(raw or "")[:60] or "Unsorted"


def project_dir(library: Path, project: str) -> Path:
    name = project_name(project)
    library = Path(library)
    if library.is_dir():
        for d in library.iterdir():
            if d.is_dir() and d.name.lower() == name.lower():
                return d
    return library / name


def _info_values(folder: Path) -> dict[str, str]:
    try:
        text = (Path(folder) / INFO).read_text()
    except OSError:
        return {}
    labels = {label: key for key, label in FIELDS}
    out = {}
    for line in text.splitlines():
        m = re.match(r"^- \*\*(.+?):\*\* (.*)$", line)
        if m and m.group(1) in labels and labels[m.group(1)] not in out:   # first one wins
            out[labels[m.group(1)]] = m.group(2).strip()
    return out


def video_dir(library: Path, project: str, title: str, video_id: str, day: date) -> Path:
    """The folder for this video in this project: the one already holding it, else a new dated one."""
    pdir = project_dir(library, project)
    if pdir.is_dir() and video_id:
        for d in sorted(pdir.iterdir()):
            if d.is_dir() and _info_values(d).get("id") == video_id:
                return d
    folder = pdir / f"{day.isoformat()} {safe_title(title)}"
    n = 2
    while folder.exists() and _info_values(folder).get("id") not in (None, video_id):
        folder = pdir / f"{day.isoformat()} {safe_title(title)} ({n})"
        n += 1
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _one_line(value) -> str:
    """Values come from the internet (titles, channels): never let one start a new line of info.md."""
    return re.sub(r"[\x00-\x1f\x7f]+", " ", str(value)).strip()


def write_info(folder: Path, meta: dict) -> None:
    """info.md: what this video is and what was collected, as a small Markdown card."""
    old = _info_values(folder)
    merged = {**old, **{k: _one_line(v) for k, v in meta.items() if v not in (None, "")}}
    lines = [f"# {merged.get('title', 'Untitled')}", ""]
    lines += [f"- **{label}:** {merged[key]}" for key, label in FIELDS if merged.get(key)]
    (Path(folder) / INFO).write_text("\n".join(lines) + "\n")


def set_summary_state(folder: Path, state: str) -> None:
    write_info(folder, {"summary": state})


@dataclass(frozen=True)
class Entry:
    folder: Path
    title: str
    url: str
    video_id: str
    channel: str
    duration: str
    project: str
    day: str
    has_video: bool
    has_transcript: bool
    has_summary: bool
    summary_state: str


def read_entry(folder: Path) -> Entry | None:
    v = _info_values(folder)
    if not v:
        return None
    folder = Path(folder)
    return Entry(folder, v.get("title", folder.name), v.get("url", ""), v.get("id", ""), v.get("channel", ""),
                 v.get("duration", ""), v.get("project", folder.parent.name), folder.name[:10],
                 (folder / "video.mp4").exists() or (folder / "audio.mp3").exists(),
                 (folder / "transcript.txt").exists(), (folder / "summary.md").exists(), v.get("summary", ""))


def scan(library: Path) -> list[Entry]:
    out = []
    library = Path(library)
    if library.is_dir():
        for pdir in library.iterdir():
            if pdir.is_dir():
                out += [e for e in (read_entry(d) for d in pdir.iterdir() if d.is_dir()) if e]
    return sorted(out, key=lambda e: (e.day, e.title), reverse=True)


def _summary_line(folder: Path) -> str:
    try:
        lines = (Path(folder) / "summary.md").read_text().splitlines()
    except OSError:
        return ""
    return next((l.strip("-* ").strip() for l in lines if l.strip() and not l.lstrip().startswith("#")), "")


def write_index(project_folder: Path) -> Path:
    """INDEX.md: every video of a project, its link and the first line of its summary."""
    project_folder = Path(project_folder)
    entries = sorted((e for e in (read_entry(d) for d in project_folder.iterdir() if d.is_dir()) if e),
                     key=lambda e: e.day)
    lines = [f"# {project_folder.name}: videos", "",
             "One folder per video: transcript.txt, summary.md, info.md, thumbnail.jpg and the video when kept.", ""]
    for e in entries:
        lines.append(f"- **{e.day} [{e.title}]({e.folder.name}/)** · {e.channel or 'unknown channel'} · {e.url}")
        if (s := _summary_line(e.folder)):
            lines.append(f"  - {s}")
    out = project_folder / "INDEX.md"
    out.write_text("\n".join(lines) + "\n")
    return out
