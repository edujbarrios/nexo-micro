"""Host-level ordering, session isolation and codebook negotiation.

The micro payload is model-facing. All envelope fields are host transport metadata;
never concatenate them into an LLM prompt without counting their cost.
This is NOT an authenticated or encrypted transport. Use authenticated TLS.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import secrets
from typing import Any, Callable, Mapping

from .protocol import Macro, MicroSession, ProtocolError
from .selection import choose, receive

PROTOCOL = "micro/1"
MAX_PAYLOAD_BYTES = 16_384


class HandshakeError(ProtocolError):
    """A peer has a different protocol, dictionary or invalid session identity."""


@dataclass(frozen=True)
class Hello:
    """Host-only capability declaration; exchange over authenticated transport."""

    protocol: str
    dictionary: str
    session_id: str

    def __post_init__(self) -> None:
        if self.protocol != PROTOCOL:
            raise HandshakeError("unsupported protocol")
        if not isinstance(self.dictionary, str) or len(self.dictionary) != 16 or any(c not in "0123456789abcdef" for c in self.dictionary):
            raise HandshakeError("invalid dictionary fingerprint")
        if not isinstance(self.session_id, str) or len(self.session_id) != 24 or any(c not in "0123456789abcdef" for c in self.session_id):
            raise HandshakeError("invalid session ID")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Hello":
        if not isinstance(data, Mapping) or set(data) != {"protocol", "dictionary", "session_id"}:
            raise HandshakeError("invalid hello fields")
        if not all(isinstance(data[k], str) for k in data):
            raise HandshakeError("invalid hello types")
        return cls(**data)

    def to_dict(self) -> dict[str, str]:
        return {"protocol": self.protocol, "dictionary": self.dictionary, "session_id": self.session_id}


@dataclass(frozen=True)
class Frame:
    """Transport-level wrapper. Payload alone is the model-visible message."""

    session_id: str
    sequence: int
    format: str
    payload: str

    def __post_init__(self) -> None:
        if not isinstance(self.session_id, str) or len(self.session_id) != 24 or any(c not in "0123456789abcdef" for c in self.session_id):
            raise ProtocolError("invalid session ID")
        if type(self.sequence) is not int or not 0 <= self.sequence < 2**53:
            raise ProtocolError("invalid sequence number")
        if not isinstance(self.format, str) or self.format not in (PROTOCOL, "json"):
            raise ProtocolError("unsupported frame format")
        if not isinstance(self.payload, str) or not self.payload:
            raise ProtocolError("payload must be nonempty text")
        if len(self.payload.encode("utf-8")) > MAX_PAYLOAD_BYTES:
            raise ProtocolError("oversized frame payload")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Frame":
        if not isinstance(data, Mapping) or set(data) != {"session_id", "sequence", "format", "payload"}:
            raise ProtocolError("invalid frame fields")
        return cls(**data)

    def to_dict(self) -> dict[str, str | int]:
        return {"session_id": self.session_id, "sequence": self.sequence, "format": self.format, "payload": self.payload}


@dataclass
class MicroEndpoint:
    """One endpoint, with independent incoming/outgoing task context.

    Explicit handshake is mandatory. All received frames must be in order;
    dropped/duplicated frames cause a hard error rather than silent context drift.
    A connection must be authenticated by its host; this class cannot prevent
    network attackers from forging a handshake or message.
    """

    macros: tuple[Macro, ...] = ()
    token_count: Callable[[str], int] | None = None
    _outgoing: MicroSession = field(init=False, repr=False)
    _incoming: MicroSession = field(init=False, repr=False)
    _session_id: str = field(init=False, repr=False)
    _peer: Hello | None = field(init=False, default=None, repr=False)
    _send_sequence: int = field(init=False, default=0, repr=False)
    _recv_sequence: int = field(init=False, default=0, repr=False)

    def __post_init__(self) -> None:
        self.macros = tuple(self.macros)
        self._outgoing = MicroSession(macros=self.macros)
        self._incoming = MicroSession(macros=self.macros)
        self._session_id = secrets.token_hex(12)

    def hello(self) -> Hello:
        return Hello(PROTOCOL, self._outgoing.fingerprint, self._session_id)

    @property
    def connected(self) -> bool:
        return self._peer is not None

    def connect(self, peer: Hello) -> None:
        if not isinstance(peer, Hello):
            raise HandshakeError("expected Hello; use Hello.from_dict for untrusted input")
        if self._peer is not None:
            raise HandshakeError("endpoint already connected")
        if peer.dictionary != self._outgoing.fingerprint:
            raise HandshakeError("peer macro dictionary mismatch")
        if peer.session_id == self._session_id:
            raise HandshakeError("peer session ID must be distinct")
        self._peer = peer

    def send(self, message: Mapping[str, Any]) -> Frame:
        if not self.connected:
            raise HandshakeError("exchange and validate Hello before sending")
        if self._send_sequence >= 2**53 - 1:
            raise ProtocolError("sequence exhausted; create new session")
        trial = self._outgoing.copy()
        if self.token_count is None:
            payload, fmt = trial.encode(message), PROTOCOL
        else:
            choice = choose(trial, message, self.token_count)
            payload, fmt = choice.payload, choice.format
        frame = Frame(self._session_id, self._send_sequence, fmt, payload)
        # No mutation until successful encoding, token selection AND size check.
        self._outgoing = trial
        self._send_sequence += 1
        return frame

    def receive(self, frame: Frame) -> dict[str, Any]:
        if self._peer is None:
            raise HandshakeError("exchange and validate Hello before receiving")
        if not isinstance(frame, Frame):
            raise ProtocolError("expected Frame; use Frame.from_dict for untrusted input")
        if frame.session_id != self._peer.session_id:
            raise ProtocolError("frame belongs to another session")
        if frame.sequence != self._recv_sequence:
            raise ProtocolError("out-of-order, missing or replayed frame")
        trial = self._incoming.copy()
        result = receive(trial, frame.payload, format=frame.format)
        # Only commit on complete success; recover by resetting both endpoints.
        self._incoming = trial
        self._recv_sequence += 1
        return result
