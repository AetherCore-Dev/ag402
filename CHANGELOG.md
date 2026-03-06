# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.11] - 2026-03-06

### Added

- **ag402 OpenClaw Adapter**: Native OpenClaw Skill and bridge adapter
  - Single-skill hybrid architecture (Skill + MCP tools)
  - Auto-install scripts for easy setup
  - Commands: setup, wallet status/deposit/history, pay, gateway start/stop, doctor
  - OpenClaw bridge for mcporter integration

### Security

- **SSRF Protection**: Block localhost, private IPs, dangerous ports
- **Race Condition Fix**: File locking with fcntl for atomic balance operations
- **API Key Authentication**: AG402_API_KEY environment variable support
- **Header Injection Prevention**: Block dangerous headers (authorization, cookie, x-api-key)
- **HTTP Method Whitelist**: Only allow safe methods (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
- **Payment Confirmation**: $10 threshold for user confirmation
- **Budget Limits**: $50 single / $20 min / $100 daily

### Fixed

- **Payment confirmation not called**: confirm_payment() now integrated in proxy_request()
- **Daily limit reset**: BudgetState properly resets on new day
- **Module imports**: Fixed __init__.py exports


## [0.1.10] - 2026-03-04

### Fixed

- **Production mode broken — `effective_rpc_url` never used**: `PaymentProviderRegistry._build_solana()` and all CLI commands used `config.solana_rpc_url` (raw env var) instead of `config.effective_rpc_url` (network-aware resolver). Localnet/mainnet routing was silently ignored
- **`ag402 balance` / `ag402 status` only showed local SQLite ledger**: Now queries on-chain USDC balance via `SolanaAdapter.check_balance()` in production mode, showing both on-chain and local ledger amounts
- **`ag402 pay` blocked by empty local ledger in production**: Pre-check now uses on-chain balance in production mode. Payment flow changed to pay-on-chain-first-then-record-locally for correct ordering
- **`ag402 setup` / `ag402 upgrade` did not persist `X402_NETWORK` or `USDC_MINT_ADDRESS`**: Mainnet configuration was incomplete, causing silent fallback to devnet defaults
- **Settlement summary mixed on-chain and ledger balances**: Production mode now re-queries on-chain balance for accurate before/after display

### Security

- **Private key no longer stored in plaintext `.env`**: Keys are now stored exclusively in encrypted `~/.ag402/wallet.key` (PBKDF2-480K + AES). `load_config()` auto-decrypts at startup using `AG402_UNLOCK_PASSWORD` env var or interactive prompt
- **Private key display masked everywhere**: `ag402 setup` summary, `ag402 env set`, and `ag402 env show` all mask values containing "key", "password", or "secret"
- **`install_key_guard()` activated in CLI**: Root logger filter now installed at `main()` entry point, redacting private keys from any log output
- **`~/.ag402/.gitignore` auto-created**: Contains `*` to prevent accidental git commit of key files
- **RPC error messages truncated**: Exception strings capped at 120 chars to prevent leaking RPC API keys
- **`ag402 upgrade` requires encryption**: Production mode upgrade now fails if `cryptography` package is not installed, preventing key-less production state
- **Example docs updated**: `ag402 setup --show-examples` no longer shows plaintext `SOLANA_PRIVATE_KEY=` in `.env` examples

## [0.1.9] - 2026-02-27

### Fixed

- **Receipt-reuse money-loss path (P1-CRITICAL)**: Previously, if a buyer paid on-chain but the upstream API failed (502, timeout), the gateway rejected subsequent retries with the same tx_hash as "replay". The buyer lost money with no way to recover. Now uses a 3-state grace window (`NEW` / `WITHIN_GRACE` / `EXPIRED`) — buyers can retry within 5 minutes, and successful upstream responses are cached for idempotent replay
- **TOCTOU race in gateway tx_hash recording**: `check_tx_status()` (SELECT) and `check_and_record_tx()` (INSERT) were not atomic — two concurrent requests could both pass the check. Fixed by verifying the `check_and_record_tx()` return value (`INSERT OR IGNORE` atomicity) and rechecking status on conflict
- **USDC mint address auto-selection for mainnet**: `USDC_MINT_ADDRESS` previously defaulted to devnet mint regardless of `X402_NETWORK`. Now auto-selects based on network mode: devnet → `4zMMC9...`, mainnet → `EPjFWdd5...`. Explicit env var still overrides. Prevents accidental use of devnet mint on mainnet (fund loss risk)
- **Hardcoded private key in devnet_buyer_test.py**: Removed hardcoded Solana private key, replaced with `_require_env("SOLANA_PRIVATE_KEY")` that exits with a clear error message if not set

### Added

- **DeliveryWorker**: Background asyncio worker that retries stuck `DELIVERING` orders with exponential backoff (30s → 60s → 120s → 240s → 480s, max 5 retries). After exhaustion, orders transition to `FAILED` terminal state for manual review
- **`FAILED` order state**: New terminal state in the payment order state machine. Orders that exhaust delivery retries are marked `FAILED` instead of staying stuck in `DELIVERING` forever
- **Response caching for grace-window retries**: Gateway caches successful upstream responses (status, headers, body) in SQLite. Grace-window retries serve the cached response instead of re-proxying, ensuring idempotent behavior
- **`PersistentReplayGuard` enhancements**: `check_tx_status()` for 3-state lookup, `mark_delivered()` to close the grace window, `cache_response()` / `get_cached_response()` for response caching, `response_cache` table created in `init_db()`
- **`ag402-claude` adapter** (`adapters/claude_code/`): Claude Code hook-based integration for automatic x402 payment. Supports pre/post hook phases, detects 402 responses in tool output, auto-pays and returns the paid response. CLI entry point: `ag402-claude-hook`
- **`ag402-openclaw` adapter** (`adapters/openclaw/`): OpenClaw bridge adapter via mcporter. Supports stdio (for mcporter) and HTTP proxy modes. Exposes `/proxy` endpoint for OpenClaw agents to make paid API calls. CLI entry point: `ag402-openclaw`
- **`.env.example`**: Comprehensive template documenting all environment variables with descriptions, organized by category (mode, network, wallet, budget, gateway, security, E2E tests)
- **27 receipt-reuse tests**: Full coverage of grace window logic, FAILED state machine, DeliveryWorker retry/exhaustion/backoff, middleware lifecycle, gateway integration, and end-to-end scenarios
- Total test count: **602+ tests** (30 protocol + 528 core + 5 MCP + 39 client MCP), all passing

## [0.1.8] - 2026-02-27

### Added

- **Google Colab notebook** (`examples/ag402_quickstart.ipynb`): One-click interactive demo — runs the full x402 payment flow in-browser with zero local setup. 18 cells covering 402 rejection, auto-pay, wallet inspection, and a "try it yourself" interactive cell
- **"Open in Colab" badge** in README header and Quick Start section
- **Real-World Cases section** in README: references [token-bugcheck](https://github.com/AetherCore-Dev/token-bugcheck) production case study with seller/buyer code snippet, plus local weather demo

## [0.1.7] - 2026-02-26

### Fixed

- **`ag402 serve` Docker binding (BUG-1)**: Changed default host from `127.0.0.1` to `0.0.0.0` and added `--host` CLI argument — Docker/Kubernetes deployments now work out of the box without workarounds
- **aiosqlite event loop crash (BUG-2)**: Replaced `uvicorn.run()` with `asyncio.run()` + `uvicorn.Server` in `_cmd_serve()` — all async initialization and serving now run in a single event loop, eliminating `RuntimeError: Event loop is closed` crashes with uvloop/aiosqlite
- **PersistentReplayGuard permission check (BUG-3)**: Added `os.access(db_dir, os.W_OK)` pre-flight check in `init_db()` — raises a clear `PermissionError` with uid info instead of the opaque `sqlite3.OperationalError`

### Added

- `--host` argument for `ag402 serve` command (default: `0.0.0.0`) — consistent with `ag402-gateway` CLI
- **`ag402 doctor` gateway checks**: Now verifies gateway port availability, `~/.ag402` directory writability, and backend URL reachability
- **Configuration loading order** documentation in README: CLI args > env vars > `~/.ag402/.env`
- 13 new tests in `test_issue_fixes.py`: `--host` argument parsing (4), event loop pattern verification (1), permission check (4), doctor gateway checks (4)
- Total test count: **575+ tests** (30 protocol + 501 core + 5 MCP + 39 client MCP), all passing

## [0.1.6] - 2026-02-24

### Added

- **Transaction idempotency (F3)**: `request_id` embedded in Solana memo field (`Ag402-v1|<request_id>`) for payment deduplication — gateway-side `PersistentReplayGuard` rejects duplicate `tx_hash` proofs
- **Priority fees (F4)**: `computeBudget` + `SetComputeUnitPrice` instructions added to Solana transactions — configurable via `X402_PRIORITY_FEE` and `X402_COMPUTE_UNIT_LIMIT` env vars for reliable confirmation during network congestion
- **RPC failover for balance/verify (F5)**: `MultiEndpointClient` failover now covers `check_balance()` and `verify_payment()` in addition to `pay()` — full RPC resilience across all Solana operations
- **Mainnet smoke test (F2)**: `test_mainnet_smoke.py` — self-transfer verification with priority fees, on-chain verification, manual-only execution (`-m mainnet`)
- **Concurrent payment tests (F1)**: `test_concurrent_payments.py` — 9 tests covering multi-agent nonce conflicts, wallet consistency under concurrent deposits/deductions, budget guard race conditions, replay guard deduplication
- `request_id` field added to `X402PaymentProof`, `PaymentResult`, and `VerifyResult` — full end-to-end idempotency tracking
- `PaymentVerifier` now accepts optional `PersistentReplayGuard` for automatic tx_hash deduplication
- Total test count: **562+ tests** (30 protocol + 488 core + 5 MCP + 39 client MCP), all passing

### Fixed

- Mock provider `pay()` signature updated to accept `request_id` keyword argument — prevents `TypeError` in middleware tests

## [0.1.5] - 2026-02-24

### Added

- **Release process skill**: `.claude/skills/releasing-to-pypi/SKILL.md` — checklist-driven release workflow preventing tag/version/lint mismatches that cause PyPI publish failures

### Fixed

- **Security test compatibility**: Updated `test_monkey_enable_disable_idempotent` and `test_monkey_concurrent_enable_disable` in `test_security_tdd_p1.py` to work with the reference-counted `enable()`/`disable()` introduced in v0.1.4

## [0.1.4] - 2026-02-24

### Fixed

- **Monkey-patch infinite recursion**: `_patched_send` now uses a `contextvars` re-entrancy guard to prevent middleware's own httpx requests from being re-intercepted — previously caused infinite recursion and repeated payments when the server returned 402
- **`enabled()` nesting bug**: Replaced `_enabled` boolean with `_enable_depth` reference counter — nested `enabled()` context managers no longer break the outer scope on inner exit
- **Middleware init race condition**: `_get_initialized_middleware()` now uses `asyncio.Lock` with double-checked locking to prevent concurrent callers from both running `init_db()` and double-depositing test funds

### Added

- 7 new tests: re-entrancy guard, nested `enabled()` (5 cases), concurrent init race
- Total test count: 500+ tests, all passing

## [0.1.3] - 2026-02-24

### Fixed

- **SQL LIKE wildcard injection**: Added `_escape_like()` to `AgentWallet` — escapes `%`, `_`, `\` in user-supplied prefixes before passing to SQL `LIKE` clause with `ESCAPE '\'`
- **Negative/zero amount bypass**: `deposit()` and `deduct()` now reject `amount <= 0` with `ValueError("Amount must be positive")` — prevents balance manipulation via negative deposits or deductions

### Added

- **109 security TDD tests** across three priority tiers:
  - **P0 (30 tests)**: SQL LIKE injection, negative/zero amount validation, encryption boundary conditions, circuit-breaker TOCTOU race conditions
  - **P1 (56 tests)**: Clock rollback attacks, replay guard edge cases, path traversal (`../` escape), protocol fuzzing (null bytes, Unicode, oversized headers), monkey-patch concurrency, SSRF IPv6-mapped bypass
  - **P2 (23 tests)**: Persistent replay guard, resource exhaustion, fault injection (corrupted DB), gateway 402 flow / rate limiting / header whitelist
- **Three-layer timeout protection**: Process-level (`subprocess.run(timeout=60)`), function-level (`pytest.mark.timeout(15)`), thread-level (`Barrier(timeout=5)`, `thread.join(timeout=10)`)
- Total test count: **500+ tests** (391 existing + 109 new security tests), all passing

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

- ~~**Concurrent payments**: No tests for multiple agents paying simultaneously with same keypair (nonce conflicts)~~ → Fixed in v0.1.6 (F1)
- ~~**Mainnet smoke test**: No real mainnet transaction tests yet — devnet/localnet only~~ → Fixed in v0.1.6 (F2)
- ~~**Transaction idempotency**: No idempotency key / dedup mechanism — agent retry may cause double-spend~~ → Fixed in v0.1.6 (F3)
- ~~**Priority fees**: No `computeBudget` / priority fee support — mainnet congestion may cause pending transactions~~ → Fixed in v0.1.6 (F4)
- ~~**RPC failover**: `MultiEndpointClient` exists but not yet integrated into production `SolanaAdapter.pay()` flow~~ → Fixed in v0.1.6 (F5)
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
