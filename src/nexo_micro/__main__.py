"""Minimal CLI."""
from __future__ import annotations
import sys
from .protocol import MicroSession


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "bench":
        from .benchmark import main as benchmark_main
        return benchmark_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        alice, bob = MicroSession(), MicroSession()
        example = {"task": 42, "intent": "complete", "critical": 3}
        wire = alice.encode(example)
        print("wire:", wire)
        print("decoded:", bob.decode(wire))
        print("next wire:", alice.encode({"task": 42, "intent": "status"}))
        return 0
    print("Usage: nexo-micro demo | nexo-micro bench [--encoding o200k_base] [--repeats 10] [--bytes-only]")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
