from creator_video_collector import subtitles

VTT = """WEBVTT
Kind: captions
Language: en

NOTE this block is skipped
and so is this line

00:00:01.000 --> 00:00:03.000
<c.colorE5E5E5>we print the coin</c> <00:00:02.100><c>at 0.2 mm</c>

00:00:03.000 --> 00:00:05.000
we print the coin at 0.2 mm then

00:00:05.000 --> 00:00:07.000
[Music] the magnet is 6 by 3 &amp; strong.
"""

SRT = """1
00:00:01,000 --> 00:00:02,000
i think it works.

2
00:00:02,000 --> 00:00:03,000
i think it works.
"""


def test_caption_markup_and_sound_tags_are_removed():
    assert subtitles.clean_caption_text("<c>hi</c> <00:00:01.000>there [Applause] ♪♪ &amp; you") == "hi there & you"


def test_a_vtt_file_is_read_without_headers_notes_or_timings(tmp_path):
    f = tmp_path / "sub.en.vtt"
    f.write_text(VTT)
    caps = subtitles.parse_subtitle_file(f)
    assert caps[0] == "we print the coin at 0.2 mm"
    assert all("-->" not in c and "NOTE" not in c and "WEBVTT" not in c for c in caps)


def test_rolling_captions_are_joined_without_repeats(tmp_path):
    f = tmp_path / "sub.en.vtt"
    f.write_text(VTT)
    out = subtitles.clean_subtitle_file_to_txt(f, tmp_path / "transcript.txt")
    text = out.read_text()
    assert text.count("we print the coin") == 1
    assert text.strip() == "we print the coin at 0.2 mm then the magnet is 6 by 3 & strong."


def test_srt_numbers_are_dropped_and_repeated_lines_kept_once(tmp_path):
    f = tmp_path / "sub.srt"
    f.write_text(SRT)
    assert subtitles.dedupe_captions(subtitles.parse_subtitle_file(f)) == "I think it works.\n"


def test_long_text_is_split_into_paragraphs():
    text = " ".join(f"Sentence number {n} is here." for n in range(12))
    assert subtitles.make_readable_paragraphs(text).count("\n\n") == 2


def test_subtitle_files_are_found_newest_first(tmp_path):
    import os
    old, new = tmp_path / "a.vtt", tmp_path / "raw" / "b.srt"
    new.parent.mkdir()
    old.write_text("x")
    new.write_text("y")
    os.utime(old, (1, 1))
    (tmp_path / "c.txt").write_text("z")
    assert subtitles.find_subtitle_files(tmp_path) == [new, old]
