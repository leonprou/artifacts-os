"""artifacts-os opt-in hook layer.

Importing this module registers the hook dispatcher with ``core.events``,
enabling declarative hooks defined in ``artifacts.yaml``.  Import
``events`` separately to enable the always-on audit stream.

Spec: s0025-artifact-events
"""
from artifacts_os.core import events as _core_events
from artifacts_os.hooks.loader import notify as _notify

# Auto-register the hook dispatcher so every dispatch triggers matching hooks.
_core_events.register_emitter(_notify)

__all__ = ["loader", "actions", "settings"]
