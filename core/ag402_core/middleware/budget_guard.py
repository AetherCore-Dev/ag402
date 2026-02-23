"""Budget enforcement — checks single-tx, per-minute, daily limits, and circuit breaker."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from decimal import Decimal

from ag402_core.config import MAX_SINGLE_TX, X402Config
from ag402_core.wallet.agent_wallet import AgentWallet
from ag402_core.wallet.models import _to_decimal

logger = logging.getLogger(__name__)


@dataclass
class BudgetCheckResult:
    allowed: bool
    reason: str = ""


class BudgetGuard:
    """Pre-payment budget checks with multi-layer limits and circuit breaker."""

    # Circuit breaker state is class-level so all instances share it
    _consecutive_failures: int = 0
    _circuit_opened_at: float = 0.0
    _lock = threading.Lock()

    def __init__(self, wallet: AgentWallet, config: X402Config):
        self._wallet = wallet
        self._config = config

    # --- Circuit breaker methods ---

    @classmethod
    def record_failure(cls) -> None:
        """Record a payment failure for circuit breaker tracking."""
        with cls._lock:
            cls._consecutive_failures += 1
            if cls._consecutive_failures >= 3:  # will use config threshold at check time
                cls._circuit_opened_at = time.time()

    @classmethod
    def record_success(cls) -> None:
        """Record a payment success — resets failure counter."""
        with cls._lock:
            cls._consecutive_failures = 0

    @classmethod
    def is_circuit_open(cls, threshold: int, cooldown: int) -> bool:
        """Check if the circuit breaker is currently open (blocking requests)."""
        with cls._lock:
            if cls._consecutive_failures < threshold:
                return False
            elapsed = time.time() - cls._circuit_opened_at
            if elapsed >= cooldown:
                # Cooldown passed — reset and allow
                cls._consecutive_failures = 0
                cls._circuit_opened_at = 0.0
                return False
            return True

    @classmethod
    def reset_circuit_breaker(cls) -> None:
        """Reset circuit breaker state (for testing)."""
        with cls._lock:
            cls._consecutive_failures = 0
            cls._circuit_opened_at = 0.0

    async def check(self, amount: float | Decimal, *, max_amount: float | None = None) -> BudgetCheckResult:
        """Check if a payment amount is within all budget constraints.

        Args:
            amount: The payment amount to check.
            max_amount: Optional caller-specified per-request cap. If provided,
                        the effective single-tx limit is min(config, max_amount).
                        This is concurrency-safe — it does NOT mutate the config.
        """
        amount_d = _to_decimal(amount)
        # 0. Circuit breaker check
        if self.is_circuit_open(
            self._config.circuit_breaker_threshold,
            self._config.circuit_breaker_cooldown,
        ):
            msg = (
                f"Circuit breaker open — {self._consecutive_failures} consecutive "
                f"failures (threshold: {self._config.circuit_breaker_threshold})"
            )
            logger.warning("[BUDGET] DENIED — %s", msg)
            return BudgetCheckResult(allowed=False, reason=msg)

        # 1. Hardcoded single-transaction ceiling (cannot be exceeded, even by config)
        max_single = _to_decimal(MAX_SINGLE_TX)
        if amount_d > max_single:
            msg = (
                f"Amount ${amount_d} exceeds hardcoded single-tx ceiling "
                f"${max_single}"
            )
            logger.warning("[BUDGET] DENIED — %s", msg)
            return BudgetCheckResult(allowed=False, reason=msg)

        # 2. Single-transaction limit (configurable, but capped by MAX_SINGLE_TX)
        effective_limit = min(_to_decimal(self._config.single_tx_limit), max_single)
        # If caller specified max_amount, tighten the limit further (never loosen)
        if max_amount is not None:
            effective_limit = min(effective_limit, _to_decimal(max_amount))
        if amount_d > effective_limit:
            msg = (
                f"Amount ${amount_d} exceeds single-tx limit "
                f"${effective_limit}"
            )
            logger.warning("[BUDGET] DENIED — %s", msg)
            return BudgetCheckResult(allowed=False, reason=msg)

        # 3. Per-minute spend limit
        minute_spend = await self._wallet.get_minute_spend()
        per_minute_limit = _to_decimal(self._config.per_minute_limit)
        if minute_spend + amount_d > per_minute_limit:
            msg = (
                f"Per-minute spend ${minute_spend} + ${amount_d} "
                f"would exceed limit ${per_minute_limit}"
            )
            logger.warning("[BUDGET] DENIED — %s", msg)
            return BudgetCheckResult(allowed=False, reason=msg)

        # 4. Per-minute count limit
        minute_count = await self._wallet.get_minute_count()
        if minute_count + 1 > self._config.per_minute_count:
            msg = (
                f"Per-minute transaction count {minute_count} + 1 "
                f"would exceed limit {self._config.per_minute_count}"
            )
            logger.warning("[BUDGET] DENIED — %s", msg)
            return BudgetCheckResult(allowed=False, reason=msg)

        # 5. Daily spend limit (configurable via env, capped by hard ceiling)
        daily_limit = _to_decimal(self._config.daily_spend_limit)
        daily_spend = await self._wallet.get_daily_spend()
        if daily_spend + amount_d > daily_limit:
            msg = (
                f"Daily spend ${daily_spend} + ${amount_d} "
                f"would exceed limit ${daily_limit}"
            )
            logger.warning("[BUDGET] DENIED — %s", msg)
            return BudgetCheckResult(allowed=False, reason=msg)

        # 6. Sufficient balance
        balance = await self._wallet.get_balance()
        if balance < amount_d:
            msg = f"Insufficient balance: ${balance} < ${amount_d}"
            logger.warning("[BUDGET] DENIED — %s", msg)
            return BudgetCheckResult(allowed=False, reason=msg)

        logger.info(
            "[BUDGET] APPROVED — $%s (daily: $%s/$%s, balance: $%s)",
            amount_d, daily_spend, daily_limit, balance,
        )
        return BudgetCheckResult(allowed=True)
