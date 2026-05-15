import pytest

from artifacts_os import create, list_artifacts, resolve, search
from artifacts_os.core.errors import AmbiguousError, NotFoundError


def test_list_all_kinds(make_vault) -> None:
    _, registry = make_vault()
    create(registry, "task", "A")
    create(registry, "research", "Some topic")
    create(registry, "agent", "helper")
    items = list_artifacts(registry)
    assert len(items) == 3
    kinds = {i.kind for i in items}
    assert kinds == {"task", "research", "agent"}


def test_list_single_kind(make_vault) -> None:
    _, registry = make_vault()
    create(registry, "task", "A")
    create(registry, "task", "B")
    create(registry, "research", "C")
    items = list_artifacts(registry, kind="task")
    assert len(items) == 2
    assert all(i.kind == "task" for i in items)


def test_list_status_filter(make_vault) -> None:
    _, registry = make_vault()
    a = create(registry, "task", "A")
    create(registry, "task", "B")
    from artifacts_os import update

    update(registry, a.id, status="ready")
    # New API: filters dict
    items = list_artifacts(registry, filters={"status": "ready"})
    assert [i.id for i in items] == ["t0001"]


def test_list_status_filter_deprecated_kwarg(make_vault) -> None:
    """Legacy status= kwarg emits DeprecationWarning but returns same result."""
    _, registry = make_vault()
    a = create(registry, "task", "A")
    create(registry, "task", "B")
    from artifacts_os import update

    update(registry, a.id, status="ready")
    with pytest.warns(DeprecationWarning, match="list_artifacts"):
        items = list_artifacts(registry, status="ready")
    assert [i.id for i in items] == ["t0001"]


def test_list_tag_filter(make_vault) -> None:
    _, registry = make_vault()
    create(registry, "task", "A", fields={"tags": ["urgent"]})
    create(registry, "task", "B", fields={"tags": ["later"]})
    # New API: filters dict using "tags" key
    items = list_artifacts(registry, filters={"tags": "urgent"})
    assert len(items) == 1
    # `name` is slug-only; the full stem lives in path.stem.
    assert items[0].name == "a"
    assert items[0].path.stem == "t0001-a"


def test_list_tag_filter_deprecated_kwarg(make_vault) -> None:
    """Legacy tag= kwarg emits DeprecationWarning but returns same result."""
    _, registry = make_vault()
    create(registry, "task", "A", fields={"tags": ["urgent"]})
    create(registry, "task", "B", fields={"tags": ["later"]})
    with pytest.warns(DeprecationWarning, match="list_artifacts"):
        items = list_artifacts(registry, tag="urgent")
    assert len(items) == 1
    assert items[0].name == "a"


def test_resolve_exact_stem(make_vault) -> None:
    _, registry = make_vault()
    a = create(registry, "task", "Fix thing")
    assert resolve(registry, a.path.stem) == a.path


def test_resolve_prefixed_short_id(make_vault) -> None:
    _, registry = make_vault()
    a = create(registry, "task", "Fix thing")
    assert resolve(registry, "t1") == a.path
    assert resolve(registry, "t0001") == a.path


def test_resolve_old_style_numeric(make_vault) -> None:
    _, registry = make_vault()
    a = create(registry, "task", "Fix thing")
    assert resolve(registry, "1") == a.path


def test_resolve_partial_stem(make_vault) -> None:
    _, registry = make_vault()
    a = create(registry, "task", "Unique token here")
    assert resolve(registry, "unique") == a.path


def test_resolve_not_found(make_vault) -> None:
    _, registry = make_vault()
    with pytest.raises(NotFoundError):
        resolve(registry, "missing")


def test_resolve_ambiguous(make_vault) -> None:
    _, registry = make_vault()
    create(registry, "task", "alpha version")
    create(registry, "task", "alpha build")
    with pytest.raises(AmbiguousError):
        resolve(registry, "alpha", kind="task")


def test_resolve_agent_by_name(make_vault) -> None:
    _, registry = make_vault()
    a = create(registry, "agent", "researcher")
    assert resolve(registry, "researcher") == a.path


def test_search_multiple(make_vault) -> None:
    _, registry = make_vault()
    create(registry, "task", "alpha one")
    create(registry, "task", "alpha two")
    results = search(registry, "alpha", kind="task")
    assert len(results) == 2


def test_search_empty(make_vault) -> None:
    _, registry = make_vault()
    assert search(registry, "nothing-here") == []


def test_list_artifacts_skips_malformed_frontmatter(make_vault, capsys) -> None:
    """A single broken file must not crash the whole vault walk.

    Regression: a bad ``>-`` block scalar in one agent file used to
    raise ``yaml.scanner.ScannerError`` out of ``list_artifacts``,
    taking down every CLI command that enumerates the vault.
    """
    root, registry = make_vault()
    good = create(registry, "task", "good")
    bad_path = root / "artifacts" / "tasks" / "t0099-broken.md"
    bad_path.write_text(
        "---\n"
        "kind: task\n"
        "id: t0099\n"
        "name: broken\n"
        "description: >- inline text after block scalar indicator\n"
        "---\n"
        "\n"
        "# Broken\n"
    )

    items = list_artifacts(registry, kind="task")

    # Good file still returned; broken file silently skipped.
    assert [i.path for i in items] == [good.path]

    # Warning surfaced on stderr so operators notice.
    err = capsys.readouterr().err
    assert "warning: skipping" in err
    assert "t0099-broken.md" in err


def test_search_skips_malformed_frontmatter(make_vault, capsys) -> None:
    """`search` shares the same enumeration semantics as list_artifacts."""
    root, registry = make_vault()
    create(registry, "task", "alpha one")
    bad_path = root / "artifacts" / "tasks" / "t0099-alpha-broken.md"
    bad_path.write_text(
        "---\n"
        "kind: task\n"
        "name: alpha-broken\n"
        "description: >- inline text after block scalar indicator\n"
        "---\n"
    )

    results = search(registry, "alpha", kind="task")
    # Only the well-formed match comes back; broken file dropped.
    assert [m.path.stem for m in results] == ["t0001-alpha-one"]
    assert "warning: skipping" in capsys.readouterr().err


def test_resolve_still_strict_for_direct_lookup(make_vault) -> None:
    """Direct ref lookups must still surface the parse error.

    When a user asks for a specific artifact and it's broken, silent
    failure would mask the real problem. Only enumeration contexts
    are resilient; ``resolve`` → ``_meta_from_file`` stay strict.
    """
    from artifacts_os.core.discover import _meta_from_file

    root, registry = make_vault()
    bad_path = root / "artifacts" / "tasks" / "t0099-broken.md"
    bad_path.write_text(
        "---\n"
        "kind: task\n"
        "name: broken\n"
        "description: >- inline text after block scalar indicator\n"
        "---\n"
    )

    # resolve() finds the file (matching is filename-based, not parse-based)…
    assert resolve(registry, "t0099-broken") == bad_path
    # …but reading its frontmatter raises.
    with pytest.raises(Exception):
        _meta_from_file(bad_path)
