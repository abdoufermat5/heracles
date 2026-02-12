"""Random data generators for load tests."""

import random
import string


def random_string(length: int = 8) -> str:
    """Generate a random lowercase string."""
    return "".join(random.choices(string.ascii_lowercase, k=length))


def random_ip() -> str:
    """Generate a random 10.x.x.x IP address."""
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


def random_mac() -> str:
    """Generate a random MAC address."""
    return ":".join(f"{random.randint(0, 255):02x}" for _ in range(6))


def pick(*choices: str) -> str:
    """Pick a random item from the arguments."""
    return random.choice(choices)
