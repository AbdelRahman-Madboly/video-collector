import subprocess

import pytest

from creator_video_collector import summarize


def test_prompt_names_the_project_and_asks_for_the_sections_in_english():
    p = summarize.build_prompt("we print at 0.2 mm", "Magnet fidget", "Workshop")
    for part in ("Workshop", "Magnet fidget", "TL;DR", "Key points", "Details for R&D", "Open questions",
                 "English", "we print at 0.2 mm"):
        assert part in p


def test_the_summary_command_is_split_like_a_shell_line():
    assert summarize.command('my-tool --flag "two words"') == ["my-tool", "--flag", "two words"]
    assert summarize.enabled("my-tool") and not summarize.enabled("   ")


def test_the_command_gets_the_prompt_on_stdin_in_an_empty_folder():
    seen = []
    def runner(cmd, **kw):
        from pathlib import Path
        seen.append((cmd, kw.get("input"), list(Path(kw["cwd"]).iterdir())))
        return subprocess.CompletedProcess(cmd, 0, "## TL;DR\nok\n", "")
    out = summarize.summarize("text", "T", "P", "my-tool --no-tools", runner=runner)
    assert out.startswith("## TL;DR")
    cmd, stdin, contents = seen[0]
    assert cmd == ["my-tool", "--no-tools"] and "text" in stdin and contents == []


def test_a_long_transcript_is_summarized_in_parts_then_together():
    calls = []
    runner = lambda cmd, **kw: calls.append(kw["input"]) or subprocess.CompletedProcess(cmd, 0, "part", "")
    summarize.summarize("word " * 50_000, "T", "P", "my-tool", runner=runner)
    assert len(calls) == 4 and "parts" in calls[-1].lower()


@pytest.mark.parametrize("fail", [
    FileNotFoundError("my-tool"), subprocess.TimeoutExpired("my-tool", 600)])
def test_failures_become_a_plain_summary_error(fail):
    def runner(cmd, **kw):
        raise fail
    with pytest.raises(summarize.SummaryError):
        summarize.summarize("t", "T", "P", "my-tool", runner=runner)


def test_a_failed_run_an_empty_command_and_a_bad_command_are_errors_too():
    bad = lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, "", "not logged in")
    with pytest.raises(summarize.SummaryError, match="not logged in"):
        summarize.summarize("t", "T", "P", "my-tool", runner=bad)
    with pytest.raises(summarize.SummaryError, match="off"):
        summarize.summarize("t", "T", "P", "")
    with pytest.raises(summarize.SummaryError, match="cannot be read"):
        summarize.summarize("t", "T", "P", 'my-tool "unclosed')
