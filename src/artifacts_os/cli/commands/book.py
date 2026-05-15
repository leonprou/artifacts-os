"""cli book commands — distro-backed artifact distribution.

Three verbs under the ``book`` namespace:

    artifacts book list                [--json]
    artifacts book show <name>         [--json]
    artifacts book pull <name>         [--json] [--dry-run]

``book`` is a deliberate exception to the flat-verb convention: it
introduces a resource namespace so the three operations read as natural
sentences.  ``--json`` applies to all three verbs; ``--dry-run`` is
exclusive to ``pull``.

Exit codes (command-specific — see §5.5):
    0  success
    1  runtime error (clone failed / manifest invalid / unknown book / write failed /
                      dest escapes vault / removed v1 `type:` field)
    2  usage error (bad flag, missing argument)
    3  vault not initialised (artifacts.yaml not found)
    4  artbook.distro_url missing or empty in artifacts.yaml

Spec: s0029-artbook-mvp-distribution-model §5, D24, D25
"""

from __future__ import annotations

import dataclasses
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.markup import escape as _markup_escape

import yaml

import artifacts_os.artbook as artbook
import artifacts_os.views as views
from artifacts_os.artbook import (
    ArtbookSettings,
    FetchError,
    ManifestError,
    UnknownBookError,
)
from artifacts_os.artbook.errors import ArtbookError
from artifacts_os.artbook.fetch import get_short_sha
from artifacts_os.artbook.manifest import load_manifest
from artifacts_os.artbook.placement import _select_files, destination_for
from artifacts_os.core import find_vault_root
from artifacts_os.core.models import ItemMeta
from artifacts_os.views._views import FieldSpec


# ---------------------------------------------------------------------------
# ItemMeta subclasses for table rendering (spec §5.1.3)
# ---------------------------------------------------------------------------


@dataclass
class BookRow(ItemMeta):
    """One book entry — rendered by ``book list``."""

    name: str
    src: str
    dest: str
    description: str = ""


@dataclass
class BookContentRow(ItemMeta):
    """One file under a book's src — rendered by ``book show``."""

    filename: str


@dataclass
class WriteActionRow(ItemMeta):
    """One planned or completed write — rendered by ``book pull``."""

    action: str       # "write" | "overwrite" | "[would] write" | "[would] overwrite"
    destination: str
    was_symlink: bool = False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_CONSOLE = Console()


def _err(cause: str, hint: str = "") -> None:
    """Print a two-line error message to stderr (spec §5.6)."""
    msg = f"error: {cause}"
    if hint:
        msg += f"\n       {hint}"
    print(msg, file=sys.stderr)


def _load_vault_and_raw() -> tuple[Path | None, dict]:
    """Return (vault_root, raw_yaml) or (None, {}) when vault is not found."""
    root = find_vault_root()
    if root is None:
        _err(
            "not in an artifacts-os vault (no artifacts.yaml found walking up from the current directory).",
            "Run `artifacts init` to create one, or cd into an existing vault.",
        )
        return None, {}

    settings_path = root / "artifacts.yaml"
    try:
        raw = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
    except Exception:
        raw = {}
    return root, raw


def _artbook_settings_from_raw(raw: dict) -> ArtbookSettings:
    """Build ArtbookSettings directly from the raw artifacts.yaml dict."""
    artbook_section = raw.get("artbook", {}) or {}
    return ArtbookSettings(distro_url=artbook_section.get("distro_url") or None)


def _book_header(manifest, distro_url: str, sha: str) -> str:
    """Single-line distro header for list/show output."""
    desc = f" — {manifest.description}" if manifest.description else ""
    sha_str = f" @ {sha}" if sha else ""
    return (
        f"[bold]Distro:[/bold] {manifest.name}{desc}\n"
        f"[bold]URL:[/bold]    {distro_url}{sha_str}"
    )


# ---------------------------------------------------------------------------
# Verb: list
# ---------------------------------------------------------------------------


def _render_book_list(manifest, distro_url: str, sha: str) -> None:
    """Render the book list table to the console (shared by local and remote paths)."""
    rows = [
        BookRow(
            name=b.name,
            src=b.src,
            dest=b.dest,
            description=b.description or "",
        )
        for b in manifest.books
    ]
    columns = [
        FieldSpec(key="name", fmt=None, label="Name"),
        FieldSpec(key="src", fmt=None, label="Source"),
        FieldSpec(key="dest", fmt=None, label="Destination"),
        FieldSpec(key="description", fmt=None, label="Description"),
    ]
    _CONSOLE.print(_book_header(manifest, distro_url, sha))
    _CONSOLE.print()
    _CONSOLE.print(views.render_table(rows, columns))
    n = len(rows)
    _CONSOLE.print(f"\n{n} book{'s' if n != 1 else ''}.")


def _run_list(args, root: Path, raw: dict) -> int:
    # D23 — local-manifest auto-detect: if artbook.yaml is in the vault root
    # and --remote is not set, read it in place without cloning.
    local_manifest_path = root / "artbook.yaml"
    if not getattr(args, "remote", False) and local_manifest_path.is_file():
        try:
            manifest = load_manifest(root)
        except ManifestError as exc:
            _err(str(exc))
            return 1

        if args.json_out:
            print(json.dumps({
                "distro": {
                    "name": manifest.name,
                    "description": manifest.description,
                    "url": None,
                    "sha": None,
                    "local": True,
                },
                "books": [dataclasses.asdict(b) for b in manifest.books],
            }, ensure_ascii=False))
            return 0

        _render_book_list(manifest, distro_url="(local)", sha="")
        return 0

    arts = _artbook_settings_from_raw(raw)
    if not arts.distro_url:
        _err(
            "artbook.distro_url not configured in artifacts.yaml",
            "Add `artbook.distro_url: <git-url>` to artifacts.yaml.",
        )
        return 4

    try:
        with tempfile.TemporaryDirectory(prefix="artbook-list-") as td:
            clone_root = Path(td) / "clone"
            manifest, _ = artbook.read_manifest(arts.distro_url, clone_into=clone_root)
            sha = get_short_sha(clone_root)

            if args.json_out:
                print(json.dumps({
                    "distro": {
                        "name": manifest.name,
                        "description": manifest.description,
                        "url": arts.distro_url,
                        "sha": sha,
                    },
                    "books": [dataclasses.asdict(b) for b in manifest.books],
                }, ensure_ascii=False))
                return 0

            _render_book_list(manifest, distro_url=arts.distro_url, sha=sha)

    except FetchError as exc:
        _err(
            f"git clone failed (exit {exc.returncode})",
            f"URL: {arts.distro_url}\nstderr: {exc.stderr.strip()}",
        )
        return 1
    except ManifestError as exc:
        _err(str(exc))
        return 1
    except ArtbookError as exc:
        _err(str(exc))
        return 1

    return 0


# ---------------------------------------------------------------------------
# Verb: show
# ---------------------------------------------------------------------------


def _render_book_show(
    book,
    manifest,
    src_dir: Path,
    root: Path,
    distro_url: str,
    sha: str,
    json_out: bool,
) -> int:
    """Render `book show` output (shared by local and remote paths).

    Returns 0 on success, 1 on error.
    """
    dest = destination_for(root, book)
    dest_rel = dest.relative_to(root)

    try:
        src_files = _select_files(src_dir, book)
    except (ManifestError, ArtbookError) as exc:
        _err(str(exc))
        return 1
    filenames = [f.name for f in src_files]

    if json_out:
        distro_info: dict = {"name": manifest.name}
        if distro_url:
            distro_info["url"] = distro_url
            distro_info["sha"] = sha
        else:
            distro_info["url"] = None
            distro_info["sha"] = None
            distro_info["local"] = True
        print(json.dumps({
            "book": dataclasses.asdict(book),
            "distro": distro_info,
            "contents": filenames,
        }, ensure_ascii=False))
        return 0

    desc = book.description or ""
    _CONSOLE.print(f"[bold]Book:[/bold]        {book.name}")
    _CONSOLE.print(f"[bold]Source:[/bold]      {book.src}")
    _CONSOLE.print(f"[bold]Destination:[/bold] {dest_rel}/")
    _CONSOLE.print(f"[bold]Description:[/bold] {desc}")
    _CONSOLE.print()
    _CONSOLE.print(f"[bold]Distro:[/bold]      {manifest.name}")
    if distro_url:
        _CONSOLE.print(f"[bold]URL:[/bold]         {distro_url} @ {sha}")
    else:
        _CONSOLE.print("[bold]URL:[/bold]         (local)")
    _CONSOLE.print()
    n = len(filenames)
    _CONSOLE.print(f"Contents ({n} file{'s' if n != 1 else ''}):")
    for name in filenames:
        _CONSOLE.print(f"  {name}")
    return 0


def _run_show(args, root: Path, raw: dict) -> int:
    book_name: str = args.name

    # D23 — local-manifest auto-detect: if artbook.yaml is in the vault root
    # and --remote is not set, read it in place without cloning.
    local_manifest_path = root / "artbook.yaml"
    if not getattr(args, "remote", False) and local_manifest_path.is_file():
        try:
            manifest = load_manifest(root)
        except ManifestError as exc:
            _err(str(exc))
            return 1

        try:
            book = artbook.find_book(manifest, book_name)
        except UnknownBookError:
            available = ", ".join(b.name for b in manifest.books)
            _err(
                f"book '{book_name}' not found in distro '{manifest.name}'",
                f"Available books: {available}.",
            )
            return 1

        src_dir = root / book.src
        return _render_book_show(
            book, manifest, src_dir, root,
            distro_url="", sha="", json_out=args.json_out,
        )

    arts = _artbook_settings_from_raw(raw)
    if not arts.distro_url:
        _err(
            "artbook.distro_url not configured in artifacts.yaml",
            "Add `artbook.distro_url: <git-url>` to artifacts.yaml.",
        )
        return 4

    try:
        with tempfile.TemporaryDirectory(prefix="artbook-show-") as td:
            clone_root = Path(td) / "clone"
            manifest, _ = artbook.read_manifest(arts.distro_url, clone_into=clone_root)
            sha = get_short_sha(clone_root)

            try:
                book = artbook.find_book(manifest, book_name)
            except UnknownBookError:
                available = ", ".join(b.name for b in manifest.books)
                _err(
                    f"book '{book_name}' not found in distro '{manifest.name}'",
                    f"Available books: {available}.",
                )
                return 1

            src_dir = clone_root / book.src
            return _render_book_show(
                book, manifest, src_dir, root,
                distro_url=arts.distro_url, sha=sha, json_out=args.json_out,
            )

    except FetchError as exc:
        _err(
            f"git clone failed (exit {exc.returncode})",
            f"URL: {arts.distro_url}\nstderr: {exc.stderr.strip()}",
        )
        return 1
    except ManifestError as exc:
        _err(str(exc))
        return 1
    except ArtbookError as exc:
        _err(str(exc))
        return 1

    return 0


# ---------------------------------------------------------------------------
# Verb: pull
# ---------------------------------------------------------------------------


def _plan_writes(book, clone_root: Path, vault_root: Path) -> list[WriteActionRow]:
    """Return planned writes without executing them (used for --dry-run).

    ``WriteActionRow.action`` stores the base action (``"write"`` or
    ``"overwrite"``); the ``[would]`` prefix is added at display time.
    """
    dest_dir = destination_for(vault_root, book)

    src_dir = clone_root / book.src
    src_files = _select_files(src_dir, book)

    rows: list[WriteActionRow] = []
    for src_file in src_files:
        dst = dest_dir / src_file.name
        was_symlink = dst.is_symlink()
        overwritten = dst.exists() or was_symlink
        rows.append(WriteActionRow(
            action="overwrite" if overwritten else "write",
            destination=str(dst.relative_to(vault_root)),
            was_symlink=was_symlink,
        ))
    return rows


def _pull_write_rows(report, vault_root: Path) -> list[WriteActionRow]:
    """Convert a PullReport's written files into WriteActionRows (relative paths)."""
    rows: list[WriteActionRow] = []
    for wf in report.written:
        base_action = "overwrite" if wf.overwritten else "write"
        action = f"{base_action} (symlink replaced)" if wf.was_symlink else base_action
        rows.append(WriteActionRow(
            action=action,
            destination=str(wf.destination.relative_to(vault_root)),
            was_symlink=wf.was_symlink,
        ))
    return rows


def _run_pull(args, root: Path, raw: dict) -> int:
    arts = _artbook_settings_from_raw(raw)
    if not arts.distro_url:
        _err(
            "artbook.distro_url not configured in artifacts.yaml",
            "Add `artbook.distro_url: <git-url>` to artifacts.yaml.",
        )
        return 4

    book_name: str = args.name
    dry_run: bool = args.dry_run

    try:
        with tempfile.TemporaryDirectory(prefix="artbook-pull-") as td:
            clone_root = Path(td) / "clone"
            manifest, _ = artbook.read_manifest(arts.distro_url, clone_into=clone_root)
            sha = get_short_sha(clone_root)

            try:
                book = artbook.find_book(manifest, book_name)
            except UnknownBookError:
                available = ", ".join(b.name for b in manifest.books)
                _err(
                    f"book '{book_name}' not found in distro '{manifest.name}'",
                    f"Available books: {available}.",
                )
                return 1

            if dry_run:
                try:
                    rows = _plan_writes(book, clone_root, root)
                except (ManifestError, ArtbookError) as exc:
                    _err(str(exc))
                    return 1
            else:
                try:
                    report = artbook.pull_book(
                        book, clone_root, root,
                        distro_url=arts.distro_url,
                        distro_sha=sha,
                    )
                except (ManifestError, ArtbookError) as exc:
                    _err(str(exc))
                    return 1
                rows = _pull_write_rows(report, root)

            # --- Compute summary stats ---
            n_written = len(rows)
            n_overwritten = sum(1 for r in rows if "overwrite" in r.action)
            n_new = n_written - n_overwritten

            if args.json_out:
                for r in rows:
                    # Use the base action for JSON (strip symlink note)
                    json_action = r.action.split(" (")[0]
                    print(json.dumps({
                        "action": json_action,
                        "destination": r.destination,
                        "overwritten": "overwrite" in r.action,
                        "was_symlink": r.was_symlink,
                    }, ensure_ascii=False))
                # Final summary line
                summary_line: dict = {
                    "summary": {
                        "written": n_written,
                        "overwritten": n_overwritten,
                        "new": n_new,
                    },
                    "distro": {"url": arts.distro_url, "sha": sha},
                    "book": book_name,
                }
                if dry_run:
                    summary_line["dry_run"] = True
                print(json.dumps(summary_line, ensure_ascii=False))
                return 0

            # --- Rich table output ---
            # Escape action strings so Rich doesn't interpret "(" or other chars
            # as markup; for dry-run prefix each action with "[would] " — escaped.
            from rich.text import Text as _Text

            dry_label = _markup_escape("[would] ") if dry_run else ""
            header_dry = _markup_escape("[dry-run] ") if dry_run else ""

            _CONSOLE.print(
                f"{header_dry}Pulling book '{_markup_escape(book_name)}' from "
                f"{_markup_escape(manifest.name)} @ {_markup_escape(sha)}…"
            )
            _CONSOLE.print()

            # Build table manually so action text is never interpreted as markup.
            from rich.table import Table as _Table

            table = _Table()
            table.add_column("Action")
            table.add_column("Destination")
            for r in rows:
                action_text = _Text(f"[would] {r.action}" if dry_run else r.action)
                table.add_row(action_text, _Text(r.destination))
            _CONSOLE.print(table)
            _CONSOLE.print()

            summary_text = (
                f"Summary: {n_written} written "
                f"({n_overwritten} overwritten, {n_new} new)."
            )
            if dry_run:
                # Use Text to avoid markup parsing on "[dry-run]"
                from rich.text import Text as _RText
                _CONSOLE.print(_RText(f"[dry-run] {summary_text}"))
            else:
                _CONSOLE.print(summary_text)

    except FetchError as exc:
        _err(
            f"git clone failed (exit {exc.returncode})",
            f"URL: {arts.distro_url}\nstderr: {exc.stderr.strip()}",
        )
        return 1
    except ManifestError as exc:
        _err(str(exc))
        return 1
    except ArtbookError as exc:
        _err(str(exc))
        return 1

    return 0


# ---------------------------------------------------------------------------
# Top-level dispatcher and registration
# ---------------------------------------------------------------------------


def _run_book(args) -> int:
    """Dispatch to the selected book sub-verb after vault/settings setup."""
    root, raw = _load_vault_and_raw()
    if root is None:
        return 3
    return args.book_func(args, root, raw)


def register(subparsers) -> None:
    """Register the ``book`` command on *subparsers*."""
    book_parser = subparsers.add_parser(
        "book",
        help="browse and pull books from a configured distro",
    )
    book_subs = book_parser.add_subparsers(dest="book_verb", metavar="VERB")
    book_subs.required = True

    # --- list ---
    list_p = book_subs.add_parser(
        "list",
        help="list available books in the distro",
    )
    list_p.add_argument(
        "--json", "-j",
        action="store_true",
        dest="json_out",
        default=False,
        help="output raw JSON (default: Rich table)",
    )
    list_p.add_argument(
        "--remote",
        action="store_true",
        dest="remote",
        default=False,
        help="force the remote-clone path even when a local artbook.yaml is present",
    )
    list_p.set_defaults(book_func=_run_list)

    # --- show ---
    show_p = book_subs.add_parser(
        "show",
        help="show details and contents of a book",
    )
    show_p.add_argument("name", help="book name")
    show_p.add_argument(
        "--json", "-j",
        action="store_true",
        dest="json_out",
        default=False,
        help="output raw JSON (default: Rich text)",
    )
    show_p.add_argument(
        "--remote",
        action="store_true",
        dest="remote",
        default=False,
        help="force the remote-clone path even when a local artbook.yaml is present",
    )
    show_p.set_defaults(book_func=_run_show)

    # --- pull ---
    pull_p = book_subs.add_parser(
        "pull",
        help="pull a book into the vault",
    )
    pull_p.add_argument("name", help="book name")
    pull_p.add_argument(
        "--json", "-j",
        action="store_true",
        dest="json_out",
        default=False,
        help="output JSONL writes + summary (default: Rich table)",
    )
    pull_p.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        default=False,
        help="plan the writes but do not execute them",
    )
    pull_p.set_defaults(book_func=_run_pull)

    book_parser.set_defaults(func=_run_book, _pre_registry=True)
