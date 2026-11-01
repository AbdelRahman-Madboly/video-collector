from __future__ import annotations

from pathlib import Path

APP_NAME = "Creator Video Collector"
APP_DIR = Path(__file__).resolve().parents[2]
ASSETS_DIR = APP_DIR / "assets"
RESOLUTION_OPTIONS = ["360", "480", "720", "1080", "Best"]
DEFAULT_SUBTITLE_LANGS = "en,en-orig,en-US,en-GB,ar,ar-orig"
