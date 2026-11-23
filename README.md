<div align="center">
  <h1>SMPC</h1>
  <p><em>A simple educational prototype for secure aggregation using secret sharing.</em></p>
  <p>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
    <a href="https://docs.pydantic.dev/"><img src="https://img.shields.io/badge/Pydantic-v2-E92063?style=for-the-badge" alt="Pydantic"></a>
    <a href="https://rich.readthedocs.io/"><img src="https://img.shields.io/badge/Rich-Terminal-555555?style=for-the-badge" alt="Rich"></a>
    <a href="https://docs.pytest.org/"><img src="https://img.shields.io/badge/pytest-Tests-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="pytest"></a>
  </p>
  <p>
    <a href="#about">About</a> ·
    <a href="#capabilities">Capabilities</a> ·
    <a href="#limitations">Limitations</a> ·
    <a href="#setup">Setup</a>
  </p>
</div>

---

## About

**SMPC** is an educational Python prototype that simulates how three hospitals can calculate their total patient count without sending their individual values to the servers. It uses additive secret sharing and a Shamir 2-of-3 extension.

---

## Capabilities

- **Additive 3-of-3:** generates shares, aggregates partial sums, and reconstructs the total using all three servers.
- **Shamir 2-of-3:** reconstructs the total even when one server is unavailable.
- **Interactive terminal:** explains each phase step by step and runs automated tests with `pytest`.

---

## Limitations

- Fixed demonstration with **three hospitals**, **three servers**, `M = 40`, and `p = 127`.
- Local simulation only: **no real cloud deployment, network communication, or TLS**.
- Assumes servers follow the protocol; it does not protect against malicious results or collusion beyond each scheme's threshold.

> [!NOTE]
> This is an **educational prototype**, not a production-ready security system.

---

## Setup

Install [uv](https://docs.astral.sh/uv/) and run the following commands from the repository root:

```bash
uv sync
uv run python main.py
```

To run the tests directly:

```bash
uv run python -m pytest -v --no-header --tb=short
```

You can also run the tests from **option 3** in the terminal menu.
