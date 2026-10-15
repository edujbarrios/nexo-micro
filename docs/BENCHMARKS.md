# Measurement methodology — no universal savings claim

Use **specific model/tokenizer**, dataset, language, grammar primer and a well-specified baseline. Bytes saved are *not* model tokens saved. Tokenizer efficiency is *not* semantic correctness or model billing.

## Local synthetic corpus

`python -m nexo_micro bench --bytes-only --repeats 10` counts UTF-8 bytes of 40 event messages (4 messages per task, 10 tasks). It reports `json_compact`, `json_min_schema`, `json_stateful`, `micro`, `micro_with_primer` and `adapted`. Only `micro_with_primer` charges the sample grammar primer once; in a real application this may be provided to multiple model instances or repeated requests. Use `--encoding o200k_base` / `cl100k_base` after installing `tiktoken` to obtain actual tokenizer counts.

The fixture intentionally has short structured status events and a shared state; it demonstrates an **advantageous workload**, not an average across arbitrary conversations. For large/irregular content, JSON or other formats can win. The `adapted` total is only a *payload* comparison, not a benchmark of end-to-end model cost.

## Fair comparisons

- Full compact JSON (explicit task, intent and event fields).
- Minimal-schema JSON (short field names and codes).
- Stateful minimal-schema JSON (shared task binding, similarly to Micro).
- Micro/1 + one-time primer, not just bare Micro frames.
- Strong external candidates (TOON/NEXO) where schemas support them, with **the same semantics**.

## A real model study must record

1. Corpus source and train/test split, anonymized and legally usable.
2. Which model/endpoint, its tokenizer/version, inference parameters and prices.
3. Total prompt + output tokens **including primer, transport metadata if prompted, repetitions and retries**.
4. Task correctness, well-formedness of model-generated micro frames, error recovery and human adjudication where needed.
5. Comparable task quality versus strongest fair baseline, confidence intervals and negative cases.
6. Code, fixed seeds, environment, runs and complete metric artifacts for reproducibility.

The included corpus verifies **deterministic roundtrip** and numerical tokenization only. It does not evaluate an LLM's decoding or generation accuracy and establishes no novel-language priority claim.
