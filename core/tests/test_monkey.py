"""Tests for ag402_core.monkey — enable/disable/enabled monkey-patch."""

from __future__ import annotations

import ag402_core
import ag402_core.monkey as monkey_mod
import httpx
import pytest


@pytest.fixture(autouse=True)
def _cleanup():
    """Ensure monkey-patch is disabled after each test."""
    yield
    if monkey_mod._enabled:
        monkey_mod.disable()
    # Reset global state
    monkey_mod._middleware = None
    monkey_mod._enabled = False
    monkey_mod._patched_httpx = False
    monkey_mod._patched_requests = False
    monkey_mod._original_httpx_send = None
    monkey_mod._original_requests_send = None


class TestEnableDisable:
    def test_enable_sets_flag(self):
        ag402_core.enable()
        assert ag402_core.is_enabled()

    def test_disable_clears_flag(self):
        ag402_core.enable()
        ag402_core.disable()
        assert not ag402_core.is_enabled()

    def test_enable_idempotent(self):
        ag402_core.enable()
        ag402_core.enable()  # should not crash
        assert ag402_core.is_enabled()

    def test_disable_idempotent(self):
        ag402_core.disable()  # should not crash when not enabled
        assert not ag402_core.is_enabled()

    def test_httpx_patched(self):
        original_send = httpx.AsyncClient.send
        ag402_core.enable()
        assert httpx.AsyncClient.send is not original_send
        ag402_core.disable()
        assert httpx.AsyncClient.send is original_send

    def test_context_manager(self):
        with ag402_core.enabled():
            assert ag402_core.is_enabled()
        assert not ag402_core.is_enabled()


class TestPassthrough:
    """Ensure non-402 responses pass through completely untouched."""

    @pytest.mark.asyncio
    async def test_200_passthrough(self):
        """200 responses must be returned exactly as-is."""
        ag402_core.enable()

        # Create a mock transport that returns 200
        class MockTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                return httpx.Response(200, json={"ok": True}, request=request)

        async with httpx.AsyncClient(transport=MockTransport()) as client:
            resp = await client.get("https://example.com/free-api")
            assert resp.status_code == 200
            assert resp.json() == {"ok": True}

    @pytest.mark.asyncio
    async def test_404_passthrough(self):
        """404 responses must pass through."""
        ag402_core.enable()

        class MockTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                return httpx.Response(404, text="Not found", request=request)

        async with httpx.AsyncClient(transport=MockTransport()) as client:
            resp = await client.get("https://example.com/missing")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_500_passthrough(self):
        """500 responses must pass through."""
        ag402_core.enable()

        class MockTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                return httpx.Response(500, text="Internal error", request=request)

        async with httpx.AsyncClient(transport=MockTransport()) as client:
            resp = await client.get("https://example.com/broken")
            assert resp.status_code == 500

    @pytest.mark.asyncio
    async def test_402_without_x402_passthrough(self):
        """402 without x402 WWW-Authenticate header must pass through."""
        ag402_core.enable()

        class MockTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                return httpx.Response(
                    402,
                    text="Payment required",
                    headers={"www-authenticate": "Basic realm=billing"},
                    request=request,
                )

        async with httpx.AsyncClient(transport=MockTransport()) as client:
            resp = await client.get("https://example.com/paywall")
            assert resp.status_code == 402

    @pytest.mark.asyncio
    async def test_disabled_402_passthrough(self):
        """When disabled, even x402 402 should pass through."""
        # NOT calling enable()
        class MockTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                return httpx.Response(402, text="Pay up", request=request)

        async with httpx.AsyncClient(transport=MockTransport()) as client:
            resp = await client.get("https://example.com/paid")
            assert resp.status_code == 402
