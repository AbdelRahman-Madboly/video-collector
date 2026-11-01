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
    summary_command: str = ""        # reads a transcript on stdin, prints a summary; empty = off
    dark: bool = True
    summary_sandbox: bool = True     # run the summary command inside bwrap when it is installed
    summary_network: bool = False    # let the sandboxed summary command reach the network
    summary_env: list = field(default_factory=list)      # extra environment variable names to pass on
    summary_guards: dict = field(default_factory=dict)   # program name -> option groups it always gets
    summary_readonly: list = field(default_factory=list)  # extra paths the sandboxed command may read


def summary_options(s: Settings):
    from .summarize import Options
    return Options(command=s.summary_command, guards=dict(s.summary_guards), sandbox=bool(s.summary_sandbox),
                   network=bool(s.summary_network), env=tuple(str(x) for x in s.summary_env),
                   readonly=tuple(str(x) for x in s.summary_readonly))


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
    if not isinstance(values.get("summary_guards", {}), dict) or not all(
            isinstance(v, list) for v in values.get("summary_guards", {}).values()):
        values.pop("summary_guards")
    for key in ("summary_env", "summary_readonly"):
        if not isinstance(values.get(key, []), list):
            values.pop(key)
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
