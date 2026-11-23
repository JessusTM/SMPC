# 02 - Shamir 2-of-3 Extension

## Goal

Implement the Shamir 2-of-3 extension proposed in the course report. Keep the additive 3-of-3 protocol unchanged. The user can run either protocol explicitly.

The same three hospitals and three servers participate. Only share generation and reconstruction change; server aggregation and message models remain the same.

## Rules

- Exactly `n = 3` hospitals and `m = 3` servers; the reconstruction threshold is `2`.
- Work with the existing `Parameters`, `Share`, and `PartialSum` models in `src/models.py`.
- Require a **prime** modulus `p > 3` and `p > n * max_value`, so server positions `1`, `2`, and `3` are distinct field elements. Additive `Parameters` may still accept `p = 2` when `max_value = 0`.
- Choose a new, independent, uniform random coefficient for each hospital with `secrets.randbelow(p)`.
- Any two distinct server partial sums can reconstruct the total. One partial sum is insufficient.
- Use the same readable Python style, docstrings, inline comments, and simple error handling from `01-core.md`.
- Do not create new participant classes, message models, or a generic protocol framework.

## 1. Share generation

Each hospital has a private input `x_i`. Choose a random coefficient `a_i` and form a degree-one polynomial:

```text
f_i(t) = (x_i + a_i * t) % p
```

Evaluate it at server positions `t = 1`, `2`, and `3`:

- Server 1 receives `f_i(1)`.
- Server 2 receives `f_i(2)`.
- Server 3 receives `f_i(3)`.

Only the shares leave the hospital. The hospital does not send `x_i` or `a_i`.

## 2. Aggregation

Reuse `Server.receive_share()` and `Server.aggregate()` **without changing them**:

```text
z_j = (f_1(j) + f_2(j) + f_3(j)) % p
```

The server partial sums are values of the combined polynomial:

```text
F(t) = (x_1 + x_2 + x_3) + (a_1 + a_2 + a_3) * t  (mod p)
```

Therefore, `F(0)` is the desired total `S`.

## 3. Reconstruction

For two different server IDs `u` and `v`, and their partial sums `z_u` and `z_v`, use Lagrange interpolation at zero:

```text
S = (v / (v - u) * z_u + u / (u - v) * z_v) mod p
```

**Modular division is not ordinary Python division.** Use `pow(denominator, -1, p)` to compute each required modular inverse.

The three possible pairs are:

```text
Servers (1, 2): S = (2 * z_1 - z_2) % p
Servers (1, 3): S = ((3 * z_1 - z_3) * pow(2, -1, p)) % p
Servers (2, 3): S = (3 * z_2 - 2 * z_3) % p
```

Implementation should follow the **general interpolation formula**, not three separately hard-coded formulas. When three partials are present, select the first two server IDs in ascending order. With fewer than two partials, raise `ProtocolError`.

## 4. Functions and responsibilities

### `src/shamir.py`

- `is_prime(value: int) -> bool`: check primality with a simple loop and no additional library.
- `create_shamir_values(value: int, p: int) -> list[int]`: generate the random coefficient and return the three share values in server order.
- `reconstruct_pair(u: int, z_u: int, v: int, z_v: int, p: int) -> int`: validate distinct server IDs in `1..3`, use modular inverses, and return `S`.
- Both functions reject a Shamir modulus `p <= 3` with `ValueError`, even if it is prime.

Keep each function short. Do not add separate classes for polynomial arithmetic.

### `src/hospital.py`

- `create_shamir_shares(session_id) -> list[Share]`: use `create_shamir_values()` with the hospital's existing input; create the three `Share` messages. Do not alter `create_additive_shares()`.

### `src/analyst.py`

- `reconstruct_shamir() -> int`: require at least two valid partial sums, choose two distinct server IDs in ascending order, then call `reconstruct_pair()`. Do not alter `reconstruct_additive()`.

### `src/simulation.py`

- `run_shamir(values: list[int], parameters: Parameters, offline_server: int = 0) -> int`: follow the existing local delivery flow, but generate Shamir shares and use Shamir reconstruction.
- Validate that `p` is prime and greater than `3` before starting. Use `ValueError` for an invalid Shamir configuration.
- Use `offline_server = 0` for normal execution or `1`, `2`, `3` to simulate one unavailable server.

Reusing small common steps is acceptable, but do not introduce unnecessary abstractions or duplicate mathematical logic.

## 5. Worked example from the report

These coefficients are **only for the written example**, not for real share generation:

```text
p = 127
max_value = 40
hospital values = [20, 25, 30]
coefficients = [1, 2, 3]

Hospital 1 shares = [21, 22, 23]
Hospital 2 shares = [27, 29, 31]
Hospital 3 shares = [33, 36, 39]

Server partial sums = [81, 87, 93]
Expected total = 75
```

Verify reconstruction with all pairs:

```text
(1, 2): (2 * 81 - 87) % 127 = 75
(1, 3): ((3 * 81 - 93) * 64) % 127 = 75
(2, 3): (3 * 87 - 2 * 93) % 127 = 75
```

Here, `64` is the modular inverse of `2` modulo `127`: `(2 * 64) % 127 == 1`.

## Acceptance criteria

- The original additive methods are unchanged and still work.
- Shamir creates three shares per hospital using a fresh, secure random coefficient.
- Servers use the same aggregation implementation as the additive protocol.
- All three example pairs reconstruct `75`.
- `run_shamir([20, 25, 30], parameters, offline_server=j)` returns `75` for each `j` in `1..3`.
- A single partial sum cannot reconstruct the result.
- The Shamir tests defined in `03-tests.md` pass.
