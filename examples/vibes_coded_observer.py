"""
Vibes-Coded Observer Middleware — ag402 integration example
===========================================================

Wraps an agent's *irreversible* actions (payments, transfers, stateful writes)
so a trust check runs against Vibes-Coded's pay-per-call x402 guard APIs
*before* ag402 settles the action.

ag402 already auto-pays any HTTP 402 (see `ag402_core.enable()`), so the guard
calls below cost a tiny per-call USDC fee and require zero payment code here.

## Setup (3 steps)
1. Install:        pip install ag402-core httpx
2. Export keys:    export AG402_SANDBOX_KEY="op_sk_sandbox_ag402_..."   # from ag402 team
                    export VIBES_ORIGIN="https://vibes-coded-production.up.railway.app"
3. Run:            python examples/vibes_coded_observer.py

## What it does
For every outgoing action the agent intends to take, `observe()` classifies the
intent and, if it maps to a guard, calls that guard endpoint. A guard returning
`allowed: false` blocks the action (the agent must justify / back off). A guard
returning `allowed: true` lets ag402 proceed to settlement.

Guards (all hosted, x402 pay-per-call):
  - idempotency-guard     -> replay / double-spend protection
  - agent-state-guard     -> pre-action reliability gate
  - memory-exfil-guard    -> data-leak / exfil screen
  - rate-limit-guard      -> amount/velocity anomaly check
  - action-receipt        -> signed, replayable post-settlement receipt (offline-verifiable)
"""

from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

import ag402_core
import httpx

VIBES_ORIGIN = os.getenv("VIBES_ORIGIN", "https://vibes-coded-production.up.railway.app").rstrip("/")
AG402_SANDBOX_KEY = os.getenv("AG402_SANDBOX_KEY", "")

# Map an action intent -> the Vibes-Coded guard endpoint that should gate it.
# Inbound actions an Observer should screen before ag402 settles them.
# All slugs below are live endpoints (see https://vibes-coded.com/for-agents).
GUARD_ROUTES: dict[str, str] = {
    "payment_or_transfer": "idempotency-guard",          # replay / double-spend protection
    "stateful_action": "agent-state-guard",              # pre-action reliability gate
    "idempotent_call": "idempotency-guard",              # same-spend guard
    "external_write": "memory-exfil-guard",              # data-leak / exfil screen
    "value_transfer": "rate-limit-guard",                # amount/velocity anomaly check
}


def emit_receipt(action: Action, observation: Observation) -> dict | None:
    """After a gated action is allowed + settled, mint a signed action-receipt.

    This is the post-settlement accountability layer impeachmentright / giskard09
    called for: a machine-checkable, replayable record of who did what, bound to the
    action tuple + observer verdict. Verifiable offline against our published key,
    so a downstream agent or auditor can trust the handoff without our service.
    """
    if not observation.allowed:
        return None
    payload_digest = action.payload.get("payload_digest") or hashlib.sha256(
        repr(sorted(action.payload.items())).encode()
    ).hexdigest()
    url = f"{VIBES_ORIGIN}/api/v1/outcomes/action-receipt"
    try:
        resp = httpx.post(
            url,
            json={
                "agent_id": action.payload.get("agent_id", "observer-agent"),
                "action": action.intent,
                "payload_digest": payload_digest,
                "nonce": uuid.uuid4().hex,          # unique per action -> replay-safe
                "quote": observation.guard,          # the guard that approved it
            },
            headers={"X-Ag402-Sandbox-Key": AG402_SANDBOX_KEY} if AG402_SANDBOX_KEY else {},
            timeout=20.0,
        )
        return resp.json()
    except Exception:
        return None


@dataclass
class Action:
    """An agent action about to be settled by ag402."""
    intent: str
    payload: dict[str, Any] = field(default_factory=dict)
    # Optional: a callable that actually executes the action (after guards pass).
    execute: Callable[[], Any] | None = None


@dataclass
class Observation:
    allowed: bool
    reason: str
    guard: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)


class VibesObserver:
    """Lightweight Observer that gates irreversible actions via Vibes-Coded guards."""

    def __init__(self, origin: str = VIBES_ORIGIN, timeout: float = 20.0) -> None:
        self.origin = origin.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def _guard_slug(self, intent: str) -> str | None:
        return GUARD_ROUTES.get(intent)

    def observe(self, action: Action) -> Observation:
        """Run the guard for `action.intent`. Block if the guard rejects."""
        guard = self._guard_slug(action.intent)
        if not guard:
            # No guard maps to this intent — allow (observer is advisory here).
            return Observation(allowed=True, reason="no guard mapped", guard=None)

        url = f"{self.origin}/api/v1/outcomes/{guard}"
        # ag402_core.enable() auto-pays the 402 on this POST; we just send the
        # action context. The guard returns {"allowed": bool, "reason": str, ...}.
        try:
            resp = self._client.post(
                url,
                json={"action": action.intent, "context": action.payload},
                headers={"X-Ag402-Sandbox-Key": AG402_SANDBOX_KEY} if AG402_SANDBOX_KEY else {},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:  # network/parse failure -> fail closed
            return Observation(allowed=False, reason=f"guard call failed: {exc}", guard=guard)

        allowed = bool(data.get("allowed", False))
        return Observation(
            allowed=allowed,
            reason=data.get("reason", "ok" if allowed else "rejected"),
            guard=guard,
            detail=data,
        )

    def run(self, action: Action) -> Any:
        """Observe, and only execute the action if guards allow it.
        On success, mints a signed action-receipt for post-settlement accountability.
        """
        obs = self.observe(action)
        if not obs.allowed:
            raise PermissionError(f"[VibesObserver] blocked '{action.intent}': {obs.reason}")
        result = action.execute() if action.execute else obs
        receipt = emit_receipt(action, obs)
        if receipt:
            print(f"[RECEIPT] {receipt.get('receipt_id')} (verify: {receipt.get('verify_endpoint')})")
        return result

    def close(self) -> None:
        self._client.close()


# ---------------------------------------------------------------------------
# Demo: a payment action gated by the orchestration guard, then settled by ag402
# ---------------------------------------------------------------------------

def _demo_payment() -> dict:
    """Simulated irreversible action ag402 would settle."""
    return {"settled": True, "amount_usdc": 0.50, "to": "9xQeWvG816bUx9EPjHmaT23yFs2nA8Lg4bQ9Z"}


def main() -> None:
    print("\n=== Vibes-Coded Observer + ag402 ===\n")
    print("ag402 auto-payment enabled — guard 402s are paid transparently.\n")
    ag402_core.enable()

    obs = VibesObserver()

    # 1) A payment the Observer should screen first.
    payment = Action(intent="payment_or_transfer", payload={"amount_usdc": 0.50, "to": "9xQeWvG816bUx9EPjHmaT23yFs2nA8Lg4bQ9Z"}, execute=_demo_payment)
    try:
        result = obs.run(payment)
        print(f"[ALLOWED] payment settled: {result}")
    except PermissionError as e:
        print(f"[BLOCKED] {e}")

    # 2) A benign read that maps to no guard -> advisory allow.
    read = Action(intent="read_only", payload={"resource": "market_data"})
    o = obs.observe(read)
    print(f"[ADVISORY] {read.intent}: allowed={o.allowed} ({o.reason})")

    obs.close()
    ag402_core.disable()


if __name__ == "__main__":
    main()
