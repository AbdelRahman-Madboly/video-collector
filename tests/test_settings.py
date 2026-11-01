from pathlib import Path

from creator_video_collector import settings


def test_defaults_when_nothing_is_saved():
    s = settings.load()
    assert s.library == Path.home() / "Videos" / "Video Collector"
    assert (s.preset, s.quality, s.subtitle_langs, s.summary_command, s.default_project) == ("watch", "720", "en,en-orig,en-US,en-GB,ar,ar-orig", "", "")


def test_save_and_load_round_trip(tmp_path):
    s = settings.Settings(library=tmp_path / "lib", default_project="Workshop", preset="research", quality="1080",
                          subtitle_langs="ar.*", summary_command="my-summarizer --quiet", dark=False)
    settings.save(s)
    assert settings.load() == s


def test_a_corrupt_file_gives_defaults():
    settings.config_path().parent.mkdir(parents=True, exist_ok=True)
    settings.config_path().write_text("{nope")
    assert settings.load().summary_command == ""
