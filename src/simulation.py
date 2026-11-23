"""Run local participant-to-participant sessions without terminal output."""

import secrets

from src.analyst import Analyst
from src.hospital import Hospital
from src.models import Parameters
from src.server import Server
from src.shamir import validate_shamir_modulus


def _participants(
    values: list[int], parameters: Parameters, offline_server: int
) -> tuple[str, list[Hospital], dict[int, Server], Analyst]:
    """Validate a session and create its three hospitals, servers and analyst."""
    if len(values) != parameters.n:
        raise ValueError("Exactly three hospital inputs are required")
    if type(offline_server) is not int or offline_server not in range(parameters.m + 1):
        raise ValueError("Invalid offline server")
    session_id = secrets.token_hex(8)
    hospitals = []
    servers = {}
    for hospital_id, value in enumerate(values, start=1):
        hospitals.append(Hospital(hospital_id, value, parameters))
    for server_id in range(1, parameters.m + 1):
        servers[server_id] = Server(server_id, parameters, session_id)
    return session_id, hospitals, servers, Analyst(parameters, session_id)


def run_additive(
    values: list[int], parameters: Parameters, offline_server: int = 0,
    trace: dict | None = None,
) -> int:
    """Deliver additive shares and reconstruct only when all servers respond."""
    session_id, hospitals, servers, analyst = _participants(values, parameters, offline_server)
    if trace is not None:
        trace.pop("total", None)
        trace.update(session_id=session_id, generated_shares=[], partial_sums=[],
                     offline_server=offline_server)
    # Deliver only to online servers, but keep every generated message in the trace.
    for hospital in hospitals:
        shares = hospital.create_additive_shares(session_id)
        for share in shares:
            if trace is not None:
                trace["generated_shares"].append(share)
            if share.destination != offline_server:
                servers[share.destination].receive_share(share)
    for server_id, server in servers.items():
        if server_id == offline_server:
            continue
        partial = server.aggregate()
        if trace is not None:
            trace["partial_sums"].append(partial)
        analyst.receive_partial(partial)
    total = analyst.reconstruct_additive()
    if trace is not None:
        trace["total"] = total
    return total


def run_shamir(
    values: list[int], parameters: Parameters, offline_server: int = 0,
    trace: dict | None = None,
) -> int:
    """Deliver Shamir shares and interpolate two available partial sums."""
    validate_shamir_modulus(parameters.p)
    session_id, hospitals, servers, analyst = _participants(values, parameters, offline_server)
    if trace is not None:
        trace.pop("total", None)
        trace.pop("first_denominator_inverse", None)
        trace.update(session_id=session_id, generated_shares=[], partial_sums=[],
                     offline_server=offline_server, coefficients={})
    # The trace receives each coefficient from the same share generation call.
    for hospital in hospitals:
        coefficient_trace = {}
        shares = hospital.create_shamir_shares(session_id, coefficient_trace)
        if trace is not None:
            trace["coefficients"][hospital.hospital_id] = coefficient_trace["coefficient"]
        for share in shares:
            if trace is not None:
                trace["generated_shares"].append(share)
            if share.destination != offline_server:
                servers[share.destination].receive_share(share)
    for server_id, server in servers.items():
        if server_id == offline_server:
            continue
        partial = server.aggregate()
        if trace is not None:
            trace["partial_sums"].append(partial)
        analyst.receive_partial(partial)
    # The analyst records the inverse computed by the actual interpolation.
    total = analyst.reconstruct_shamir(trace)
    if trace is not None:
        trace["total"] = total
    return total
