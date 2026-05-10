"""artifacts-os log module.

Writes and reads structured JSONL records for agent runs and artifact
operations. Stdlib only — no external dependencies.

Depends on `core`.

Spec: s0005-artifacts-os-module-system § log
Implementation spec: s0004-artifacts-os-log-module

Note: the always-on artifact event stream (``artifact.created``,
``artifact.updated``, etc.) lives in ``artifacts_os.events``, not here.
This module owns the opt-in operational log (``Logger`` / ``LogReader``
API) for callers who want structured per-run records.  See
``s0025-artifact-events`` for the event stream and hook layer.
"""

__all__: list[str] = []
