"""Collect server aggregates and reconstruct a session's total."""

from src.models import Parameters, PartialSum, ProtocolError
from src.shamir import reconstruct_pair


class Analyst:
    """Accept one partial per server and reconstruct either protocol."""

    def __init__(self, parameters: Parameters, session_id: str) -> None:
        """Start a session with no received server partials."""
        if not session_id:
            raise ValueError("Session ID must not be empty")
        self.parameters = parameters
        self.session_id = session_id
        self.partials: dict[int, PartialSum] = {}

    def receive_partial(self, partial: PartialSum) -> bool:
        """Reject wrong-session, invalid or duplicate server messages."""
        if partial.session_id != self.session_id:
            return False
        if partial.server_id not in range(1, self.parameters.m + 1):
            return False
        if not 0 <= partial.value < self.parameters.p:
            return False
        if partial.server_id in self.partials:
            return False
        self.partials[partial.server_id] = partial
        return True

    def reconstruct_additive(self) -> int:
        """Require every server's partial and sum modulo the session modulus."""
        if len(self.partials) != self.parameters.m:
            raise ProtocolError("Missing server partial sums")
        total = 0
        for partial in self.partials.values():
            total += partial.value
        return total % self.parameters.p

    def reconstruct_shamir(self, trace: dict | None = None) -> int:
        """Interpolate the first two available positions, optionally tracing it."""
        if len(self.partials) < 2:
            raise ProtocolError("Need two server partial sums")
        # Sorting selects the same pair whether or not a trace is requested.
        server_ids = sorted(self.partials)
        u = server_ids[0]
        v = server_ids[1]
        return reconstruct_pair(u, self.partials[u].value, v,
                                self.partials[v].value, self.parameters.p, trace)
