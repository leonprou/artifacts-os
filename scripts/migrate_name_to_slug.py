#!/usr/bin/env python3
"""One-shot migration: rewrite `name: <id>-<slug>` to `name: <slug>`.

Walks artifacts/{tasks,specs,research,...} for numbered kinds and strips
the leading `<id>-` prefix from the persisted `name` frontmatter field.
Non-numbered kinds (e.g. `agents`) are left alone — their `name` is
already slug-only.

Idempotent: rerunning is a no-op once every artifact is migrated.

Usage::

    python scripts/migrate_name_to_slug.py             # apply in CWD vault
    python scripts/migrate_name_to_slug.py --dry-run   # preview changes
    python scripts/migrate_name_to_slug.py --root PATH # explicit vault root

Spec: t0037-redefine-name-field-as-slug
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from artifacts_os.core import frontmatter as _frontmatter
from artifacts_os.core.registry import Registry
from artifacts_os.core.vault import find_vault_root


def _iter_numbered_artifacts(root: Path, registry: Registry):
    for kd in registry.all():
        if not kd.numbered:
            continue
        subdir = root / "artifacts" / kd.dir
        if not subdir.is_dir():
            continue
        for path in sorted(subdir.glob("*.md")):
            yield kd, path


def migrate(root: Path, *, dry_run: bool = False) -> int:
    registry = Registry([], root=root)
    changed = 0
    for kd, path in _iter_numbered_artifacts(root, registry):
        text = path.read_text(encoding="utf-8")
        meta, body = _frontmatter.parse(text)

        aid = meta.get("id", "")
        name = meta.get("name", "")
        if not aid or not name:
            continue

        prefix = f"{aid}-"
        if not name.startswith(prefix):
            continue  # already migrated or unexpected shape

        new_name = name[len(prefix):]
        if not new_name:
            print(f"[skip] {path}: stripping prefix yields empty slug")
            continue

        new_meta = {**meta, "name": new_name}
        new_text = _frontmatter.dump(new_meta, body)

        action = "[dry-run]" if dry_run else "[write]"
        print(f"{action} {path}: name {name!r} -> {new_name!r}")
        if not dry_run:
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(new_text, encoding="utf-8")
            tmp.replace(path)
        changed += 1
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None,
                        help="vault root (default: walk up from CWD)")
    parser.add_argument("--dry-run", action="store_true",
                        help="preview changes without writing")
    args = parser.parse_args(argv)

    root = args.root or find_vault_root(Path.cwd())
    if root is None:
        print("error: not inside an artifacts-os vault", file=sys.stderr)
        return 2

    changed = migrate(root, dry_run=args.dry_run)
    print(f"\n{changed} file(s) {'would be ' if args.dry_run else ''}migrated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
