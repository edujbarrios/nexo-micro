"""Tokenizer-gated selection for a specific model (no universal guarantee)."""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable, Mapping

from .protocol import MicroSession, ProtocolError

CountTokens = Callable[[str], int]


@dataclass(frozen=True)
class Selection:
    format: str
    payload: str
    micro_tokens: int
    json_tokens: int


def choose(session: MicroSession, message: Mapping[str, Any], count_tokens: CountTokens) -> Selection:
    """Choose Micro only when cheaper than compact JSON for THIS tokenizer.

    Measures bare model-facing payloads, not transport envelopes or instructions.
    A real deployment MUST separately measure prompt overhead, both directions,
    and all messages from an actual agent workload.
    """
    trial = session.copy()
    micro = trial.encode(message)
    # JSON carries the task explicitly. Micro may reference it through session state.
    canonical = dict(message)
    if "task" not in canonical:
        canonical["task"] = trial.active_task
    compact_json = json.dumps(canonical, separators=(",", ":"), ensure_ascii=False, sort_keys=True)
    mt, jt = count_tokens(micro), count_tokens(compact_json)
    if type(mt) is not int or type(jt) is not int or min(mt, jt) < 0:
        raise ValueError("token counter must return nonnegative integers")
    if mt < jt:
        session.active_task = trial.active_task
        return Selection("micro/1", micro, mt, jt)
    session.active_task = trial.active_task
    return Selection("json", compact_json, mt, jt)


def receive(session: MicroSession, selection: Selection | str, *, format: str | None = None) -> dict[str, Any]:
    if isinstance(selection, Selection):
        format, payload = selection.format, selection.payload
    else:
        payload = selection
    if format == "micro/1":
        return session.decode(payload)
    if format == "json":
        def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            obj: dict[str, Any] = {}
            for key, value in pairs:
                if key in obj:
                    raise ProtocolError("duplicate JSON keys are forbidden")
                obj[key] = value
            return obj

        data = json.loads(payload, object_pairs_hook=reject_duplicate_keys)
        if not isinstance(data, dict):
            raise ValueError("expected JSON object")
        # Validate before updating context. Authorization still belongs to the host.
        trial = session.copy()
        trial.encode(data)
        if "task" not in data:
            data["task"] = trial.active_task
        session.active_task = trial.active_task
        return data
    raise ValueError("unnegotiated frame format")
