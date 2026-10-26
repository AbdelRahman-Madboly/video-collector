"""What the owner chose once and should not have to choose again."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path


def default_library() -> Path:
    return Path.home() / "Videos" / "Video Collector"


@dataclass
class Settings:
    library: Path = field(default_factory=default_library)
    default_project: str = ""
    preset: str = "watch"            # watch | research | everything | audio
    quality: str = "720"             # 360 | 480 | 720 | 1080 | Best
    subtitle_langs: str = "en,en-orig,en-US,en-GB,ar,ar-orig"  # exact codes: "en.*" also pulls every machine translation
    engine: str = "cli-a"           # cli-a | cli-b | off
    dark: bool = True


def config_path() -> Path:
    env = os.environ.get("VIDEO_COLLECTOR_CONFIG")
    return Path(env) if env else Path.home() / ".config" / "video-collector" / "settings.json"


def load() -> Settings:
    try:
        raw = json.loads(config_path().read_text())
    except (OSError, ValueError):
        return Settings()
    known = {f.name for f in fields(Settings)}
    values = {k: v for k, v in raw.items() if k in known}
    if "library" in values:
        values["library"] = Path(values["library"]).expanduser()
    try:
        return Settings(**values)
    except TypeError:
        return Settings()


def save(s: Settings) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(s)
    data["library"] = str(s.library)
    path.write_text(json.dumps(data, indent=2))
