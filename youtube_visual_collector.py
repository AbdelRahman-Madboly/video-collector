#!/usr/bin/env python3
"""Launcher kept for the old command name: starts Creator Video Collector."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from creator_video_collector.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
