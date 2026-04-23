from pathlib import Path

from artifacts_os.core.ids import next_prefixed_id, slugify, validate_slug


def test_next_prefixed_id_empty_dir(tmp_path: Path) -> None:
    assert next_prefixed_id(tmp_path, "t") == "t0001"


def test_next_prefixed_id_with_existing(tmp_path: Path) -> None:
    for stem in ["t0001-a", "t0002-b", "t0005-e"]:
        (tmp_path / f"{stem}.md").touch()
    assert next_prefixed_id(tmp_path, "t") == "t0006"


def test_next_prefixed_id_prefix_isolation(tmp_path: Path) -> None:
    for stem in ["t0001-a", "s0007-b", "r0003-c"]:
        (tmp_path / f"{stem}.md").touch()
    assert next_prefixed_id(tmp_path, "t") == "t0002"
    assert next_prefixed_id(tmp_path, "s") == "s0008"


def test_next_prefixed_id_ignores_non_prefixed(tmp_path: Path) -> None:
    (tmp_path / "readme.md").touch()
    (tmp_path / "t0003-something.md").touch()
    assert next_prefixed_id(tmp_path, "t") == "t0004"


def test_slugify_basic() -> None:
    assert slugify("Fix the bug!") == "fix-the-bug"


def test_slugify_max_words() -> None:
    assert slugify("one two three four five six seven") == "one-two-three-four-five"


def test_slugify_collapses_non_alnum() -> None:
    assert slugify("Hello, World/World") == "hello-world-world"


def test_slugify_empty() -> None:
    assert slugify("!!!") == ""


def test_validate_slug() -> None:
    assert validate_slug("fix-the-bug")
    assert validate_slug("t0042")
    assert not validate_slug("Fix-Bug")
    assert not validate_slug("fix bug")
    assert not validate_slug("-leading")
    assert not validate_slug("trailing-")
    assert not validate_slug("double--hyphen")
