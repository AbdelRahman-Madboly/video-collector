"""Every program the collector starts (yt-dlp and the summary tool) goes through here, so closing the window
can stop them instead of leaving them running with no window."""
from __future__ import annotations

import subprocess
import threading
from typing import Callable

_lock = threading.Lock()
_running: set[subprocess.Popen] = set()


def _track(p: subprocess.Popen) -> None:
    with _lock:
        _running.add(p)


def _untrack(p: subprocess.Popen) -> None:
    with _lock:
        _running.discard(p)


def running() -> int:
    with _lock:
        return len(_running)


def stop_all() -> None:
    with _lock:
        procs = list(_running)
    for p in procs:
        p.terminate()
    for p in procs:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()


def run(cmd: list[str], input: str | None = None, capture_output: bool = True, text: bool = True,
        timeout: float | None = None, cwd: str | None = None) -> subprocess.CompletedProcess:
    """subprocess.run, but stoppable by stop_all()."""
    pipe = subprocess.PIPE if capture_output else None
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE if input is not None else None, stdout=pipe, stderr=pipe,
                         text=text, cwd=cwd)
    _track(p)
    try:
        out, err = p.communicate(input=input, timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        p.communicate()
        raise
    finally:
        _untrack(p)
    return subprocess.CompletedProcess(cmd, p.returncode, out, err)


def stream(cmd: list[str], on_line: Callable[[str], None]) -> int:
    """Run cmd, handing each output line to on_line; returns the exit code."""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    _track(p)
    try:
        assert p.stdout is not None
        for line in p.stdout:
            on_line(line.rstrip())
        return p.wait()
    finally:
        _untrack(p)
