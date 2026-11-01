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


def test_summary_safety_settings_default_to_sandboxed_and_offline_and_bad_values_are_dropped():
    s = settings.Settings()
    assert (s.summary_command, s.summary_sandbox, s.summary_network, s.summary_env, s.summary_guards) == (
        "", True, False, [], {})
    settings.config_path().parent.mkdir(parents=True, exist_ok=True)
    settings.config_path().write_text('{"summary_guards": ["nope"], "summary_env": "X", "summary_command": "t"}')
    loaded = settings.load()
    assert (loaded.summary_guards, loaded.summary_env, loaded.summary_command) == ({}, [], "t")
    o = settings.summary_options(settings.Settings(summary_command="t", summary_guards={"t": ["--safe"]}))
    assert (o.command, o.guards, o.sandbox, o.network) == ("t", {"t": ["--safe"]}, True, False)
