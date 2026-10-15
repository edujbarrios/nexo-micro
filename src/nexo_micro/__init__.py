"""NEXO Micro: experimental semantic micro-messaging for AI agents.

Encoding is not encryption. This library has no network or crypto primitives.
"""
from .protocol import Macro, MicroSession, ProtocolError, b36, from_b36
from .selection import Selection, choose, receive
from .trainer import train_macros
from .endpoint import Frame, HandshakeError, Hello, MicroEndpoint

__all__ = [
    "Frame", "HandshakeError", "Hello", "Macro", "MicroEndpoint", "MicroSession",
    "ProtocolError", "Selection", "b36", "from_b36", "choose", "receive", "train_macros",
]
__version__ = "0.1.0"
