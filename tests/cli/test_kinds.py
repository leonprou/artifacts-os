"""Tests for cli kinds command."""

import json
from pathlib import Path

import pytest

from artifacts_os.cli import main


def test_kinds_quiet_default_four(vault, capsys):
    """Fresh vault lists all four registered kinds sorted."""
    main(["kinds", "-q"])
    out = capsys.readouterr().out
    names = out.strip().splitlines()
    assert names == sorted(names), "names should be sorted"
    assert names == ["agent", "research", "spec", "task"]


def test_kinds_json_output(vault, capsys):
    """JSON output produces list of dicts with exactly the required keys."""
    main(["kinds", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) == 4
    expected_keys = {"name", "dir", "prefix", "numbered", "statuses"}
    for obj in data:
        assert set(obj.keys()) == expected_keys, f"unexpected keys in {obj}"
    # Spot-check values for task kind
    task = next(o for o in data if o["name"] == "task")
    assert task["dir"] == "tasks"
    assert task["prefix"] == "t"
    assert task["numbered"] is True
    assert "backlog" in task["statuses"]


def test_kinds_custom_vault_kind_appears(vault, capsys):
    """A kind defined only in artifacts/kinds/ shows up in output."""
    kinds_dir = vault / "artifacts" / "kinds"
    schema = {"x-dir": "changelogs", "x-prefix": "c", "x-numbered": True}
    (kinds_dir / "changelog.json").write_text(json.dumps(schema))

    main(["kinds", "-q"])
    out = capsys.readouterr().out
    assert "changelog" in out.strip().splitlines()


def test_kinds_vault_overrides_caller_kind(vault, monkeypatch, capsys):
    """A vault-defined kind wins over a caller-registered kind of the same name."""
    from artifacts_os.core.models import KindDef
    import artifacts_os.cli as cli_module

    # Register a caller-provided "task" kind with a different dir
    caller_task = KindDef(name="task", dir="caller-tasks", prefix="x", numbered=False)
    monkeypatch.setattr(cli_module, "_registered_kinds", [caller_task])

    main(["kinds", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    task = next(o for o in data if o["name"] == "task")
    # Vault definition (dir="tasks") should win over caller (dir="caller-tasks")
    assert task["dir"] == "tasks"


def test_kinds_mutually_exclusive_flags(vault):
    """-q and -j together produce a non-zero exit."""
    with pytest.raises(SystemExit) as exc:
        main(["kinds", "-q", "-j"])
    assert exc.value.code != 0
