# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.13] - 2026-03-08

### Security

- **S1-1 Private key removed from env**: Decrypted private key no longer stored in `os.environ`; kept in module-level `_decrypted_private_key` with `get_decrypted_private_key()` getter in `config.py`
- **S1-2 Mode-aware host binding**: Gateway and CLI bind to `127.0.0.1` in test mode, `0.0.0.0` in production — prevents accidental test instance exposure
- **S1-3 Strict mock payment verification**: `MockSolanaAdapter.verify_payment()` only accepts tx_hashes recorded by `.pay()` — removes `mock_tx_` prefix fallback
- **S2-1 Minimal health endpoint**: `/health` returns only `{"status":"healthy"}` in production mode — no `target_url` or metrics leakage
- **S2-2 Temp directory permissions**: `os.chmod(tmpdir, 0o700)` applied in both `cli.py::_cmd_run` and `runners/base.py::_create_sitecustomize`

### Fixed

- **B1 Event loop crash**: Added `loop="asyncio"` to uvicorn in `cli.py`, `gateway.py`, and `bridge.py` — prevents `uvloop` import failures on macOS/Windows
- **B2 ATA error detection**: `SolanaAdapter.pay()` now detects missing Associated Token Account and returns a friendly error message instead of raw RPC error
- **B3 Improved ConfigError**: `registry.py` error message now mentions `SOLANA_PRIVATE_KEY` env var and `ag402 setup` command for quick resolution

### Changed

- Version bumped to `0.1.13`
- 17 new TDD security tests in `test_security_fixes_v013.py`
- Test suite: **588 passed**, 0 failed

## [0.1.12] - 2026-03-07

### Fixed

- **Version sync**: All 4 packages (open402, ag402-core, ag402-mcp, ag402-client-mcp) now at 0.1.12
- **CLI crash**: `ag402 env init` called `_cmd_setup()` without required args — fixed
- **Docker**: Dockerfile now includes `examples/` so `weather-api` service starts correctly
- **docker-compose**: Added `--app-dir` for correct module resolution in container

### Security

- **SSRF protection (core)**: `ag402 pay` now validates target URL via `validate_url_safety()` — blocks private IPs, non-HTTPS, reserved ranges (localhost allowed in test mode only)
- **RateLimiter bounded**: Added `max_keys` limit (default 10,000) and periodic sweep to prevent unbounded memory growth under DDoS

### Changed

- **BudgetGuard circuit breaker**: Refactored from class-level (global mutable) state to instance-level `CircuitBreaker` object. Each BudgetGuard instance owns its own breaker by default; pass a shared `CircuitBreaker` when cross-instance sharing is needed. Eliminates test pollution and multi-process state confusion.
- **CLI status**: Circuit breaker display now shows configuration parameters instead of runtime state (which only exists in the gateway process)

### Removed

- `issues-ag402.md` — all tracked issues were resolved; file was stale

### Security (ag402-skill)

This release includes comprehensive security fixes identified through deep code audit:

- **SSRF Protection**: Added comprehensive SSRF protection to `pay` command
  - Blocks HTTP protocol (requires HTTPS)
  - Blocks localhost and private IPs
  - Blocks IPv6 variants
  - Blocks decimal/hex IP formats
  - DNS rebinding protection

- **Authentication**: Added API key authentication
  - Protected commands require AG402_API_KEY
  - Protected: wallet deposit, gateway start/stop
  - Public: wallet status, wallet history, doctor

- **Race Condition Fix**: Added file locking (fcntl.flock)
  - Atomic balance operations
  - Prevents TOCTOU vulnerabilities

- **Input Validation**: Added comprehensive input validation
  - Negative amount rejection
  - Non-number input handling
  - Maximum amount limit (1,000,000)

- **Header Filtering**: Added header whitelist
  - Blocks dangerous headers (Authorization, Cookie, X-Api-Key)
  - Blocks IP spoofing headers (X-Forwarded-For, Host)

### Added

- **Prepaid System**: New prepaid payment mechanism for AI Agent API calls
  - `prepaid_models.py`: Data models for packages, credentials, usage logs
  - `prepaid_client.py`: Buyer-side budget pool management
  - `prepaid_server.py`: Seller-side verification with HMAC signature
  - 5 package tiers: 3/7/30/365/730 days with bundled calls
  - HMAC-SHA256 signature verification
  - Automatic fallback to standard 402 when prepaid exhausted

## [0.1.11] - 2026-03-05

### Security

- **Seller-No-Key documentation hardening**: Comprehensive audit ensuring sellers are never misled into providing a private key
- `.env.example`: Removed seller private key field; `SOLANA_PRIVATE_KEY` marked `⚠️ BUYER ONLY` with role-specific comments
- `.env.example`: Added bottom-of-file seller security notice
- `SECURITY.md`: Added **Seller-No-Key Architecture** to Security Design section
- `setup_wizard.py`: Added security reminder box and private-key-paste detection for seller role
- `cli.py`: `ag402 serve` now prints seller security reminder on startup
- `llms.txt`: Enhanced Sell Skill and added Red Flags section for LLM agents
