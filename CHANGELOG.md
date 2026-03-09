# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security

- **S1-1+ Private key memory safety**: Private keys now use `bytearray` throughout the entire lifecycle instead of immutable `str`, enabling real memory wiping via `ctypes.memset`
  - Added `secure_zero()` — zeroes bytearray buffers using `ctypes.memset` (cannot be optimised away by the interpreter)
  - Added `decrypt_private_key_bytes()` — returns decrypted key as wipeable `bytearray` instead of `str`
  - Module-level `_decrypted_private_key` in `config.py` changed from `str` to `bytearray`
  - Added `clear_decrypted_private_key()` to securely zero and discard the stored key
  - Added `get_decrypted_private_key_buf()` for callers that can work with `bytearray`
  - `SolanaAdapter.__init__()` now accepts `str | bytearray`; wipes input buffer after Keypair creation
  - `PaymentProviderRegistry._build_solana()` passes key as `bytearray` so adapter can wipe it
  - `wipe_from_memory()` upgraded to use `secure_zero()` for bytearrays
  - 14 new dedicated tests in `test_memory_safety.py`
  - Full backward compatibility preserved — all existing APIs still accept `str`
- **Wallet password minimum length raised from 8 to 12 characters** (NIST 800-63B recommendation). Salt size (16 bytes / 128 bit) and encryption algorithm (Fernet/AES-128-CBC + HMAC-SHA256) are already standards-compliant and unchanged

### Fixed

- **Monkey patch resource leak**: Replaced per-request `ThreadPoolExecutor` creation in `requests` sync→async bridge with a module-level shared instance, preventing thread pool churn in Jupyter/async environments
- **Monkey patch stale state**: `disable()` now clears middleware, init lock, and thread pool when reference count reaches zero, ensuring `re-enable()` with different config gets a fresh middleware instance
- 4 new tests in `test_monkey.py` for disable cleanup behavior
- **CI workflow deduplication**: Removed 3 duplicate workflow files (`pip-audit.yml`, `trivy.yml`, `semgrep.yml`) — all security scans consolidated into single `security.yml`. Removed redundant `test` job from `security.yml` (testing is `ci.yml`'s responsibility)
- **RPC failover resource leak**: `SolanaAdapter._reconnect_client()` now closes the old `AsyncClient` before creating a new one, preventing httpx session leaks on endpoint failover
- **Exception handling diagnostics**: Added `exc_info=True` traceback to `pay()` and `verify_payment()` catch-all blocks; added missing `logger.error` to `pay()` catch-all (previously silent)

## [0.1.14] - 2026-03-08

### Fixed

- **CI Workflows**: Fix monorepo `pip install -e .` to install sub-packages (`protocol/`, `core/`, `adapters/`)
- **CI Workflows**: Upgrade `semgrep-action` to container-based approach; upgrade `codeql-action` v3→v4; pin `scorecard-action` to v2.4.1
- **CI Workflows**: Add required `security-events: write` and `id-token: write` permissions
- **Lint F821**: Add module-level `API_KEY` variable in `bridge.py` (was undefined NameError)
- **Lint SIM105**: Use `contextlib.suppress` in `solana_adapter.py`
- **Lint SIM102**: Merge nested `if` statements in `prepaid_server.py`
- **Lint B007**: Prefix unused loop variable with `_` in `challenge_validator.py`
- **Semgrep**: Replace `urllib.request` with `socket` check in `setup_wizard.py`
- **Lint W293**: Fix 35 whitespace-on-blank-line errors across openclaw adapter files
- **Ruff config**: Add `N999` exemption for `ag402-skill` directory

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

[0.1.14]: https://github.com/AetherCore-Dev/ag402/compare/v0.1.13...v0.1.14
[0.1.13]: https://github.com/AetherCore-Dev/ag402/compare/v0.1.12...v0.1.13
[0.1.12]: https://github.com/AetherCore-Dev/ag402/compare/v0.1.11...v0.1.12
[0.1.11]: https://github.com/AetherCore-Dev/ag402/releases/tag/v0.1.11
