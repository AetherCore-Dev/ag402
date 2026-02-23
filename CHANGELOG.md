# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-23

### Added

- **open402**: x402 protocol types, header parsing, version negotiation (zero dependencies)
- **ag402-core**: Payment engine with wallet (SQLite), 6-layer budget guard, Solana adapter, middleware, CLI (18 commands)
- **ag402-mcp**: HTTP gateway adapter — wrap any API with x402 paywall
- **ag402-client-mcp**: MCP client adapter for Claude Code, Cursor, OpenClaw
- Monkey-patch SDK: `ag402_core.enable()` for transparent httpx/requests interception
- Interactive setup wizard: `ag402 setup`
- Full E2E demo: `ag402 demo`
- PBE wallet encryption (PBKDF2-HMAC-SHA256 + AES)
- 6-layer safety system: single-tx cap, per-minute cap, daily cap, circuit breaker, auto-rollback, key filter
- Docker support with encrypted wallet
- 430+ tests, 90%+ coverage

### Security

- Non-custodial: private keys never leave your machine
- Zero telemetry: no usage tracking, no IP logging
- Replay protection, SSRF protection, header whitelist
- RPC retry + failover for Solana adapter
- Comprehensive security audit: all P0/P1/P2 issues fixed (24 issues, 19 resolved)
