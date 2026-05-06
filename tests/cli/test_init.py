"""Tests for cli init command — §18.1 through §18.10 of s0021."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from artifacts_os.cli import main
from artifacts_os.cli.commands.init import (
    _derive_project_alias,
    _discover_agents,
    _discover_kinds,
    _get_project_name,
    _interpolate,
    _load_agent_template,
    _load_kind_artifact,
    _load_kind_schema,
    _load_settings_template,
    _parse_selection,
)


# ─── Helpers ──────────────────────────────────────────────────────────────


def init_noninteractive(tmp_path, monkeypatch, extra_args=None):
    """Run init with all three flags so it runs non-interactively."""
    monkeypatch.chdir(tmp_path)
    args = ["init", "--template", "standard", "--kinds", "task,note,spec", "--agents", "none"]
    if extra_args:
        args.extend(extra_args)
    main(args)


def run_init(*args, expected_exit=0):
    """Call main(["init", *args]), assert SystemExit code if non-zero."""
    if expected_exit == 0:
        main(["init", *args])
    else:
        with pytest.raises(SystemExit) as exc:
            main(["init", *args])
        assert exc.value.code == expected_exit


# ─── §18.1 Bundled-template loading ──────────────────────────────────────


class TestBundledTemplateLoading:
    def test_18_1_1_load_settings_minimal(self):
        text = _load_settings_template("minimal")
        assert text.strip()
        assert "layout_version" in text

    def test_18_1_1_load_settings_standard(self):
        text = _load_settings_template("standard")
        assert text.strip()
        assert "default_views" in text

    def test_18_1_2_discover_kinds(self):
        kinds = _discover_kinds()
        assert kinds == ["agent", "note", "research", "spec", "task"]

    def test_18_1_3_discover_agents(self):
        agents = _discover_agents()
        assert agents == [
            "architect",
            "author",
            "developer",
            "devrel",
            "product-manager",
            "project-manager",
            "researcher",
            "security-engineer",
            "technical-writer",
        ]

    def test_18_1_4_unknown_tier_raises(self):
        with pytest.raises(FileNotFoundError, match="template not found"):
            _load_settings_template("nonexistent")

    def test_18_1_load_kind_schema(self):
        for kind in ("task", "note", "spec", "research", "agent"):
            text = _load_kind_schema(kind)
            schema = json.loads(text)
            assert "x-dir" in schema

    def test_18_1_load_kind_artifact(self):
        for kind in ("task", "note", "spec", "research", "agent"):
            text = _load_kind_artifact(kind)
            assert text.strip()

    def test_18_1_load_agent_template(self):
        for name in ("architect", "developer", "author", "researcher", "technical-writer"):
            text = _load_agent_template(name)
            assert "kind: agent" in text

    @pytest.mark.parametrize("tier", ["minimal", "standard"])
    def test_18_1_template_views_parse_with_intact_columns(self, tier):
        """Regression: every view's `columns` must survive YAML parsing.

        Flow-mapping syntax like ``{ columns: a,b,c, filters: ... }`` silently
        drops every comma-separated token after the first because YAML treats
        the comma as a key separator.  All ``columns`` values must be quoted.
        """
        import yaml

        text = _load_settings_template(tier)
        # Stub interpolation placeholders so the YAML is loadable.
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
            # Detect the comma-eats-columns bug: any view that has unexpected
            # bare keys (e.g. 'description', 'assignee') in the same flow map
            # means YAML split them out as keys with null values.
            extra_keys = set(view.keys()) - {"columns", "filters", "sort"}
            assert not extra_keys, (
                f"view '{name}' has unexpected keys {extra_keys}; "
                f"this means an unquoted CSV columns value leaked tokens "
                f"into the surrounding flow mapping. Quote it: "
                f"`columns: \"a,b,c\"`."
            )


# ─── §18.2 Variable interpolation ────────────────────────────────────────


class TestVariableInterpolation:
    def test_18_2_1_project_name_from_claude_md(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("# My Cool Project\n\nSome text.\n")
        assert _get_project_name(tmp_path) == "My Cool Project"

    def test_18_2_1_artifacts_os_skipped(self, tmp_path):
        """CLAUDE.md with 'Artifacts OS' as H1 falls back to dir name."""
        (tmp_path / "CLAUDE.md").write_text("# Artifacts OS\n")
        assert _get_project_name(tmp_path) == tmp_path.name

    def test_18_2_1_open_station_skipped(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("# Open Station\n")
        assert _get_project_name(tmp_path) == tmp_path.name

    def test_18_2_2_falls_back_to_dir_name(self, tmp_path):
        project = tmp_path / "cool-project"
        project.mkdir()
        assert _get_project_name(project) == "cool-project"

    def test_18_2_2_no_claude_md(self, tmp_path):
        assert _get_project_name(tmp_path) == tmp_path.name

    def test_18_2_3_alias_strips_and_lowercases(self):
        # "My-Project" → first word = "My-Project" → lower alphanumeric = "myproject" → 8 = "myprojec"
        assert _derive_project_alias("My-Project") == "myprojec"
        # "artifacts-os" → first word = "artifacts-os" → lower alnum = "artifactsos" → 8 = "artifact"
        assert _derive_project_alias("artifacts-os") == "artifact"
        # "hello world" → first word = "hello" → "hello"
        assert _derive_project_alias("hello world") == "hello"

    def test_18_2_3_alias_truncates_at_8(self):
        assert _derive_project_alias("toolongname") == "toolongn"

    def test_18_2_3_alias_alphanumeric_only(self):
        # "my_proj!" → lower alphanumeric = "myproj"
        assert _derive_project_alias("my_proj!") == "myproj"

    def test_18_2_4_created_is_today(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main(["init", "--template", "minimal", "--kinds", "none", "--agents", "none"])
        text = (tmp_path / "artifacts" / "artifacts.yaml").read_text()
        import datetime
        assert datetime.date.today().isoformat() in text

    def test_18_2_5_unknown_token_passes_through(self):
        content = "hello {{unknown_var}} world {{project_name}}"
        result = _interpolate(content, "MyProj", "myproj", "2026-01-01")
        assert "{{unknown_var}}" in result
        assert "MyProj" in result


# ─── §18.3 Step skipping and flag/prompt precedence ──────────────────────


class TestStepSkipping:
    def test_18_3_1_all_flags_non_interactive(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # All three flags: no prompts needed even if not TTY
        main([
            "init",
            "--template", "minimal",
            "--kinds", "task",
            "--agents", "none",
        ])
        assert (tmp_path / "artifacts" / "artifacts.yaml").is_file()
        text = (tmp_path / "artifacts" / "artifacts.yaml").read_text()
        assert "layout_version" in text

    def test_18_3_3_yes_flag_uses_defaults(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main(["init", "-y"])
        assert (tmp_path / "artifacts" / "artifacts.yaml").is_file()
        # standard is the default tier — check for its marker
        text = (tmp_path / "artifacts" / "artifacts.yaml").read_text()
        assert "default_views" in text

    def test_18_3_3_yes_with_template_override(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main(["init", "-y", "--template", "minimal"])
        text = (tmp_path / "artifacts" / "artifacts.yaml").read_text()
        # minimal omits the standard-tier 'default_views' / per-type slices
        assert "default_views" not in text
        assert "features" not in text
        # default kinds should be installed
        assert (tmp_path / "artifacts" / "kinds" / "task.json").is_file()

    def test_18_3_3_yes_defaults_install_task_note_spec(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main(["init", "-y"])
        for kind in ("task", "note", "spec"):
            assert (tmp_path / "artifacts" / "kinds" / f"{kind}.json").is_file()
        # research and agent NOT installed by default
        assert not (tmp_path / "artifacts" / "kinds" / "research.json").is_file()
        assert not (tmp_path / "artifacts" / "kinds" / "agent.json").is_file()

    def test_18_3_4_non_tty_no_flags_exits_2(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # In test context stdin is not a TTY; no -y or all three flags
        with pytest.raises(SystemExit) as exc:
            main(["init"])
        assert exc.value.code == 2

    def test_18_3_4_non_tty_partial_flags_exits_2(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            main(["init", "--template", "minimal"])
        assert exc.value.code == 2


# ─── §18.4 Multi-select parsing ───────────────────────────────────────────


class TestMultiSelectParsing:
    OPTIONS = ["task", "note", "spec", "research", "agent"]
    DEFAULTS = ["task", "note", "spec"]

    def test_18_4_1_empty_returns_defaults(self):
        assert _parse_selection("", self.OPTIONS, self.DEFAULTS) == ["task", "note", "spec"]

    def test_18_4_2_star_returns_all(self):
        assert _parse_selection("*", self.OPTIONS, self.DEFAULTS) == list(self.OPTIONS)

    def test_18_4_3_dash_returns_none(self):
        assert _parse_selection("-", self.OPTIONS, self.DEFAULTS) == []

    def test_18_4_4_numbers(self):
        assert _parse_selection("1,3,5", self.OPTIONS, self.DEFAULTS) == [
            "task", "spec", "agent"
        ]

    def test_18_4_5_names(self):
        assert _parse_selection("task,spec", self.OPTIONS, self.DEFAULTS) == [
            "task", "spec"
        ]

    def test_18_4_6_mixed_numbers_and_names(self):
        assert _parse_selection("1,spec", self.OPTIONS, self.DEFAULTS) == [
            "task", "spec"
        ]

    def test_18_4_7_out_of_range_returns_none(self, capsys):
        result = _parse_selection("7", self.OPTIONS, self.DEFAULTS)
        assert result is None
        assert "out of range" in capsys.readouterr().err

    def test_18_4_8_unknown_name_returns_none(self, capsys):
        result = _parse_selection("bogus", self.OPTIONS, self.DEFAULTS)
        assert result is None
        assert "not a valid choice" in capsys.readouterr().err

    def test_18_4_9_duplicates_deduped(self):
        result = _parse_selection("1,1,task", self.OPTIONS, self.DEFAULTS)
        assert result == ["task"]


# ─── §18.5 Existing-file guard ────────────────────────────────────────────


class TestExistingFileGuard:
    def test_18_5_1_refuses_if_already_initialised(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main(["init", "--template", "minimal", "--kinds", "none", "--agents", "none"])
        with pytest.raises(SystemExit) as exc:
            main(["init", "--template", "minimal", "--kinds", "none", "--agents", "none"])
        assert exc.value.code == 2

    def test_18_5_1_error_message(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        main(["init", "--template", "minimal", "--kinds", "none", "--agents", "none"])
        capsys.readouterr()
        with pytest.raises(SystemExit):
            main(["init", "--template", "minimal", "--kinds", "none", "--agents", "none"])
        assert "already initialised" in capsys.readouterr().err

    def test_18_5_2_force_overwrites(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main(["init", "--template", "minimal", "--kinds", "none", "--agents", "none"])
        # Write something custom to check it gets overwritten
        yaml_path = tmp_path / "artifacts" / "artifacts.yaml"
        yaml_path.write_text("# custom\n")
        main([
            "init",
            "--template", "standard",
            "--kinds", "task",
            "--agents", "none",
            "--force",
        ])
        text = yaml_path.read_text()
        assert "default_views" in text  # standard tier content

    def test_18_5_3_force_per_file_only_touches_selected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # First init with task kind
        main([
            "init",
            "--template", "minimal",
            "--kinds", "task",
            "--agents", "none",
        ])
        extra = tmp_path / "artifacts" / "extra.txt"
        extra.write_text("untouched")
        # Re-init with force — extra.txt should be untouched
        main([
            "init",
            "--template", "minimal",
            "--kinds", "task",
            "--agents", "none",
            "--force",
        ])
        assert extra.read_text() == "untouched"


# ─── §18.6 Agent ↔ agent-kind coupling ────────────────────────────────────


class TestAgentKindCoupling:
    def test_18_6_1_agent_auto_included(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        main([
            "init",
            "--template", "standard",
            "--kinds", "task,note",
            "--agents", "architect",
        ])
        out = capsys.readouterr().out
        assert "agent kind auto-included for selected agents" in out
        # agent kind files should be present
        assert (tmp_path / "artifacts" / "kinds" / "agent.json").is_file()
        assert (tmp_path / "artifacts" / "kinds" / "agent" / "ARTIFACT.md").is_file()

    def test_18_6_2_no_agents_no_auto_include(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main([
            "init",
            "--template", "standard",
            "--kinds", "task",
            "--agents", "none",
        ])
        assert not (tmp_path / "artifacts" / "kinds" / "agent.json").is_file()

    def test_18_6_3_multiple_agents_single_agent_kind(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        main([
            "init",
            "--template", "standard",
            "--kinds", "task",
            "--agents", "architect,developer",
        ])
        # agent kind installed once
        agent_json = tmp_path / "artifacts" / "kinds" / "agent.json"
        assert agent_json.is_file()
        # verify no duplicate install (just check it parses as JSON)
        schema = json.loads(agent_json.read_text())
        assert schema["x-dir"] == "agents"

    def test_18_6_1_agent_already_in_kinds_no_duplicate(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        main([
            "init",
            "--template", "standard",
            "--kinds", "task,agent",
            "--agents", "architect",
        ])
        out = capsys.readouterr().out
        # auto-include message should NOT appear since agent was already requested
        assert "agent kind auto-included" not in out


# ─── §18.7 Rendered settings parse correctly ────────────────────────────


class TestRenderedSettings:
    @pytest.mark.parametrize("tier", ["minimal", "standard"])
    def test_18_7_1_rendered_yaml_parses_with_intact_columns(
        self, tier, tmp_path, monkeypatch
    ):
        """Regression: the rendered settings file must round-trip through
        PyYAML with all column tokens preserved (not eaten by flow-mapping
        comma syntax).
        """
        import yaml

        monkeypatch.chdir(tmp_path)
        main([
            "init",
            "--template", tier,
            "--kinds", "task",
            "--agents", "none",
        ])
        text = (tmp_path / "artifacts" / "artifacts.yaml").read_text()
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


# ─── §18.8 Dry-run ────────────────────────────────────────────────────────


class TestDryRun:
    def test_18_8_1_no_files_written(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main([
            "init",
            "--template", "standard",
            "--kinds", "task",
            "--agents", "none",
            "--dry-run",
        ])
        # No files should have been created
        assert not (tmp_path / "artifacts").exists()

    def test_18_8_2_output_prefixed_would(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        main([
            "init",
            "--template", "minimal",
            "--kinds", "task",
            "--agents", "none",
            "--dry-run",
        ])
        out = capsys.readouterr().out
        # Every action line should be prefixed [would]
        action_lines = [
            line for line in out.splitlines() if line.strip().startswith("[would]")
        ]
        assert len(action_lines) > 0

    def test_18_8_3_exit_0_even_with_preexisting_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # init once to create files
        main([
            "init",
            "--template", "minimal",
            "--kinds", "task",
            "--agents", "none",
        ])
        # dry-run on already-inited vault with --force: should exit 0
        main([
            "init",
            "--template", "minimal",
            "--kinds", "task",
            "--agents", "none",
            "--dry-run",
            "--force",
        ])


# ─── §18.9 Error handling ─────────────────────────────────────────────────


class TestErrorHandling:
    def test_18_9_1_write_failure_partial_success(self, tmp_path, monkeypatch):
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
            main([
                "init",
                "--template", "minimal",
                "--kinds", "task,note",
                "--agents", "none",
            ])
        assert exc.value.code == 1

    def test_18_9_2_missing_bundled_template(self, monkeypatch, tmp_path):
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
            main([
                "init",
                "--template", "standard",
                "--kinds", "none",
                "--agents", "none",
            ])
        assert exc.value.code == 2

    def test_18_9_3_unknown_template_flag(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # argparse handles --template validation → exits 2
        with pytest.raises(SystemExit) as exc:
            main(["init", "--template", "ultra"])
        assert exc.value.code == 2

    def test_18_9_4_unknown_kinds_flag(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            main([
                "init",
                "--template", "standard",
                "--kinds", "nonexistent",
                "--agents", "none",
            ])
        assert exc.value.code == 2
        assert "nonexistent" in capsys.readouterr().err


# ─── §18.10 Backwards compatibility ──────────────────────────────────────


class TestBackwardsCompat:
    def test_18_10_1_refuse_already_init_without_force(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        main([
            "init",
            "--template", "minimal",
            "--kinds", "none",
            "--agents", "none",
        ])
        capsys.readouterr()
        with pytest.raises(SystemExit) as exc:
            main([
                "init",
                "--template", "minimal",
                "--kinds", "none",
                "--agents", "none",
            ])
        assert exc.value.code == 2
        assert "already initialised" in capsys.readouterr().err

    def test_18_10_2_openstation_compat_creates_symlink(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main([
            "init",
            "--template", "minimal",
            "--kinds", "none",
            "--agents", "none",
            "--openstation-compat",
        ])
        symlink = tmp_path / "openstation"
        assert symlink.is_symlink()
        assert symlink.resolve() == (tmp_path / "artifacts").resolve()

    def test_18_10_2_no_symlink_without_flag(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main([
            "init",
            "--template", "minimal",
            "--kinds", "none",
            "--agents", "none",
        ])
        assert not (tmp_path / "openstation").exists()

    def test_18_10_3_pre_registry_flag_set(self):
        """init runs without a registry (pre_registry=True)."""
        import argparse
        from artifacts_os.cli.commands.init import register

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="cmd")
        register(sub)
        args = parser.parse_args(
            ["init", "--template", "minimal", "--kinds", "none", "--agents", "none"]
        )
        assert getattr(args, "_pre_registry", False) is True


# ─── Integration: full vault structure ────────────────────────────────────


class TestFullVaultStructure:
    def test_kinds_and_artifact_md_installed(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main([
            "init",
            "--template", "standard",
            "--kinds", "task,note,spec",
            "--agents", "none",
        ])
        for kind in ("task", "note", "spec"):
            assert (tmp_path / "artifacts" / "kinds" / f"{kind}.json").is_file()
            assert (tmp_path / "artifacts" / "kinds" / kind / "ARTIFACT.md").is_file()

    def test_gitkeep_created_for_each_kind(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main([
            "init",
            "--template", "minimal",
            "--kinds", "task,note,spec",
            "--agents", "none",
        ])
        assert (tmp_path / "artifacts" / "tasks" / ".gitkeep").is_file()
        assert (tmp_path / "artifacts" / "notes" / ".gitkeep").is_file()
        assert (tmp_path / "artifacts" / "specs" / ".gitkeep").is_file()

    def test_agents_installed(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main([
            "init",
            "--template", "standard",
            "--kinds", "agent",
            "--agents", "architect,developer",
        ])
        assert (tmp_path / "artifacts" / "agents" / "architect.md").is_file()
        assert (tmp_path / "artifacts" / "agents" / "developer.md").is_file()
        assert not (tmp_path / "artifacts" / "agents" / "author.md").is_file()

    def test_all_agents_flag(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main([
            "init",
            "--template", "standard",
            "--kinds", "task",
            "--agents", "all",
        ])
        for name in _discover_agents():
            assert (tmp_path / "artifacts" / "agents" / f"{name}.md").is_file()

    def test_project_name_in_yaml(self, tmp_path, monkeypatch):
        project = tmp_path / "my-awesome-project"
        project.mkdir()
        monkeypatch.chdir(project)
        main([
            "init",
            "--template", "minimal",
            "--kinds", "none",
            "--agents", "none",
        ])
        text = (project / "artifacts" / "artifacts.yaml").read_text()
        assert "my-awesome-project" in text

    def test_project_name_from_claude_md(self, tmp_path, monkeypatch):
        (tmp_path / "CLAUDE.md").write_text("# My Fancy Project\n\ndetails.\n")
        monkeypatch.chdir(tmp_path)
        main([
            "init",
            "--template", "minimal",
            "--kinds", "none",
            "--agents", "none",
        ])
        text = (tmp_path / "artifacts" / "artifacts.yaml").read_text()
        assert "My Fancy Project" in text

    def test_kind_json_valid(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        main([
            "init",
            "--template", "minimal",
            "--kinds", "task,note,spec,research,agent",
            "--agents", "none",
        ])
        kinds_dir = tmp_path / "artifacts" / "kinds"
        for kind in ("task", "note", "spec", "research", "agent"):
            schema = json.loads((kinds_dir / f"{kind}.json").read_text())
            assert "x-dir" in schema

    def test_target_directory_argument(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        target = tmp_path / "sub"
        target.mkdir()
        main([
            "init", str(target),
            "--template", "minimal",
            "--kinds", "task",
            "--agents", "none",
        ])
        assert (target / "artifacts" / "artifacts.yaml").is_file()

    def test_init_then_list_works(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
        main([
            "init",
            "--template", "standard",
            "--kinds", "task,spec",
            "--agents", "none",
        ])
        capsys.readouterr()
        main(["list", "-q"])
        out = capsys.readouterr().out
        assert out == ""  # empty vault
