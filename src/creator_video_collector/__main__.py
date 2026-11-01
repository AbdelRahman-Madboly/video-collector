"""Entry point: uv run python -m creator_video_collector"""
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from . import settings
from .config import APP_NAME
from .ui.window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setDesktopFileName("youtube-visual-collector")
    app.setWindowIcon(QIcon.fromTheme("mytools-video-collector"))
    win = MainWindow(settings.load())
    win.resize(1320, 860)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
