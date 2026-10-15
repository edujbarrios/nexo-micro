"""Two hosts exchange Micro/1 frames. This is not a network demonstration."""
from nexo_micro import MicroEndpoint, Macro

macros = (Macro("review_diff", "A", ("files", "critical")),)
alice = MicroEndpoint(macros=macros)
bob = MicroEndpoint(macros=macros)

# In production send Hello through an authenticated channel and parse with
# Hello.from_dict(). NEVER use an unauthenticated hello to identify peers.
alice.connect(bob.hello())
bob.connect(alice.hello())

for message in [
    {"task": 42, "intent": "status"},
    {"task": 42, "intent": "macro", "name": "review_diff", "args": {"files": 7, "critical": 3}},
    {"task": 42, "intent": "complete", "critical": 3},
]:
    frame = alice.send(message)
    print("LLM-visible:", frame.payload, " host frame:", frame.to_dict())
    assert bob.receive(frame) == message
