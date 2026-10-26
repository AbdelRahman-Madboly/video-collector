import json
import subprocess
from datetime import date
from pathlib import Path

from creator_video_collector import jobs, library
from creator_video_collector.downloader import VideoMetadata

TODAY = date(2026, 10, 27)
VTT = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nwe print the coin at 0.2 mm\n\n00:00:03.000 --> 00:00:05.000\nthe magnet is 6 by 3\n"


def meta(subs=True):
    return VideoMetadata(title="Coin: slider 🎥", qualities=[], manual_subtitles=["en"] if subs else [],
                         auto_subtitles=[], uploader="Maker", duration="12:04", video_id="abc123",
                         url="https://www.youtube.com/watch?v=abc123", upload_date="2026-10-01")


class FakeYtDlp:
    """Creates the files yt-dlp would, from the output templates in the command."""
    def __init__(self, subs=True):
        self.subs, self.calls = subs, []

    def __call__(self, cmd, on_line):
        self.calls.append(cmd)
        outs = {}
        for i, a in enumerate(cmd):
            if a == "-o":
                kind, _, tmpl = cmd[i + 1].rpartition(":") if cmd[i + 1].split(":", 1)[0] in (
                    "thumbnail", "subtitle", "infojson") else ("", "", cmd[i + 1])
                outs[kind.split(":")[-1] if kind else "default"] = tmpl
        if "--skip-download" not in cmd:
            ext = "mp3" if "--extract-audio" in cmd else "mp4"
            Path(outs["default"].replace("%(ext)s", ext)).write_bytes(b"media")
        if "--write-thumbnail" in cmd:
            Path(outs["thumbnail"].replace("%(ext)s", "jpg")).write_bytes(b"jpg")
        if "--write-subs" in cmd and self.subs:
            p = Path(outs["subtitle"].replace("%(ext)s", "en.vtt"))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(VTT)
        if "--write-info-json" in cmd:
            p = Path(outs["infojson"] + ".info.json")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("{}")
        on_line("[download] 100%")
        return 0


def summary_ok(cmd, **kw):
    return subprocess.CompletedProcess(cmd, 0, "## TL;DR\nCoins print at 0.2 mm.\n", "")


def job(tmp_path, preset, engine="cli-a"):
    return jobs.Job(url="https://www.youtube.com/watch?v=abc123", project="Workshop", parts=set(jobs.PRESETS[preset]),
                    quality="720", format_selector=None, library=tmp_path / "lib", langs="en.*,ar.*", engine=engine)


def run(tmp_path, preset, dl=None, summary=summary_ok, subs=True, engine="cli-a"):
    dl = dl or FakeYtDlp(subs)
    entry = jobs.run(job(tmp_path, preset, engine), on_line=lambda l: None, fetch=lambda url: meta(subs),
                     download=dl, summary_runner=summary, today=TODAY)
    return entry, dl


def test_watch_preset_makes_a_tidy_folder(tmp_path):
    e, _ = run(tmp_path, "watch")
    files = sorted(p.name for p in e.folder.iterdir())
    assert files == ["info.md", "thumbnail.jpg", "transcript.txt", "video.mp4"]
    assert e.folder.parent.name == "Workshop" and e.folder.name.startswith("2026-10-27 Coin - slider")
    assert "0.2 mm" in (e.folder / "transcript.txt").read_text()
    assert (tmp_path / "lib" / "Workshop" / "INDEX.md").exists()


def test_research_preset_has_no_video_and_a_summary(tmp_path):
    e, dl = run(tmp_path, "research")
    assert not e.has_video and e.has_summary and "--skip-download" in dl.calls[0]
    assert library.read_entry(e.folder).summary_state.startswith("done")
    assert "Coins print at 0.2 mm." in (tmp_path / "lib" / "Workshop" / "INDEX.md").read_text()


def test_everything_keeps_raw_subtitles_and_info_json(tmp_path):
    e, _ = run(tmp_path, "everything")
    assert (e.folder / "raw" / "sub.en.vtt").exists() and (e.folder / "raw" / "info.info.json").exists()
    assert e.has_video and e.has_summary


def test_a_second_run_only_adds_what_is_missing_and_keeps_an_edited_summary(tmp_path):
    e, _ = run(tmp_path, "everything")
    (e.folder / "summary.md").write_text("my notes")
    (e.folder / "thumbnail.jpg").unlink()
    again, dl = run(tmp_path, "everything")
    assert again.folder == e.folder
    assert "--skip-download" in dl.calls[0] and "--write-thumbnail" in dl.calls[0]
    assert (e.folder / "summary.md").read_text() == "my notes"


def test_no_subtitles_keeps_the_video_and_skips_the_summary(tmp_path):
    called = []
    e, _ = run(tmp_path, "everything", subs=False, summary=lambda c, **k: called.append(c))
    assert e.has_video and not e.has_transcript and not called
    text = (e.folder / "info.md").read_text()
    assert "**Transcript:** none" in text


def test_a_failed_summary_keeps_the_files_and_says_why(tmp_path):
    def gone(cmd, **kw):
        raise FileNotFoundError("cli-a")
    e, _ = run(tmp_path, "research", summary=gone)
    assert e.has_transcript and not e.has_summary
    assert library.read_entry(e.folder).summary_state == "failed, cli-a is not installed"


def test_a_failed_download_raises_but_keeps_what_arrived(tmp_path):
    def broken(cmd, on_line):
        on_line("ERROR: video unavailable")
        return 1
    import pytest
    with pytest.raises(jobs.JobError, match="video unavailable"):
        run(tmp_path, "watch", dl=broken)


def test_the_hub_summary_counts_the_videos(tmp_path):
    run(tmp_path, "watch")
    d = json.loads((tmp_path / "shared-data" / "video-collector.json").read_text())
    assert d["data"]["videos"] == 1 and "Coin" in d["headline"]
