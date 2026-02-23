"""
Centralized configuration for ag402-core.

All settings are read from environment variables with sensible defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum


class RunMode(Enum):
    """Operating mode of the gateway."""

    PRODUCTION = "production"
    TEST = "test"


# --- Safety constants ---
# Hardcoded upper bounds that cannot be exceeded even via environment variables.
MAX_DAILY_SPEND_HARD_CEILING: float = 1000.0  # USD — absolute maximum for daily limit
MAX_SINGLE_TX: float = 5.0  # USD — absolute single-transaction ceiling
MAX_PER_MINUTE_LIMIT_CEILING: float = 10.0  # USD — max per-minute $ cap
MAX_PER_MINUTE_COUNT_CEILING: int = 50  # max per-minute TX count
MAX_CIRCUIT_BREAKER_THRESHOLD_CEILING: int = 20
MAX_CIRCUIT_BREAKER_COOLDOWN_CEILING: int = 3600  # seconds

PRIVATE_KEY_LOG_PATTERNS: list[str] = [
    "private_key",
    "secret_key",
    "mnemonic",
    "seed_phrase",
]


def _env_float(name: str, default: float, ceiling: float) -> float:
    """Read a float from env, clamped to ceiling."""
    import logging as _log

    raw = os.getenv(name, str(default))
    try:
        val = float(raw)
    except (ValueError, TypeError):
        _log.getLogger(__name__).warning(
            "Invalid value for %s='%s', falling back to default %.2f", name, raw, default
        )
        val = default
    return min(val, ceiling)


def _env_int(name: str, default: int, ceiling: int) -> int:
    """Read an int from env, clamped to ceiling."""
    import logging as _log

    raw = os.getenv(name, str(default))
    try:
        val = int(raw)
    except (ValueError, TypeError):
        _log.getLogger(__name__).warning(
            "Invalid value for %s='%s', falling back to default %d", name, raw, default
        )
        val = default
    return min(val, ceiling)


@dataclass(frozen=True)
class X402Config:
    """Immutable configuration loaded once at startup."""

    # --- Core ---
    mode: RunMode = field(default_factory=lambda: RunMode(os.getenv("X402_MODE", "test")))
    protocol_version: str = "v1.0"

    # --- Wallet ---
    solana_private_key: str = field(default_factory=lambda: os.getenv("SOLANA_PRIVATE_KEY", ""), repr=False)
    solana_rpc_url: str = field(
        default_factory=lambda: os.getenv(
            "SOLANA_RPC_URL", "https://api.devnet.solana.com"
        )
    )
    solana_rpc_backup_url: str = field(
        default_factory=lambda: os.getenv("SOLANA_RPC_BACKUP_URL", "")
    )
    usdc_mint_address: str = field(
        default_factory=lambda: os.getenv(
            "USDC_MINT_ADDRESS",
            # Solana devnet USDC mint
            "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",
        )
    )

    # --- Budget ---
    single_tx_limit: float = field(
        default_factory=lambda: _env_float(
            "X402_SINGLE_TX_LIMIT", 5.0, MAX_SINGLE_TX
        )
    )
    daily_limit: float = field(
        default_factory=lambda: _env_float(
            "X402_DAILY_LIMIT", 10.0, MAX_DAILY_SPEND_HARD_CEILING
        )
    )
    per_minute_limit: float = field(
        default_factory=lambda: _env_float(
            "X402_PER_MINUTE_LIMIT", 2.0, MAX_PER_MINUTE_LIMIT_CEILING
        )
    )
    per_minute_count: int = field(
        default_factory=lambda: _env_int(
            "X402_PER_MINUTE_COUNT", 5, MAX_PER_MINUTE_COUNT_CEILING
        )
    )

    # --- Circuit Breaker ---
    circuit_breaker_threshold: int = field(
        default_factory=lambda: _env_int(
            "X402_CIRCUIT_BREAKER_THRESHOLD", 3, MAX_CIRCUIT_BREAKER_THRESHOLD_CEILING
        )
    )
    circuit_breaker_cooldown: int = field(
        default_factory=lambda: _env_int(
            "X402_CIRCUIT_BREAKER_COOLDOWN", 60, MAX_CIRCUIT_BREAKER_COOLDOWN_CEILING
        )
    )

    # --- Gateway ---
    gateway_host: str = field(default_factory=lambda: os.getenv("X402_HOST", "127.0.0.1"))
    gateway_port: int = field(default_factory=lambda: _env_int("X402_PORT", 4020, 65535))

    # --- Wallet DB ---
    wallet_db_path: str = field(
        default_factory=lambda: os.getenv("X402_WALLET_DB", os.path.expanduser("~/.ag402/wallet.db"))
    )

    # --- Security ---
    replay_window_seconds: int = 30
    rate_limit_per_minute: int = field(
        default_factory=lambda: _env_int("X402_RATE_LIMIT", 60, 10000)
    )
    trusted_addresses: list[str] = field(default_factory=list)

    # --- Dual-mode fallback ---
    # If target doesn't support x402, forward with this API key instead
    fallback_api_key: str = field(
        default_factory=lambda: os.getenv("X402_FALLBACK_API_KEY", "")
    )

    # --- V2 Extension Points (pre-defined, inactive in V1) ---

    # Registry (yellow pages)
    registry_url: str = field(default_factory=lambda: os.getenv("X402_REGISTRY_URL", ""))

    # --- PBE Wallet Encryption ---
    unlock_password: str = field(
        default_factory=lambda: os.getenv("AG402_UNLOCK_PASSWORD", ""), repr=False
    )
    encrypted_wallet_path: str = field(
        default_factory=lambda: os.getenv(
            "AG402_WALLET_KEY_PATH",
            os.path.expanduser("~/.ag402/wallet.key"),
        )
    )

    @property
    def is_test_mode(self) -> bool:
        return self.mode == RunMode.TEST

    @property
    def daily_spend_limit(self) -> float:
        """Daily spend limit — configurable via X402_DAILY_LIMIT, capped at $1000."""
        return self.daily_limit


def load_config() -> X402Config:
    """Load configuration from environment variables.

    Automatically reads ~/.ag402/.env if present (does not override
    existing env vars).
    """
    from ag402_core.env_manager import load_dotenv

    load_dotenv()  # ~/.ag402/.env → os.environ (no override)
    return X402Config()
