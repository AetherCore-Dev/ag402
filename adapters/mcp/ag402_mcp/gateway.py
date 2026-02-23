"""
x402 MCP Gateway -- reverse proxy that adds x402 payment gating to any HTTP API.

Wraps any upstream HTTP service (e.g. a weather API, an MCP server) and
requires x402 payment before proxying requests. Clients that do not present
a valid payment proof receive HTTP 402 with a WWW-Authenticate challenge.

Usage as library:
    gateway = X402Gateway(target_url="http://localhost:8000", price="0.02", address="...")
    app = gateway.create_app()
    uvicorn.run(app, host="0.0.0.0", port=8001)

Usage as CLI:
    ag402-gateway --target http://localhost:8000 --price 0.02 --address SolAddr...
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from contextlib import asynccontextmanager

import httpx
from ag402_core.gateway.auth import PaymentVerifier
from ag402_core.security.rate_limiter import RateLimiter
from ag402_core.security.replay_guard import PersistentReplayGuard, ReplayGuard
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from open402.headers import build_www_authenticate
from open402.spec import X402PaymentChallenge, X402ServiceDescriptor

logger = logging.getLogger(__name__)


class X402Gateway:
    """Wraps any HTTP API/MCP server and adds x402 payment gate."""

    def __init__(
        self,
        target_url: str,
        price: str,
        chain: str = "solana",
        token: str = "USDC",
        address: str = "",
        verifier: PaymentVerifier | None = None,
        replay_window: int = 30,
        replay_db_path: str = "",
        rate_limit_per_minute: int = 60,
    ):
        self.target_url = target_url.rstrip("/")
        self.price = price
        self.chain = chain
        self.token = token
        self.address = address or "GtwRecipientAddr1111111111111111111111111111"
        self._replay_guard = ReplayGuard(window_seconds=replay_window)

        # P0-1.2: Detect test mode from environment; warn prominently
        self._is_test_mode = os.getenv("X402_MODE", "test").lower() == "test"
        if verifier is not None:
            self.verifier = verifier
        elif self._is_test_mode:
            logger.warning(
                "========================================\n"
                "  WARNING: GATEWAY RUNNING IN TEST MODE\n"
                "  No on-chain payment verification!\n"
                "  Set X402_MODE=production for real use.\n"
                "========================================"
            )
            self.verifier = PaymentVerifier()  # test mode
        else:
            raise ValueError(
                "Production mode (X402_MODE=production) requires an explicit "
                "PaymentVerifier with a payment provider. Either provide a "
                "'verifier' argument or set X402_MODE=test for development."
            )
        self._replay_guard = ReplayGuard(window_seconds=replay_window)
        # Persistent tx_hash deduplication (survives restarts)
        self._replay_db_path = replay_db_path or os.path.expanduser("~/.ag402/gateway_replay.db")
        self._persistent_guard = PersistentReplayGuard(db_path=self._replay_db_path)
        # Shared httpx client (created/closed via lifespan)
        self._http_client: httpx.AsyncClient | None = None

        # P1-2.7: IP-based rate limiter
        self._rate_limiter = RateLimiter(
            max_requests=rate_limit_per_minute, window_seconds=60
        )

        # P2-3.6: Lightweight metrics counters
        self._metrics = {
            "requests_total": 0,
            "payments_verified": 0,
            "payments_rejected": 0,
            "replays_rejected": 0,
            "challenges_issued": 0,
            "proxy_errors": 0,
            "started_at": time.time(),
        }

        # Build the service descriptor for 402 challenges
        self._service = X402ServiceDescriptor(
            endpoint=self.target_url,
            price=self.price,
            chain=self.chain,
            token=self.token,
            address=self.address,
        )

    def _build_challenge(self) -> X402PaymentChallenge:
        """Build the payment challenge for 402 responses."""
        return self._service.to_challenge()

    def _build_402_response(self) -> JSONResponse:
        """Build an HTTP 402 response with x402 WWW-Authenticate header."""
        challenge = self._build_challenge()
        www_auth_value = build_www_authenticate(challenge)
        return JSONResponse(
            status_code=402,
            content={
                "error": "Payment Required",
                "protocol": "x402",
                "chain": challenge.chain,
                "token": challenge.token,
                "amount": challenge.amount,
                "address": challenge.address,
            },
            headers={"WWW-Authenticate": www_auth_value},
        )

    def create_app(self) -> FastAPI:
        """Create a FastAPI app that proxies requests with payment gate."""
        gateway = self

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Manage shared resources: httpx client and persistent replay guard."""
            gateway._http_client = httpx.AsyncClient(timeout=30.0)
            await gateway._persistent_guard.init_db()
            yield
            await gateway._http_client.aclose()
            gateway._http_client = None
            await gateway._persistent_guard.close()

        app = FastAPI(
            title="x402 Payment Gateway",
            description=f"Payment-gated proxy to {self.target_url}",
            lifespan=lifespan,
        )

        # P2-3.6: Health check endpoint (not gated behind payment)
        @app.get("/health")
        async def health_check() -> JSONResponse:
            """Return gateway health status and metrics."""
            uptime = time.time() - self._metrics["started_at"]
            return JSONResponse(content={
                "status": "healthy",
                "mode": "test" if self._is_test_mode else "production",
                "target_url": self.target_url,
                "uptime_seconds": round(uptime, 1),
                "metrics": {
                    "requests_total": self._metrics["requests_total"],
                    "payments_verified": self._metrics["payments_verified"],
                    "payments_rejected": self._metrics["payments_rejected"],
                    "replays_rejected": self._metrics["replays_rejected"],
                    "challenges_issued": self._metrics["challenges_issued"],
                    "proxy_errors": self._metrics["proxy_errors"],
                },
            })

        @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
        async def gateway_handler(request: Request, path: str) -> Response:
            """Catch-all route that gates all requests behind x402 payment."""
            self._metrics["requests_total"] += 1

            # P1-2.7: IP-based rate limiting
            client_ip = request.client.host if request.client else "unknown"
            if not self._rate_limiter.allow(client_ip):
                self._metrics["rate_limited"] = self._metrics.get("rate_limited", 0) + 1
                logger.warning("[GATEWAY] Rate limited: %s", client_ip)
                return JSONResponse(
                    status_code=429,
                    content={"error": "Too Many Requests", "detail": "Rate limit exceeded"},
                )

            authorization = request.headers.get("authorization", "")

            # 1. Check for Authorization header
            if not authorization:
                # No auth at all -> 402 challenge
                logger.info("[GATEWAY] No Authorization header -- returning 402")
                self._metrics["challenges_issued"] += 1
                return self._build_402_response()

            # 2. Check if it's x402 format
            if not authorization.strip().lower().startswith("x402 "):
                # Non-x402 auth (e.g. Bearer token) -> 403 Forbidden
                logger.info("[GATEWAY] Non-x402 Authorization -- returning 403")
                return JSONResponse(
                    status_code=403,
                    content={"error": "Forbidden", "detail": "x402 payment proof required"},
                )

            # 3. Replay protection (timestamp + nonce check) — MANDATORY
            ts = request.headers.get("x-x402-timestamp", "")
            nonce = request.headers.get("x-x402-nonce", "")
            replay_ok, replay_err = self._replay_guard.check(ts, nonce)
            if not replay_ok:
                logger.warning("[GATEWAY] Replay check failed: %s", replay_err)
                self._metrics["replays_rejected"] += 1
                return JSONResponse(
                    status_code=403,
                    content={"error": "Replay rejected", "detail": replay_err},
                )

            # 4. Verify the x402 proof
            result = await self.verifier.verify(
                authorization,
                expected_amount=float(self.price),
                expected_address=self.address,
            )

            if not result.valid:
                logger.warning("[GATEWAY] Invalid payment proof: %s", result.error)
                self._metrics["payments_rejected"] += 1
                return JSONResponse(
                    status_code=403,
                    content={"error": "Payment verification failed", "detail": result.error},
                )

            # 5b. Persistent tx_hash replay check (survives restarts)
            is_new = await self._persistent_guard.check_and_record_tx(result.tx_hash)
            if not is_new:
                logger.warning("[GATEWAY] Duplicate tx_hash rejected: %s", result.tx_hash[:32])
                self._metrics["replays_rejected"] += 1
                return self._build_402_response()

            # 6. Proxy the request to the target
            self._metrics["payments_verified"] += 1
            logger.info("[GATEWAY] Payment verified (tx: %s) -- proxying to %s", result.tx_hash, self.target_url)
            try:
                return await self._proxy_request(request, path)
            except Exception as exc:
                self._metrics["proxy_errors"] += 1
                logger.error("[GATEWAY] Proxy error: %s", exc)
                return JSONResponse(status_code=502, content={"error": "Bad Gateway"})

        return app

    async def _proxy_request(self, request: Request, path: str) -> Response:
        """Forward the request to the upstream target service."""
        target = f"{self.target_url}/{path}"
        if request.url.query:
            target = f"{target}?{request.url.query}"

        # Read request body
        body = await request.body()

        # P2-3.4: Whitelist-based header forwarding — only pass known-safe headers
        # to prevent X-Forwarded-For spoofing, Cookie leakage, Connection abuse, etc.
        _ALLOWED_HEADERS = {
            "accept", "accept-encoding", "accept-language",
            "content-type", "user-agent", "origin", "referer",
            "cache-control", "if-none-match", "if-modified-since",
            "x-request-id", "x-correlation-id",
        }
        proxy_headers = {}
        for key, value in request.headers.items():
            if key.lower() in _ALLOWED_HEADERS:
                proxy_headers[key] = value

        # Use shared client (falls back to per-request if lifespan not used)
        client = self._http_client
        if client is None:
            client = httpx.AsyncClient(timeout=30.0)

        try:
            upstream_response = await client.request(
                method=request.method,
                url=target,
                headers=proxy_headers,
                content=body if body else None,
            )
        finally:
            # Only close if we created a fallback client
            if self._http_client is None:
                await client.aclose()

        # Build response headers (exclude hop-by-hop)
        response_headers = {}
        skip_response_headers = {"transfer-encoding", "content-encoding", "content-length"}
        for key, value in upstream_response.headers.items():
            if key.lower() not in skip_response_headers:
                response_headers[key] = value

        return Response(
            content=upstream_response.content,
            status_code=upstream_response.status_code,
            headers=response_headers,
        )


def cli_main() -> None:
    """Entry point for `ag402-gateway` CLI command."""
    parser = argparse.ArgumentParser(
        description="x402 Payment Gateway -- adds pay-per-call to any HTTP API",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="URL of the upstream service to protect (e.g. http://localhost:8000)",
    )
    parser.add_argument(
        "--price",
        default="0.02",
        help="Price per call in token units (default: 0.02)",
    )
    parser.add_argument(
        "--address",
        default="",
        help="Recipient wallet address for payments",
    )
    parser.add_argument(
        "--chain",
        default="solana",
        help="Blockchain network (default: solana)",
    )
    parser.add_argument(
        "--token",
        default="USDC",
        help="Payment token (default: USDC)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind the gateway (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port to bind the gateway (default: 8001)",
    )

    args = parser.parse_args()

    import uvicorn

    gateway = X402Gateway(
        target_url=args.target,
        price=args.price,
        chain=args.chain,
        token=args.token,
        address=args.address,
    )
    app = gateway.create_app()

    logger.info(
        "[GATEWAY] Starting x402 gateway on %s:%d -> %s (price: %s %s)",
        args.host, args.port, args.target, args.price, args.token,
    )

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    cli_main()
