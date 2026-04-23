"""cli validate command — check artifact frontmatter correctness."""

import json
import sys

from rich.console import Console

from artifacts_os.core import get, list_artifacts, update, Registry
from artifacts_os.core.validate import validate_one, validate_many, ValidationResult


def register(subparsers) -> None:
    p = subparsers.add_parser("validate", help="validate artifact frontmatter")
    p.add_argument("ref", nargs="?", help="artifact reference")
    p.add_argument("--kind", "-k", help="filter by kind")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--fix", action="store_true",
                      help="auto-correct fixable issues")
    mode.add_argument("--dry-run", action="store_true",
                      help="show fixes without writing")
    p.add_argument("--all", action="store_true", dest="all_artifacts",
                   help="validate all artifacts (default when no ref)")
    p.add_argument("-j", "--json", action="store_true", dest="json_out",
                   help="JSON output")
    p.set_defaults(func=run)


def run(args, registry: Registry) -> int:
    if args.ref:
        meta = get(registry, args.ref, kind=args.kind or None)
        results = [validate_one(meta, registry)]
    else:
        metas = list_artifacts(registry, kind=args.kind or None)
        results = validate_many(metas, registry)

    if args.fix or args.dry_run:
        _apply_fixes(args, registry, results)

    if args.json_out:
        _print_json(results)
    else:
        _print_table(results)

    has_errors = any(r.errors for r in results)
    return 2 if has_errors else 0


def _apply_fixes(args, registry: Registry, results: list[ValidationResult]) -> None:
    """Apply or preview fixes for fixable issues."""
    console = Console()
    for result in results:
        fixable = [i for i in result.issues if i.fixable]
        if not fixable:
            continue
        fields: dict = {}
        for issue in fixable:
            if issue.field == "status":
                kind_def = registry.get(result.kind)
                if kind_def.statuses:
                    new_val = kind_def.statuses[0]
                    fields["status"] = new_val
                    if args.dry_run:
                        console.print(
                            f"[dry-run] {result.name}: would set status → {new_val}"
                        )
        if fields and not args.dry_run:
            update(registry, result.name, fields=fields)
            # Update the result's issues to remove fixed ones
            for issue in fixable:
                if issue.field in fields:
                    result.issues.remove(issue)


def _print_table(results: list[ValidationResult]) -> None:
    """Print human-readable table output."""
    console = Console(stderr=False)
    error_count = sum(len(r.errors) for r in results)
    warning_count = sum(len(r.warnings) for r in results)
    artifacts_with_issues = [r for r in results if r.issues]

    if error_count or warning_count:
        console.print(
            f"validate — {error_count} error(s), {warning_count} warning(s) "
            f"across {len(results)} artifact(s)\n"
        )

    for result in artifacts_with_issues:
        console.print(f"  [bold]{result.kind} / {result.name}[/bold]")
        for issue in result.issues:
            marker = "E" if issue.severity == "error" else "W"
            fixable_tag = "  [fixable]" if issue.fixable else ""
            console.print(
                f"    {marker}  {issue.field:<8} {issue.message}{fixable_tag}"
            )
        console.print()

    # Summary line
    total = len(results)
    valid_count = sum(1 for r in results if r.valid)
    error_arts = sum(1 for r in results if r.errors)
    warn_arts = sum(1 for r in results if r.warnings and not r.errors)
    console.print(
        f"{total} artifact(s) checked — {valid_count} valid, "
        f"{error_arts} with errors, {warn_arts} with warnings"
    )


def _print_json(results: list[ValidationResult]) -> None:
    """Print JSON output. Only includes artifacts with issues."""
    output = []
    for result in results:
        if not result.issues:
            continue
        output.append({
            "name": result.name,
            "kind": result.kind,
            "issues": [
                {
                    "field": issue.field,
                    "message": issue.message,
                    "fixable": issue.fixable,
                    "severity": issue.severity,
                }
                for issue in result.issues
            ],
        })
    print(json.dumps(output))
