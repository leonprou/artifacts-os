"""Tests for `artifacts list --tail [N]` (s0027 § C4, C5)."""

import json
from pathlib import Path

import pytest

from artifacts_os.cli import _run


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_tasks(root: Path, n: int) -> None:
    """Write *n* task artifacts numbered t0001…t{n}."""
    from artifacts_os.core import frontmatter as _fm

    tasks_dir = root / "artifacts" / "tasks"
    for i in range(1, n + 1):
        stem = f"t{i:04d}-task-{i}"
        fm = {
            "kind": "task",
            "id": f"t{i:04d}",
            "name": f"task-{i}",
            "status": "ready",
        }
        (tasks_dir / f"{stem}.md").write_text(_fm.dump(fm, ""))


# ---------------------------------------------------------------------------
# --tail tests
# ---------------------------------------------------------------------------


def test_list_tail_default_50(vault: Path, capsys):
    """`--tail` (no value) returns the last 50 of 80 tasks."""
    _write_tasks(vault, 80)

    code = _run(["list", "--tail", "-q"])
    assert code == 0
    out = capsys.readouterr().out.strip().splitlines()
    # 50 results (not 80)
    assert len(out) == 50
    # The 50th task (last of 80) is present; the 30th (first outside window) is not.
    assert any("t0080" in line for line in out)
    assert not any("t0030" in line for line in out)


def test_list_tail_explicit(vault: Path, capsys):
    """`--tail 10` returns the last 10 of 20 tasks."""
    _write_tasks(vault, 20)

    code = _run(["list", "--tail", "10", "-q"])
    assert code == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 10
    assert any("t0020" in line for line in out)
    assert not any("t0010" in line for line in out)


def test_list_tail_after_filter(vault: Path, write_artifact, capsys):
    """`--tail` slices the filtered set, not the full vault."""
    from artifacts_os.core import frontmatter as _fm

    tasks_dir = vault / "artifacts" / "tasks"
    # 10 ready + 10 done tasks
    for i in range(1, 11):
        stem = f"t{i:04d}-ready-{i}"
        fm = {"kind": "task", "id": f"t{i:04d}", "name": f"ready-{i}", "status": "ready"}
        (tasks_dir / f"{stem}.md").write_text(_fm.dump(fm, ""))
    for i in range(11, 21):
        stem = f"t{i:04d}-done-{i}"
        fm = {"kind": "task", "id": f"t{i:04d}", "name": f"done-{i}", "status": "done"}
        (tasks_dir / f"{stem}.md").write_text(_fm.dump(fm, ""))

    # Filter to ready only (10 items), then tail 5 → last 5 ready tasks.
    code = _run(["list", "--status", "ready", "--tail", "5", "-q"])
    assert code == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 5
    # done tasks must not appear
    assert not any("done" in line for line in out)


def test_list_no_tail_unchanged(vault: Path, capsys):
    """Without --tail, all artifacts are listed (no implicit cap)."""
    _write_tasks(vault, 15)

    code = _run(["list", "-q"])
    assert code == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 15


def test_list_tail_zero_yields_empty(vault: Path, capsys):
    """`--tail 0` returns an empty result set."""
    _write_tasks(vault, 5)

    code = _run(["list", "--tail", "0", "-q"])
    assert code == 0
    out = capsys.readouterr().out.strip()
    assert out == ""


def test_list_tail_json_mode(vault: Path, capsys):
    """`--tail N` works in --json mode."""
    _write_tasks(vault, 10)

    code = _run(["list", "--tail", "3", "-j"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 3
