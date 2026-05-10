"""artifacts-os event catalog and always-on audit stream.

Importing this module registers the JSONL stream writer with
``core.events``, enabling the always-on audit trail.  Import ``hooks``
separately to enable the opt-in reactive layer.

Spec: s0025-artifact-events
"""
from artifacts_os.core import events as _core_events
from artifacts_os.events import stream as _stream

# Auto-register the stream writer so every dispatch writes a JSONL line.
_core_events.register_emitter(_stream.append)

__all__ = ["stream"]
