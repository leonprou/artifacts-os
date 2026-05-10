"""DAG-glue dispatcher for artifact events.

This module is the only coupling point between ``core/store.py`` and the
``events/`` / ``hooks/`` layers.  It knows zero specific event types — the
catalog lives in ``events/catalog.py``.

Invariants (from s0025):
    I1  A failed emitter never propagates — ``_dispatch`` catches every
        exception.
    I3  ``core`` imports nothing from ``events/``, ``hooks/``, or ``log/``.
    I4  Pre-phase hooks are the only mechanism that can abort a CRUD
        operation, and only when explicitly marked ``blocking: true``.

Spec: s0025-artifact-events § C2
"""
from __future__ import annotations

import sys
from typing import Callable

EmitterFn = Callable[[str, dict], None]

_emitters: list[EmitterFn] = []


def register_emitter(fn: EmitterFn) -> None:
    """Register an emitter called on every ``_dispatch`` / ``_dispatch_pre``.

    Order is registration order.  Re-registration is allowed (creates a
    duplicate entry — the emitter fires twice).
    """
    _emitters.append(fn)


def unregister_emitter(fn: EmitterFn) -> None:
    """Remove the first matching registration.

    No-op if the function is not registered.  Used by tests to clean up
    between cases.
    """
    try:
        _emitters.remove(fn)
    except ValueError:
        pass


def _dispatch(event: str, **payload: object) -> None:
    """Fire *event* to every registered emitter.

    Failures are caught, warned to stderr, and otherwise swallowed.
    ``_dispatch`` must never propagate an exception out of a CRUD call
    (invariant I1).

    The ``_phase`` sentinel ``"post"`` is injected into the payload dict
    so emitters can distinguish post-phase calls from pre-phase calls.
    """
    p = dict(payload)
    p["_phase"] = "post"
    for fn in list(_emitters):
        try:
            fn(event, dict(p))
        except Exception as e:  # noqa: BLE001 — invariant I1
            sys.stderr.write(f"warning: events emitter failed: {e!r}\n")


def _dispatch_pre(event: str, **payload: object) -> None:
    """Pre-phase dispatch — runs *before* the file is written.

    Identical to ``_dispatch`` except that ``BlockedByPreHook`` is allowed
    to propagate.  Any other exception is swallowed with a stderr warning.

    A pre-phase hook that raises ``BlockedByPreHook`` aborts the CRUD
    operation (invariant I4).

    The ``_phase`` sentinel ``"pre"`` is injected into the payload dict
    so emitters can identify this as a pre-phase call.
    """
    from artifacts_os.core.errors import BlockedByPreHook  # local — avoids circular

    p = dict(payload)
    p["_phase"] = "pre"
    for fn in list(_emitters):
        try:
            fn(event, dict(p))
        except BlockedByPreHook:
            raise
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"warning: pre-emitter failed: {e!r}\n")
