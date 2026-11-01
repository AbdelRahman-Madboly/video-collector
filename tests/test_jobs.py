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


def job(tmp_path, preset, summary_command="summarize-tool"):
    return jobs.Job(url="https://www.youtube.com/watch?v=abc123", project="Workshop", parts=set(jobs.PRESETS[preset]),
                    quality="720", format_selector=None, library=tmp_path / "lib", langs="en.*,ar.*", summary_command=summary_command)


def run(tmp_path, preset, dl=None, summary=summary_ok, subs=True, summary_command="summarize-tool"):
    dl = dl or FakeYtDlp(subs)
    entry = jobs.run(job(tmp_path, preset, summary_command), on_line=lambda l: None, fetch=lambda url: meta(subs),
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
    assert library.read_entry(e.folder).summary_state == "done (summarize-tool)"
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
        raise FileNotFoundError("summarize-tool")
    e, _ = run(tmp_path, "research", summary=gone)
    assert e.has_transcript and not e.has_summary
    assert library.read_entry(e.folder).summary_state == "failed, summarize-tool is not installed"


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


def test_a_link_can_never_become_a_yt_dlp_option(tmp_path):
    import pytest
    from creator_video_collector import downloader
    with pytest.raises(ValueError):
        downloader.build_job_command("--exec=rm -rf ~", tmp_path, {"video"}, format_selector=None,
                                     fallback_resolution="720", subtitle_languages="en.*")
    cmd = downloader.build_job_command("https://y/1", tmp_path, {"video"}, format_selector=None,
                                       fallback_resolution="720", subtitle_languages="en.*")
    assert cmd[-2:] == ["--", "https://y/1"]
    bad = VideoMetadata(title="L", qualities=[], manual_subtitles=[], auto_subtitles=[], is_playlist=True,
                        entries=("https://y/ok", "--exec=touch x", "file:///etc/passwd"))
    assert jobs.expand("https://y/list", True, lambda u: bad) == ["https://y/ok"]


def test_a_failed_subtitle_does_not_fail_the_video_and_a_stray_subtitle_is_still_used(tmp_path):
    def partly(cmd, on_line):
        out = cmd[cmd.index("-o") + 1]
        Path(out.replace("%(ext)s", "mp4")).write_bytes(b"media")
        Path(out.replace("%(ext)s", "en.vtt")).write_text(VTT)      # yt-dlp stopped before moving it into raw/
        on_line("ERROR: Unable to download video subtitles for 'en-de': HTTP Error 429: Too Many Requests")
        return 1
    e, _ = run(tmp_path, "watch", dl=partly)
    assert e.has_video and e.has_transcript and "0.2 mm" in (e.folder / "transcript.txt").read_text()
    assert not list(e.folder.glob("video.*.vtt"))


def test_subtitle_requests_are_spaced_out(tmp_path):
    from creator_video_collector import downloader
    cmd = downloader.build_job_command("https://y/1", tmp_path, {"subs"}, format_selector=None,
                                       fallback_resolution="720", subtitle_languages="en")
    assert "--sleep-subtitles" in cmd


def test_summary_brings_its_transcript_along(tmp_path):
    j = job(tmp_path, "research")
    j.parts = {"summary"}
    e = jobs.run(j, on_line=lambda l: None, fetch=lambda url: meta(), download=FakeYtDlp(), summary_runner=summary_ok,
                 today=TODAY)
    assert e.has_transcript and e.has_summary


def test_a_one_off_folder_does_not_take_over_the_hub_count(tmp_path):
    j = job(tmp_path, "watch")
    j.library = tmp_path / "elsewhere"
    jobs.run(j, on_line=lambda l: None, fetch=lambda url: meta(), download=FakeYtDlp(), summary_runner=summary_ok,
             today=TODAY, publish_library=tmp_path / "lib")
    d = json.loads((tmp_path / "shared-data" / "video-collector.json").read_text())
    assert d["data"]["library"] == str(tmp_path / "lib") and d["data"]["videos"] == 0


def test_metadata_keeps_the_thumbnail_link():
    from creator_video_collector import downloader
    m = downloader.parse_metadata({"id": "x", "title": "T", "thumbnail": "https://i.ytimg.com/vi/x/hq.jpg"})
    assert m.thumbnail == "https://i.ytimg.com/vi/x/hq.jpg"


def test_playlists_are_read_flat():
    from creator_video_collector import downloader
    seen = []
    def runner(cmd, **kw):
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, json.dumps({"entries": [{"url": "https://y/1"}, {"url": "https://y/2"}],
                                                                "title": "L"}), "")
    m = downloader.fetch_metadata("https://y/list", True, runner=runner)
    assert "--flat-playlist" in seen[0] and "--yes-playlist" in seen[0] and m.entries == ("https://y/1", "https://y/2")


def test_stop_all_ends_running_processes():
    from creator_video_collector import procs
    import threading
    out = {}
    t = threading.Thread(target=lambda: out.setdefault("r", procs.run(["sleep", "30"], capture_output=True, text=True, timeout=60)))
    t.start()
    import time
    for _ in range(100):
        if procs.running():
            break
        time.sleep(0.02)
    procs.stop_all()
    t.join(5)
    assert not t.is_alive() and out["r"].returncode != 0


def test_only_web_thumbnails_are_kept():
    from creator_video_collector import downloader
    assert downloader.parse_metadata({"id": "x", "title": "T", "thumbnail": "file:///etc/passwd"}).thumbnail == ""


def test_a_failed_download_still_leaves_a_readable_folder(tmp_path):
    def broken(cmd, on_line):
        on_line("ERROR: video unavailable")
        return 1
    import pytest
    with pytest.raises(jobs.JobError):
        run(tmp_path, "watch", dl=broken)
    folders = [d for d in (tmp_path / "lib" / "Workshop").iterdir() if d.is_dir()]
    entry = library.read_entry(folders[0])
    assert entry is not None and entry.video_id == "abc123" and not entry.has_video


def test_an_empty_subtitle_gives_no_transcript_and_no_summary(tmp_path):
    class Silent(FakeYtDlp):
        def __call__(self, cmd, on_line):
            code = super().__call__(cmd, on_line)
            for f in tmp_path.rglob("*.vtt"):
                f.write_text("WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n[Music]\n")
            return code
    called = []
    e, _ = run(tmp_path, "research", dl=Silent(), summary=lambda c, **k: called.append(c))
    assert not e.has_transcript and not called
    text = (e.folder / "info.md").read_text()
    assert "**Transcript:** none" in text and "**Summary:** none, no transcript" in text


def test_a_summary_is_not_asked_for_an_empty_transcript(tmp_path):
    e, _ = run(tmp_path, "watch")
    (e.folder / "transcript.txt").write_text("   \n")
    called = []
    assert jobs.make_summary(e.folder, "summarize-tool", runner=lambda c, **k: called.append(c)) is False
    assert not called
