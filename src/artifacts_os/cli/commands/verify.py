"""cli verify command — check artifact verification checklists."""

import json
import re

from rich.console import Console

from artifacts_os.core import get, list_artifacts, Registry
from artifacts_os.core.models import Artifact, ArtifactMeta

_CHECKBOX_RE = re.compile(r"^\s*-\s*\[([ xX])\]\s*(.+)$", re.MULTILINE)


def _parse_checklist(body: str) -> list[dict]:
    """Extract checklist items from markdown body."""
    items = []
    for m in _CHECKBOX_RE.finditer(body):
        checked = m.group(1).strip().lower() == "x"
        text = m.group(2).strip()
        items.append({"text": text, "checked": checked})
    return items


def _verify_artifact(artifact: Artifact) -> dict:
    items = _parse_checklist(artifact.body)
    total = len(items)
    done = sum(1 for i in items if i["checked"])
    return {
        # Use path stem — the canonical identifier — rather than the
        # slug-only frontmatter `name`.
        "name": artifact.path.stem,
        "kind": artifact.kind,
        "total": total,
        "done": done,
        "complete": done == total and total > 0,
        "items": items,
    }


def register(subparsers) -> None:
    p = subparsers.add_parser("verify", help="check artifact verification checklist")
    p.add_argument("ref", nargs="?", help="artifact reference (omit to use --all)")
    p.add_argument("--kind", "-k", help="filter by kind (used with --all)")
    p.add_argument("--all", action="store_true", dest="all_artifacts",
                   help="check all artifacts")
    p.add_argument("-j", "--json", action="store_true", dest="json_out",
                   help="JSON output")
    p.set_defaults(func=run)


def run(args, registry: Registry) -> int:
    console = Console()

    if args.ref:
        artifact = get(registry, args.ref, kind=args.kind or None)
        result = _verify_artifact(artifact)

        if args.json_out:
            print(json.dumps(result, default=str))
        else:
            _print_result(console, result)
        return 0 if result["complete"] else 1

    # --all or no ref: list artifacts
    metas: list[ArtifactMeta] = list_artifacts(
        registry, kind=args.kind or None
    )

    results = []
    for meta in metas:
        artifact = get(registry, meta.path.stem, kind=meta.kind or None)
        r = _verify_artifact(artifact)
        if r["total"] > 0:
            results.append(r)

    if args.json_out:
        print(json.dumps(results, default=str))
    else:
        for r in results:
            _print_result(console, r)

    incomplete = [r for r in results if not r["complete"]]
    return 0 if not incomplete else 1


def _print_result(console: Console, result: dict) -> None:
    status = "✓" if result["complete"] else "✗"
    console.print(
        f"[bold]{result['name']}[/bold] {status} "
        f"({result['done']}/{result['total']})"
    )
    for item in result["items"]:
        mark = "[x]" if item["checked"] else "[ ]"
        console.print(f"  {mark} {item['text']}")
