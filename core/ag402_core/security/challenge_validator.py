"""Validate 402 payment challenges before paying."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from ag402_core.config import X402Config

# Solana base58 alphabet: excludes 0, O, I, l
_BASE58_RE = re.compile(r"^[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]+$")

# V1: only USDC is allowed
_ALLOWED_TOKENS = {"USDC"}

# Hostnames that are always considered local
_LOCAL_HOSTNAMES = {"localhost"}


def _is_local_address(hostname: str) -> bool:
    """Check if a hostname resolves to a loopback or private address.

    Handles:
    - "localhost"
    - "127.0.0.1" through "127.255.255.255" (IPv4 loopback)
    - "::1" and "[::1]" (IPv6 loopback)
    - "0.0.0.0" (unspecified / local bind)
    """
    if hostname in _LOCAL_HOSTNAMES:
        return True
    # Strip IPv6 bracket notation
    bare = hostname.strip("[]")
    try:
        addr = ipaddress.ip_address(bare)
        return addr.is_loopback or addr == ipaddress.ip_address("0.0.0.0")
    except ValueError:
        return False


@dataclass
class ChallengeValidation:
    valid: bool
    error: str = ""


def validate_challenge(
    url: str,
    amount: float,
    address: str,
    token: str,
    config: X402Config,
) -> ChallengeValidation:
    """Validate a 402 payment challenge before executing payment.

    Checks:
    - URL scheme is HTTPS (HTTP allowed only for localhost / 127.0.0.1)
    - Amount is in valid range: 0 < amount <= config.single_tx_limit
    - Address looks like a valid Solana base58 address (32-44 chars, no 0/O/I/l)
    - Token is in the allowed list (V1: only "USDC")
    - If config.trusted_addresses is non-empty, address must be whitelisted
    """
    # 1. URL scheme check
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()

    if scheme != "https":
        # Allow http for local addresses only (loopback, 0.0.0.0)
        is_local = _is_local_address(hostname)
        if scheme != "http" or not is_local:
            return ChallengeValidation(
                valid=False,
                error=f"Insecure URL scheme '{scheme}' — HTTPS required (HTTP allowed for localhost only)",
            )

    # 2. Amount range check
    if amount <= 0:
        return ChallengeValidation(
            valid=False,
            error=f"Invalid amount {amount} — must be > 0",
        )
    if amount > config.single_tx_limit:
        return ChallengeValidation(
            valid=False,
            error=f"Amount {amount} exceeds single-tx limit {config.single_tx_limit}",
        )

    # 3. Address validation (Solana base58: 32-44 chars, no 0/O/I/l)
    if not (32 <= len(address) <= 44):
        return ChallengeValidation(
            valid=False,
            error=f"Invalid address length {len(address)} — expected 32-44 characters",
        )
    if not _BASE58_RE.match(address):
        return ChallengeValidation(
            valid=False,
            error="Invalid address — contains characters not in Solana base58 alphabet",
        )

    # 4. Token whitelist
    if token not in _ALLOWED_TOKENS:
        return ChallengeValidation(
            valid=False,
            error=f"Token '{token}' not allowed — accepted: {_ALLOWED_TOKENS}",
        )

    # 5. Trusted addresses whitelist
    if config.trusted_addresses and address not in config.trusted_addresses:
        return ChallengeValidation(
            valid=False,
            error=f"Address '{address}' not in trusted addresses whitelist",
        )

    return ChallengeValidation(valid=True)
