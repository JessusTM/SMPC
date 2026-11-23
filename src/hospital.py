"""Create private additive shares for a hospital."""

import secrets

from src.models import Parameters, Share


class Hospital:
    """Keep a private input and generate messages for the servers."""

    def __init__(self, hospital_id: int, value: int, parameters: Parameters) -> None:
        """Validate the hospital identity and its bounded input."""
        if type(hospital_id) is not int or hospital_id not in range(1, parameters.n + 1):
            raise ValueError("Invalid hospital ID")
        if type(value) is not int or not 0 <= value <= parameters.max_value:
            raise ValueError("Invalid hospital value")
        self.hospital_id = hospital_id
        self.value = value
        self.parameters = parameters

    def create_additive_shares(self, session_id: str) -> list[Share]:
        """Split the input into independently random modular shares."""
        values = []
        for _ in range(self.parameters.m - 1):
            values.append(secrets.randbelow(self.parameters.p))
        values.append((self.value - sum(values)) % self.parameters.p)
        shares = []
        for server_id in range(1, self.parameters.m + 1):
            shares.append(Share(session_id=session_id, origin=self.hospital_id,
                                destination=server_id, value=values[server_id - 1]))
        return shares
