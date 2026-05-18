"""Tests for cli init command — books-driven two-stage flow (s0030)."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from artifacts_os.cli import main
from artifacts_os.cli.commands.init import (
    BookSpec,
    _derive_project_alias,
    _get_project_name,
    _interpolate,
    _load_settings_template,
    _parse_book_flags,
    _parse_selection,
)


# ─── Module fixture ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clear_distro_env(monkeypatch):
    """Clear ARTIFACTS_DISTRO_URL by default for all tests in this module.

    Tests that need a distro URL set it explicitly via monkeypatch.setenv().
    """
    monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)


# ─── Helpers ──────────────────────────────────────────────────────────────


def run_init(*args, expected_exit=0):
    """Call main(["init", *args]), assert SystemExit code if non-zero."""
    if expected_exit == 0:
        main(["init", *args])
    else:
        with pytest.raises(SystemExit) as exc:
            main(["init", *args])
        assert exc.value.code == expected_exit


def _git(args: list, cwd: Path) -> None:
    import subprocess
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def _make_distro_repo(root: Path) -> Path:
    """Create a minimal distro git repo with 'agents' and 'cmds' books."""
    import yaml

    root.mkdir(parents=True, exist_ok=True)
    _git(["git", "init", "--initial-branch", "main"], root)
    _git(["git", "config", "user.email", "test@test.com"], root)
    _git(["git", "config", "user.name", "Test"], root)

    # agents book (flat walker)
    agents_dir = root / "agents"
    agents_dir.mkdir()
    (agents_dir / "architect.md").write_text("# Architect\nbody.", encoding="utf-8")
    (agents_dir / "developer.md").write_text("# Developer\nbody.", encoding="utf-8")

    # cmds book (flat walker)
    cmds_dir = root / "cmds"
    cmds_dir.mkdir()
    (cmds_dir / "foo.md").write_text("# Foo command\nbody.", encoding="utf-8")

    artbook = {
        "version": 1,
        "distro": {"name": "test-distro", "description": "Test distro."},
        "books": [
            {
                "name": "agents",
                # dest omitted → D37 default: artifacts/agents/
                "src": "agents/",
                "promote": ".claude/agents/",
                "description": "Agent specs.",
            },
            {
                "name": "cmds",
                "src": "cmds/",
                "dest": "artifacts/commands/",
                "promote": ".claude/commands/",
                "description": "Slash commands.",
            },
        ],
    }
    (root / "artbook.yaml").write_text(yaml.dump(artbook), encoding="utf-8")
    _git(["git", "add", "."], root)
    _git(["git", "commit", "-m", "init"], root)
    return root


# ─── Bundled settings template loading ───────────────────────────────────


class TestBundledTemplateLoading:
    def test_load_settings_minimal(self):
        text = _load_settings_template("minimal")
        assert text.strip()
        assert "layout_version" in text

    def test_load_settings_standard(self):
        text = _load_settings_template("standard")
        assert text.strip()
        assert "default_views" in text

    def test_unknown_tier_raises(self):
        with pytest.raises(FileNotFoundError, match="template not found"):
            _load_settings_template("nonexistent")

    @pytest.mark.parametrize("tier", ["minimal", "standard"])
    def test_template_views_parse_with_intact_columns(self, tier):
        """Regression: every view's columns must survive YAML parsing."""
        import yaml

        text = _load_settings_template(tier)
        text = (
            text.replace("{{project_name}}", "X")
            .replace("{{project_alias}}", "x")
            .replace("{{created}}", "2026-01-01")
        )
        data = yaml.safe_load(text)
        views = (data or {}).get("views") or {}
        for name, view in views.items():
            assert isinstance(view, dict), (
                f"view '{name}' did not parse to a mapping — likely a flow-mapping "
                f"comma syntax error: {view!r}"
            )
            cols = view.get("columns")
            assert cols, f"view '{name}' is missing columns: {view!r}"
            extra_keys = set(view.keys()) - {"columns", "filters", "sort"}
            assert not extra_keys, (
                f"view '{name}' has unexpected keys {extra_keys}; "
                f"this means an unquoted CSV columns value leaked tokens "
                f"into the surrounding flow mapping."
            )


# ─── Variable interpolation ────────────────────────────────────────────────


class TestVariableInterpolation:
    def test_project_name_from_claude_md(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("# My Cool Project\n\nSome text.\n")
        assert _get_project_name(tmp_path) == "My Cool Project"

    def test_artifacts_os_skipped(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("# Artifacts OS\n")
        assert _get_project_name(tmp_path) == tmp_path.name

    def test_open_station_skipped(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("# Open Station\n")
        assert _get_project_name(tmp_path) == tmp_path.name

    def test_falls_back_to_dir_name(self, tmp_path):
        project = tmp_path / "cool-project"
        project.mkdir()
        assert _get_project_name(project) == "cool-project"

    def test_no_claude_md(self, tmp_path):
        assert _get_project_name(tmp_path) == tmp_path.name

    def test_alias_strips_and_lowercases(self):
        assert _derive_project_alias("My-Project") == "myprojec"
        assert _derive_project_alias("artifacts-os") == "artifact"
        assert _derive_project_alias("hello world") == "hello"

    def test_alias_truncates_at_8(self):
        assert _derive_project_alias("toolongname") == "toolongn"

    def test_alias_alphanumeric_only(self):
        assert _derive_project_alias("my_proj!") == "myproj"

    def test_created_is_today(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main(["init", "--template", "minimal", "-y"])
        text = (tmp_path / "artifacts.yaml").read_text()
        import datetime
        assert datetime.date.today().isoformat() in text

    def test_unknown_token_passes_through(self):
        content = "hello {{unknown_var}} world {{project_name}}"
        result = _interpolate(content, "MyProj", "myproj", "2026-01-01")
        assert "{{unknown_var}}" in result
        assert "MyProj" in result


# ─── Multi-select parsing ───────────────────────────────────────────────────


class TestMultiSelectParsing:
    OPTIONS = ["task", "note", "spec", "research", "agent"]
    DEFAULTS = ["task", "note", "spec"]

    def test_empty_returns_defaults(self):
        assert _parse_selection("", self.OPTIONS, self.DEFAULTS) == ["task", "note", "spec"]

    def test_star_returns_all(self):
        assert _parse_selection("*", self.OPTIONS, self.DEFAULTS) == list(self.OPTIONS)

    def test_dash_returns_none(self):
        assert _parse_selection("-", self.OPTIONS, self.DEFAULTS) == []

    def test_numbers(self):
        assert _parse_selection("1,3,5", self.OPTIONS, self.DEFAULTS) == [
            "task", "spec", "agent"
        ]

    def test_names(self):
        assert _parse_selection("task,spec", self.OPTIONS, self.DEFAULTS) == [
            "task", "spec"
        ]

    def test_mixed_numbers_and_names(self):
        assert _parse_selection("1,spec", self.OPTIONS, self.DEFAULTS) == [
            "task", "spec"
        ]

    def test_out_of_range_returns_none(self, capsys):
        result = _parse_selection("7", self.OPTIONS, self.DEFAULTS)
        assert result is None
        assert "out of range" in capsys.readouterr().err

    def test_unknown_name_returns_none(self, capsys):
        result = _parse_selection("bogus", self.OPTIONS, self.DEFAULTS)
        assert result is None
        assert "not a valid choice" in capsys.readouterr().err

    def test_duplicates_deduped(self):
        result = _parse_selection("1,1,task", self.OPTIONS, self.DEFAULTS)
        assert result == ["task"]


# ─── Existing-file guard ────────────────────────────────────────────────────


class TestExistingFileGuard:
    def test_refuses_if_already_initialised(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main(["init", "--template", "minimal", "-y"])
        with pytest.raises(SystemExit) as exc:
            main(["init", "--template", "minimal", "-y"])
        assert exc.value.code == 2

    def test_error_message(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        main(["init", "--template", "minimal", "-y"])
        capsys.readouterr()
        with pytest.raises(SystemExit):
            main(["init", "--template", "minimal", "-y"])
        assert "already initialised" in capsys.readouterr().err

    def test_force_overwrites(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main(["init", "--template", "minimal", "-y"])
        yaml_path = tmp_path / "artifacts.yaml"
        yaml_path.write_text("# custom\n")
        main(["init", "--template", "standard", "--force", "-y"])
        text = yaml_path.read_text()
        assert "default_views" in text  # standard tier content

    def test_force_per_file_only_touches_selected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main(["init", "--template", "minimal", "-y"])
        extra = tmp_path / "artifacts" / "extra.txt"
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_text("untouched")
        main(["init", "--template", "minimal", "--force", "-y"])
        assert extra.read_text() == "untouched"


# ─── Rendered settings parse correctly ─────────────────────────────────────


class TestRenderedSettings:
    @pytest.mark.parametrize("tier", ["minimal", "standard"])
    def test_rendered_yaml_parses_with_intact_columns(self, tier, tmp_path, monkeypatch):
        """Regression: rendered settings file must round-trip through PyYAML."""
        import yaml

        monkeypatch.chdir(tmp_path)
        main(["init", "--template", tier, "-y"])
        text = (tmp_path / "artifacts.yaml").read_text()
        data = yaml.safe_load(text)
        views = (data or {}).get("views") or {}
        for name, view in views.items():
            assert isinstance(view, dict), f"view '{name}' did not parse to a mapping"
            cols = view.get("columns", "")
            extra_keys = set(view.keys()) - {"columns", "filters", "sort"}
            assert not extra_keys, (
                f"view '{name}' leaked tokens into surrounding keys "
                f"({extra_keys}); columns={cols!r}"
            )


# ─── Dry-run ────────────────────────────────────────────────────────────────


class TestDryRun:
    def test_no_files_written(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main(["init", "--template", "standard", "--dry-run", "-y"])
        # No files should have been created
        assert not (tmp_path / "artifacts.yaml").is_file()

    def test_output_prefixed_would(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        main(["init", "--template", "minimal", "--dry-run", "-y"])
        out = capsys.readouterr().out
        action_lines = [
            line for line in out.splitlines() if line.strip().startswith("[would]")
        ]
        assert len(action_lines) > 0

    def test_exit_0_even_with_preexisting_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main(["init", "--template", "minimal", "-y"])
        # dry-run on already-inited vault with --force: should exit 0
        main(["init", "--template", "minimal", "--dry-run", "--force", "-y"])


# ─── D2: No-distro fallback ─────────────────────────────────────────────────


class TestD2NoDistroFallback:
    """D2: art init (no --distro) writes artifacts.yaml + bundled skill."""

    def test_writes_artifacts_yaml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        main(["init", "--template", "minimal", "-y"])
        assert (tmp_path / "artifacts.yaml").is_file()

    def test_writes_bundled_skill(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        main(["init", "--template", "minimal", "-y"])
        skill_file = tmp_path / ".claude" / "skills" / "artifacts-os" / "SKILL.md"
        assert skill_file.is_file()
        assert skill_file.read_text(encoding="utf-8").strip()

    def test_no_kinds_no_agents(self, tmp_path, monkeypatch):
        """D2: no kinds or agents directory written."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        main(["init", "--template", "minimal", "-y"])
        assert not (tmp_path / "artifacts" / "kinds").exists()
        assert not (tmp_path / "artifacts" / "agents").exists()

    def test_no_distro_url_in_yaml(self, tmp_path, monkeypatch):
        """D2: no artbook.distro_url injected when no distro configured."""
        import yaml as _yaml
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        main(["init", "--template", "minimal", "-y"])
        data = _yaml.safe_load((tmp_path / "artifacts.yaml").read_text())
        assert "artbook" not in data or "distro_url" not in data.get("artbook", {})

    def test_skill_not_installed_twice_on_force(self, tmp_path, monkeypatch):
        """--force re-init still writes the skill (not skipped)."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        main(["init", "--template", "minimal", "-y"])
        main(["init", "--template", "standard", "--force", "-y"])
        skill_file = tmp_path / ".claude" / "skills" / "artifacts-os" / "SKILL.md"
        assert skill_file.is_file()


# ─── D40: D2 fallback — canonical-write + promote ───────────────────────────


class TestD40BundledSkillPromotion:
    """D40: D2 fallback writes canonical file + promotes via symlink."""

    def test_canonical_skill_file_written(self, tmp_path, monkeypatch):
        """Canonical skill written to artifacts/skills/artifacts-os/SKILL.md."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        main(["init", "--template", "minimal", "-y"])
        canonical = tmp_path / "artifacts" / "skills" / "artifacts-os" / "SKILL.md"
        assert canonical.is_file()
        assert not canonical.is_symlink()  # regular file, not a symlink

    def test_promotion_symlink_created(self, tmp_path, monkeypatch):
        """Promoted symlink at .claude/skills/artifacts-os/SKILL.md → canonical."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        main(["init", "--template", "minimal", "-y"])
        promote_target = tmp_path / ".claude" / "skills" / "artifacts-os" / "SKILL.md"
        assert promote_target.is_symlink()
        canonical = tmp_path / "artifacts" / "skills" / "artifacts-os" / "SKILL.md"
        assert promote_target.resolve() == canonical.resolve()

    def test_state_file_records_promotion(self, tmp_path, monkeypatch):
        """artifacts/.artbook/state.json records the synthetic book promotion."""
        import json

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        main(["init", "--template", "minimal", "-y"])
        state_path = tmp_path / "artifacts" / ".artbook" / "state.json"
        assert state_path.is_file()
        state = json.loads(state_path.read_text())
        assert "artifacts-os-skill" in state["promotions"]

    def test_no_promote_skips_symlink(self, tmp_path, monkeypatch):
        """--no-promote: canonical file written; no .claude/skills/ dir."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        main(["init", "--template", "minimal", "-y", "--no-promote"])
        canonical = tmp_path / "artifacts" / "skills" / "artifacts-os" / "SKILL.md"
        assert canonical.is_file()
        promote_dir = tmp_path / ".claude" / "skills"
        assert not promote_dir.exists()

    def test_no_promote_skips_state_file(self, tmp_path, monkeypatch):
        """--no-promote: state file not written."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        main(["init", "--template", "minimal", "-y", "--no-promote"])
        state_path = tmp_path / "artifacts" / ".artbook" / "state.json"
        assert not state_path.exists()

    def test_idempotent_force_reinit(self, tmp_path, monkeypatch):
        """Second --force init is idempotent: state file byte-stable."""
        import json

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        main(["init", "--template", "minimal", "-y"])
        state_path = tmp_path / "artifacts" / ".artbook" / "state.json"
        state1 = json.loads(state_path.read_text())
        main(["init", "--template", "minimal", "--force", "-y"])
        state2 = json.loads(state_path.read_text())
        assert state1["promotions"] == state2["promotions"]


# ─── D6: -y with no distro ──────────────────────────────────────────────────


class TestD6YesNoDistro:
    """D6: art init -y with no distro = D2 fallback, no prompts."""

    def test_yes_no_distro_writes_skill(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        main(["init", "-y"])
        skill = tmp_path / ".claude" / "skills" / "artifacts-os" / "SKILL.md"
        assert skill.is_file()

    def test_yes_no_distro_uses_standard_tier(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        main(["init", "-y"])
        text = (tmp_path / "artifacts.yaml").read_text()
        assert "default_views" in text  # standard tier marker

    def test_yes_no_distro_no_fetching_output(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        main(["init", "-y"])
        out = capsys.readouterr().out
        assert "Fetching distro manifest" not in out

    def test_yes_with_template_override(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        main(["init", "-y", "--template", "minimal"])
        text = (tmp_path / "artifacts.yaml").read_text()
        assert "default_views" not in text
        assert "features" not in text


# ─── Step skipping and flag/prompt precedence ────────────────────────────────


class TestStepSkipping:
    def test_template_flag_sets_tier(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main(["init", "--template", "standard", "-y"])
        assert (tmp_path / "artifacts.yaml").is_file()
        text = (tmp_path / "artifacts.yaml").read_text()
        assert "layout_version" in text

    def test_non_tty_no_flags_exits_2(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # stdin is not a TTY in test context; no -y
        with pytest.raises(SystemExit) as exc:
            main(["init"])
        assert exc.value.code == 2

    def test_non_tty_distro_partial_flags_exits_2(self, tmp_path, monkeypatch):
        """With distro set, --template alone is not sufficient (needs --book or -y)."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("ARTIFACTS_DISTRO_URL", "https://example.com/distro.git")
        with pytest.raises(SystemExit) as exc:
            main(["init", "--template", "minimal"])
        assert exc.value.code == 2

    def test_all_flags_non_interactive(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        # Template flag alone is sufficient for no-distro non-interactive
        # (no distro = distro_fully_flagged = True)
        main(["init", "--template", "minimal"])
        assert (tmp_path / "artifacts.yaml").is_file()


# ─── Error handling ──────────────────────────────────────────────────────────


class TestErrorHandling:
    def test_write_failure_partial_success(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        original_write = Path.write_text
        call_count = [0]

        def failing_write(self, content, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise OSError("Permission denied")
            return original_write(self, content, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", failing_write)

        with pytest.raises(SystemExit) as exc:
            main(["init", "--template", "minimal", "-y"])
        assert exc.value.code == 1

    def test_missing_bundled_template(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)

        def bad_load(tier):
            raise FileNotFoundError(
                "template not found: artifacts_os/templates/settings/standard.yaml\n"
                "       (this is a bug — please file an issue)"
            )

        monkeypatch.setattr(
            "artifacts_os.cli.commands.init._load_settings_template", bad_load
        )
        with pytest.raises(SystemExit) as exc:
            main(["init", "--template", "standard", "-y"])
        assert exc.value.code == 2

    def test_unknown_template_flag(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            main(["init", "--template", "ultra"])
        assert exc.value.code == 2

    def test_kinds_flag_unrecognized(self, tmp_path, monkeypatch):
        """--kinds is removed; argparse should reject it with exit 2."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            main(["init", "--template", "standard", "--kinds", "task", "-y"])
        assert exc.value.code == 2

    def test_agents_flag_unrecognized(self, tmp_path, monkeypatch):
        """--agents is removed; argparse should reject it with exit 2."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            main(["init", "--template", "standard", "--agents", "architect", "-y"])
        assert exc.value.code == 2


# ─── openstation-compat ──────────────────────────────────────────────────────


class TestOpenstationCompat:
    def test_creates_symlink(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main(["init", "--template", "minimal", "--openstation-compat", "-y"])
        symlink = tmp_path / "openstation"
        assert symlink.is_symlink()
        assert symlink.resolve() == (tmp_path / "artifacts").resolve()

    def test_no_symlink_without_flag(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main(["init", "--template", "minimal", "-y"])
        assert not (tmp_path / "openstation").exists()

    def test_pre_registry_flag_set(self):
        """init runs without a registry (pre_registry=True)."""
        import argparse
        from artifacts_os.cli.commands.init import register

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="cmd")
        register(sub)
        args = parser.parse_args(["init", "--template", "minimal"])
        assert getattr(args, "_pre_registry", False) is True


# ─── BookSpec and --book flag parser ────────────────────────────────────────


class TestBookFlagParser:
    """Q1.b: --book NAME[:items] flag parsing."""

    def _make_args(self, book_flags):
        """Create a minimal args namespace with book flags."""
        import argparse
        ns = argparse.Namespace(book=book_flags)
        return ns

    def test_no_book_flags_returns_none(self):
        args = self._make_args([])
        result = _parse_book_flags(args, "https://example.com/distro")
        assert result is None

    def test_none_book_attr_returns_none(self):
        args = self._make_args(None)
        result = _parse_book_flags(args, "https://example.com/distro")
        assert result is None

    def test_single_book_no_items(self):
        args = self._make_args(["agents"])
        result = _parse_book_flags(args, "https://example.com/distro")
        assert result == [BookSpec(name="agents", items=None)]

    def test_single_book_with_items(self):
        args = self._make_args(["agents:architect,developer"])
        result = _parse_book_flags(args, "https://example.com/distro")
        assert result == [BookSpec(name="agents", items=["architect", "developer"])]

    def test_multiple_books(self):
        args = self._make_args(["agents:architect", "cmds"])
        result = _parse_book_flags(args, "https://example.com/distro")
        assert result == [
            BookSpec(name="agents", items=["architect"]),
            BookSpec(name="cmds", items=None),
        ]

    def test_no_distro_url_returns_none(self):
        args = self._make_args(["agents"])
        result = _parse_book_flags(args, None)
        assert result is None

    def test_empty_name_returns_none(self, capsys):
        args = self._make_args([":items"])
        result = _parse_book_flags(args, "https://example.com/distro")
        assert result is None
        assert "invalid --book value" in capsys.readouterr().err

    def test_book_without_distro_exits_2(self, tmp_path, monkeypatch, capsys):
        """--book without distro URL → exit 2."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        with pytest.raises(SystemExit) as exc:
            main(["init", "--template", "minimal", "--book", "agents", "-y"])
        assert exc.value.code == 2
        assert "--book requires --distro" in capsys.readouterr().err

    def test_items_whitespace_stripped(self):
        args = self._make_args(["agents: architect , developer "])
        result = _parse_book_flags(args, "https://example.com/distro")
        assert result == [BookSpec(name="agents", items=["architect", "developer"])]


# ─── Distro integration ──────────────────────────────────────────────────────


class TestDistroBookLoop:
    """D1 + D3: distro-configured flow."""

    def test_distro_url_injected_in_yaml(self, tmp_path, monkeypatch):
        """artbook.distro_url written into artifacts.yaml."""
        distro = _make_distro_repo(tmp_path / "distro")
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)
        main([
            "init", "--template", "minimal",
            "--distro", str(distro),
            "--book", "agents", "-y",
        ])
        import yaml as _yaml
        data = _yaml.safe_load((vault / "artifacts.yaml").read_text())
        assert data.get("artbook", {}).get("distro_url") == str(distro)

    def test_pull_all_books_y(self, tmp_path, monkeypatch):
        """-y + distro pulls all books, all items."""
        distro = _make_distro_repo(tmp_path / "distro")
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)
        main([
            "init", "--template", "minimal",
            "--distro", str(distro), "-y",
        ])
        assert (vault / ".claude" / "agents" / "architect.md").is_file()
        assert (vault / ".claude" / "agents" / "developer.md").is_file()
        assert (vault / ".claude" / "commands" / "foo.md").is_file()

    def test_pull_specific_book_via_book_flag(self, tmp_path, monkeypatch):
        """--book agents -y pulls only agents book."""
        distro = _make_distro_repo(tmp_path / "distro")
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)
        main([
            "init", "--template", "minimal",
            "--distro", str(distro),
            "--book", "agents", "-y",
        ])
        assert (vault / ".claude" / "agents" / "architect.md").is_file()
        # cmds book NOT pulled
        assert not (vault / ".claude" / "commands" / "foo.md").is_file()

    def test_pull_filtered_items_via_book_flag(self, tmp_path, monkeypatch):
        """--book agents:architect pulls only architect."""
        distro = _make_distro_repo(tmp_path / "distro")
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)
        main([
            "init", "--template", "minimal",
            "--distro", str(distro),
            "--book", "agents:architect", "-y",
        ])
        assert (vault / ".claude" / "agents" / "architect.md").is_file()
        assert not (vault / ".claude" / "agents" / "developer.md").is_file()

    def test_vault_written_before_distro_pull(self, tmp_path, monkeypatch):
        """artifacts.yaml exists before distro clone attempted."""
        distro = _make_distro_repo(tmp_path / "distro")
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)
        main([
            "init", "--template", "minimal",
            "--distro", str(distro),
            "--book", "agents", "-y",
        ])
        assert (vault / "artifacts.yaml").is_file()

    def test_no_bundled_skill_when_distro_configured(self, tmp_path, monkeypatch):
        """Q4: bundled skill NOT installed when distro is configured."""
        distro = _make_distro_repo(tmp_path / "distro")
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)
        main([
            "init", "--template", "minimal",
            "--distro", str(distro), "-y",
        ])
        # Bundled skill should NOT be written from bundle
        # (anything in .claude/skills/ must come from the distro)
        # Our test distro doesn't have a skills book, so nothing there
        bundle_skill = vault / ".claude" / "skills" / "artifacts-os" / "SKILL.md"
        assert not bundle_skill.is_file()

    def test_book_order_follows_manifest(self, tmp_path, monkeypatch, capsys):
        """Q5.a: books are pulled in manifest declaration order."""
        distro = _make_distro_repo(tmp_path / "distro")
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)
        main([
            "init", "--template", "minimal",
            "--distro", str(distro), "-y",
        ])
        out = capsys.readouterr().out
        agents_pos = out.find("agents")
        cmds_pos = out.find("cmds")
        assert agents_pos < cmds_pos, "agents book should appear before cmds in output"

    def test_unknown_book_in_book_flag_exits_2(self, tmp_path, monkeypatch, capsys):
        """--book with unknown book name → exit 2 before any pull."""
        distro = _make_distro_repo(tmp_path / "distro")
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)
        with pytest.raises(SystemExit) as exc:
            main([
                "init", "--template", "minimal",
                "--distro", str(distro),
                "--book", "nonexistent-book", "-y",
            ])
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "nonexistent-book" in err
        assert "available" in err.lower()


# ─── Q6: Error semantics ─────────────────────────────────────────────────────


class TestQ6ErrorSemantics:
    """Q6: two-tier error handling in the book loop."""

    def test_clone_failure_exits_nonzero(self, tmp_path, monkeypatch, capsys):
        """git clone failure → vault preserved, error printed, non-zero exit."""
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)
        with pytest.raises(SystemExit) as exc:
            main([
                "init", "--template", "minimal",
                "--distro", "https://invalid.example.com/no-such-repo.git",
                "-y",
            ])
        assert exc.value.code in (1, 2)
        assert (vault / "artifacts.yaml").is_file()
        err = capsys.readouterr().err
        assert "error" in err.lower()

    def test_cli_distro_clone_failure_exits_2(self, tmp_path, monkeypatch, capsys):
        """CLI-supplied --distro clone failure → exit 2."""
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)
        with pytest.raises(SystemExit) as exc:
            main([
                "init", "--template", "minimal",
                "--distro", "https://invalid.example.com/no-such-repo.git",
                "-y",
            ])
        assert exc.value.code == 2

    def test_env_distro_clone_failure_exits_1(self, tmp_path, monkeypatch, capsys):
        """Env-supplied ARTIFACTS_DISTRO_URL clone failure → exit 1 (softer)."""
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)
        monkeypatch.setenv("ARTIFACTS_DISTRO_URL", "https://invalid.example.com/no-such.git")
        with pytest.raises(SystemExit) as exc:
            main(["init", "--template", "minimal", "-y"])
        assert exc.value.code == 1

    def test_per_book_failure_continues_loop(self, tmp_path, monkeypatch, capsys):
        """Per-book failure → log error, continue other books, exit 1."""
        distro = _make_distro_repo(tmp_path / "distro")
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)

        import artifacts_os.artbook as artbook_module
        original_pull = artbook_module.pull_book

        def patched_pull(book, clone_root, vault_root, **kw):
            if book.name == "agents":
                from artifacts_os.artbook.errors import ArtbookError
                raise ArtbookError("simulated failure for agents")
            return original_pull(book, clone_root, vault_root, **kw)

        monkeypatch.setattr(artbook_module, "pull_book", patched_pull)

        with pytest.raises(SystemExit) as exc:
            main([
                "init", "--template", "minimal",
                "--distro", str(distro), "-y",
            ])
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "agents" in err
        # cmds book should have been pulled despite agents failure
        assert (vault / ".claude" / "commands" / "foo.md").is_file()

    def test_dry_run_no_clone_no_write(self, tmp_path, monkeypatch, capsys):
        """--dry-run prints planned pull without cloning or writing."""
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)
        main([
            "init", "--template", "minimal",
            "--distro", "https://invalid.example.com/no-such-repo.git",
            "--book", "agents", "-y", "--dry-run",
        ])
        out = capsys.readouterr().out
        assert "[would]" in out
        assert "invalid.example.com" in out
        assert not (vault / "artifacts.yaml").is_file()


# ─── Q3: Resource resolution ────────────────────────────────────────────────


class TestQ3ResourceResolution:
    """Q3: bundled skill is accessible via importlib.resources."""

    def test_skill_root_resolves(self):
        """importlib.resources.files(...).joinpath('artifacts-os') resolves."""
        from importlib.resources import files
        root = files("artifacts_os.ai.claude.skills").joinpath("artifacts-os")
        assert root is not None

    def test_skill_md_non_empty(self):
        """SKILL.md is accessible and has content."""
        from importlib.resources import files
        skill_file = files("artifacts_os.ai.claude.skills").joinpath(
            "artifacts-os", "SKILL.md"
        )
        content = skill_file.read_text(encoding="utf-8")
        assert content.strip()

    def test_bundled_skill_installed_in_vault(self, tmp_path, monkeypatch):
        """D2 fallback: SKILL.md is written to .claude/skills/artifacts-os/."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        main(["init", "-y"])
        skill = tmp_path / ".claude" / "skills" / "artifacts-os" / "SKILL.md"
        assert skill.is_file()
        assert skill.read_text(encoding="utf-8").strip()

    def test_no_init_py_in_installed_skill(self, tmp_path, monkeypatch):
        """__init__.py is excluded from the bundled skill install."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        main(["init", "-y"])
        skill_dir = tmp_path / ".claude" / "skills" / "artifacts-os"
        assert skill_dir.is_dir()
        assert not (skill_dir / "__init__.py").exists()


# ─── ARTIFACTS_DISTRO_URL env var ────────────────────────────────────────────


class TestDistroEnvVarDefault:
    """ARTIFACTS_DISTRO_URL supplies the default value for --distro."""

    def test_env_var_supplies_default_distro(self, tmp_path, monkeypatch):
        distro = _make_distro_repo(tmp_path / "distro")
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)
        monkeypatch.setenv("ARTIFACTS_DISTRO_URL", str(distro))
        main(["init", "--template", "minimal", "-y"])
        import yaml as _yaml
        data = _yaml.safe_load((vault / "artifacts.yaml").read_text())
        assert data.get("artbook", {}).get("distro_url") == str(distro)
        assert (vault / ".claude" / "agents" / "architect.md").is_file()

    def test_cli_flag_overrides_env_var(self, tmp_path, monkeypatch):
        distro_a = _make_distro_repo(tmp_path / "distro_a")
        distro_b = _make_distro_repo(tmp_path / "distro_b")
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)
        monkeypatch.setenv("ARTIFACTS_DISTRO_URL", str(distro_a))
        main([
            "init", "--template", "minimal",
            "--distro", str(distro_b), "-y",
        ])
        import yaml as _yaml
        data = _yaml.safe_load((vault / "artifacts.yaml").read_text())
        assert data.get("artbook", {}).get("distro_url") == str(distro_b)

    def test_unset_env_var_no_distro_step(self, tmp_path, monkeypatch, capsys):
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)
        monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)
        main(["init", "--template", "minimal", "-y"])
        import yaml as _yaml
        data = _yaml.safe_load((vault / "artifacts.yaml").read_text())
        assert "artbook" not in data or "distro_url" not in data.get("artbook", {})
        out = capsys.readouterr().out
        assert "Fetching distro manifest" not in out

    @pytest.mark.parametrize("env_value", ["", "   ", "\t\n"])
    def test_empty_env_var_treated_as_unset(self, tmp_path, monkeypatch, env_value):
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)
        monkeypatch.setenv("ARTIFACTS_DISTRO_URL", env_value)
        main(["init", "--template", "minimal", "-y"])
        import yaml as _yaml
        data = _yaml.safe_load((vault / "artifacts.yaml").read_text())
        assert "artbook" not in data or "distro_url" not in data.get("artbook", {})

    def test_book_flag_works_with_env_var_alone(self, tmp_path, monkeypatch):
        """--book works when env var provides the distro URL (no --distro flag)."""
        distro = _make_distro_repo(tmp_path / "distro")
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)
        monkeypatch.setenv("ARTIFACTS_DISTRO_URL", str(distro))
        main([
            "init", "--template", "minimal",
            "--book", "agents", "-y",
        ])
        assert (vault / ".claude" / "agents" / "architect.md").is_file()
        # cmds book NOT pulled
        assert not (vault / ".claude" / "commands" / "foo.md").is_file()

    def test_summary_annotates_env_source(self, tmp_path, monkeypatch, capsys):
        distro = _make_distro_repo(tmp_path / "distro")
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)
        monkeypatch.setenv("ARTIFACTS_DISTRO_URL", str(distro))
        main(["init", "--template", "minimal", "-y"])
        out = capsys.readouterr().out
        assert "(from ARTIFACTS_DISTRO_URL)" in out

    def test_summary_no_annotation_for_cli_distro(self, tmp_path, monkeypatch, capsys):
        distro = _make_distro_repo(tmp_path / "distro")
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.chdir(vault)
        monkeypatch.setenv("ARTIFACTS_DISTRO_URL", "https://example.com/other.git")
        main([
            "init", "--template", "minimal",
            "--distro", str(distro), "-y",
        ])
        out = capsys.readouterr().out
        assert "(from ARTIFACTS_DISTRO_URL)" not in out


# ─── Documentation content checks ────────────────────────────────────────────


class TestDocContent:
    """Verify documentation files contain required consumer-facing content."""

    def test_artbook_md_has_consumer_quickstart(self):
        docs_dir = Path(__file__).parents[2] / "docs" / "artbook.md"
        text = docs_dir.read_text(encoding="utf-8")
        assert "--distro" in text
        assert "Consumer Quickstart" in text

    def test_artbook_md_documents_env_var(self):
        docs_dir = Path(__file__).parents[2] / "docs" / "artbook.md"
        text = docs_dir.read_text(encoding="utf-8")
        assert "ARTIFACTS_DISTRO_URL" in text

    def test_cli_readme_documents_distro_and_book(self):
        readme = (
            Path(__file__).parents[2]
            / "src" / "artifacts_os" / "cli" / "README.md"
        )
        text = readme.read_text(encoding="utf-8")
        assert "--distro" in text
        assert "--book" in text

    def test_cli_readme_documents_env_var(self):
        readme = (
            Path(__file__).parents[2]
            / "src" / "artifacts_os" / "cli" / "README.md"
        )
        text = readme.read_text(encoding="utf-8")
        assert "ARTIFACTS_DISTRO_URL" in text


# ─── Integration: vault structure ────────────────────────────────────────────


class TestVaultStructure:
    def test_project_name_in_yaml(self, tmp_path, monkeypatch):
        project = tmp_path / "my-awesome-project"
        project.mkdir()
        monkeypatch.chdir(project)
        main(["init", "--template", "minimal", "-y"])
        text = (project / "artifacts.yaml").read_text()
        assert "my-awesome-project" in text

    def test_project_name_from_claude_md(self, tmp_path, monkeypatch):
        (tmp_path / "CLAUDE.md").write_text("# My Fancy Project\n\ndetails.\n")
        monkeypatch.chdir(tmp_path)
        main(["init", "--template", "minimal", "-y"])
        text = (tmp_path / "artifacts.yaml").read_text()
        assert "My Fancy Project" in text

    def test_target_directory_argument(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        target = tmp_path / "sub"
        target.mkdir()
        main(["init", str(target), "--template", "minimal", "-y"])
        assert (target / "artifacts.yaml").is_file()

    def test_init_then_list_works(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
        main(["init", "--template", "standard", "-y"])
        capsys.readouterr()
        main(["list", "-q"])
        out = capsys.readouterr().out
        assert out == ""  # empty vault
