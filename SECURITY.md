# Security Policy

NEXO Micro v0.1.x is experimental. Please report vulnerabilities privately through
[GitHub private vulnerability reporting](https://github.com/edujbarrios/nexo-micro/security/advisories/new)
if enabled, rather than disclosing exploit details publicly.

## Trust boundaries

- **Encoding is not encryption.** No confidentiality, integrity or peer authentication is provided by NEXO Micro.
- Exchange `Hello` and `Frame` using mutually authenticated, encrypted transport and enforce application authorization.
- Sequence checks reject duplicates and out-of-order messages within one connected endpoint; they are **not**
  durable replay prevention across process restarts or multiple workers.
- Don't treat macros or decoded message fields as authorization to execute code, shell commands, payments or writes.
- Don't accept untrusted macro definitions. Only negotiate versioned and audited dictionaries.
- Don't deserialize unbounded network data. Apply independent transport limits to JSON and hello packets.
- Don't log prompts, keys, PII or production task content in public benchmark fixtures.
- Inbound model text is untrusted. Validate decoded instructions and execute actions through authorized host tools.

## Support status

The 0.1 series receives best-effort fixes. No security audit or production hardening is claimed.
