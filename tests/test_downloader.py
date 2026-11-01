import subprocess

import pytest

from creator_video_collector import downloader


def test_qualities_are_listed_best_first_and_video_only_formats_get_audio():
    m = downloader.parse_metadata({"id": "x", "title": "T", "upload_date": "20261001", "formats": [
        {"format_id": "18", "vcodec": "avc1", "acodec": "mp4a", "height": 360, "ext": "mp4"},
        {"format_id": "137", "vcodec": "avc1", "acodec": "none", "height": 1080, "ext": "mp4"},
        {"format_id": "140", "vcodec": "none", "acodec": "mp4a", "ext": "m4a"},
    ], "subtitles": {"en": []}, "automatic_captions": {"ar": [], "en": []}})
    assert [q.label.split()[0] for q in m.qualities] == ["1080p", "360p"]
    assert m.qualities[0].selector == "137+ba[ext=m4a]/137+ba" and m.qualities[1].selector == "18"
    assert (m.manual_subtitles, m.auto_subtitles, m.upload_date) == (["en"], ["ar", "en"], "2026-10-01")


def test_a_height_limit_never_falls_back_to_audio_only():
    fmt = downloader.resolution_to_format("720")
    assert "height<=720" in fmt and all("vcodec!=none" in p or "vcodec^=avc1" in p for p in fmt.split("/"))


def test_a_failed_check_raises_the_yt_dlp_error():
    runner = lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, "", "ERROR: private video\n")
    with pytest.raises(RuntimeError, match="private video"):
        downloader.fetch_metadata("https://y/1", False, runner=runner)


def test_a_check_never_sends_a_non_web_link():
    with pytest.raises(ValueError):
        downloader.fetch_metadata("/etc/passwd", False, runner=lambda *a, **k: None)
