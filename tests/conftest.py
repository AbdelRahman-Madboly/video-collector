import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def _private_paths(tmp_path, monkeypatch):
    """No test reads or writes the real settings or the shared folder."""
    monkeypatch.setenv("VIDEO_COLLECTOR_CONFIG", str(tmp_path / "config" / "settings.json"))
    monkeypatch.setenv("MYTOOLS_SHARED", str(tmp_path / "shared-data"))
