"""Receive hospital messages and aggregate them at a single server."""

from src.models import Parameters, PartialSum, ProtocolError, Share


class Server:
    """Store only valid shares for one server and one active session."""

    def __init__(self, server_id: int, parameters: Parameters, session_id: str) -> None:
        """Set the server identity and empty session storage."""
        if type(server_id) is not int or server_id not in range(1, parameters.m + 1):
            raise ValueError("Invalid server ID")
        if not session_id:
            raise ValueError("Session ID must not be empty")
        self.server_id = server_id
        self.parameters = parameters
        self.session_id = session_id
        self.shares: dict[tuple[str, int], Share] = {}

    def receive_share(self, share: Share) -> bool:
        """Reject wrong-session, misaddressed, out-of-range or duplicate shares."""
        if share.session_id != self.session_id or share.destination != self.server_id:
            return False
        if share.origin not in range(1, self.parameters.n + 1):
            return False
        if not 0 <= share.value < self.parameters.p:
            return False
        key = (share.session_id, share.origin)
        if key in self.shares:
            return False
        self.shares[key] = share
        return True

    def aggregate(self) -> PartialSum:
        """Sum one share from every hospital, or report an incomplete session."""
        if len(self.shares) != self.parameters.n:
            raise ProtocolError("Missing hospital shares")
        total = 0
        for share in self.shares.values():
            total += share.value
        return PartialSum(session_id=self.session_id, server_id=self.server_id,
                          value=total % self.parameters.p)
