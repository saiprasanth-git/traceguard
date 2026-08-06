# Contributing

## Setup

```bash
git clone <repo>
cd traceguard
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Checks

Run all three before opening a pull request:

```bash
ruff check .                                        # lint
pytest                                              # 50 tests
cd examples/altitude_hold && make test && make trace   # example still builds and traces
```

The example is part of the test suite: `tests/test_example_project.py` compiles it
with `gcc -Werror` and asserts it stays at 100% implementation and verification
coverage with zero findings. If TraceGuard ever stops detecting gaps, that test
fails - so do not "fix" it by relaxing the assertion.

## Adding a rule

1. Implement the check in `src/traceguard/analyzer.py`. Append a `Finding`; never
   raise. One run must report every problem in the repository, not stop at the
   first.
2. Take the next free `TGnnn` number. **Numbers are permanent** - they appear in
   users' waiver files and review records, so renaming or renumbering is a
   breaking change.
3. Write the message so it names the fix, not just the problem. Compare
   "No source code carries an @implements annotation for this LLR" against
   "trace error".
4. Register it in `cli.RULES` so `traceguard rules` documents it.
5. Update the rule tables in `README.md` and `docs/annotation-reference.md`.
6. Add two tests in `tests/test_analyzer.py`: one project that provokes exactly
   that finding, and - where a similar-looking situation exists - one that proves
   the rule stays quiet.

## Adding language support

Annotation detection is regex-based, so any language whose comments can hold
`@implements LLR-...` already works with no code change; just extend the `code`
and `tests` globs in `traceguard.toml`.

Only symbol resolution (the readable name in reports) is language-specific. Add a
matcher in `parsers._lookahead_symbol` alongside `_c_symbol` and `_PY_SYMBOL`.
Keep it best-effort: if no symbol is found the file stem is used, and the trace
link must never be lost because of it.

## Style

- Line length 100, enforced by ruff.
- Type hints on public functions.
- No third-party runtime dependencies. Standard library only - this keeps the tool
  simple to install on locked-down build agents and simple to reason about if
  anyone ever pursues tool qualification. Development dependencies (`pytest`,
  `ruff`) are fine.
- Docstrings explain **why**, not what. The code says what.
- Layering is strict: `cli -> reporters -> analyzer -> parsers -> model`. Nothing
  lower may import something higher.

## Definition of done

- [ ] `ruff check .` clean
- [ ] `pytest` green
- [ ] `make test && make trace` green in `examples/altitude_hold`
- [ ] New behaviour covered by a test, including the negative case
- [ ] Documentation updated in the same change set
- [ ] `CHANGELOG.md` updated
