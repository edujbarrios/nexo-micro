# NEXO Micro

**Open-source semantic micro-messages for cooperating AI agents.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![CI](https://github.com/edujbarrios/nexo-micro/actions/workflows/ci.yml/badge.svg)](https://github.com/edujbarrios/nexo-micro/actions/workflows/ci.yml)

NEXO Micro is a Python **library** and an experimental versioned language (`micro/1`) for *short, model-visible* messages between cooperating AI agents. It is a **separate project** from [NEXO](https://github.com/edujbarrios/nexo): NEXO encodes arbitrary structured values reversibly; NEXO Micro deliberately encodes only narrowly defined **semantic events**, often omitting a previously shared task ID.

> **Research prototype, not a universal efficiency claim.** Less text and fewer UTF-8 bytes do not guarantee fewer model tokens, less API spending, or equivalent comprehension. NEXO Micro is neither encryption nor an open-ended, lossless natural-language codec. The built-in benchmark measures tokenizer counts, **not model understanding**. See [research limitations](docs/RESEARCH.md) and [benchmarks](docs/BENCHMARKS.md).

**Español:** [Guía de inicio](docs/GUIA_ES.md) · **Protocol:** [Micro/1 specification](docs/PROTOCOL.md) · **Releases:** [PyPI guide](docs/PYPI.md)

## Why semantic micro-messages?

When two hosts already agree on task 42, a conventional message repeats its context:

```json
{"intent":"complete","task":42,"critical":3}
```

Micro/1 encodes the same *typed intent* as a first message `@16|!3`, then as `!3` if task 42 is already bound. `@16` is task 42 in base36; `!3` means completed with 3 critical findings. The dictionary is defined in advance. The language is intentionally limited: arbitrary prose must travel in another format.

| Model-visible wire | Meaning in the current task |
| --- | --- |
| `@16|?` | Bind task 42 and request its status |
| `?` | Request status of the currently bound task |
| `~28` | Progress is 80% (base36) |
| `!3` | Complete, with 3 critical findings |
| `x4` | Error code 4 |
| `>` | Proceed |
| `^A.7.3` | Negotiated typed macro A with two integer arguments |

This is **semantic specialization**, not magic compression: short messages are possible because both sides already share grammar, task context, and any macro definitions. Setup, synchronization and prompt instructions have costs. Counterparties need to receive messages *in order*.

## Install and run

Requires **Python 3.10+**. Before first PyPI release, install from source:

```bash
git clone https://github.com/edujbarrios/nexo-micro.git
cd nexo-micro
python -m pip install -e .
python -m nexo_micro demo
python examples/handshake_agents.py
```

After publication: `pip install nexo-micro`. CLI command: `nexo-micro`.

### Quick start: local codec

```python
from nexo_micro import MicroSession

sender, receiver = MicroSession(), MicroSession()
message = {"task": 42, "intent": "complete", "critical": 3}
wire = sender.encode(message)
assert wire == "@16|!3"
assert receiver.decode(wire) == message
assert sender.encode({"task": 42, "intent": "status"}) == "?"
```

### Two cooperating agents: authenticated host transport required

Use `MicroEndpoint` when exchanging frames between two *applications hosting* agents. It negotiates a matching codebook, includes host-level sequence numbers, rejects replayed/missing frames, and keeps each conversation direction's context separate. The *host* transports the `Frame`; the **LLM only needs the micro payload** when its prompt already specifies the grammar.

```python
from nexo_micro import MicroEndpoint

alice, bob = MicroEndpoint(), MicroEndpoint()
# Over an authenticated transport in production:
alice.connect(bob.hello())
bob.connect(alice.hello())

frame = alice.send({"task": 42, "intent": "complete", "critical": 3})
print(frame.payload)     # @16|!3
print(frame.to_dict())   # host metadata (not the model's message)
assert bob.receive(frame) == {"task": 42, "intent": "complete", "critical": 3}
```

The initial `Hello` and frame metadata **are not free** if you embed them in prompts. The example is local simulation, not a network server or a security demonstration. Use TLS with authenticated peers, application authorization and persistent replay protection if needed. See [security](SECURITY.md).

### Typed macro dictionary

```python
from nexo_micro import Macro, MicroSession

macro = Macro("review_diff", "A", ("files", "critical"))
a, b = MicroSession(macros=(macro,)), MicroSession(macros=(macro,))
assert a.fingerprint == b.fingerprint  # check this over trusted transport
msg = {"task": 42, "intent": "macro", "name": "review_diff", "args": {"files": 7, "critical": 3}}
assert b.decode(a.encode(msg)) == msg
```

`train_macros()` greedily assigns short code letters using observations and a supplied tokenizer. It does **not** train a model, infer meanings or guarantee an optimal codebook. Negotiate and pin the codebook on both peers before exchanging messages.

### Token-aware fallback

```python
# pip install 'nexo-micro[bench]'
import tiktoken
from nexo_micro import MicroSession, choose, receive

encoding = tiktoken.get_encoding("o200k_base")
count = lambda text: len(encoding.encode(text))
a, b = MicroSession(), MicroSession()
choice = choose(a, {"task": 42, "intent": "complete", "critical": 3}, count)
assert receive(b, choice) == {"task": 42, "intent": "complete", "critical": 3}
print(choice.format, choice.payload, choice.micro_tokens, choice.json_tokens)
```

`choose()` compares **bare payloads** to compact JSON using the supplied tokenizer. A real service must also account for setup prompts, host framing that enters prompts, both directions, retries and model correctness. For a small one-off message, plain JSON may be better.

## Reproducible experiments

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
ruff check src tests examples
python -m nexo_micro bench --bytes-only --repeats 10
python -m nexo_micro bench --encoding o200k_base --repeats 100
python -m nexo_micro bench --encoding cl100k_base --repeats 100
python -m build
python -m twine check dist/*
```

Benchmarks compare conventional JSON, short-key JSON, stateful JSON, Micro, Micro plus a one-time grammar primer, and per-message adaptive selection. CI publishes a JSON artifact of tokenizer results. **Do not extrapolate this synthetic corpus to real chat or total API billing** without a held-out workload and verified model outputs. See [benchmark methodology](docs/BENCHMARKS.md).

## Scope and open-source status

- API: `MicroSession`, `Macro`, `MicroEndpoint`, `Hello`, `Frame`, `choose`, `receive`, `train_macros`.
- Strict, versioned integer-only syntax with canonical base36 and atomic state updates; no arbitrary string substitution.
- JSON fallback remains explicit and structured. Transport encryption, agent discovery, tool execution and general natural-language compression are **out of scope**.
- Prior work exists in compact representations and agent coordination. See [research map](docs/RESEARCH.md). No assertion of being the first protocol of its kind is made.
- **MIT licensed**: use, modification, distribution and commercial usage are permitted with the required license notice. Contributions welcome: [CONTRIBUTING.md](CONTRIBUTING.md).

## Publication status

`pyproject.toml`, tests, artifact-build checks and a PyPI Trusted Publishing workflow are provided. **Publishing requires the repository owner to configure a PyPI Trusted Publisher and GitHub environment and explicitly publish a GitHub Release.** The package is not assumed to be on PyPI until a real release succeeds. Instructions: [docs/PYPI.md](docs/PYPI.md).
