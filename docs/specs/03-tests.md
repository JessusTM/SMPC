# 03 - Verification and Tests

## Goal

Use `pytest` to check the behavior defined in `01-core.md` and `02-shamir.md`, following the final report's **T1-T10** test plan.

Keep the tests straightforward, with names containing the corresponding test ID. Use clear English comments, simple `assert` statements, and explicit loops. Do not use complex fixtures, comprehensions, statistical libraries, or mocks unless absolutely necessary.

T1–T10 are plan IDs, not the number of pytest functions: some checks can share a function, and the additional contract checks may use separate functions. Menu option 3 in `01-core.md` introduces this plan without an advance table, then displays the actual verbose pytest function names, statuses, failure details, and summary counts (including errors) from that run.

## Test files

- `tests/test_protocol.py`: tests T1-T9 for the additive protocol.
- `tests/test_shamir.py`: T10 and small checks for Shamir.

Test inputs may be generated with a **seeded `random.Random`** instance to make test cases reproducible. The secret-sharing implementation must always use **`secrets`** for its random values.

## T1 - Random valid inputs

- Run **1,000** additive protocol executions using three randomly selected integers in `[0, max_value]`.
- Verify that every result equals the sum of the three original inputs.
- Requirements: F1, F2, F3.

## T2 - Maximum allowed inputs

- Use `[40, 40, 40]` with `p = 127`.
- Expect `120`.
- Requirements: F1, F3, R1.

## T3 - Zero inputs

- Use `[0, 0, 0]`.
- Expect `0`.
- Requirements: F1, F3.

## T4 - Invalid modulus

- Create `Parameters(n=3, m=3, p=120, max_value=40)`.
- Expect Pydantic to reject the configuration because `p <= n * max_value`.
- Requirement: R1.

## T5 - Invalid hospital values

- Test a hospital with `-1` and with `41` when `max_value = 40`.
- Expect each value to be rejected before shares are generated.
- Requirement: R1.

## T6 - Duplicate share

- Send one valid share to a server, then send a second share from the same hospital for the same session.
- Expect the second call to `receive_share()` to return `False` and preserve the original stored share.
- Requirement: F2.

## T7 - Wrong session ID

- Send a share whose `session_id` differs from the server's active session.
- Expect `receive_share()` to return `False` without storing the share.
- Requirement: F2. This test checks session validation, not TLS.

## T8 - One additive server unavailable

- Run `run_additive()` with server 2 offline.
- Expect `ProtocolError`, because the analyst cannot receive all three partial sums. No total is returned.
- Requirement: D1.

## T9 - Informative uniformity check

This is a **statistical diagnostic**, not a mandatory pass/fail security test. It must **not** fail the test suite merely because of random variation.

- Fix a hospital input, for example `20`, and generate its first additive share **30,000 times** with `p = 127`.
- Group the observed share values into **10 buckets** using simple loops.
- Calculate the expected frequency in each bucket according to how many values in `0..126` belong to it; the buckets do not all have exactly the same size.
- Calculate Pearson's chi-square statistic using the observed and expected frequencies:

```text
chi_square += (observed - expected) ** 2 / expected
```

- Compare the resulting statistic with `27.88`, the approximate critical value for 9 degrees of freedom and a significance level of `0.001` from the course notes.
- **Report** the value and whether it is at or below the threshold. Do not assert that it must always be below `27.88`.
- It is acceptable to assert basic non-statistical conditions, such as all generated shares belonging to `0..126`.
- Requirement: P1.

Name the test with `t9` and print the statistical result. To view that output explicitly, use the dedicated T9 command below.

This check can help detect poor random generation; it does not prove privacy or cryptographic unpredictability.

## T10 - Shamir reconstruction from any two servers

- Use the report's three example partial sums: `z_1 = 81`, `z_2 = 87`, and `z_3 = 93` with `p = 127`.
- Verify that pairs `(1, 2)`, `(1, 3)`, and `(2, 3)` each reconstruct `75` using `reconstruct_pair()`.
- Run the complete Shamir simulation three times, with a different server offline each time. Expect `75` in every run.
- Requirements: F3, D1.

## Additional simple contract checks

These are small implementation checks, **not** extra numbered tests:

- Additive shares sum to the hospital input modulo `p`.
- A server rejects an invalid origin, destination, value outside `Z_p`, or repeated share.
- A server with missing hospital shares raises `ProtocolError` during aggregation.
- The analyst rejects an invalid session, server ID, or repeated partial sum.
- The analyst raises `ProtocolError` if Shamir reconstruction is attempted with only one partial.
- Shamir rejects a non-prime modulus even when `p > n * max_value`.
- Pydantic models reject invalid types, unexpected fields, and attempts to modify them.

Use a few clear tests for related behaviors; do not add files just to separate these checks.

## Traceability

| Requirement | Verification |
| --- | --- |
| F1 | T1, T2, T3: hospital contribution and sharing. |
| F2 | T1, T6, T7: server aggregation and message checks. |
| F3 | T1, T2, T3, T10: reconstruction. |
| P1 | T9: informative statistical check. |
| P2 | T7 checks the session ID; TLS is not executed in the local simulation. |
| D1 | T8 detects an unavailable server; T10 verifies Shamir tolerance. |
| R1 | T2, T4, T5: allowed inputs and parameters. |

## Commands

Run from the repository root:

```bash
uv sync
uv run python -m pytest -q
uv run python -m pytest -q -s tests/test_protocol.py -k t9
uv run python main.py
```

The third command displays the informative T9 statistic; menu option 3 need not display T9's captured output. The other numbered tests and additional contract checks must pass normally.

## Completion criteria

1. T1-T8 and T10 pass, and T9 runs and reports its statistic without an arbitrary random failure blocking the suite.
2. The additional contract checks pass.
3. `main.py` shows the normal additive result and successful Shamir reconstruction; T8 verifies the unavailable-server additive failure through automated tests.
4. The implementation matches the report's interfaces and the coding rules in `01-core.md`.
5. Do not claim that the tests passed until they have actually been executed.
