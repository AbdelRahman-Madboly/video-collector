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
    s = settings.Settings(library=tmp_path / "lib", summary_command="summarize-tool")
    asked = []
    runners = {"fetch": lambda url: meta(), "download": FakeYtDlp(), "summary": summary_ok,
               "launch": lambda argv: None, "confirm": lambda text, n: asked.append(n) or True,
               "pick_dir": lambda start: str(tmp_path / "elsewhere"), "version": lambda: "2026.10.21",
               "thumb": lambda url: b"", "expand": lambda url: [url], **over}
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
    w = _window(tmp_path, expand=lambda url: list(many.entries) if url == "https://y/list" else [url],
                confirm=lambda text, n: w.asked.append(n) or False)
    d = w.page("Download")
    d.playlist.setChecked(True)
    d.links.setPlainText("https://y/list")
    d.start()
    assert _wait(lambda: w.asked == [12]) and d.queue.count() == 0


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
    p.summary_command.setText("  my-summarizer --no-tools  ")
    p.save()
    s = settings.load()
    assert (s.library, s.summary_command) == (tmp_path / "mine", "my-summarizer --no-tools")


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


def test_playlists_expand_off_the_window_thread_and_errors_are_shown(tmp_path):
    def boom(url):
        raise RuntimeError("network down")
    w = _window(tmp_path, expand=boom)
    d = w.page("Download")
    d.playlist.setChecked(True)
    d.links.setPlainText("https://y/list")
    d.start()
    assert _wait(lambda: "network down" in d.status.text())
    assert d.queue.count() == 0


def test_a_checked_quality_is_not_reused_for_the_next_link(tmp_path):
    from creator_video_collector.downloader import QualityChoice
    checked = meta()
    checked = type(checked)(**{**checked.__dict__, "qualities": [QualityChoice("1080p mp4", "137+ba")]})
    w = _window(tmp_path, fetch=lambda url: checked)
    d = w.page("Download")
    d.links.setPlainText("https://y/1")
    d.check()
    assert _wait(lambda: d.quality.currentData() == "137+ba")
    d.start()
    assert _wait(lambda: d.queue_done())
    assert d.quality.currentData() is None


def test_the_one_off_folder_is_cleared_after_queueing(tmp_path):
    w = _window(tmp_path)
    d = w.page("Download")
    d.change_folder()
    d.links.setPlainText("https://y/1")
    d.start()
    assert d.target_library() == w.settings.library
    assert _wait(lambda: d.queue_done()) and (tmp_path / "elsewhere").is_dir()


def test_summary_is_not_ticked_when_summaries_are_off(tmp_path):
    w = _window(tmp_path)
    w.apply_settings(settings.Settings(library=tmp_path / "lib", summary_command=""))
    d = w.page("Download")
    d.apply_preset("research")
    assert not d.part_boxes["summary"].isChecked()


def test_closing_mid_download_asks_and_stops(tmp_path):
    from creator_video_collector import procs
    stopped = []
    w = _window(tmp_path, confirm=lambda text, n: True)
    w.page("Download")._running = True
    import pytest
    mp = pytest.MonkeyPatch()
    mp.setattr(procs, "stop_all", lambda: stopped.append(1))
    from PySide6.QtGui import QCloseEvent
    ev = QCloseEvent()
    w.closeEvent(ev)
    mp.undo()
    assert ev.isAccepted() and stopped == [1]


def test_a_quality_checked_for_one_link_is_not_used_for_another(tmp_path):
    from creator_video_collector.downloader import QualityChoice
    checked = type(meta())(**{**meta().__dict__, "qualities": [QualityChoice("1080p mp4", "137+ba")]})
    w = _window(tmp_path, fetch=lambda url: checked)
    d = w.page("Download")
    d.links.setPlainText("https://y/A")
    d.check()
    assert _wait(lambda: d.quality.currentData() == "137+ba")
    d.links.setPlainText("https://y/B")
    d.start()
    assert d._last_job_format is None
