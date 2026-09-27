from __future__ import annotations

from pathlib import Path

APP_NAME = "Creator Video Collector"
APP_TAGLINE = "Video, subtitle, and transcript collector for creators"
APP_STATUS_TEXT = "Preparing creator workspace"
SPLASH_DURATION_MS = 2400
DEFAULT_DOWNLOAD_PATH = Path.home() / "Downloads" / "Creator Video Collector"
APP_DIR = Path(__file__).resolve().parents[2]
ASSETS_DIR = APP_DIR / "assets"
APP_ICON = ASSETS_DIR / "creator-video-collector.svg"

RESOLUTION_OPTIONS = ["360", "480", "720", "1080", "Best"]
MODE_OPTIONS = [
    "Video + TXT + Cover",
    "Video only",
    "TXT subtitles only",
    "Audio only MP3",
    "Everything",
]
DEFAULT_SUBTITLE_LANGS = "en.*,ar.*"

LIGHT_PALETTE = {
    "window": "#f0f2f5",
    "surface": "#ffffff",
    "surface_alt": "#f0f2f5",
    "text": "#1a1d23",
    "muted": "#6b7280",
    "accent": "#2563eb",
    "success": "#16a34a",
    "error": "#dc2626",
    "warning": "#d97706",
    "border": "#d9dde5",
    "log_bg": "#f6f8fa",
    "log_fg": "#57606a",
    "log_dim": "#d0d7de",
}

DARK_PALETTE = {
    "window": "#131620",
    "surface": "#1c2232",
    "surface_alt": "#1e2a3a",
    "text": "#e2e8f0",
    "muted": "#94a3b8",
    "accent": "#3b82f6",
    "success": "#22c55e",
    "error": "#ef4444",
    "warning": "#f59e0b",
    "border": "#303846",
    "log_bg": "#0d1117",
    "log_fg": "#8b949e",
    "log_dim": "#30363d",
}
