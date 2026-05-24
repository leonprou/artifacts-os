"""Registry: merges caller-provided kinds with vault-defined kinds.

Spec: s2060-artifacts-os-architecture § registry.py
"""

import json
import re
import string
import warnings
from pathlib import Path

import yaml

from artifacts_os.core.errors import ValidationError
from artifacts_os.core.models import KindDef

# Words whose appearance in a description triggers a hard error.
_DESCRIPTION_RESERVED_WORDS: tuple[str, ...] = ("anthropic", "claude")
# Simple XML-tag pattern — angle-bracket opener with non-empty content.
_XML_TAG_RE = re.compile(r"<[^>]+>")

# Directory-storage primitive (s0032 §2.1).
_KNOWN_STORAGE_VALUES: frozenset[str] = frozenset({"file", "directory"})
_KNOWN_TEMPLATE_TOKENS: frozenset[str] = frozenset({"slug", "id", "name", "stem"})


def _read_artifact_md_frontmatter(path: Path) -> dict:
    """Read ONLY the YAML frontmatter block from *path*.

    Stops reading at the closing ``---`` delimiter so the body is never
    loaded (L1 layer-isolation invariant, s0017 § 4).
    """
    lines: list[str] = []
    with path.open("r", encoding="utf-8") as fh:
        first = fh.readline()
        if first.strip() != "---":
            return {}
        for line in fh:
            if line.rstrip("\n") == "---":
                break
            lines.append(line)
    return yaml.safe_load("".join(lines)) or {}


def _validate_description(description: str, kind_name: str) -> str:
    """Validate a non-empty description string.  Returns it unchanged on success.

    Raises ``ValidationError`` for hard failures (length cap, XML tags,
    reserved words).  Callers handle soft failures (absent/empty) themselves.
    """
    if len(description) > 1024:
        raise ValidationError(
            f"Kind '{kind_name}': description exceeds 1024 characters"
        )
    if _XML_TAG_RE.search(description):
        raise ValidationError(
            f"Kind '{kind_name}': description contains an XML tag"
        )
    lower = description.lower()
    for word in _DESCRIPTION_RESERVED_WORDS:
        if word in lower:
            raise ValidationError(
                f"Kind '{kind_name}': description contains reserved word '{word}'"
            )
    return description


class Registry:
    def __init__(
        self,
        kinds: list[KindDef],
        root: Path | None = None,
    ) -> None:
        self._root = Path(root).resolve() if root is not None else None
        seen: set[str] = set()
        for kd in kinds:
            if kd.name in seen:
                raise ValueError(f"duplicate kind '{kd.name}' in Registry kinds list")
            seen.add(kd.name)
        self._kinds: dict[str, KindDef] = {kd.name: kd for kd in kinds}
        if self._root is not None:
            for kd in self._load_vault_kinds(self._root):
                self._kinds[kd.name] = kd

    @property
    def root(self) -> Path | None:
        return self._root

    def get(self, kind: str) -> KindDef:
        if kind not in self._kinds:
            raise ValueError(f"Unknown kind: {kind!r}")
        return self._kinds[kind]

    def all(self) -> list[KindDef]:
        return list(self._kinds.values())

    def for_dir(self, dir_name: str) -> KindDef | None:
        for kd in self._kinds.values():
            if kd.dir == dir_name:
                return kd
        return None

    def exists_stem(self, stem: str) -> bool:
        """Return True if any artifact with *stem* exists anywhere in the vault.

        Checks every registered kind directory for an exact stem match
        (``stem.md``) or a numbered-kind prefix match (``stem-*.md``).
        Returns False when the registry has no root set.
        """
        if self._root is None:
            return False
        for kd in self._kinds.values():
            kind_dir = self._root / "artifacts" / kd.dir
            if not kind_dir.is_dir():
                continue
            if (kind_dir / f"{stem}.md").is_file():
                return True
            if any(kind_dir.glob(f"{stem}-*.md")):
                return True
        return False

    @staticmethod
    def _load_vault_kinds(root: Path) -> list[KindDef]:
        kinds_dir = root / "artifacts" / "kinds"
        if not kinds_dir.is_dir():
            return []

        # Warn about stray flat-form files so authors know to migrate.
        for flat in sorted(kinds_dir.glob("*.json")):
            warnings.warn(
                f"Kind '{flat.stem}': flat schema file '{flat}' is not supported. "
                f"Migrate to folder form: artifacts/kinds/{flat.stem}/kind.json. "
                f"The flat file will not be registered as a kind.",
                stacklevel=2,
            )

        # Folder form only: artifacts/kinds/<name>/kind.json
        schema_paths: dict[str, Path] = {}
        for folder in sorted(kinds_dir.iterdir()):
            if not folder.is_dir():
                continue
            kind_json = folder / "kind.json"
            if kind_json.is_file():
                schema_paths[folder.name] = kind_json

        # --- Load each kind ---
        out: list[KindDef] = []
        for name, schema_path in sorted(schema_paths.items()):
            with schema_path.open("r", encoding="utf-8") as f:
                schema = json.load(f)
            if not isinstance(schema, dict):
                raise ValidationError(
                    f"Vault kind schema must be an object: {schema_path}"
                )
            kind_dir = schema.get("x-dir")
            if not kind_dir:
                raise ValidationError(
                    f"Vault kind schema missing required 'x-dir': {schema_path}"
                )
            statuses = (
                schema.get("properties", {})
                .get("status", {})
                .get("enum", [])
            )
            meta: dict = {}
            if "x-columns" in schema:
                meta["columns"] = schema["x-columns"]
            if "x-status-colors" in schema:
                meta["status_colors"] = schema["x-status-colors"]
            required_fields = schema.get("x-required-fields")

            # --- Directory-storage primitive (s0032 §2.1) ---
            storage = schema.get("x-storage", "file")
            if storage not in _KNOWN_STORAGE_VALUES:
                raise ValidationError(
                    f"Kind '{name}': unknown 'x-storage' value {storage!r}; "
                    f"expected one of {sorted(_KNOWN_STORAGE_VALUES)}"
                )
            manifest_name_template = schema.get("x-manifest-name", "{slug}.md")
            if "x-manifest-name" in schema and storage != "directory":
                raise ValidationError(
                    f"Kind '{name}': 'x-manifest-name' is only valid when "
                    f"x-storage is 'directory'; found x-storage={storage!r}"
                )
            if storage == "directory":
                # Validate template tokens — fail fast before any artifact is created.
                formatter = string.Formatter()
                for _, field_name, _, _ in formatter.parse(manifest_name_template):
                    if field_name is None:
                        continue
                    if field_name not in _KNOWN_TEMPLATE_TOKENS:
                        raise ValidationError(
                            f"Kind '{name}': 'x-manifest-name' template "
                            f"contains unknown token '{{{field_name}}}'; "
                            f"known tokens: {sorted(_KNOWN_TEMPLATE_TOKENS)}"
                        )

            # --- L1: read ARTIFACT.md frontmatter only ---
            artifact_md = kinds_dir / name / "ARTIFACT.md"
            has_template = artifact_md.is_file()
            description: str | None = None

            if has_template:
                fm = _read_artifact_md_frontmatter(artifact_md)
                raw_desc = fm.get("description")
                if not raw_desc:
                    warnings.warn(
                        f"Kind '{name}': ARTIFACT.md missing or empty 'description' field; "
                        "kind will be listed with description=None.",
                        stacklevel=2,
                    )
                else:
                    description = _validate_description(str(raw_desc), name)
            else:
                warnings.warn(
                    f"Kind '{name}': no ARTIFACT.md found; has_template=False.",
                    stacklevel=2,
                )

            out.append(
                KindDef(
                    name=name,
                    dir=kind_dir,
                    prefix=schema.get("x-prefix", ""),
                    numbered=bool(schema.get("x-numbered", True)),
                    statuses=list(statuses),
                    schema=schema,
                    meta=meta,
                    required_fields=list(required_fields) if required_fields is not None else None,
                    description=description,
                    has_template=has_template,
                    storage=storage,
                    manifest_name=manifest_name_template,
                )
            )
        return out
