# Micro/1 protocol specification (experimental)

Micro/1 is a **semantic**, stateful encoding for a fixed set of typed events, not lossless arbitrary text. This document is normative for v0.1.x; future breaking changes require `micro/2`.

## Grammar

All bytes are ASCII. `N` is uppercase canonical base36 (`0-9A-Z`), no leading zeros except `0`, `0 <= N <= 2^53-1`.

```abnf
message    = event / bind / (bind "|" event)
bind       = "@" number
event      = "?" / ">" / "!" number / "~" number / "x" number / macro
macro      = "^" %x41-5A *("." number)
number     = "0" / (%x31-39 / %x41-5A) *(DIGIT / %x41-5A)
```

The grammar alone is insufficient: parser must also enforce macro arity, codebook fingerprint, numerical limits, and exact event types. `~N` has range `[0,100]`. No whitespace or lowercase base36 is accepted. A bind-only `@N` is supported by `MicroSession.decode()` for explicit initial state setup.

| Event | Object shape | Example |
| --- | --- | --- |
| status | `{ "intent":"status", "task":42 }` | `@16|?` |
| progress | `{ "intent":"progress", "task":42, "percent":80 }` | `~28` after binding |
| complete | `{ "intent":"complete", "task":42, "critical":3 }` | `!3` after binding |
| error | `{ "intent":"error", "task":42, "code":4 }` | `x4` after binding |
| next | `{ "intent":"next", "task":42 }` | `>` after binding |
| macro | `{ "intent":"macro", "task":42, "name":"review_diff", "args":{"files":7,"critical":3} }` | `^A.7.3` after binding |

`task` must be specified by sender until a task is already bound. A different task requires `@N|`. Short events do **not** include their task identity; a receiver with an incorrect active task will interpret them incorrectly. Agent host code must enforce strict ordering or reject messages and resynchronize.

### Golden vectors

```text
@16|?      -> {"intent":"status","task":42}
~28        -> {"intent":"progress","task":42,"percent":80}
!3         -> {"intent":"complete","task":42,"critical":3}
x4         -> {"intent":"error","task":42,"code":4}
>          -> {"intent":"next","task":42}
@RR|!0     -> {"intent":"complete","task":999,"critical":0}
^A.7.3     -> custom pre-agreed Macro('review_diff','A',('files','critical')) on task 42
```

Invalid strings including `@16|~2T`, `!00`, `^A.1.2` with wrong codebook, and empty frames **must fail**. The implementation limits micro payload length to 120 characters and individual integers to interoperable 53-bit precision.

## Negotiation and host framing

- Both peers exchange `Hello(protocol='micro/1', dictionary=fingerprint, session_id=random)` **through an authenticated channel**. A mismatch aborts communication; the fingerprint is a truncated SHA-256 collision-detection aid, *not* an authentication mechanism.
- `MicroEndpoint` maintains independent incoming and outgoing `MicroSession` instances. Do **not** share one mutable state machine across two directions.
- For each direction, `Frame(session_id, sequence, format, payload)` is sent out-of-band and inspected by the host. Host accepts only the expected sequence and session ID, commits decoded state only after successful validation, and never interprets unauthenticated macro definitions.
- `format` is either `micro/1` or `json`. The latter is compact JSON with the same narrowly defined event schema. No arbitrary JSON input can invoke new capabilities.
- In a network deployment use authenticated TLS, limits on inbound JSON, strict connection binding and session restarts on packet loss. Current code does **not** include networking, persistent sequence storage, encryption, authorization or durable replay prevention.

## Macro registry

`Macro(name, code, parameters)` is static within one session. `name` and all parameter names are lowercase snake_case (1-40 chars), code is exactly one uppercase ASCII letter, and up to three unique integer parameters are allowed. Names/codes cannot duplicate. Peers compare a deterministic 16-hex-digit fingerprint of sorted macro schemas with protocol version.

Never infer unknown macro semantics from free text. A macro is metadata, not executable code. Applications must authorize resulting actions separately.

## Model visibility and efficiency

An LLM must be instructed how to interpret and emit the grammar, and in some cases given macro meanings. That prompt may dominate a short dialogue. The host-level handshake and frame fields are **not model-facing** by default; inserting them in the prompt increases token cost. Stateful codecs reduce redundant information only when peers already share the same task state.
