"""Core implementation of artifacts_os.views.

Provides column layout, field formatting, and rich table construction.
Does not emit output — returns renderables or strings to callers.

Spec: s0007-artifacts-os-views-module
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence

from rich.table import Table
from rich.text import Text

from artifacts_os.core.models import ItemMeta, KindDef


@dataclass
class FieldSpec:
    """Describes one display column: frontmatter key, optional format, display label."""

    key: str
    fmt: str | None
    label: str


def parse_field_specs(spec_str: str) -> list[FieldSpec]:
    """Parse a comma-separated field spec string into list[FieldSpec].

    Token syntax: ``field[:format] [as Label]``

    Examples::

        parse_field_specs("id")                     # FieldSpec("id", None, "id")
        parse_field_specs("created:date")            # FieldSpec("created", "date", "created")
        parse_field_specs("created:date as Date")    # FieldSpec("created", "date", "Date")
    """
    specs: list[FieldSpec] = []
    for token in spec_str.split(","):
        token = token.strip()
        if not token:
            continue

        # Extract optional " as Label" suffix
        if " as " in token:
            field_part, label = token.split(" as ", 1)
            label = label.strip()
        else:
            field_part = token
            label = None

        # Extract optional ":format" suffix
        if ":" in field_part:
            key, fmt = field_part.split(":", 1)
            key = key.strip()
            fmt = fmt.strip() or None
        else:
            key = field_part.strip()
            fmt = None

        specs.append(FieldSpec(key=key, fmt=fmt, label=label if label is not None else key))

    return specs


def format_field(value: Any, fmt: str | None) -> str:
    """Format a raw frontmatter value for display.

    - ``fmt="date"``     — parse ISO datetime string, return ``YYYY-MM-DD``
    - ``fmt="datetime"`` — return ``YYYY-MM-DD HH:MM``
    - ``fmt=None``       — ``str(value)`` with ``None`` → ``""``
    - list/tuple values  — each element formatted, joined with ``", "``
    """
    if value is None:
        return ""

    if isinstance(value, (list, tuple)):
        return ", ".join(format_field(v, fmt) for v in value)

    if fmt == "date":
        try:
            return datetime.fromisoformat(str(value)).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return str(value)

    if fmt == "datetime":
        try:
            return datetime.fromisoformat(str(value)).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            return str(value)

    return str(value)


def default_columns(kind_def: KindDef) -> list[FieldSpec]:
    """Return the default column list from ``kind_def.meta``.

    Reads ``meta["columns"]`` (list of field spec strings).
    Falls back to ``["name", "summary"]`` when the key is absent.
    """
    columns: list[str] = kind_def.meta.get("columns", ["name", "summary"])
    return parse_field_specs(",".join(columns))


def render_table(
    items: Sequence[ItemMeta],
    columns: list[FieldSpec],
    *,
    status_colors: Mapping[str, str] | None = None,
) -> Table:
    """Build and return a ``rich.Table`` from *items* and *columns*.

    - One column per :class:`FieldSpec` using ``label`` as header.
    - One row per :class:`ItemMeta`; each cell value from
      ``item.cell(key, default="")`` formatted via :func:`format_field`.
    - When *status_colors* is provided, the ``status`` cell is wrapped in a
      :class:`rich.text.Text` with the mapped style string.

    The caller is responsible for extracting ``status_colors`` from a
    ``KindDef`` (via ``kind_def.meta.get("status_colors", {})``) and
    passing it here explicitly.
    """
    table = Table()
    for col in columns:
        table.add_column(col.label)

    colors: Mapping[str, str] = status_colors or {}

    for item in items:
        row: list[Any] = []
        for col in columns:
            raw = item.cell(col.key, "")
            cell_str = format_field(raw, col.fmt)
            if col.key == "status" and cell_str in colors:
                row.append(Text(cell_str, style=colors[cell_str]))
            else:
                row.append(cell_str)
        table.add_row(*row)

    return table
