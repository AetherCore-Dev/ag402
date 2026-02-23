"""
Tests for the x402 payment gateway adapter (ag402-mcp).

Tests:
1. test_no_auth_returns_402         -- Request without auth -> 402 with x402 headers
2. test_valid_auth_proxies_request  -- Request with valid x402 auth -> proxied to target
3. test_invalid_auth_returns_403    -- Request with non-x402 auth -> 403
4. test_402_response_has_correct_headers -- The 402 response has proper WWW-Authenticate header
5. test_gateway_proxies_full_response    -- Proxied response body matches target

IMPORTANT: ASGITransport does NOT trigger FastAPI lifespan events.
Therefore we must:
  - Use a tmp_path-based replay DB to avoid locking the real ~/.ag402/ file
  - Manually call init_db() / close() on the persistent guard
  - Mock httpx.AsyncClient with proper AsyncMock (request + aclose)
"""

from __future__ import annotations

import json
import time
import uuid
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from ag402_core.gateway.auth import PaymentVerifier
from ag402_mcp.gateway import X402Gateway
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from open402.headers import parse_www_authenticate


def _replay_headers() -> dict[str, str]:
    """Generate valid X-x402-Timestamp and X-x402-Nonce headers."""
    return {
        "X-x402-Timestamp": str(int(time.time())),
        "X-x402-Nonce": uuid.uuid4().hex,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_upstream_response(
    status_code: int = 200,
    body: dict | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Build a real httpx.Response for mocking upstream calls."""
    body = body or {}
    content = json.dumps(body).encode()
    resp_headers = headers or {"content-type": "application/json"}
    return httpx.Response(
        status_code=status_code,
        content=content,
        headers=resp_headers,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _create_mock_upstream() -> FastAPI:
    """Create a simple mock upstream service."""
    upstream = FastAPI()

    @upstream.get("/weather")
    async def weather(city: str = "Tokyo"):
        return JSONResponse(content={"city": city, "temp": 22, "condition": "sunny"})

    @upstream.get("/health")
    async def health():
        return JSONResponse(content={"status": "ok"})

    @upstream.post("/data")
    async def post_data():
        return JSONResponse(content={"received": True}, status_code=201)

    return upstream


@pytest.fixture
def upstream_app() -> FastAPI:
    return _create_mock_upstream()


@pytest.fixture
async def gateway_app(tmp_path) -> FastAPI:
    """Create a gateway app with a test-mode verifier and temp replay DB.

    Uses tmp_path to avoid locking the real ~/.ag402/gateway_replay.db.
    Manually inits the persistent replay guard since ASGITransport skips lifespan.
    """
    verifier = PaymentVerifier()  # test mode -- accepts any x402 proof
    replay_db = str(tmp_path / "test_replay.db")
    gateway = X402Gateway(
        target_url="http://mock-upstream",
        price="0.02",
        chain="solana",
        token="USDC",
        address="TestRecipientAddr1111111111111111111111111",
        verifier=verifier,
        replay_db_path=replay_db,
    )
    app = gateway.create_app()
    # Manually init the persistent guard (lifespan won't fire in ASGITransport)
    await gateway._persistent_guard.init_db()
    yield app
    await gateway._persistent_guard.close()


@pytest.fixture
def upstream_transport(upstream_app: FastAPI) -> ASGITransport:
    return ASGITransport(app=upstream_app)


# ---------------------------------------------------------------------------
# Test 1: No auth -> 402
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_auth_returns_402(gateway_app: FastAPI) -> None:
    """Request without Authorization header should return 402 Payment Required."""
    transport = ASGITransport(app=gateway_app)
    async with AsyncClient(transport=transport, base_url="http://testgateway") as client:
        response = await client.get("/weather?city=Tokyo")

    assert response.status_code == 402
    body = response.json()
    assert body["error"] == "Payment Required"
    assert body["protocol"] == "x402"
    assert body["amount"] == "0.02"


# ---------------------------------------------------------------------------
# Test 2: Valid x402 auth -> proxy
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_valid_auth_proxies_request(
    gateway_app: FastAPI, upstream_transport: ASGITransport
) -> None:
    """Request with valid x402 Authorization should be proxied to the upstream."""
    transport = ASGITransport(app=gateway_app)

    mock_upstream_resp = _make_mock_upstream_response(
        status_code=200,
        body={"city": "Tokyo", "temp": 22, "condition": "sunny"},
    )

    # Mock the fallback httpx.AsyncClient that gateway creates when lifespan
    # hasn't set up the shared client.  Must mock both request() and aclose().
    with patch("ag402_mcp.gateway.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.request.return_value = mock_upstream_resp
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        async with AsyncClient(transport=transport, base_url="http://testgateway") as client:
            response = await client.get(
                "/weather?city=Tokyo",
                headers={
                    "Authorization": "x402 mock_tx_abc123def456",
                    **_replay_headers(),
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["city"] == "Tokyo"
    assert data["temp"] == 22


# ---------------------------------------------------------------------------
# Test 3: Non-x402 auth -> 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_auth_returns_403(gateway_app: FastAPI) -> None:
    """Request with non-x402 Authorization (e.g. Bearer) should return 403."""
    transport = ASGITransport(app=gateway_app)
    async with AsyncClient(transport=transport, base_url="http://testgateway") as client:
        response = await client.get(
            "/weather?city=Tokyo",
            headers={"Authorization": "Bearer some-jwt-token"},
        )

    assert response.status_code == 403
    body = response.json()
    assert "x402" in body.get("detail", "").lower() or "x402" in body.get("error", "").lower()


# ---------------------------------------------------------------------------
# Test 4: 402 has correct WWW-Authenticate header
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_402_response_has_correct_headers(gateway_app: FastAPI) -> None:
    """The 402 response should have a valid WWW-Authenticate header with x402 challenge."""
    transport = ASGITransport(app=gateway_app)
    async with AsyncClient(transport=transport, base_url="http://testgateway") as client:
        response = await client.get("/weather?city=London")

    assert response.status_code == 402

    www_auth = response.headers.get("www-authenticate", "")
    assert www_auth, "WWW-Authenticate header must be present"
    assert www_auth.startswith("x402 "), "WWW-Authenticate must use x402 scheme"

    # Parse the header and verify fields
    challenge = parse_www_authenticate(www_auth)
    assert challenge is not None, "WWW-Authenticate header must be parseable"
    assert challenge.chain == "solana"
    assert challenge.token == "USDC"
    assert challenge.amount == "0.02"
    assert challenge.address == "TestRecipientAddr1111111111111111111111111"


# ---------------------------------------------------------------------------
# Test 5: Proxied response body matches target
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gateway_proxies_full_response(
    gateway_app: FastAPI, upstream_transport: ASGITransport
) -> None:
    """Proxied response body should exactly match what the upstream returns."""
    transport = ASGITransport(app=gateway_app)

    expected_body = {"city": "Berlin", "temp": 12, "condition": "overcast"}
    mock_upstream_resp = _make_mock_upstream_response(
        status_code=200,
        body=expected_body,
    )

    with patch("ag402_mcp.gateway.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.request.return_value = mock_upstream_resp
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        async with AsyncClient(transport=transport, base_url="http://testgateway") as client:
            response = await client.get(
                "/weather?city=Berlin",
                headers={
                    "Authorization": "x402 mock_tx_proxy_test_hash",
                    **_replay_headers(),
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data == expected_body
