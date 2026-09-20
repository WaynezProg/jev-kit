# Authored retrieval-assisted coding fixture

This is an intentionally small, **authored synthetic utility repository**. It
is not a production repository and its eight bug reports do not measure real
software-engineering productivity. It supplies a controlled test of whether
retrieval/reranking puts the repair target into a fixed top-five context.

The corpus contains 48 standalone, stdlib-only Python functions across eight
modules. Each task names behavior but neither a module path nor symbol. The
retrieval corpus strips function docstrings and comments before scoring, so
descriptive prose cannot state the corrected requirement verbatim. The
benchmark retrieves a fixed top 30 candidates. Normal repair arms give a model
only a selected five snippets, while the `full30` control gives it all 30. It
must return a target ID and a complete replacement for that one function.
`references.json` and test paths are never part of that model input.

`verify_fixture.py` is a preflight: every baseline must fail its own test, and
each hidden reference replacement must pass in an isolated copied fixture.
Run it with `python3 verify_fixture.py`. `corpus.json` is generated once using
`build_corpus.py` and then checked in. Do not regenerate it after a measured
campaign begins.
