"""Registry: merges caller-provided kinds with vault-defined kinds.

Spec: s2060-artifacts-os-architecture § registry.py
"""

import json
from pathlib import Path

from artifacts_os.core.errors import ValidationError
from artifacts_os.core.models import KindDef


class Registry:
    def __init__(
        self,
        kinds: list[KindDef],
        root: Path | None = None,
    ) -> None:
        self._root = Path(root).resolve() if root is not None else None
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

    @staticmethod
    def _load_vault_kinds(root: Path) -> list[KindDef]:
        kinds_dir = root / "artifacts" / "kinds"
        if not kinds_dir.is_dir():
            return []
        out: list[KindDef] = []
        for path in sorted(kinds_dir.glob("*.json")):
            with path.open("r", encoding="utf-8") as f:
                schema = json.load(f)
            if not isinstance(schema, dict):
                raise ValidationError(
                    f"Vault kind schema must be an object: {path}"
                )
            kind_dir = schema.get("x-dir")
            if not kind_dir:
                raise ValidationError(
                    f"Vault kind schema missing required 'x-dir': {path}"
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
            out.append(
                KindDef(
                    name=path.stem,
                    dir=kind_dir,
                    prefix=schema.get("x-prefix", ""),
                    numbered=bool(schema.get("x-numbered", True)),
                    statuses=list(statuses),
                    schema=schema,
                    meta=meta,
                    required_fields=list(required_fields) if required_fields is not None else None,
                )
            )
        return out
