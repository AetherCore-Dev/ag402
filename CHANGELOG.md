# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`@ag402/fetch` v0.1.0** — TypeScript SDK for x402 auto-payment (`sdk/typescript/`).
  - `createX402Fetch({ wallet, provider?, config?, paymentTimeoutMs? })` — wraps the native `fetch()` to auto-handle HTTP 402 Payment Required
  - `InMemoryWallet` — micro-unit arithmetic (avoids float drift), deduct/rollback/deposit; rejects NaN/Infinity balance
  - `Wallet` / `PaymentProvider` interfaces — drop-in custom implementations
  - `MockPaymentProvider` — test-mode provider (fake tx hash, no Solana transaction); warns in production environments
  - `X402FetchMeta.blocked` — distinguishes local budget rejection from server-returned 402
  - `getTotalSpent()` — method on the returned fetch function for spend tracking across calls
  - `paymentTimeoutMs` — configurable timeout for provider.pay() with automatic wallet rollback
  - Full protocol utilities: `parseWwwAuthenticate`, `buildWwwAuthenticate`, `parseAuthorization`, `buildAuthorization`, `parseAmount`, `descriptorToChallenge`
  - `attachMeta` with Proxy fallback — safe property attachment for frozen `Response` objects (Bun/Deno/CF Workers)
  - Config array defensive copy — external mutation after construction cannot affect accepted chains/tokens
  - All construction options validated fail-fast (maxAmountPerCall, maxTotalSpend, acceptedChains, acceptedTokens, paymentTimeoutMs)
  - `buildAuthorization` fallback after on-chain payment — unsafe `provider.getAddress()` return value cannot crash post-payment
  - TypeScript types: `Wallet`, `X402FetchFunction`, `X402FetchMeta`, `X402PaymentChallenge`, `X402PaymentProof`, `X402ServiceDescriptor`
  - Zero runtime dependencies; Node.js 18+; dual ESM + CJS
  - 100 tests across 3 files (wallet, protocol, fetch)

## [0.1.17] - 2026-03-10

### Added

- **`ag402 prepaid recover`** — self-service credential recovery after gateway timeout; auto-reads `~/.ag402/pending_purchase.json` so no arguments are needed in the common case
- **`ag402 prepaid pending`** — shows current in-flight purchase waiting for recovery (gateway URL, tx_hash, package_id, save time)
- **Idempotent `/prepaid/purchase`** — same `tx_hash` always returns the identical credential (same expiry, same signature); safe to retry after any failure
- **Prepaid issuance ledger** (`prepaid_issued` SQLite table) — persists across gateway restarts; records are purged after 366 days on startup to prevent unbounded growth
- **Pending purchase file** (`~/.ag402/pending_purchase.json`) — written atomically after on-chain broadcast; integrity-protected with HMAC-SHA256; expires after 30 days; permissions `0600` on Unix

### Fixed

- **TOCTOU race condition** (`gateway.py`): two concurrent requests with the same `tx_hash` now produce one identical credential — `INSERT OR IGNORE` + `rowcount` check ensures only one winner; loser re-reads and replays the winner's credential
- **Pending file permissions** (`cli.py`): file created with mode `0600` (owner-only) on Unix before writing sensitive data
- **Pending file integrity** (`cli.py`): HMAC-SHA256 tag detects accidental or opportunistic tampering; failed check warns and ignores the file instead of silently using bad data
- **Silent failure on pending save** (`cli.py`): failure now prints a visible warning with the manual `recover` command so the user knows to act
- **Pending file expiry** (`cli.py`): records older than 30 days are ignored to prevent stale state from causing incorrect recovery
- **`_pending_hmac` Windows crash** (`cli.py`): replaced `os.uname().nodename` (unavailable on Windows) with `socket.gethostname()`; added `os.getlogin()` fallback to `USERNAME`/`USER` env vars for container environments
- **README prepaid buy syntax** (`README.md`): removed non-existent `--list` flag; used real package IDs (`p3d_100`); added `recover` command documentation
- **Test docstring** (`test_gateway_adapter.py`): corrected "409 Conflict" to "403 Forbidden" to match actual behaviour

### Changed

- Test suite: **96 passed** (gateway 26 + verifier 21 + integration 50 - 1 pre-existing Windows permission skip)
- `/prepaid/purchase` endpoint buyer_address conflict now returns `403` (not `409`) to avoid information leakage



### Added

- **Prepaid documentation** — README quick start for buyers/sellers, llms.txt CLI reference with all 5 package IDs, `AG402_PREPAID_SIGNING_KEY` env var doc
- **`examples/prepaid_demo.py`** — full end-to-end prepaid demo: browse packages, purchase in test mode, store credential, API calls via prepaid path, check remaining calls

### Fixed

- **Credential serialization safety** (`x402_middleware.py`): `to_header_value()` now wrapped in try/except — malformed stored credential rolls back deduction and falls through to on-chain x402 instead of crashing
- **CLI JSON guard** (`cli.py`): `resp.json()` calls in `prepaid buy` now guarded against non-JSON / non-dict gateway responses (packages list + credential extraction)
- **Credential file permissions** (`client.py`): `~/.ag402/` directory set to `0o700` on Unix to prevent world-readable credential files
- **Corrupt credentials backup** (`client.py`): corrupt credentials file is backed up to `.json.bak` before treating as empty — prevents silent data loss
- **Weak signing key warning** (`gateway.py`): logs warning when `--prepaid-signing-key` is shorter than 32 chars; includes `secrets.token_hex(32)` keygen hint
- **Import sort** (`test_memory_safety.py`): fix ruff I001 lint error introduced by upstream commit
- **Example API fix** (`prepaid_demo.py`): corrected 4 wrong API calls (non-existent `PrepaidCredentialStore`, `middleware.send()`, `result.get()`)

### Changed

- Test suite: **88 passed**, 0 failed



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

## [0.1.15] - 2026-03-10

### Added

- **Production-mode auto-broadcast** (`ag402 prepaid buy`) — `_cmd_prepaid_buy` now calls `PaymentProviderRegistry.get_provider().pay()` in production mode instead of prompting for manual tx_hash input
  - Test mode: auto-generates synthetic tx_hash for zero-config end-to-end testing
  - Production mode: confirms with user → broadcasts USDC on-chain → submits tx_hash to gateway automatically
  - Price cap check: gateway-supplied price validated against `cfg.single_tx_limit` before broadcast
  - Confirmation gate: irreversible payments require explicit `[Y/n]` prompt
- **`GET /prepaid/packages`** gateway endpoint — publicly accessible, returns all 5 package tiers with calls/days/price/seller_address
- **`POST /prepaid/purchase`** gateway endpoint — verifies tx_hash payment and issues HMAC-signed credential JSON
  - `tx_hash` input validated against `[A-Za-z0-9_-]{1,128}` to prevent header injection
  - Credential built but NOT stored on seller side (returned as JSON; buyer stores locally)
  - Test mode: accepts any well-formed tx_hash without on-chain check
- **`ag402 prepaid buy <gateway_url> <package_id>`** CLI command — full purchase flow
- **`ag402 prepaid status`** CLI command — displays all credentials grouped by seller
- **`ag402 prepaid purge`** CLI command — removes expired and depleted credentials
- **`PrepaidVerifier`** (`ag402_core/prepaid/verifier.py`) — stateless seller-side HMAC-SHA256 verifier
  - 5-step validation: JSON parse → seller_address match → expiry → remaining_calls > 0 → HMAC signature
  - `hmac.compare_digest()` for constant-time comparison (timing attack prevention)
- **Gateway prepaid fast-path** (`gateway.py`) — `X-Prepaid-Credential` header processed before on-chain auth
  - Valid credential → proxy immediately (1ms local verify, no chain call)
  - Invalid/expired/depleted → return 402 with standard x402 challenge so buyer falls back to on-chain
  - `prepaid_verified` / `prepaid_rejected` metrics counters; exposed in `/health` test-mode response
  - `/prepaid/purchase` endpoint now protected by `_rate_limiter` (was bypassed previously)
- **`--prepaid-signing-key` CLI arg** for `ag402-gateway` (or `AG402_PREPAID_SIGNING_KEY` env var)
- **Prepaid system integrated into ag402-core main branch** (`ag402_core/prepaid/`)
  - `models.py`: `PrepaidCredential` dataclass + 5 package tiers (Starter→Enterprise)
  - `client.py`: Buyer-side storage at `~/.ag402/prepaid_credentials.json`. `check_and_deduct()`, `rollback_call()`, `add_credential()`, `get_all_credentials()`, `purge_invalid_credentials()`, `create_credential()`
- **Middleware prepaid fast-path** (`x402_middleware.py:_try_prepaid()`)
  - Before every on-chain payment attempt, checks local prepaid credential for the seller
  - Valid credential → attach `X-Prepaid-Credential` header, skip on-chain payment (1ms vs 500ms+)
  - Seller rejects (402) or network error → rollback deduction, fall back to on-chain x402
  - `check_and_deduct` + `rollback_call` both serialized under `_payment_lock` (prevents TOCTOU)

### Fixed

- **DNS rebinding protection**: `_is_private_address()` now includes `addr.is_link_local` — blocks AWS/GCP metadata endpoint `169.254.169.254` (Python 3.10 compat)
- **`prepaid_rejected` metric**: Incremented on failed prepaid verification (was only incrementing `challenges_issued`)
- **Health endpoint**: Test-mode `/health` now returns `prepaid_rejected` counter alongside `prepaid_verified`
- **PrepaidVerifier security**: `signature=null` / non-string → returns `invalid_signature` instead of crash
- **Atomic credential write**: `_save()` uses `tempfile.mkstemp()` + `os.replace()` — prevents file corruption on crash
- **Rollback cap**: `min(remaining+1, original_calls)` prevents adversarial seller from inflating credential via repeated reject-loop
- **Network error rollback**: Both rollback paths execute under `_payment_lock` to prevent concurrent writes

### Changed

- Test suite: **88 passed**, 0 failed (gateway 17 + verifier 21 + integration 50)

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
