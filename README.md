# SMPC Prototype

A local, educational simulation of three hospitals sharing private counts with
three servers. Additive sharing requires all three servers; Shamir sharing can
recover the total from two. The walkthrough displays private inputs and shares
for teaching purposes; real participants only receive their addressed messages.

Install and run from the repository root (Python 3.12+ and `uv` required):

```bash
uv sync
uv run python main.py
```

Choose 1 for additive sharing, 2 for Shamir with server 2 offline, 3 to run the
existing pytest suite, or 4 to exit. Both demonstrations use inputs
`[20, 25, 30]`, modulus `127`, and reconstruct `75`. Option 3 executes the
same tests as:

```bash
uv run python -m pytest -q
```

For the informative T9 randomness diagnostic:

```bash
uv run python -m pytest -q -s tests/test_protocol.py -k t9
```
