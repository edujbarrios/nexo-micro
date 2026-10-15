"""Minimal, explicitly scoped semantic micro-language (version 0.1).

Not a universal language, not encryption, and not a lossless codec for prose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any, Mapping

_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_BIND = re.compile(r"^@([0-9A-Z]+)$")
_EVENT = re.compile(r"^([!~x])([0-9A-Z]+)$")
_MACRO = re.compile(r"^\^([A-Z])(?:\.([0-9A-Z]+(?:\.[0-9A-Z]+)*))?$")


class ProtocolError(ValueError):
    """A malformed or unsupported micro message or local operation."""


def b36(value: int) -> str:
    if type(value) is not int or value < 0:
        raise ProtocolError("expected a nonnegative integer")
    if value == 0:
        return "0"
    out = ""
    while value:
        value, remainder = divmod(value, 36)
        out = _DIGITS[remainder] + out
    return out


def from_b36(text: str) -> int:
    if not text or len(text) > 13 or any(c not in _DIGITS for c in text):
        raise ProtocolError("invalid or oversized base36 number")
    value = int(text, 36)
    if b36(value) != text:
        raise ProtocolError("noncanonical base36 integer")
    if value > 2**53 - 1:
        raise ProtocolError("integer exceeds interoperable 53-bit limit")
    return value


def _n(value: Any, *, max_value: int = 2**53 - 1) -> int:
    if type(value) is not int or not 0 <= value <= max_value:
        raise ProtocolError(f"expected integer in [0, {max_value}]")
    return value


@dataclass(frozen=True)
class Macro:
    """A pre-negotiated typed semantic instruction (NOT executable code)."""

    name: str
    code: str
    parameters: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Z]", self.code):
            raise ProtocolError("macro code must be one uppercase A-Z character")
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", self.name):
            raise ProtocolError("macro name must be snake_case")
        if len(self.parameters) > 3 or len(set(self.parameters)) != len(self.parameters):
            raise ProtocolError("macros support at most 3 distinct parameters")
        for param in self.parameters:
            if not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", param):
                raise ProtocolError("macro parameter must be snake_case")


@dataclass
class MicroSession:
    """Stateful encoder/decoder. Each peer needs its OWN instance and same macros.

    Peers MUST process messages in order and negotiate a shared macro fingerprint.
    Keep task binding scoped to a trusted conversation/session.
    """

    active_task: int | None = None
    macros: tuple[Macro, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.active_task is not None:
            _n(self.active_task)
        self.macros = tuple(self.macros)
        if len(set(m.name for m in self.macros)) != len(self.macros):
            raise ProtocolError("duplicate macro name")
        if len(set(m.code for m in self.macros)) != len(self.macros):
            raise ProtocolError("duplicate macro code")

    @property
    def fingerprint(self) -> str:
        spec = {"version": 1, "macros": [
            {"name": m.name, "code": m.code, "parameters": list(m.parameters)}
            for m in sorted(self.macros, key=lambda m: m.code)
        ]}
        payload = json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(payload).hexdigest()[:16]

    def copy(self) -> "MicroSession":
        return MicroSession(self.active_task, self.macros)

    def _encode_event(self, message: Mapping[str, Any]) -> str:
        intent = message.get("intent")
        if intent == "status":
            self._keys(message, {"intent", "task"})
            return "?"
        if intent == "complete":
            self._keys(message, {"intent", "task", "critical"})
            return "!" + b36(_n(message.get("critical")))
        if intent == "progress":
            self._keys(message, {"intent", "task", "percent"})
            return "~" + b36(_n(message.get("percent"), max_value=100))
        if intent == "error":
            self._keys(message, {"intent", "task", "code"})
            return "x" + b36(_n(message.get("code")))
        if intent == "next":
            self._keys(message, {"intent", "task"})
            return ">"
        if intent == "macro":
            self._keys(message, {"intent", "task", "name", "args"})
            macro = next((m for m in self.macros if m.name == message.get("name")), None)
            if macro is None:
                raise ProtocolError("unknown macro; negotiate shared dictionary first")
            args = message.get("args")
            if not isinstance(args, Mapping) or set(args) != set(macro.parameters):
                raise ProtocolError("macro arguments do not match negotiated schema")
            values = [b36(_n(args[p])) for p in macro.parameters]
            return "^" + macro.code + ("." + ".".join(values) if values else "")
        raise ProtocolError("unsupported intent")

    @staticmethod
    def _keys(message: Mapping[str, Any], allowed: set[str]) -> None:
        if set(message) != allowed:
            raise ProtocolError(f"expected keys {sorted(allowed)}")

    def encode(self, message: Mapping[str, Any]) -> str:
        """Encode an EXACT typed message; update state only after validation succeeds."""
        if not isinstance(message, Mapping):
            raise ProtocolError("message must be a mapping")
        if "task" not in message:
            if self.active_task is None:
                raise ProtocolError("task must be specified until bound")
            message = dict(message, task=self.active_task)
        task = _n(message["task"])
        event = self._encode_event(message)
        # Never rely on a context the sender hasn't established.
        result = ("@" + b36(task) + "|" if task != self.active_task else "") + event
        self.active_task = task
        return result

    def decode(self, wire: str) -> dict[str, Any]:
        """Strict atomic decode. A binder-only frame can be used to initialise context."""
        if not isinstance(wire, str) or not wire or len(wire) > 120:
            raise ProtocolError("invalid wire length")
        parts = wire.split("|")
        if len(parts) > 2:
            raise ProtocolError("too many frames")
        task = self.active_task
        if parts[0].startswith("@"):
            match = _BIND.fullmatch(parts[0])
            if match is None:
                raise ProtocolError("invalid task binding")
            task = from_b36(match.group(1))
            if len(parts) == 1:
                self.active_task = task
                return {"intent": "bind", "task": task}
            event = parts[1]
        else:
            if len(parts) != 1:
                raise ProtocolError("bind must precede event")
            event = parts[0]
        if task is None:
            raise ProtocolError("unbound task")
        message: dict[str, Any] = {"task": task}
        if event == "?":
            message["intent"] = "status"
        elif event == ">":
            message["intent"] = "next"
        else:
            match = _EVENT.fullmatch(event)
            if match:
                kind, value = match.groups()
                value_num = from_b36(value)
                if kind == "!":
                    message.update(intent="complete", critical=value_num)
                elif kind == "~":
                    if value_num > 100:
                        raise ProtocolError("progress exceeds 100 percent")
                    message.update(intent="progress", percent=value_num)
                else:
                    message.update(intent="error", code=value_num)
            else:
                match = _MACRO.fullmatch(event)
                if match is None:
                    raise ProtocolError("unknown micro message")
                code, encoded_params = match.groups()
                macro = next((m for m in self.macros if m.code == code), None)
                if macro is None:
                    raise ProtocolError("macro dictionary mismatch")
                parts_ = encoded_params.split(".") if encoded_params else []
                if len(parts_) != len(macro.parameters):
                    raise ProtocolError("incorrect macro arity")
                message.update(intent="macro", name=macro.name,
                               args={key: from_b36(value) for key, value in zip(macro.parameters, parts_)})
        self.active_task = task
        return message
