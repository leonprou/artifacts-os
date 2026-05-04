"""Tests for the ``--version`` / ``-v`` flag and ``__version__`` exports."""

import pytest

from artifacts_os.cli import main


def _expected_version() -> str:
    """Read version directly from package metadata for cross-checking."""
    from importlib.metadata import version

    return version("artifacts-os")


def test_version_long_flag(capsys):
    """``artifacts --version`` prints ``artifacts <version>`` and exits 0."""
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert out.strip() == f"artifacts {_expected_version()}"


def test_version_short_flag(capsys):
    """``-v`` is the short form of ``--version``."""
    with pytest.raises(SystemExit) as exc:
        main(["-v"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert out.strip() == f"artifacts {_expected_version()}"


def test_version_works_outside_vault(tmp_path, monkeypatch, capsys):
    """``--version`` must work even when no vault is present (no exit 2)."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert _expected_version() in capsys.readouterr().out


def test_version_listed_in_help(capsys):
    """The top-level ``--help`` advertises the version flag."""
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--version" in out
    assert "-v" in out


def test_dunder_version_is_re_exported():
    """``artifacts_os.__version__`` mirrors ``artifacts_os.core.__version__``."""
    import artifacts_os
    import artifacts_os.core

    assert artifacts_os.__version__ == artifacts_os.core.__version__
    assert artifacts_os.__version__ == _expected_version()


def test_version_is_in_core_all():
    """``__version__`` is part of the core public API contract."""
    import artifacts_os
    import artifacts_os.core

    assert "__version__" in artifacts_os.core.__all__
    assert "__version__" in artifacts_os.__all__
