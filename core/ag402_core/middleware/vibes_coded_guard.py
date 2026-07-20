"""Vibes-Coded trust guard — pre-settlement screening + signed action-receipts.

Drop-in ag402 middleware (lives alongside ``budget_guard``). Before an irreversible
action is settled, it screens the action through Vibes-Coded's hosted pay-per-call
guards (idempotency / spend / contract-pin / agent-state) and, on allow, mints a
signed, offline-verifiable action-receipt.

The guard calls are x402 402s — ag402's own payment middleware pays them transparently,
so this integrates as a pure trust layer: the agent only pays a tiny per-call USDC fee
when an action is actually screened. No seats, no minimums.

Commercials: pay-per-call x402 (Agent Economy > Vibes-Coded on vibes-coded.com).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Hosted guard endpoints (x402 pay-per-call). The preimage the action-receipt binds
# is the frozen action tuple, so any downstream agent can recompute it offline.
VIBES_ORIGIN = "https://vibes-coded-production.up.railway.app"
ACTION_RECEIPT_URL = f"{VIBES_ORIGIN}/api/v1/outcomes/action-receipt"

# Map an action intent -> the Vibes-Coded guard that should gate it.
GUARD_ROUTES: dict[str, str] = {
    "payment_or_transfer": "idempotency-guard",   # replay / double-spend
    "stateful_action": "agent-state-guard",        # pre-action reliability gate
    "idempotent_call": "idempotency-guard",
    "external_write": "memory-exfil-guard",        # data-leak / exfil screen
    "value_transfer": "rate-limit-guard",          # amount/velocity anomaly
    "contract_call": "contract-pin-guard",         # runtime contract-drift gate
}


@dataclass
class GuardResult:
    allowed: bool
    reason: str = ""
    guard: str | None = None
    receipt_id: str | None = None
    detail: dict[str, Any] = None  # type: ignore[assignment]


class VibesCodedGuard:
    """Screen irreversible actions through Vibes-Coded's hosted trust guards.

    Usage::

        guard = VibesCodedGuard(sandbox_key=AG402_SANDBOX_KEY)
        result = await guard.screen(intent="payment_or_transfer",
                                    payload={"amount_usdc": 0.50, "to": "..."})
        if not result.allowed:
            raise PermissionError(result.reason)   # fail closed
        # settle via ag402, then result.receipt_id proves what happened
    """

    def __init__(
        self,
        origin: str = VIBES_ORIGIN,
        timeout: float = 20.0,
        sandbox_key: str = "",
        emit_receipt: bool = True,
    ) -> None:
        self._origin = origin.rstrip("/")
        self._timeout = timeout
        self._sandbox_key = sandbox_key
        self._emit_receipt = emit_receipt
        self._client = httpx.Client(timeout=timeout)

    # -- helpers ---------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        if self._sandbox_key:
            return {"X-Ag402-Sandbox-Key": self._sandbox_key}
        return {}

    def _guard_slug(self, intent: str) -> str | None:
        return GUARD_ROUTES.get(intent)

    def _emit_receipt(self, intent: str, payload: dict[str, Any], guard: str) -> str | None:
        import hashlib

        digest = payload.get("payload_digest") or hashlib.sha256(
            repr(sorted(payload.items())).encode()
        ).hexdigest()
        try:
            resp = self._client.post(
                f"{self._origin}/api/v1/outcomes/action-receipt",
                json={
                    "agent_id": payload.get("agent_id", "observer-agent"),
                    "action": intent,
                    "payload_digest": digest,
                    "nonce": uuid.uuid4().hex,
                    "quote": guard,
                },
                headers=self._headers(),
            )
            data = resp.json()
            return data.get("receipt_id")
        except Exception as exc:  # receipt is best-effort; never block on it
            logger.warning("[VIBES] receipt mint failed: %s", exc)
            return None

    # -- main entry ------------------------------------------------------------

    def screen(self, intent: str, payload: dict[str, Any]) -> GuardResult:
        """Run the mapped guard; block if it rejects. Fail closed on any error."""
        guard = self._guard_slug(intent)
        if not guard:
            # No guard maps to this intent — advisory allow (observer is opt-in here).
            return GuardResult(allowed=True, reason="no guard mapped", guard=None)

        try:
            resp = self._client.post(
                f"{self._origin}/api/v1/outcomes/{guard}",
                json={"action": intent, "context": payload},
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:  # network/parse failure -> fail closed
            return GuardResult(allowed=False, reason=f"guard call failed: {exc}", guard=guard)

        allowed = bool(data.get("allowed", False))
        if not allowed:
            return GuardResult(
                allowed=False,
                reason=data.get("reason", "rejected"),
                guard=guard,
                detail=data,
            )

        receipt_id = None
        if self._emit_receipt:
            receipt_id = self._emit_receipt(intent, payload, guard)
        return GuardResult(
            allowed=True,
            reason=data.get("reason", "ok"),
            guard=guard,
            receipt_id=receipt_id,
            detail=data,
        )

    def close(self) -> None:
        self._client.close()
