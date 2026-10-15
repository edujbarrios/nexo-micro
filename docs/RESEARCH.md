# Research map (October 2026)

This project must **not** claim to be the first system for compact agent communication. Relevant prior art:

- TOON: https://github.com/toon-format/toon — text format for token-efficient structured data; impressive results on some datasets, not always smaller than minified JSON.
- ACCP: https://datatracker.ietf.org/doc/draft-benzing-accp/ — expired individual Internet-Draft from April 2026 for semantic agent-context compression; not an approved IETF standard.
- AACP: https://www.ietf.org/archive/id/draft-mackay-aacp-03.html — agent action compression/typed coordination; May/June 2026 individual drafts, not IETF standards.
- State Delta Encoding: https://aclanthology.org/2025.emnlp-main.518/ — research in communicating state changes.
- Emergent language survey: https://link.springer.com/article/10.1007/s10458-025-09691-y
- TOON vs JSON generation study: https://arxiv.org/abs/2603.03306 — highlights the cost of prompt instructions ("prompt tax") and model generation error rates.

## What would count as proof?

Record a fixed dataset of actual conversations, target tokenizer and its version, both model input and output tokens, model-side instruction overhead, binary/task bindings, errors and retries, per-message correctness (human or schema judge), total cost, and variance over multiple trials. Include natural language, compact JSON, minimal-schema JSON, original NEXO, and TOON where each baseline is applicable. Split into training and held-out tasks. Calculate savings only for equivalent outcomes.

### Core success test

Compared with the strongest fair baseline, a defined workload must have:

1. Fewer measured **total** tokens, including the amortized one-time primer.
2. Equivalent or better completion correctness and no unacceptable drop in robustness.
3. Reproducible numbers with full source and pinned model/tokenizer versions.
4. Clearly stated limits, confidence intervals and negative examples.

Current prototype has not yet passed this experiment.
