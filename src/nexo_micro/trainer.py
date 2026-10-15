"""Experimental, deterministic tokenizer-aware macro codebook builder.

This is a simple heuristic, NOT a globally optimal language-learning algorithm.
In particular it never infers meaning from natural language text.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Iterable, Mapping

from .protocol import Macro, ProtocolError, _n, b36


def train_macros(
    schemas: Mapping[str, tuple[str, ...]],
    observations: Iterable[Mapping[str, Any]],
    token_count: Callable[[str], int],
) -> tuple[Macro, ...]:
    """Assign short macro codes using recorded arg frequencies and one tokenizer.

    Greedily selects the least-cost (name, code) pair, weighted by occurrences.
    Sender and receiver MUST independently agree on the resulting codebook
    and exchange/verify its fingerprint prior to sending macro messages.
    """
    if len(schemas) > 26:
        raise ProtocolError("at most 26 macros")
    spec = dict(schemas)
    for name, params in spec.items():
        Macro(name, "A", tuple(params))  # validates schema independently
    traces: dict[str, list[tuple[int, ...]]] = defaultdict(list)
    for obs in observations:
        name = obs.get("name")
        if name not in spec:
            raise ProtocolError("observation references unknown macro")
        args = obs.get("args")
        if not isinstance(args, Mapping) or set(args) != set(spec[name]):
            raise ProtocolError("observation arguments do not match schema")
        traces[name].append(tuple(_n(args[p]) for p in spec[name]))
    # Stable ordering; unseen macros still get a valid code.
    available = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    todo = sorted(spec)
    selected = []
    while todo:
        scores = []
        for name in todo:
            params = spec[name]
            args_list = traces[name] or [tuple(0 for _ in params)]
            for code in available:
                strings = ["^" + code + ("." + ".".join(b36(x) for x in values) if values else "")
                           for values in args_list]
                total = sum(token_count(text) for text in strings)
                scores.append((total / len(args_list), -len(args_list), name, code))
        _, _, name, code = min(scores)
        selected.append(Macro(name, code, tuple(spec[name])))
        available.remove(code)
        todo.remove(name)
    return tuple(sorted(selected, key=lambda m: m.name))
