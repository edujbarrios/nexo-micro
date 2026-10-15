# Contributing to NEXO Micro

Contributions are welcome under the MIT license.

1. Open an issue describing the use case, protocol compatibility and expected benefit.
2. Create a topic branch; run `python -m pip install -e '.[dev]'`, `python -m pytest -q`,
   `ruff check src tests examples` and `python -m build`.
3. Add tests for every change, especially malformed frames, atomic state transitions and benchmarks.
4. Avoid breaking the `micro/1` syntax. Protocol changes require a new version and golden vectors.
5. Do not claim token savings without specifying tokenizer, corpus, setup overhead and measurement method.
6. Open a pull request. Never commit secrets, user transcripts or private data.

By contributing you agree that your work is distributed under the MIT license.
See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
