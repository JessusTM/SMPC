# 01 - Core SMPC Protocol and Terminal Demonstration

## Goal

Implement the additive 3-of-3 secret-sharing protocol from the course report as a small, local Python simulation. Three hospitals share private patient counts with three servers. Each server calculates a partial sum, and the analyst reconstructs the total.

The additive protocol is the **main protocol**. Shamir 2-of-3 is the separate extension defined in `02-shamir.md`.

The program is also a **step-by-step educational demonstration**: show how the real values produced by each execution move through the three phases, rather than printing only the final total.

## Project structure

The repository is named `smpc`. Put the modules directly inside **`src/`**, without another package folder.

```text
smpc/
├── specs/
│   ├── 01-core.md
│   ├── 02-shamir.md
│   └── 03-tests.md
├── src/
│   ├── __init__.py
│   ├── models.py
│   ├── hospital.py
│   ├── server.py
│   ├── analyst.py
│   ├── shamir.py
│   └── simulation.py
├── tests/
│   ├── test_protocol.py
│   └── test_shamir.py
├── main.py
├── pyproject.toml
└── README.md
```

Use simple imports, for example `from src.models import Parameters`. Do not create additional layers, modules, or frameworks unless absolutely necessary.

## Technology and coding style

- Python 3.12+, Pydantic v2, `pytest`, `uv`, and **Rich** for terminal formatting. Prefer Python's standard library for everything else.
- Use Rich only for presentation, mainly `Console`, `Table`, `Panel`, `Padding`, and `Text`. No graphical interface, web server, or advanced terminal widgets.
- All code, names, docstrings, inline comments, tests, and messages printed in the terminal must be in **English**.
- Use familiar Python: regular classes, dictionaries, lists, explicit `for` loops, and clear `if` statements.
- Do **not** use comprehensions, generator expressions, lambdas, nested ternaries, or one-line `if`, `for`, or `while` statements. Do not place a loop and a condition in the same expression.
- Follow the single-responsibility principle: one clear purpose per function. Prefer small functions and avoid creating many tiny helpers without a need.
- Every Python file begins with a docstring explaining its purpose. Classes and functions have short, clear docstrings.
- Add simple inline comments in English to explain meaningful steps in each function. Do not comment every obvious line.
- Avoid inheritance hierarchies, abstract classes, dependency injection, design patterns, asynchronous code, and complex exception handling.
- Use Pydantic validation errors for invalid models, `ValueError` for invalid inputs or arguments, and **one** custom `ProtocolError` for an incomplete session. Do not create an exception hierarchy or broad `except` blocks.

## Fixed simulation parameters

- Exactly **3 hospitals** (`n = 3`) and **3 servers** (`m = 3`), identified by numbers 1, 2, and 3.
- Maximum hospital input: `max_value = 40`, corresponding to `M` in the report.
- Default modulus: `p = 127`. It satisfies `p > n * max_value = 120` and is prime, so both protocols can use it.
- Hospital inputs for both menu options: `[20, 25, 30]`; expected result: `75`.
- Create a fresh `session_id` with `secrets.token_hex(8)` for each execution.
- `offline_server = 0` means all servers are available. Values `1`, `2`, or `3` represent an unavailable server.
- Run everything locally and synchronously. Messages are passed through method calls, not across a real network. Simulate a missing response without real waiting or timers.
- Do not add sockets, TLS implementation, Docker, cloud services, databases, logging systems, or retries.

## Data models: `src/models.py`

Use Pydantic `BaseModel` only for the following three models. Configure strict validation, immutable models (`frozen=True`), and rejection of unexpected fields (`extra='forbid'`). Keep validators simple.

### `Parameters`

Fields:

- `n: int` — must equal `3`.
- `m: int` — must equal `3`.
- `p: int` — must be at least `2` and satisfy `p > n * max_value`.
- `max_value: int` — must be nonnegative.

Reject invalid configurations when the model is created. Pass the same `Parameters` object to the participants; do not repeat these numbers inside their methods.

### `Share`

Represents the report's `Fragmento(sid, i, j, s_ij)` message.

- `session_id: str` — nonempty.
- `origin: int` — hospital ID.
- `destination: int` — server ID.
- `value: int` — nonnegative share.

The receiving server checks the IDs, the active session, the range `0 <= value < p`, and duplicates.

### `PartialSum`

Represents the report's `SumaParcial(sid, j, z_j)` message.

- `session_id: str` — nonempty.
- `server_id: int` — server ID.
- `value: int` — nonnegative partial sum.

The analyst checks the IDs, the active session, the range `0 <= value < p`, and duplicates.

### `ProtocolError`

Define one small custom exception for an incomplete session, such as missing shares or missing partial sums.

## Hospital: `src/hospital.py`

Class: `Hospital(hospital_id, value, parameters)`.

- Require `hospital_id` to be in `1..n`.
- Require `value` to be an integer, but not a boolean, and `0 <= value <= max_value`.
- Keep the hospital's original input inside its object. Never include that input in the `Share` message.

Method: `create_additive_shares(session_id) -> list[Share]`.

1. Generate `m - 1` independent random values using `secrets.randbelow(p)`.
2. Compute the final share using `(value - sum(first_shares)) % p`.
3. Create a `Share` for each server, numbered `1..m`.
4. Return the list. Do not print from this method.

The shares must satisfy `(s_1 + s_2 + s_3) % p == value`.

Shamir share generation belongs to `02-shamir.md`.

## Server: `src/server.py`

Class: `Server(server_id, parameters, session_id)`.

Store the received shares in one dictionary named `shares`, keyed by `(session_id, origin)`. A server stores only shares addressed to itself.

Method: `receive_share(share: Share) -> bool`.

1. Check the session ID, destination, hospital ID `1..n`, and `0 <= value < p`.
2. Check that this hospital has not already sent a valid share in the current session.
3. If invalid or duplicated, do not change the dictionary and return `False`.
4. Otherwise save the share and return `True`.

Method: `aggregate() -> PartialSum`.

1. Require one valid share from each of the three hospitals. Otherwise raise `ProtocolError`.
2. Compute `z_j = sum(received_values) % p`.
3. Return a `PartialSum` for this server and session.

## Analyst: `src/analyst.py`

Class: `Analyst(parameters, session_id)`.

Store partial sums in a dictionary named `partials`, keyed by `server_id`.

Method: `receive_partial(partial: PartialSum) -> bool`.

1. Check the session ID, server ID `1..m`, and `0 <= value < p`.
2. Reject a duplicate partial from the same server.
3. Return `False` if rejected, leaving the dictionary unchanged. Otherwise store it and return `True`.

Method: `reconstruct_additive() -> int`.

1. Require a valid partial sum from all three servers. Otherwise raise `ProtocolError`.
2. Compute and return `S = sum(partial_values) % p`.

Shamir reconstruction belongs to `02-shamir.md`.

## Simulation: `src/simulation.py`

Keep the simulation separate from terminal formatting. It must perform the actual protocol operations by calling the participant methods. Do not repeat sharing, aggregation, or reconstruction formulas inside the simulator.

Function:

```python
run_additive(
    values: list[int],
    parameters: Parameters,
    offline_server: int = 0,
    trace: dict | None = None,
) -> int
```

1. Check that exactly three input values were provided and that `offline_server` is valid.
2. Create a fresh session, three hospitals, three servers, and one analyst.
3. Generate the hospital shares and deliver them to the corresponding available servers.
4. Aggregate the shares on each available server and send its partial sum to the analyst.
5. Reconstruct the additive total. Raise `ProtocolError` if a required partial is missing.
6. Return the integer total, just as before.

### Optional educational trace

The optional `trace` is a **plain dictionary passed by the caller**. If provided, fill it with the values from the same execution:

- `session_id`: the generated session identifier.
- `generated_shares`: a list of the real `Share` messages generated by the hospitals.
- `partial_sums`: a list of the real `PartialSum` messages produced by available servers.
- `offline_server`: the server number marked unavailable, or `0`.
- `total`: the reconstructed total, only when reconstruction succeeds.

Record each item when it is produced so that the dictionary also contains useful intermediate data if a session fails. Do not invent example shares for the output. The optional dictionary must not change the returned value or normal protocol behavior.

The demonstration in `main.py` may also display the known hospital inputs, because this is an **educational, local view of the whole simulation**. The actual server and analyst methods must not gain access to inputs they are not supposed to know.

Use the same optional trace idea for `run_shamir()` in `02-shamir.md`, additionally recording the **random coefficient chosen by each hospital** so the polynomial calculations can be displayed. Those coefficients must come from the actual Shamir execution, not from a second random generation. Keep the existing integer return value for the automated tests.

## Terminal interface: `main.py`

`main.py` is the only file responsible for terminal interaction and Rich formatting. It must not implement or duplicate the mathematics of the protocol.

Run the program from the repository root:

```bash
uv run python main.py
```

Show exactly four menu choices (three actions and Exit):

```text
SMPC Prototype

1. Additive Secret Sharing (3-of-3)
2. Shamir Secret Sharing (2-of-3)
3. Run Automated Tests
4. Exit

Select an option:
```

- Use a simple `while` loop for the menu. After a completed demonstration, return to the menu.
- Handle invalid menu choices with a short message and show the menu again.
- Use the fixed inputs `[20, 25, 30]` and `p = 127`. Do not ask for custom input values, settings, or server numbers.
- Selecting option 1 or 2 executes the selected protocol once. Use the collected trace to **present the phases in order**, pausing with `input()` and a `Press Enter to continue...` prompt between them. Option 3 runs the tests; option 4 exits.
- Use only simple Rich elements (`Console`, `Table`, `Panel`, `Padding`, `Text`) and a small number of colors. Avoid progress bars, animations, ASCII art, or extra menus.
- Display the actual computed numbers from the execution. They will normally change between runs because randomness is regenerated, but the correct total remains `75`.
- The educational display intentionally shows all values, including private inputs, shares, and Shamir coefficients. This is a privileged view for explaining the algorithm, **not** what one server or the analyst can observe in the actual protocol.

### Menu option 1: Additive Secret Sharing (3-of-3)

Run the additive protocol with **all three servers available**. Show its three phases:

**Phase 1 — Sharing**

- Label the first panel `Number of hospitals (n): 3`, `Number of servers (m): 3`, `Maximum patients per hospital (M): 40`, `Modulus (p): 127`, and `Session ID (sid):` followed by the actual ID. Directly below it, without another panel, show this subdued quote verbatim: `Session ID generated using secrets.token_hex(8) to identify this execution.`
- Show hospital inputs `H1 = 20`, `H2 = 25`, and `H3 = 30`.
- Display a Rich table with one row per hospital and columns for its input and three generated shares.
- Start with a brief explanation that each hospital divides its input into three shares, one for each server, choosing two secure random shares in `Zₚ` and calculating the third; retain the user's agreed wording for this introduction. Before the worked calculations, add a brief English transition. Show `sᵢ,₃ = (xᵢ − sᵢ,₁ − sᵢ,₂) mod p` and `(sᵢ,₁ + sᵢ,₂ + sᵢ,₃) mod p = xᵢ`; define `i` and `j` in a small subdued italic left-bar note like the session note. For each hospital, substitute its actual input and shares on separate indented, highlighted lines: show subtraction before modulo (including negative values), the resulting third share, and a green check that its three actual shares sum to its input modulo `p`.
- The displayed shares must come from the current execution.

**Phase 2 — Aggregation**

- Explain `z_j = (sum from i=1 to n of s_i,j) % p`, specialize to `n = 3`, and define hospital index `i`, server index `j`, and partial `z_j` in a small subdued italic left-bar note. Add a brief English transition before the worked calculations. For each server show its three received shares, the substituted sum before modulo, and its traced `z_1`, `z_2`, or `z_3`.

**Phase 3 — Reconstruction**

- Explain `S = (sum from j=1 to m of z_j) % p`, specialize to the three terms, and define `j` and `S` in a small subdued italic left-bar note. Add a brief English transition before the worked calculations. Show the analyst receiving all three traced partials, their substituted sum before modulo, the final `S = 75`, and a check against `20 + 25 + 30 = 75`.
- Pause as needed, then return to the main menu.

### Menu option 2: Shamir Secret Sharing (2-of-3)

Run the Shamir extension with **server 2 unavailable**. Use the same inputs and parameters. Show its three phases:

**Phase 1 — Polynomial sharing**

- Show the session ID, parameters, and hospital inputs.
- Explain the degree-at-most-one polynomial `f_i(t) = (x_i + a_i * t) % p` and define `x_i`, `a_i`, `t`, `p`, and `i` in a small subdued italic left-bar note. Add a brief English transition before the worked polynomial evaluations. For each hospital show its actual coefficient and polynomial, then substitute `t = 1, 2, 3` with the arithmetic before modulo and each traced share.
- Mark the shares for server 2 as generated but **not delivered**, because that server is unavailable.

**Phase 2 — Aggregation**

- Use the same general three-hospital aggregation formula and symbol definitions as in the additive walkthrough, with a small subdued italic left-bar note. Add a brief English transition before the worked calculations. Show the received shares, actual pre-modulo sum and traced `z_1` and `z_3` for the available servers; server 2 has no partial.

**Phase 3 — Lagrange reconstruction**

- Start with the general two-partial formula `S = (v / (v − u) × zᵤ + u / (u − v) × zᵥ) mod p`; define `u`, `v`, `zᵤ`, `zᵥ`, `p`, and `S`, and explain that division is modular in a small subdued italic left-bar note. Add a brief English transition before the worked Lagrange reconstruction. Show full aligned, indented, highlighted steps for servers 1 and 3: substitute their IDs in both fractions, simplify to `(3 × z₁ − z₃) / 2`, substitute both traced partials, show `pow(2, -1, 127) = 64`, the actual numerator and its multiplication by 64 before modulo, and `S = 75`. This changes only the display, not interpolation logic.
- Pause as needed, then return to the main menu.

### Menu option 3: Run Automated Tests

- Introduce option 3 with this exact sentence: `These automated tests verify protocol correctness, input validation, message handling, and server failures.` Mention the T1–T10 plan in `03-tests.md` and the additional contract checks, distinguishing plan IDs from the actual number of pytest functions; do not show an advance T1–T10 table. T9 is informative and does not fail solely because of random variation.
- Run the existing `pytest` suite from `tests/` using Python's standard library. Do not implement a second test runner or duplicate test logic in `main.py`.
- From `main.py`, use `subprocess.run()` with `sys.executable`, `-m`, `pytest`, `-v`, `--no-header`, `--tb=short`, and optionally `tests/`. This uses the current Python environment started by `uv`. Show real pytest function names and their PASSED/FAILED status, retaining failure details; capturing and reprinting the output is allowed.
- After the test process finishes, show actual summary counts (including errors when present) from that run and success/failure status based on the subprocess exit code; never hard-code a test count or claim success before the run finishes. Do not hide failure details.
- Let the user press Enter to return to the main menu.
- Do not require extra files, a test framework wrapper, or advanced subprocess handling.
- The T9 statistical diagnostic remains informative: it reports its statistic but does not fail solely due to random variation, as defined in `03-tests.md`.

### Menu option 4: Exit

Exit normally after a short message. Do not require extra confirmation.

### Presentation rules

- Keep all user-facing text short and in English, like a clear classroom walkthrough.
- Present each phase top-to-bottom: purpose, general formula, symbol meanings, a brief English transition, actual substitutions, intermediate arithmetic, result, and a brief green check where useful. Keep the existing Rich panels, share table, colors, and pauses. Use `Padding` and `Text` for consistent math layout: indent general formulas and participant headings by 4 spaces, and participant operations, substitutions, and checks by 8 spaces. Use readable Unicode symbols, highlighted mathematical lines, and separate intermediate substitution lines instead of long inline equations. Render symbol explanations across both protocols as small subdued italic left-bar notes like the session note, without extra panels. Presentation may calculate arithmetic solely to explain intermediate steps; shares, partials, inverse, and reconstructed total must come from the execution trace, not recomputation.
- Use a compact green final-result panel for both additive and Shamir; preserve the share table and existing phase panels, without adding a panel for the session note.
- Explain **what happened**, rather than printing large objects or raw Pydantic representations.
- Do not print fake results, use hard-coded shares, or modify the protocol to make the display look nicer.
- Keep all `print()`, `input()`, and Rich calls out of `src/` participant classes and mathematical functions.
- Do not run tests automatically at startup or when demonstrating a protocol. Run them only when the user selects option 3. Keep the separate `pytest` commands in `03-tests.md` available.

## README and verification

The `README.md` should briefly explain installation, execution, and how option 3 runs the same `pytest` suite:

```bash
uv sync
uv run python main.py
uv run python -m pytest -q
```

Keep the test plan T1–T10 from `03-tests.md`. The extension should have **at least two independent test functions**: one for reconstruction with different pairs and another for successful reconstruction with a server unavailable. Additional contract tests should remain small.

## Acceptance criteria

1. The additive protocol uses the same participants, messages, and mathematics as the report.
2. Pydantic validates parameters and messages. Invalid inputs, duplicate shares, and wrong sessions are rejected.
3. The additive protocol returns `75` when all servers respond and cannot reconstruct when a server is unavailable.
4. Shamir reconstructs `75` using servers 1 and 3 while server 2 is unavailable, following `02-shamir.md`.
5. `main.py` provides **four choices**: additive demonstration, Shamir demonstration, automated tests, and Exit. Both protocols present their three phases with actual intermediate values.
6. The display uses Rich without mixing presentation code into the protocol implementation.
7. Option 3 introduces the T1–T10 plan and additional checks without an advance table or conflating plan IDs with pytest function counts, runs the existing automated tests, shows real test names and statuses and failure details, and reports actual summary counts including errors and exit status. T9 is informative as in `03-tests.md`. The same tests remain callable separately.
8. The implementation respects the simple, readable English coding style defined above.
