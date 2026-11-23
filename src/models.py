"""Validated protocol parameters and messages."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProtocolError(Exception):
    """Signal that a session lacks enough valid messages to finish."""


class Parameters(BaseModel):
    """Fixed participant counts and a modulus large enough for the total."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    n: int = 3
    m: int = 3
    p: int = 127
    max_value: int = Field(default=40, ge=0)

    @model_validator(mode="after")
    def check_parameters(self) -> "Parameters":
        """Reject unsupported participant counts or a wrapping modulus."""
        if self.n != 3 or self.m != 3 or self.p < 2:
            raise ValueError("Require three hospitals, three servers, and p >= 2")
        if self.p <= self.n * self.max_value:
            raise ValueError("Modulus must exceed the maximum possible total")
        return self


class Share(BaseModel):
    """One hospital's modular share addressed to one server."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    session_id: str = Field(min_length=1)
    origin: int
    destination: int
    value: int = Field(ge=0)


class PartialSum(BaseModel):
    """One server's modular aggregate addressed to the analyst."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    session_id: str = Field(min_length=1)
    server_id: int
    value: int = Field(ge=0)
