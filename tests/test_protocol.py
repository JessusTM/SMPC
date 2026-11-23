"""Verify additive sharing, validation, availability, and the T9 diagnostic."""

import random

import pytest
from pydantic import ValidationError

from src.analyst import Analyst
from src.hospital import Hospital
from src.models import Parameters, PartialSum, ProtocolError, Share
from src.server import Server
from src.simulation import run_additive


def test_t1_reproducible_random_inputs() -> None:
    """Reconstruct the exact total for 1,000 seeded input triples."""
    parameters = Parameters(n=3, m=3, p=127, max_value=40)
    generator = random.Random(2026)
    for _ in range(1000):
        values = []
        for _ in range(3):
            values.append(generator.randint(0, 40))
        assert run_additive(values, parameters) == sum(values)


def test_t2_maximum_inputs() -> None:
    """Retain the maximum unwrapped total."""
    parameters = Parameters(n=3, m=3, p=127, max_value=40)
    assert run_additive([40, 40, 40], parameters) == 120


def test_t3_zero_inputs() -> None:
    """Reconstruct zero when no hospital contributes a count."""
    parameters = Parameters(n=3, m=3, p=127, max_value=40)
    assert run_additive([0, 0, 0], parameters) == 0


def test_additive_accepts_modulus_two_with_zero_maximum() -> None:
    """The additive protocol still operates over the smallest allowed field."""
    parameters = Parameters(n=3, m=3, p=2, max_value=0)
    trace = {}
    assert run_additive([0, 0, 0], parameters, trace=trace) == 0
    assert len(trace["generated_shares"]) == 9
    assert len(trace["partial_sums"]) == 3
    for share in trace["generated_shares"]:
        assert share.value in (0, 1)
    for partial in trace["partial_sums"]:
        assert partial.value in (0, 1)


def test_t4_modulus_must_exceed_maximum_total() -> None:
    """Reject the boundary modulus that could wrap the maximum total."""
    with pytest.raises(ValidationError):
        Parameters(n=3, m=3, p=120, max_value=40)


def test_t5_reject_invalid_hospital_values() -> None:
    """Reject out-of-range and boolean counts before generating shares."""
    parameters = Parameters(n=3, m=3, p=127, max_value=40)
    for value in (-1, 41, True):
        with pytest.raises(ValueError):
            Hospital(1, value, parameters)


def test_t6_duplicate_share_preserves_first_message() -> None:
    """Do not replace a previously accepted hospital share."""
    parameters = Parameters(n=3, m=3, p=127, max_value=40)
    server = Server(2, parameters, "session")
    first = Share(session_id="session", origin=1, destination=2, value=12)
    duplicate = Share(session_id="session", origin=1, destination=2, value=37)
    assert server.receive_share(first) is True
    assert server.receive_share(duplicate) is False
    assert server.shares == {("session", 1): first}


def test_t7_wrong_session_share_is_not_stored() -> None:
    """Ignore a share from a different active session."""
    parameters = Parameters(n=3, m=3, p=127, max_value=40)
    server = Server(2, parameters, "session")
    wrong = Share(session_id="other", origin=1, destination=2, value=12)
    assert server.receive_share(wrong) is False
    assert server.shares == {}


def test_t8_additive_cannot_reconstruct_with_server_two_offline() -> None:
    """Require all three server partials before additive reconstruction."""
    parameters = Parameters(n=3, m=3, p=127, max_value=40)
    trace = {}
    with pytest.raises(ProtocolError):
        run_additive([20, 25, 30], parameters, offline_server=2, trace=trace)
    assert trace["offline_server"] == 2
    assert len(trace["generated_shares"]) == 9
    assert len(trace["partial_sums"]) == 2
    assert "total" not in trace


def test_t9_first_additive_share_uniformity_diagnostic() -> None:
    """Print a size-corrected chi-square statistic without random failure."""
    parameters = Parameters(n=3, m=3, p=127, max_value=40)
    hospital = Hospital(1, 20, parameters)
    bucket_sizes = [0] * 10
    observed = [0] * 10
    for value in range(parameters.p):
        bucket_sizes[value * 10 // parameters.p] += 1
    for _ in range(30000):
        share = hospital.create_additive_shares("session")[0]
        assert 0 <= share.value < parameters.p
        observed[share.value * 10 // parameters.p] += 1
    assert sum(observed) == 30000
    assert sum(bucket_sizes) == 127
    assert bucket_sizes.count(13) == 7
    assert bucket_sizes.count(12) == 3
    # Each expected frequency reflects its bucket's number of field elements.
    chi_square = 0.0
    for index in range(10):
        expected = 30000 * bucket_sizes[index] / parameters.p
        chi_square += (observed[index] - expected) ** 2 / expected
    print(f"T9 chi-square: {chi_square:.4f}; threshold: 27.88; at or below: {chi_square <= 27.88}")


def test_additive_shares_and_server_aggregation() -> None:
    """Preserve each hospital's input and aggregate received shares modulo p."""
    parameters = Parameters(n=3, m=3, p=127, max_value=40)
    server = Server(1, parameters, "session")
    expected_sum = 0
    for hospital_id, value in enumerate((20, 25, 30), start=1):
        shares = Hospital(hospital_id, value, parameters).create_additive_shares("session")
        assert len(shares) == 3
        share_total = 0
        for destination, share in enumerate(shares, start=1):
            assert share.session_id == "session"
            assert share.origin == hospital_id
            assert share.destination == destination
            assert 0 <= share.value < 127
            share_total += share.value
        assert share_total % 127 == value
        assert server.receive_share(shares[0]) is True
        expected_sum += shares[0].value
    assert server.aggregate() == PartialSum(
        session_id="session", server_id=1, value=expected_sum % 127
    )


def test_server_rejects_invalid_messages_and_missing_shares() -> None:
    """Keep invalid messages out and refuse to aggregate an incomplete set."""
    parameters = Parameters(n=3, m=3, p=127, max_value=40)
    server = Server(1, parameters, "session")
    invalid = (
        Share(session_id="session", origin=0, destination=1, value=1),
        Share(session_id="session", origin=4, destination=1, value=1),
        Share(session_id="session", origin=1, destination=2, value=1),
        Share(session_id="session", origin=1, destination=1, value=127),
    )
    for share in invalid:
        assert server.receive_share(share) is False
        assert server.shares == {}
    with pytest.raises(ProtocolError):
        server.aggregate()
    assert server.receive_share(Share(session_id="session", origin=1, destination=1, value=0))
    with pytest.raises(ProtocolError):
        server.aggregate()


def test_analyst_rejects_invalid_partials_and_requires_all_three() -> None:
    """Preserve the first valid partial and require all server contributions."""
    parameters = Parameters(n=3, m=3, p=127, max_value=40)
    analyst = Analyst(parameters, "session")
    invalid = (
        PartialSum(session_id="other", server_id=1, value=1),
        PartialSum(session_id="session", server_id=0, value=1),
        PartialSum(session_id="session", server_id=4, value=1),
        PartialSum(session_id="session", server_id=1, value=127),
    )
    for partial in invalid:
        assert analyst.receive_partial(partial) is False
        assert analyst.partials == {}
    first = PartialSum(session_id="session", server_id=1, value=120)
    assert analyst.receive_partial(first) is True
    assert analyst.receive_partial(
        PartialSum(session_id="session", server_id=1, value=11)
    ) is False
    assert analyst.partials == {1: first}
    with pytest.raises(ProtocolError):
        analyst.reconstruct_additive()
    assert analyst.receive_partial(PartialSum(session_id="session", server_id=2, value=40))
    with pytest.raises(ProtocolError):
        analyst.reconstruct_additive()
    assert analyst.receive_partial(PartialSum(session_id="session", server_id=3, value=50))
    assert analyst.reconstruct_additive() == 83


def test_models_are_strict_frozen_and_forbid_extra_fields() -> None:
    """Reject coercions, unexpected fields, and mutation for all three models."""
    models = (
        (Parameters, {"n": 3, "m": 3, "p": 127, "max_value": 40}, "n"),
        (Share, {"session_id": "session", "origin": 1, "destination": 2, "value": 0}, "origin"),
        (PartialSum, {"session_id": "session", "server_id": 1, "value": 0}, "server_id"),
    )
    for model_type, fields, integer_field in models:
        invalid_type = dict(fields)
        invalid_type[integer_field] = "1"
        with pytest.raises(ValidationError):
            model_type(**invalid_type)
        extra_field = dict(fields)
        extra_field["unexpected"] = 1
        with pytest.raises(ValidationError):
            model_type(**extra_field)
        instance = model_type(**fields)
        with pytest.raises(ValidationError):
            setattr(instance, integer_field, 2)
    for model_type, fields in (
        (Share, {"session_id": "", "origin": 1, "destination": 1, "value": 0}),
        (PartialSum, {"session_id": "", "server_id": 1, "value": 0}),
        (Share, {"session_id": "session", "origin": 1, "destination": 1, "value": -1}),
        (PartialSum, {"session_id": "session", "server_id": 1, "value": -1}),
    ):
        with pytest.raises(ValidationError):
            model_type(**fields)


def test_invalid_simulation_arguments() -> None:
    """Reject unsupported input counts and offline server numbers."""
    parameters = Parameters(n=3, m=3, p=127, max_value=40)
    for values in ([20, 25], [20, 25, 30, 35]):
        with pytest.raises(ValueError):
            run_additive(values, parameters)
    for offline_server in (-1, 4, True):
        with pytest.raises(ValueError):
            run_additive([20, 25, 30], parameters, offline_server=offline_server)


def test_additive_trace_matches_returned_session() -> None:
    """Record the same generated messages, partial sums, and successful total."""
    parameters = Parameters(n=3, m=3, p=127, max_value=40)
    trace = {}
    assert run_additive([20, 25, 30], parameters, trace=trace) == 75
    assert trace["total"] == 75
    assert trace["offline_server"] == 0
    assert len(trace["session_id"]) == 16
    assert len(trace["generated_shares"]) == 9
    assert len(trace["partial_sums"]) == 3
    for partial in trace["partial_sums"]:
        received_total = 0
        for share in trace["generated_shares"]:
            assert share.session_id == trace["session_id"]
            if share.destination == partial.server_id:
                received_total += share.value
        assert partial.session_id == trace["session_id"]
        assert partial.value == received_total % parameters.p
