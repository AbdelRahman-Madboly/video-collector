import subprocess

import pytest

from creator_video_collector import summarize


def test_prompt_names_the_project_and_asks_for_the_sections_in_english():
    p = summarize.build_prompt("we print at 0.2 mm", "Magnet fidget", "Workshop")
    for part in ("Workshop", "Magnet fidget", "TL;DR", "Key points", "Details for R&D", "Open questions",
                 "English", "we print at 0.2 mm"):
        assert part in p


def test_cli_a_runs_with_no_tools_and_the_prompt_on_stdin():
    seen = []
    def runner(cmd, **kw):
        seen.append((cmd, kw.get("input")))
        return subprocess.CompletedProcess(cmd, 0, "## TL;DR\nok\n", "")
    out = summarize.summarize("text", "T", "P", "cli-a", runner=runner)
    assert out.startswith("## TL;DR")
    cmd, stdin = seen[0]
    assert cmd[:2] == ["cli-a", "-p"] and "--disallowedTools" in cmd and "text" in stdin


def test_a_long_transcript_is_summarized_in_parts_then_together():
    calls = []
    runner = lambda cmd, **kw: calls.append(kw["input"]) or subprocess.CompletedProcess(cmd, 0, "part", "")
    summarize.summarize("word " * 50_000, "T", "P", "cli-b", runner=runner)
    assert len(calls) == 4 and "parts" in calls[-1].lower()


@pytest.mark.parametrize("fail", [
    FileNotFoundError("cli-a"), subprocess.TimeoutExpired("cli-a", 600)])
def test_failures_become_a_plain_summary_error(fail):
    def runner(cmd, **kw):
        raise fail
    with pytest.raises(summarize.SummaryError):
        summarize.summarize("t", "T", "P", "cli-a", runner=runner)


def test_a_failed_run_and_off_are_errors_too():
    bad = lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, "", "not logged in")
    with pytest.raises(summarize.SummaryError, match="not logged in"):
        summarize.summarize("t", "T", "P", "cli-a", runner=bad)
    with pytest.raises(summarize.SummaryError, match="off"):
        summarize.summarize("t", "T", "P", "off")
