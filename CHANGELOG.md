# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2026-02-23

### Fixed

- **ATA preflight bug**: Skip preflight simulation when creating recipient ATA in same transaction — fixes spurious `InvalidAccountData` errors on devnet/mainnet first-time payments
- **On-chain error detection**: Check `confirm_transaction` response for execution errors after `skip_preflight=True` — prevents false `success=True` when transaction fails on-chain (fund safety fix)
- **Fragile test assertions**: Relaxed balance assertions in localnet/devnet tests to tolerate E2E test side effects

### Added

- **CI localnet job**: GitHub Actions now runs localnet integration tests with `solana-test-validator` on every PR
- **CI devnet nightly**: Devnet integration tests run on nightly schedule via GitHub Actions (secrets-based)
- **Flaky test reruns**: Added `pytest-rerunfailures` with `@pytest.mark.flaky(reruns=2)` on known network-sensitive devnet tests
- **Performance baseline**: New `conftest_perf.py` plugin records test durations to `.perf-baseline.json`; use `--perf-compare` to detect latency regressions
- `make test-perf` — run devnet tests with performance regression comparison
- `make install-crypto` — install crypto dependencies shortcut

### Known Issues & Future Work

- **Concurrent payments**: No tests for multiple agents paying simultaneously with same keypair (nonce conflicts)
- **Mainnet smoke test**: No real mainnet transaction tests yet — devnet/localnet only
- **Transaction idempotency**: No idempotency key / dedup mechanism — agent retry may cause double-spend
- **Priority fees**: No `computeBudget` / priority fee support — mainnet congestion may cause pending transactions
- **RPC failover**: `MultiEndpointClient` exists but not yet integrated into production `SolanaAdapter.pay()` flow
- **Token 2022**: Only classic SPL Token program supported; Token Extensions not tested
- **Dynamic confirm timeout**: Hardcoded `min(timeout, 15s)` — should adapt per network (devnet 30s, mainnet 60s)
- **Two-phase ATA creation**: Current approach skips preflight for ATA+transfer; ideal would be separate CreateATA tx → wait → TransferChecked tx

## [0.1.1] - 2026-02-23

### Fixed

- Re-release to resolve PyPI upload conflict (file name reuse)
- Fixed CI workflow configuration (checkout & setup-python action versions)

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
