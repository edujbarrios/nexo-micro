from nexo_micro import Macro, MicroSession

# In production: both agents must independently authenticate and negotiate
# exact protocol version AND dictionary fingerprint BEFORE exchanging payloads.
macros = (Macro("review_diff", "A", ("files", "critical")),)
alice = MicroSession(macros=macros)
bob = MicroSession(macros=macros)
assert alice.fingerprint == bob.fingerprint

messages = [
    {"intent": "status", "task": 42},
    {"intent": "progress", "task": 42, "percent": 80},
    {"intent": "macro", "task": 42, "name": "review_diff", "args": {"files": 7, "critical": 3}},
    {"intent": "complete", "task": 42, "critical": 3},
]
for msg in messages:
    wire = alice.encode(msg)
    decoded = bob.decode(wire)
    assert decoded == msg
    print(f"{wire:10} -> {decoded}")
