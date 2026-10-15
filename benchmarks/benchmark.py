"""Run with: python -m nexo_micro bench --encoding o200k_base --repeats 10"""
from __future__ import annotations

import argparse
import json
from nexo_micro import MicroSession, choose

PRIMER = (
    "Micro/1: @N binds current task (base36); ?=status query; ~N=progress percentage; "
    "!N=task completed with N critical findings; xN=error code; >=continue. "
    "Numbers are uppercase base36. Interpret using the active task."
)


def corpus(repeats: int):
    if repeats < 1:
        raise ValueError("repeats must be positive")
    for task in range(42, 42 + repeats):
        yield {"intent": "status", "task": task}
        yield {"intent": "progress", "task": task, "percent": 80}
        yield {"intent": "complete", "task": task, "critical": 3}
        yield {"intent": "next", "task": task}


def measure(repeats: int, count):
    messages = list(corpus(repeats))
    s, examples = MicroSession(), []
    totals = {"json_compact": 0, "json_min_schema": 0, "json_stateful": 0, "micro": 0, "micro_with_primer": count(PRIMER), "adapted": 0}
    schema_op = {"status": "?", "progress": "~", "complete": "!", "error": "x", "next": ">"}
    number_field = {"progress": "percent", "complete": "critical", "error": "code"}
    current_task = None
    for m in messages:
        micro = s.encode(m)
        text_json = json.dumps(m, separators=(",", ":"), sort_keys=True)
        totals["json_compact"] += count(text_json)
        schema = {"t": m["task"], "i": schema_op[m["intent"]]}
        if m["intent"] in number_field:
            schema["n"] = m[number_field[m["intent"]]]
        totals["json_min_schema"] += count(json.dumps(schema, separators=(",", ":"), sort_keys=True))
        if current_task == m["task"]:
            schema.pop("t")
        current_task = m["task"]
        totals["json_stateful"] += count(json.dumps(schema, separators=(",", ":"), sort_keys=True))
        totals["micro"] += count(micro)
        totals["micro_with_primer"] += count(micro)
        if len(examples) < 5:
            examples.append({"json": text_json, "micro": micro})
    adaptive = MicroSession()
    for m in messages:
        pick = choose(adaptive, m, count)
        totals["adapted"] += count(pick.payload)
    totals["messages"] = len(messages)
    totals["primer_once"] = count(PRIMER)
    totals["examples"] = examples
    return totals


def main(args=None):
    parser = argparse.ArgumentParser(description="Reproducible micro message benchmark")
    parser.add_argument("--encoding", default="o200k_base", help="tiktoken model encoding")
    parser.add_argument("--repeats", type=int, default=10, help="number of 4-message task cycles")
    parser.add_argument("--bytes-only", action="store_true", help="measure UTF-8 bytes, NOT model tokens")
    ns = parser.parse_args(args)
    if ns.bytes_only:
        metric, count = "UTF-8 bytes (not tokens)", lambda s: len(s.encode("utf-8"))
    else:
        try:
            import tiktoken
            encoder = tiktoken.get_encoding(ns.encoding)
        except ImportError:
            parser.error("real LLM token measurement requires: pip install 'nexo-micro[bench]'")
        metric, count = f"tiktoken {ns.encoding} tokens", lambda s: len(encoder.encode(s))
    totals = measure(ns.repeats, count)
    print(json.dumps({"unit": metric, **totals, "message_only_savings_pct": round(
        100 * (1-totals['micro']/totals['json_compact']), 2
    )}, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
