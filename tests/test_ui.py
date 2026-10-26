import json
import subprocess
import time
from datetime import date
from pathlib import Path

from PySide6.QtWidgets import QApplication

from creator_video_collector import library, settings
from creator_video_collector.downloader import VideoMetadata
from creator_video_collector.ui.window import MainWindow
from tests.test_jobs import FakeYtDlp, meta, summary_ok


def _app():
    return QApplication.instance() or QApplication([])


def _wait(cond, seconds=10):
    end = time.time() + seconds
    while not cond() and time.time() < end:
        _app().processEvents()
        time.sleep(0.01)
    return cond()


def _window(tmp_path, **over):
    _app()
    s = settings.Settings(library=tmp_path / "lib")
    asked = []
    runners = {"fetch": lambda url: meta(), "download": FakeYtDlp(), "summary": summary_ok,
               "launch": lambda argv: None, "confirm": lambda text, n: asked.append(n) or True,
               "pick_dir": lambda start: str(tmp_path / "elsewhere"), "version": lambda: "2026.10.21",
               "thumb": lambda url: b"", **over}
    w = MainWindow(s, runners)
    w.asked = asked
    return w


def test_window_fits_a_small_screen(tmp_path):
    w = _window(tmp_path)
    w.resize(1280, 800)
    w.show()
    for page in ("Download", "Library", "Settings"):
        w.show_page(page)
        _app().processEvents()
        assert w.current_page().horizontalScrollBar().maximum() == 0


def test_two_links_are_queued_and_both_land_in_the_library(tmp_path):
    w = _window(tmp_path)
    d = w.page("Download")
    d.links.setPlainText("https://y/1\nhttps://y/2\n")
    d.project.setCurrentText("Workshop")
    d.start()
    assert _wait(lambda: d.queue_done())
    assert [d.queue.item(i).text().split(" · ")[-1] for i in range(d.queue.count())] == ["Done", "Done"]
    assert (tmp_path / "lib" / "Workshop").is_dir()


def test_a_big_playlist_asks_first(tmp_path):
    many = VideoMetadata(title="List", qualities=[], manual_subtitles=[], auto_subtitles=[], is_playlist=True,
                         playlist_count=12, entries=tuple(f"https://y/{i}" for i in range(12)))
    w = _window(tmp_path, fetch=lambda url: many if url == "https://y/list" else meta(),
                confirm=lambda text, n: w.asked.append(n) or False)
    d = w.page("Download")
    d.playlist.setChecked(True)
    d.links.setPlainText("https://y/list")
    d.start()
    assert w.asked == [12] and d.queue.count() == 0


def test_change_folder_is_used_for_this_batch_only(tmp_path):
    w = _window(tmp_path)
    d = w.page("Download")
    d.change_folder()
    assert d.target_library() == tmp_path / "elsewhere"
    assert settings.load().library != tmp_path / "elsewhere"


def test_settings_are_saved(tmp_path):
    w = _window(tmp_path)
    p = w.page("Settings")
    p.library.setText(str(tmp_path / "mine"))
    p.engine.setCurrentIndex(p.engine.findData("cli-b"))
    p.save()
    s = settings.load()
    assert (s.library, s.engine) == (tmp_path / "mine", "cli-b")


def test_library_lists_videos_and_makes_a_summary(tmp_path):
    folder = library.video_dir(tmp_path / "lib", "Workshop", "Coin slider", "id9", date(2026, 10, 27))
    (folder / "transcript.txt").write_text("we print at 0.2 mm")
    library.write_info(folder, {"title": "Coin slider", "id": "id9", "url": "https://y/id9", "project": "Workshop"})
    w = _window(tmp_path)
    lib = w.page("Library")
    lib.refresh_entries()
    assert lib.list.count() == 1
    lib.list.setCurrentRow(0)
    lib.make_summary()
    assert _wait(lambda: (folder / "summary.md").exists())
