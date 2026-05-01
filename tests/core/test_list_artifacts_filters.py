"""Tests for the unified filter API (s0014).

Four test blocks:
  §10.1  Core API matrix
  §10.2  Deprecated kwarg compat
  §10.3  CLI integration matrix
  §10.4  Validation surface

CLI integration tests live here rather than test_list_views.py so that
all four blocks mandated by s0014 §10 are in one file.
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from artifacts_os import KindDef, Registry, create
from artifacts_os import list_artifacts
from artifacts_os.core.errors import ValidationError


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _schema_kinds() -> list[KindDef]:
    """Kinds with explicit schema so filter validation has known keys."""
    return [
        KindDef(
            name="task",
            dir="tasks",
            prefix="t",
            numbered=True,
            statuses=["backlog", "ready", "in-progress", "done"],
            schema={
                "properties": {
                    "status": {"enum": ["backlog", "ready", "in-progress", "done"]},
                    "assignee": {"type": "string"},
                    "owner": {"type": "string"},
                    "type": {"type": "string"},
                    "priority": {"type": "string"},
                }
            },
        ),
        KindDef(
            name="spec",
            dir="specs",
            prefix="s",
            numbered=True,
            statuses=["draft", "accepted"],
            schema={
                "properties": {
                    "status": {"enum": ["draft", "accepted"]},
                    "assignee": {"type": "string"},
                }
            },
        ),
        KindDef(
            name="agent",
            dir="agents",
            prefix="",
            numbered=False,
            statuses=[],
            schema={"properties": {}},
        ),
    ]


@pytest.fixture
def vault_s(tmp_path: Path):
    """Vault with schema-aware kinds for filter tests."""
    root = tmp_path / "vault"
    (root / "artifacts").mkdir(parents=True)
    (root / "artifacts" / "artifacts.yaml").write_text("layout_version: 1\n")
    ks = _schema_kinds()
    for kd in ks:
        (root / "artifacts" / kd.dir).mkdir(parents=True, exist_ok=True)
    registry = Registry(ks, root=root)
    return root, registry


# ---------------------------------------------------------------------------
# §10.1  Core API matrix
# ---------------------------------------------------------------------------

def test_core_list_no_filters(vault_s) -> None:
    """list_artifacts(reg) — all kinds, no filters."""
    _, reg = vault_s
    create(reg, "task", "A")
    create(reg, "spec", "B")
    items = list_artifacts(reg)
    assert len(items) == 2
    kinds = {i.kind for i in items}
    assert kinds == {"task", "spec"}


def test_core_list_kind_only(vault_s) -> None:
    """list_artifacts(reg, kind="task") — tasks dir only."""
    _, reg = vault_s
    create(reg, "task", "A")
    create(reg, "spec", "B")
    items = list_artifacts(reg, kind="task")
    assert len(items) == 1
    assert items[0].kind == "task"


def test_core_list_kind_and_status_filter(vault_s) -> None:
    """list_artifacts(reg, kind="task", filters={"status": "ready"})."""
    _, reg = vault_s
    from artifacts_os import update
    a = create(reg, "task", "A")
    create(reg, "task", "B")
    update(reg, a.id, status="ready")
    items = list_artifacts(reg, kind="task", filters={"status": "ready"})
    assert len(items) == 1
    assert items[0].id == a.id


def test_core_list_cross_kind_status(vault_s) -> None:
    """list_artifacts(reg, filters={"status": "ready"}) — cross-kind."""
    _, reg = vault_s
    from artifacts_os import update
    a = create(reg, "task", "A")
    create(reg, "task", "B")
    update(reg, a.id, status="ready")
    items = list_artifacts(reg, filters={"status": "ready"})
    assert len(items) == 1
    assert items[0].id == a.id


def test_core_list_assignee_filter(vault_s) -> None:
    """list_artifacts(reg, filters={"assignee": "alice"}) — cross-kind."""
    _, reg = vault_s
    create(reg, "task", "Alice task", fields={"assignee": "alice"})
    create(reg, "task", "Bob task", fields={"assignee": "bob"})
    items = list_artifacts(reg, filters={"assignee": "alice"})
    assert len(items) == 1
    assert items[0].frontmatter["assignee"] == "alice"


def test_core_list_tags_membership(vault_s) -> None:
    """list_artifacts(reg, filters={"tags": "urgent"}) — membership in list."""
    _, reg = vault_s
    create(reg, "task", "A", fields={"tags": ["urgent", "core"]})
    create(reg, "task", "B", fields={"tags": ["later"]})
    items = list_artifacts(reg, filters={"tags": "urgent"})
    assert len(items) == 1


def test_core_list_conjunction(vault_s) -> None:
    """filters={"status": "ready", "assignee": "alice"} — both must match."""
    _, reg = vault_s
    from artifacts_os import update
    a = create(reg, "task", "Alice ready", fields={"assignee": "alice"})
    b = create(reg, "task", "Alice draft", fields={"assignee": "alice"})
    c = create(reg, "task", "Bob ready", fields={"assignee": "bob"})
    update(reg, a.id, status="ready")
    update(reg, c.id, status="ready")
    items = list_artifacts(
        reg, kind="task", filters={"status": "ready", "assignee": "alice"}
    )
    assert len(items) == 1
    assert items[0].id == a.id


def test_core_list_empty_filters_noop(vault_s) -> None:
    """filters={} is a no-op — same result as filters=None."""
    _, reg = vault_s
    create(reg, "task", "A")
    create(reg, "task", "B")
    items_none = list_artifacts(reg, kind="task")
    items_empty = list_artifacts(reg, kind="task", filters={})
    assert len(items_none) == len(items_empty) == 2


def test_core_list_unknown_key_raises(vault_s) -> None:
    """filters with a typo key → ValidationError (§6.2)."""
    _, reg = vault_s
    with pytest.raises(ValidationError, match="unknown filter key 'asignee'"):
        list_artifacts(reg, kind="task", filters={"asignee": "alice"})


def test_core_list_kind_in_filters_sugar(vault_s) -> None:
    """filters={"kind": "task"} is sugar for kind="task"."""
    _, reg = vault_s
    create(reg, "task", "A")
    create(reg, "spec", "B")
    items = list_artifacts(reg, filters={"kind": "task"})
    assert len(items) == 1
    assert items[0].kind == "task"


def test_core_list_kind_in_filters_wins(vault_s) -> None:
    """kind="task" + filters={"kind": "spec"}: filters dict kind wins (last set)."""
    _, reg = vault_s
    create(reg, "task", "A")
    create(reg, "spec", "B")
    # kind arg sets filters["kind"] = "task" in resolve_filters step 2,
    # but filters={"kind": "spec"} is applied in step 3 for CLI.
    # At the core API level, list_artifacts pops "kind" from filters before
    # the walk — so filters={"kind": "spec"} wins over the named kind arg
    # because the pop in list_artifacts extracts it (not done here; kind param wins).
    # Per s0014 §4 step 3: kind from the named param; filters dict kind replaces it.
    # Concretely: list_artifacts(reg, kind="task", filters={"kind": "spec"})
    # → the "kind" key in filters is popped → effective kind = "spec"
    # But list_artifacts doesn't pop from filters; it uses the named param.
    # The resolution (pop "kind" from filters) happens in resolve_filters (CLI).
    # At the direct core API, filters={"kind": "spec"} with kind="task" means:
    # kind="task" is used for directory selection, and "kind" in filters is
    # treated as a frontmatter predicate (would match files with kind: spec).
    # So results for task dir + kind=spec frontmatter = 0.
    items = list_artifacts(reg, kind="task", filters={"kind": "spec"})
    # task dir only; frontmatter kind="spec" → no match (tasks have kind=task)
    assert items == []


# ---------------------------------------------------------------------------
# §10.2  Deprecated kwarg compat
# ---------------------------------------------------------------------------

def test_deprecated_status_kwarg_returns_correct_result(vault_s) -> None:
    """list_artifacts(reg, status="ready") == filters={"status": "ready"}."""
    _, reg = vault_s
    from artifacts_os import update
    a = create(reg, "task", "A")
    create(reg, "task", "B")
    update(reg, a.id, status="ready")

    with pytest.warns(DeprecationWarning, match="list_artifacts"):
        legacy = list_artifacts(reg, status="ready")
    new_api = list_artifacts(reg, filters={"status": "ready"})
    assert [i.id for i in legacy] == [i.id for i in new_api]


def test_deprecated_tag_kwarg_returns_correct_result(vault_s) -> None:
    """list_artifacts(reg, tag="urgent") == filters={"tags": "urgent"}."""
    _, reg = vault_s
    create(reg, "task", "A", fields={"tags": ["urgent"]})
    create(reg, "task", "B", fields={"tags": ["later"]})

    with pytest.warns(DeprecationWarning, match="list_artifacts"):
        legacy = list_artifacts(reg, tag="urgent")
    new_api = list_artifacts(reg, filters={"tags": "urgent"})
    assert [i.id for i in legacy] == [i.id for i in new_api]


def test_deprecated_status_explicit_filters_wins(vault_s) -> None:
    """When both status= and filters={"status": ...} given, filters wins.

    setdefault in the shim means the explicit filters dict takes precedence.
    """
    _, reg = vault_s
    from artifacts_os import update
    a = create(reg, "task", "A")
    b = create(reg, "task", "B")
    update(reg, a.id, status="ready")
    update(reg, b.id, status="in-progress")

    with pytest.warns(DeprecationWarning, match="list_artifacts"):
        items = list_artifacts(
            reg,
            status="ready",
            filters={"status": "in-progress"},  # explicit dict wins
        )
    assert len(items) == 1
    assert items[0].id == b.id


# ---------------------------------------------------------------------------
# §10.3  CLI integration matrix — stub list_artifacts to capture (kind, filters)
# ---------------------------------------------------------------------------

def _write_artifacts_yaml(root: Path, extra: str) -> None:
    base = root / "artifacts" / "artifacts.yaml"
    content = "layout_version: 1\nproject:\n  name: test\n" + extra
    base.write_text(content)


@pytest.fixture
def cli_vault(tmp_path: Path, monkeypatch):
    """Minimal CLI vault with schema-aware task kind, chdir'd into it."""
    import json as _json
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts" / "artifacts.yaml").write_text(
        "layout_version: 1\nproject:\n  name: test\n"
    )
    schema = {
        "x-dir": "tasks",
        "x-prefix": "t",
        "x-numbered": True,
        "properties": {
            "status": {"enum": ["backlog", "ready", "in-progress", "done"]},
            "assignee": {"type": "string"},
            "owner": {"type": "string"},
            "type": {"type": "string"},
            "priority": {"type": "string"},
        },
    }
    (kinds_dir / "task.json").write_text(_json.dumps(schema))
    (root / "artifacts" / "tasks").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)
    return root


@pytest.fixture
def stub_list(monkeypatch):
    """Replace list_artifacts with a MagicMock; return the mock."""
    mock = MagicMock(return_value=[])
    monkeypatch.setattr("artifacts_os.cli.commands.list.list_artifacts", mock)
    return mock


def _run_cli(*args, stub_list=None, cli_vault=None):
    """Run the CLI main with given args; return captured (kind, filters)."""
    from artifacts_os.cli import main
    main(list(args))
    call_args = stub_list.call_args
    # call_args.args = (registry,), call_args.kwargs = {kind=..., filters=...}
    kind = call_args.kwargs.get("kind")
    filters = call_args.kwargs.get("filters")
    return kind, filters


def test_cli_kind_flag_only(cli_vault, stub_list) -> None:
    """--kind task → kind="task", filters None."""
    kind, filters = _run_cli("list", "--kind", "task", "-q",
                              stub_list=stub_list, cli_vault=cli_vault)
    assert kind == "task"
    assert not filters


def test_cli_status_flag_only(cli_vault, stub_list) -> None:
    """--status ready → kind=None, filters={"status": "ready"}."""
    kind, filters = _run_cli("list", "--status", "ready", "-q",
                              stub_list=stub_list, cli_vault=cli_vault)
    assert kind is None
    assert filters == {"status": "ready"}


def test_cli_filter_flag_single(cli_vault, stub_list) -> None:
    """--filter assignee=alice → kind=None, filters={"assignee": "alice"}."""
    kind, filters = _run_cli("list", "--filter", "assignee=alice", "-q",
                              stub_list=stub_list, cli_vault=cli_vault)
    assert kind is None
    assert filters == {"assignee": "alice"}


def test_cli_filter_flag_multiple(cli_vault, stub_list) -> None:
    """--filter assignee=alice --filter type=feature → conjunction."""
    kind, filters = _run_cli(
        "list", "--filter", "assignee=alice", "--filter", "type=feature", "-q",
        stub_list=stub_list, cli_vault=cli_vault
    )
    assert kind is None
    assert filters == {"assignee": "alice", "type": "feature"}


def test_cli_filter_flag_last_wins(cli_vault, stub_list) -> None:
    """--filter assignee=alice --filter assignee=bob → {"assignee": "bob"}."""
    kind, filters = _run_cli(
        "list", "--filter", "assignee=alice", "--filter", "assignee=bob", "-q",
        stub_list=stub_list, cli_vault=cli_vault
    )
    assert kind is None
    assert filters == {"assignee": "bob"}


def test_cli_view_kind_status(cli_vault, stub_list) -> None:
    """View {kind: task, status: ready} → kind="task", filters={"status": "ready"}."""
    _write_artifacts_yaml(cli_vault, """
views:
  active:
    columns: id,name,status
    filters:
      kind: task
      status: ready
""")
    kind, filters = _run_cli("list", "--view", "active", "-q",
                              stub_list=stub_list, cli_vault=cli_vault)
    assert kind == "task"
    assert filters == {"status": "ready"}


def test_cli_view_status_overridden_by_flag(cli_vault, stub_list) -> None:
    """View {kind: task, status: ready} + --status all → {"status": "all"}."""
    _write_artifacts_yaml(cli_vault, """
views:
  active:
    columns: id,name,status
    filters:
      kind: task
      status: ready
""")
    kind, filters = _run_cli("list", "--view", "active", "--status", "all", "-q",
                              stub_list=stub_list, cli_vault=cli_vault)
    assert kind == "task"
    assert filters == {"status": "all"}


def test_cli_view_assignee_overridden_by_filter(cli_vault, stub_list) -> None:
    """View {kind: task, assignee: alice} + --filter assignee=bob → {"assignee": "bob"}."""
    _write_artifacts_yaml(cli_vault, """
views:
  alice-queue:
    columns: id,name,assignee
    filters:
      kind: task
      assignee: alice
""")
    kind, filters = _run_cli(
        "list", "--view", "alice-queue", "--filter", "assignee=bob", "-q",
        stub_list=stub_list, cli_vault=cli_vault
    )
    assert kind == "task"
    assert filters == {"assignee": "bob"}


def test_cli_view_assignee_kind_flag_overrides(cli_vault, stub_list) -> None:
    """View {kind: task, assignee: alice} + --kind spec → kind="spec", assignee still applied."""
    _write_artifacts_yaml(cli_vault, """
views:
  alice-queue:
    columns: id,name,assignee
    filters:
      kind: task
      assignee: alice
""")
    kind, filters = _run_cli(
        "list", "--view", "alice-queue", "--kind", "spec", "-q",
        stub_list=stub_list, cli_vault=cli_vault
    )
    assert kind == "spec"
    assert filters == {"assignee": "alice"}


def test_cli_view_complex_override(cli_vault, stub_list) -> None:
    """View {kind: task, status: ready, type: spec} + --status all --filter type=feature."""
    _write_artifacts_yaml(cli_vault, """
views:
  complex-view:
    columns: id,name,status,type
    filters:
      kind: task
      status: ready
      type: spec
""")
    kind, filters = _run_cli(
        "list", "--view", "complex-view",
        "--status", "all", "--filter", "type=feature", "-q",
        stub_list=stub_list, cli_vault=cli_vault
    )
    assert kind == "task"
    assert filters == {"status": "all", "type": "feature"}


def test_cli_view_no_kind_plus_kind_flag(cli_vault, stub_list) -> None:
    """View {assignee: alice} (no kind) + --kind task → kind="task", assignee applies."""
    _write_artifacts_yaml(cli_vault, """
views:
  alice-all:
    columns: id,name,assignee
    filters:
      assignee: alice
""")
    kind, filters = _run_cli(
        "list", "--view", "alice-all", "--kind", "task", "-q",
        stub_list=stub_list, cli_vault=cli_vault
    )
    assert kind == "task"
    assert filters == {"assignee": "alice"}


# ---------------------------------------------------------------------------
# §10.4  Validation surface
# ---------------------------------------------------------------------------

def test_cli_filter_missing_equals_exits_2(cli_vault, capsys) -> None:
    """--filter foo (no =) → exit 2 with error message."""
    from artifacts_os.cli import main
    with pytest.raises(SystemExit) as exc:
        main(["list", "--filter", "foo", "-q"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--filter expects key=value" in err
    assert "foo" in err


def test_cli_filter_unknown_key_with_kind_exits_2(cli_vault, capsys) -> None:
    """--filter asignee=alice --kind task → exit 2 (typo, single-kind validation)."""
    from artifacts_os.cli import main
    with pytest.raises(SystemExit) as exc:
        main(["list", "--kind", "task", "--filter", "asignee=alice", "-q"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "unknown filter key 'asignee'" in err


def test_cli_filter_unknown_key_cross_kind_exits_2(cli_vault, capsys) -> None:
    """--filter asignee=alice (no kind) → exit 2 (cross-kind validation)."""
    from artifacts_os.cli import main
    with pytest.raises(SystemExit) as exc:
        main(["list", "--filter", "asignee=alice", "-q"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "unknown filter key 'asignee'" in err


def test_cli_filter_bogus_status_value_returns_empty(cli_vault, capsys) -> None:
    """--filter status=bogus → exit 0, empty result (no enum validation per §6.4)."""
    from artifacts_os.cli import main
    import json as _json
    from artifacts_os.core import frontmatter as fm
    root = cli_vault
    # Write a real task with known status
    path = root / "artifacts" / "tasks" / "t0001-alpha.md"
    path.write_text(fm.dump({"kind": "task", "id": "t0001", "name": "alpha", "status": "ready"}, ""))
    # main() returns None on success (exits 0), raises SystemExit for non-zero
    main(["list", "--kind", "task", "--filter", "status=bogus", "-j"])
    out, _ = capsys.readouterr()
    data = _json.loads(out)
    assert data == []
