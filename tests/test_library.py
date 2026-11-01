from datetime import date

from creator_video_collector import library


def test_a_messy_title_becomes_a_safe_short_folder_name():
    name = library.safe_title("A/B: c? 🎥 " + "x" * 200)
    assert "/" not in name and ":" not in name and "?" not in name
    assert 0 < len(name) <= 80


def test_project_names():
    assert library.project_name("") == "Unsorted"
    assert library.project_name("  Workshop / fidgets ") == "Workshop - fidgets"


def test_project_matches_an_existing_folder_ignoring_case(tmp_path):
    (tmp_path / "Workshop").mkdir()
    assert library.project_dir(tmp_path, "workshop") == tmp_path / "Workshop"
    assert library.project_dir(tmp_path, "New one") == tmp_path / "New one"


def test_the_same_video_reuses_its_folder_in_a_project(tmp_path):
    first = library.video_dir(tmp_path, "Workshop", "Magnet fidget", "abc123", date(2026, 10, 27))
    assert first.name == "2026-10-27 Magnet fidget"
    library.write_info(first, {"title": "Magnet fidget", "id": "abc123", "url": "https://y/abc123", "project": "Workshop"})
    again = library.video_dir(tmp_path, "workshop", "Magnet fidget (new title)", "abc123", date(2026, 11, 2))
    assert again == first
    other = library.video_dir(tmp_path, "Studio", "Magnet fidget", "abc123", date(2026, 11, 2))
    assert other.parent.name == "Studio"


def test_info_round_trips_and_scan_finds_it(tmp_path):
    folder = library.video_dir(tmp_path, "Workshop", "Coin slider", "id9", date(2026, 10, 27))
    (folder / "video.mp4").write_bytes(b"v")
    (folder / "transcript.txt").write_text("words")
    library.write_info(folder, {"title": "Coin slider", "id": "id9", "url": "https://y/id9", "channel": "Maker",
                                "duration": "12:04", "project": "Workshop", "transcript": "en"})
    [e] = library.scan(tmp_path)
    assert (e.title, e.video_id, e.channel, e.project) == ("Coin slider", "id9", "Maker", "Workshop")
    assert e.has_video and e.has_transcript and not e.has_summary
    library.set_summary_state(folder, "failed, timed out")
    assert library.read_entry(folder).summary_state == "failed, timed out"


def test_index_lists_every_video_with_its_link_and_summary_line(tmp_path):
    a = library.video_dir(tmp_path, "Workshop", "One", "1", date(2026, 10, 27))
    library.write_info(a, {"title": "One", "id": "1", "url": "https://y/1", "project": "Workshop"})
    (a / "summary.md").write_text("# Summary\n\n## TL;DR\nMagnets snap at 3 mm.\n")
    b = library.video_dir(tmp_path, "Workshop", "Two", "2", date(2026, 10, 28))
    library.write_info(b, {"title": "Two", "id": "2", "url": "https://y/2", "project": "Workshop"})
    text = library.write_index(tmp_path / "Workshop").read_text()
    assert "https://y/1" in text and "https://y/2" in text and "Magnets snap at 3 mm." in text


def test_a_title_with_line_breaks_cannot_forge_info_lines(tmp_path):
    folder = library.video_dir(tmp_path, "Workshop", "x", "real_id", date(2026, 10, 27))
    library.write_info(folder, {"title": "Nice\u2028- **ID:** stolen0", "id": "real_id", "duration": "1:00\u2028- **ID:** stolen", "channel": "c\n- **ID:** stolen2", "project": "Workshop"})
    e = library.read_entry(folder)
    assert e.video_id == "real_id" and "\n" not in e.title
