"""Generate degree-one Shamir shares and interpolate two server partials."""

import secrets


def is_prime(value: int) -> bool:
    """Check a positive integer for primality by trial division."""
    if type(value) is not int or value < 2:
        return False
    divisor = 2
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 1
    return True


def validate_shamir_modulus(p: int) -> None:
    """Require a prime field with three distinct nonzero server positions."""
    if not is_prime(p) or p <= 3:
        raise ValueError("Shamir requires a prime modulus greater than 3")


def create_shamir_values(value: int, p: int, trace: dict | None = None) -> list[int]:
    """Evaluate a random linear polynomial at server positions one to three."""
    validate_shamir_modulus(p)
    if type(value) is not int or not 0 <= value < p:
        raise ValueError("Shamir requires an input in Z_p")
    coefficient = secrets.randbelow(p)
    if trace is not None:
        trace["coefficient"] = coefficient
    values = []
    for server_id in range(1, 4):
        values.append((value + coefficient * server_id) % p)
    return values


def reconstruct_pair(
    u: int, z_u: int, v: int, z_v: int, p: int, trace: dict | None = None
) -> int:
    """Interpolate two server evaluations, optionally recording the first inverse."""
    validate_shamir_modulus(p)
    if type(u) is not int or type(v) is not int or u not in range(1, 4):
        raise ValueError("Invalid server positions")
    if v not in range(1, 4) or u == v:
        raise ValueError("Server positions must be distinct")
    if type(z_u) is not int or type(z_v) is not int:
        raise ValueError("Partial sums must be integers")
    if not 0 <= z_u < p or not 0 <= z_v < p:
        raise ValueError("Partial sums must be in Z_p")
    # The first modular inverse is also the one displayed for servers 1 and 3.
    first_inverse = pow(v - u, -1, p)
    if trace is not None:
        trace["first_denominator_inverse"] = first_inverse
    # Each weight is a Lagrange basis polynomial evaluated at zero.
    first_weight = v * first_inverse
    second_weight = u * pow(u - v, -1, p)
    return (first_weight * z_u + second_weight * z_v) % p
