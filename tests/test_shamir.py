"""Verify Shamir pair interpolation, offline recovery, and field contracts."""

import pytest

from src.analyst import Analyst
from src.hospital import Hospital
from src.models import Parameters, PartialSum, ProtocolError
from src.shamir import create_shamir_values, is_prime, reconstruct_pair
from src.simulation import run_shamir


def test_t10_report_example_all_three_pairs() -> None:
    """Reconstruct the report's total with every pair of example partials."""
    for u, z_u, v, z_v in ((1, 81, 2, 87), (1, 81, 3, 93), (2, 87, 3, 93)):
        assert reconstruct_pair(u, z_u, v, z_v, 127) == 75


def test_t10_full_simulation_with_each_server_offline() -> None:
    """Recover the same input total independently of which server is absent."""
    parameters = Parameters(n=3, m=3, p=127, max_value=40)
    for offline_server in (1, 2, 3):
        assert run_shamir([20, 25, 30], parameters, offline_server=offline_server) == 75
    assert run_shamir([20, 25, 30], parameters) == 75


def test_shamir_one_partial_is_insufficient() -> None:
    """Require two distinct server positions for analyst reconstruction."""
    parameters = Parameters(n=3, m=3, p=127, max_value=40)
    analyst = Analyst(parameters, "session")
    with pytest.raises(ProtocolError):
        analyst.reconstruct_shamir()
    assert analyst.receive_partial(PartialSum(session_id="session", server_id=1, value=81))
    with pytest.raises(ProtocolError):
        analyst.reconstruct_shamir()


def test_shamir_rejects_composite_modulus_above_total() -> None:
    """A sufficient additive modulus is not automatically a Shamir field."""
    parameters = Parameters(n=3, m=3, p=121, max_value=40)
    assert is_prime(121) is False
    assert is_prime(127) is True
    with pytest.raises(ValueError):
        run_shamir([20, 25, 30], parameters)
    with pytest.raises(ValueError):
        create_shamir_values(20, 121)
    with pytest.raises(ValueError):
        reconstruct_pair(1, 81, 3, 93, 121)


def test_shamir_rejects_small_prime_at_each_public_entry_point() -> None:
    """Positions 1, 2, and 3 require a prime strictly greater than three."""
    for p in (2, 3):
        parameters = Parameters(n=3, m=3, p=p, max_value=0)
        with pytest.raises(ValueError):
            run_shamir([0, 0, 0], parameters)
        with pytest.raises(ValueError):
            create_shamir_values(0, p)
        with pytest.raises(ValueError):
            reconstruct_pair(1, 0, 2, 0, p)


def test_shamir_accepts_smallest_valid_prime() -> None:
    """The first field with three distinct nonzero server positions works."""
    parameters = Parameters(n=3, m=3, p=5, max_value=0)
    shares = create_shamir_values(0, 5)
    assert len(shares) == 3
    assert reconstruct_pair(1, shares[0], 3, shares[2], 5) == 0
    assert run_shamir([0, 0, 0], parameters, offline_server=2) == 0


def test_shamir_shares_follow_traced_polynomial() -> None:
    """Use one recorded coefficient for all three real hospital shares."""
    parameters = Parameters(n=3, m=3, p=127, max_value=40)
    hospital = Hospital(1, 20, parameters)
    coefficient_trace = {}
    shares = hospital.create_shamir_shares("session", coefficient_trace)
    coefficient = coefficient_trace["coefficient"]
    assert 0 <= coefficient < 127
    assert len(shares) == 3
    for server_id, share in enumerate(shares, start=1):
        assert share.session_id == "session"
        assert share.origin == 1
        assert share.destination == server_id
        assert share.value == (20 + coefficient * server_id) % 127


def test_shamir_trace_records_actual_shares_and_online_partials() -> None:
    """Expose real intermediate values without changing the returned result."""
    parameters = Parameters(n=3, m=3, p=127, max_value=40)
    trace = {}
    assert run_shamir([20, 25, 30], parameters, offline_server=2, trace=trace) == 75
    assert trace["total"] == 75
    assert trace["offline_server"] == 2
    assert len(trace["session_id"]) == 16
    assert len(trace["generated_shares"]) == 9
    assert len(trace["partial_sums"]) == 2
    assert trace["first_denominator_inverse"] == 64
    for hospital_id, value in enumerate((20, 25, 30), start=1):
        coefficient = trace["coefficients"][hospital_id]
        assert 0 <= coefficient < 127
        for share in trace["generated_shares"]:
            if share.origin == hospital_id:
                assert share.session_id == trace["session_id"]
                assert share.value == (value + coefficient * share.destination) % 127
    for partial in trace["partial_sums"]:
        assert partial.server_id in (1, 3)
        assert partial.session_id == trace["session_id"]
        received_total = 0
        for share in trace["generated_shares"]:
            if share.destination == partial.server_id:
                received_total += share.value
        assert partial.value == received_total % 127


def test_shamir_rejects_invalid_pairs() -> None:
    """Reject repeated, out-of-range server positions and invalid field values."""
    for u, v in ((1, 1), (0, 2), (1, 4)):
        with pytest.raises(ValueError):
            reconstruct_pair(u, 81, v, 87, 127)
    for value in (-1, 127):
        with pytest.raises(ValueError):
            reconstruct_pair(1, value, 2, 87, 127)
