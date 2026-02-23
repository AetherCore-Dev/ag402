"""
Replay attack protection using timestamp + nonce.

Client side: inject X-x402-Timestamp and X-x402-Nonce into requests.
Server side: reject requests older than replay_window_seconds or with duplicate nonces.

P0-4: Added PersistentReplayGuard for tx_hash deduplication backed by SQLite.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from collections import OrderedDict

import aiosqlite

logger = logging.getLogger(__name__)

# Max nonces to remember (prevents unbounded memory growth)
_MAX_NONCE_CACHE = 10_000

# Max nonce length — reject oversized nonces to prevent memory abuse
_MAX_NONCE_LENGTH = 128


class ReplayGuard:
    """Server-side replay attack protection."""

    def __init__(self, window_seconds: int = 30, max_cache: int = _MAX_NONCE_CACHE):
        self._window = window_seconds
        self._max_cache = max_cache
        self._seen_nonces: OrderedDict[str, float] = OrderedDict()

    def check(self, timestamp_str: str, nonce: str) -> tuple[bool, str]:
        """
        Check if a request is fresh (not a replay).

        Returns:
            (is_valid, error_message)
        """
        # 1. Validate timestamp
        if not timestamp_str:
            return False, "Missing X-x402-Timestamp header"
        if not nonce:
            return False, "Missing X-x402-Nonce header"

        # P2-3.3: Reject oversized nonces to prevent memory abuse
        if len(nonce) > _MAX_NONCE_LENGTH:
            return False, f"Nonce too long ({len(nonce)} > {_MAX_NONCE_LENGTH})"

        try:
            request_time = float(timestamp_str)
        except (ValueError, TypeError):
            return False, f"Invalid timestamp format: {timestamp_str}"

        now = time.time()
        age = now - request_time

        if age > self._window:
            logger.warning(
                "[REPLAY] Rejected stale request (age: %.1fs > %ds)",
                age, self._window,
            )
            return False, f"Request too old ({age:.1f}s > {self._window}s window)"

        if age < -self._window:
            # Clock skew: request from the future
            logger.warning("[REPLAY] Rejected future request (age: %.1fs)", age)
            return False, f"Request timestamp is in the future ({-age:.1f}s ahead)"

        # 2. Check nonce uniqueness
        if nonce in self._seen_nonces:
            logger.warning("[REPLAY] Rejected duplicate nonce: %s", nonce[:32])
            return False, "Duplicate nonce (possible replay)"

        # P2-3.3: If cache is full after pruning, reject (anti-flood)
        self._prune()
        if len(self._seen_nonces) >= self._max_cache:
            logger.warning("[REPLAY] Nonce cache full (%d) — rejecting request", self._max_cache)
            return False, "Server overloaded — too many requests, try again later"

        # 3. Record nonce
        self._seen_nonces[nonce] = now

        return True, ""

    def _prune(self) -> None:
        """Remove old nonces to prevent unbounded memory growth."""
        now = time.time()
        cutoff = now - self._window * 2  # Keep 2x window for safety

        # Prune by time
        while self._seen_nonces:
            oldest_nonce, oldest_time = next(iter(self._seen_nonces.items()))
            if oldest_time < cutoff:
                self._seen_nonces.pop(oldest_nonce)
            else:
                break

        # Prune by size
        while len(self._seen_nonces) > self._max_cache:
            self._seen_nonces.popitem(last=False)


class PersistentReplayGuard:
    """SQLite-backed tx_hash deduplication for gateway replay protection.

    Unlike the in-memory ReplayGuard (for nonce checks), this persists
    consumed tx_hashes to disk so they survive process restarts.
    """

    def __init__(self, db_path: str = "x402_replay.db") -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def init_db(self) -> None:
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        self._db = await aiosqlite.connect(self.db_path, timeout=10.0)
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA busy_timeout=5000")
        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS consumed_tx_hashes (
                tx_hash TEXT PRIMARY KEY,
                recorded_at REAL NOT NULL
            )
            """
        )
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_consumed_at ON consumed_tx_hashes(recorded_at)"
        )
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    async def _ensure_db(self) -> None:
        """Lazy-init DB connection if not yet initialized."""
        if self._db is None:
            await self.init_db()

    async def check_and_record_tx(self, tx_hash: str) -> bool:
        """Check if tx_hash is new; if so, record it.

        Uses INSERT OR IGNORE for atomicity — eliminates the TOCTOU race
        condition that existed in the previous SELECT-then-INSERT approach.

        Returns:
            True if the tx_hash is new (first time seen).
            False if it was already consumed (replay).
        """
        await self._ensure_db()
        cursor = await self._db.execute(
            "INSERT OR IGNORE INTO consumed_tx_hashes (tx_hash, recorded_at) VALUES (?, ?)",
            (tx_hash, time.time()),
        )
        await self._db.commit()
        is_new = cursor.rowcount > 0
        if not is_new:
            logger.warning("[REPLAY] Duplicate tx_hash rejected: %s", tx_hash[:32])
        return is_new

    async def prune(self, max_age_seconds: float = 86400 * 7) -> int:
        """Remove tx_hashes older than max_age_seconds.

        Returns the number of pruned entries.
        """
        await self._ensure_db()
        cutoff = time.time() - max_age_seconds
        cursor = await self._db.execute(
            "DELETE FROM consumed_tx_hashes WHERE recorded_at < ?",
            (cutoff,),
        )
        await self._db.commit()
        return cursor.rowcount


def generate_replay_headers() -> dict[str, str]:
    """Generate timestamp + nonce headers for a client request."""
    return {
        "X-x402-Timestamp": f"{time.time():.3f}",
        "X-x402-Nonce": uuid.uuid4().hex,
    }
