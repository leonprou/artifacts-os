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
    items = list_artifacts(registry, status="ready")
    assert [i.id for i in items] == ["t0001"]


def test_list_tag_filter(make_vault) -> None:
    _, registry = make_vault()
    create(registry, "task", "A", fields={"tags": ["urgent"]})
    create(registry, "task", "B", fields={"tags": ["later"]})
    items = list_artifacts(registry, tag="urgent")
    assert len(items) == 1
    assert items[0].name.endswith("-a")


def test_resolve_exact_stem(make_vault) -> None:
    _, registry = make_vault()
    a = create(registry, "task", "Fix thing")
    assert resolve(registry, a.name) == a.path


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
