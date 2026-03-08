<p align="center">
  <h1 align="center">Ag402</h1>
  <p align="center">
    <strong>The secure payment layer for AI agents.</strong>
  </p>
  <p align="center">
    <a href="https://github.com/AetherCore-Dev/ag402/actions/workflows/ci.yml"><img src="https://github.com/AetherCore-Dev/ag402/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
    <img src="https://img.shields.io/badge/tests-588%2B_passing-brightgreen" alt="Tests" />
    <img src="https://img.shields.io/badge/coverage-90%25-brightgreen" alt="Coverage" />
    <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python" />
    <a href="https://github.com/AetherCore-Dev/ag402/blob/main/LICENSE"><img src="https://img.shields.io/github/license/AetherCore-Dev/ag402" alt="License" /></a>
  </p>
</p>

---

## What Is Ag402?

Ag402 is a **non-custodial, zero-config payment engine** that lets AI agents automatically pay for API calls using the HTTP 402 protocol and Solana USDC.

```
AI Agent → calls API → HTTP 402 → Ag402 auto-pays on-chain → retries → 200 OK
```

---

## Table of Contents

- [Feature Matrix](#feature-matrix)
- [Packages](#packages)
- [Quick Start](#quick-start)
- [Integration Guide (Buyer)](#integration-guide-buyer-side)
- [Integration Guide (Seller)](#integration-guide-seller-side)
- [CLI Reference](#cli-reference)
- [Configuration](#configuration)
- [Security Architecture](#security-architecture)
- [Protocol Specification](#protocol-specification)
- [Documentation](#documentation)

---

## Feature Matrix

> Quick reference for integration developers. Each feature links to its source module.

### Core Payment Engine (`ag402-core`)

| Category | Feature | Description | Module |
|----------|---------|-------------|--------|
| **Monkey-Patch SDK** | `enable()` / `disable()` | Zero-code-change auto-pay for all `httpx` + `requests` calls | `monkey.py` |
| | `enabled()` context manager | Scoped auto-pay — active only within `with` block | `monkey.py` |
| | `is_enabled()` | Check if monkey-patch is currently active | `monkey.py` |
| **Wallet** | SQLite ledger | Persistent balance, deposits, deductions, history | `wallet/agent_wallet.py` |
| | Payment order state machine | `PENDING → PAID → CONFIRMED / FAILED / ROLLED_BACK` | `wallet/payment_order.py` |
| | Test faucet | `deposit(100.0)` for test mode — no real funds | `wallet/faucet.py` |
| | Transaction history | Per-address breakdown, stats, export (JSON/CSV) | `wallet/agent_wallet.py` |
| **Payment Providers** | `SolanaAdapter` | Real Solana USDC transfers (devnet + mainnet) | `payment/solana_adapter.py` |
| | `MockSolanaAdapter` | Deterministic mock for testing (strict verify) | `payment/solana_adapter.py` |
| | Provider registry | Auto-select provider by `X402_MODE` (test/production) | `payment/registry.py` |
| | RPC retry + failover | Exponential backoff → backup RPC (`SOLANA_RPC_BACKUP_URL`) | `payment/solana_adapter.py` |
| | Priority fees | `computeBudget` + `SetComputeUnitPrice` for congestion | `payment/solana_adapter.py` |
| | ATA error detection | Friendly error when Associated Token Account missing | `payment/solana_adapter.py` |
| | Configurable finality | `confirmed` (fast) or `finalized` (safe) commitment | `payment/solana_adapter.py` |
| **Middleware** | `X402PaymentMiddleware` | Core 402 interception + auto-pay + retry logic | `middleware/x402_middleware.py` |
| | `BudgetGuard` | 6-layer budget enforcement (see Security section) | `middleware/budget_guard.py` |
| | Circuit breaker | Instance-level, configurable threshold + cooldown | `middleware/budget_guard.py` |
| **Security** | Wallet encryption | PBKDF2-HMAC-SHA256 (480K iter) + Fernet/AES | `security/wallet_encryption.py` |
| | Key guard | Redacts private key patterns from all log output | `security/key_guard.py` |
| | Rate limiter | IP-based sliding window, bounded key set (`max_keys`) | `security/rate_limiter.py` |
| | Replay guard | In-memory + persistent (SQLite) nonce/tx_hash dedup | `security/replay_guard.py` |
| | Challenge validator | x402 header parsing, HMAC verification, localhost detection | `security/challenge_validator.py` |
| | SSRF protection | Blocks private IPs, non-HTTPS, reserved ranges | `config.py` (`validate_url_safety`) |
| **Gateway (Server)** | Payment gate | x402 verification + proxy to backend | `gateway/auth.py` |
| | Header whitelist | Strips dangerous headers (Cookie, X-Forwarded-For, etc.) | `gateway/auth.py` |
| | Health endpoint | `/health` — minimal in production, detailed in test | Gateway |
| **Proxy** | Forward proxy | HTTP proxy with x402 interception, SSRF-safe | `proxy/forward_proxy.py` |
| **Runners** | Agent runner | `ag402 run -- python script.py` with auto-injection | `runners/base.py` |
| | Secure tmpdir | `sitecustomize.py` injection, `0o700` permissions | `runners/base.py` |
| **CLI** | 20+ commands | Setup, wallet, payments, diagnostics, export | `cli.py` |
| | Interactive wizard | `ag402 setup` / `ag402 upgrade` for humans | `setup_wizard.py` |
| | Non-interactive init | `ag402 init` for AI agents (no prompts) | `cli.py` |
| **Config** | Auto `.env` loading | `~/.ag402/.env` with priority: CLI > env > file | `config.py` |
| | Mode system | `test` (virtual funds) / `production` (real Solana) | `config.py` |
| | Env management | `ag402 env show/set` for configuration | `cli.py` |

### Protocol Layer (`open402`)

| Feature | Description | Module |
|---------|-------------|--------|
| x402 header parsing | Parse `WWW-Authenticate: x402 ...` response headers | `headers.py` |
| x402 header building | Build `Authorization: x402 <tx_hash>` request headers | `headers.py` |
| Version negotiation | Client/server version compatibility check | `negotiation.py` |
| Protocol spec | Constants, chain/token definitions, amount validation | `spec.py` |
| Zero dependencies | No external dependencies — safe to embed anywhere | `pyproject.toml` |

### MCP Gateway Adapter (`ag402-mcp`)

| Feature | Description | Module |
|---------|-------------|--------|
| HTTP payment gateway | Starlette-based 402 gateway for API providers | `gateway.py` |
| Persistent tx_hash dedup | SQLite-backed replay guard for production | `gateway.py` |
| Configurable pricing | `--price`, `--address` CLI args | `gateway.py` |
| Auto demo backend | Starts built-in demo API if no `--target` given | `gateway.py` |
| Mode-aware binding | `127.0.0.1` in test, `0.0.0.0` in production | `gateway.py` |
| Health monitoring | `/health` with mode-appropriate detail level | `gateway.py` |

### MCP Client Adapter (`ag402-client-mcp`)

| Feature | Description | Module |
|---------|-------------|--------|
| MCP server (stdio + SSE) | Model Context Protocol server for AI tools | `server.py` |
| `fetch_with_autopay` tool | HTTP request with automatic x402 payment | `tools.py` |
| `wallet_status` tool | Balance + budget usage query | `tools.py` |
| `transaction_history` tool | Recent payment history | `tools.py` |
| One-command install | `ag402 install cursor/claude-code/openclaw` | `config_examples.py` |
| Config generation | `ag402 mcp-config` for manual setup | `config_examples.py` |

### OpenClaw Adapter (`ag402-openclaw`)

| Feature | Description | Module |
|---------|-------------|--------|
| OpenClaw bridge | Full OpenClaw skill integration | `bridge.py` |
| Prepaid system | Bulk purchase packages (3/7/30/365/730 days) | `prepaid_client.py` |
| HMAC-SHA256 credentials | Prepaid authentication with signature verification | `prepaid_server.py` |
| Auto-fallback | Falls back to standard 402 when prepaid exhausted | `prepaid_client.py` |

---

## Packages

Four composable packages — install only what you need:

| Package | PyPI | Role | Dependencies |
|---------|------|------|-------------|
| `open402` | [![PyPI](https://img.shields.io/pypi/v/open402)](https://pypi.org/project/open402/) | Protocol standard | **Zero** |
| `ag402-core` | [![PyPI](https://img.shields.io/pypi/v/ag402-core)](https://pypi.org/project/ag402-core/) | Payment engine + CLI + wallet | `httpx`, `aiosqlite`, `cryptography`, `solders`, `solana` |
| `ag402-mcp` | [![PyPI](https://img.shields.io/pypi/v/ag402-mcp)](https://pypi.org/project/ag402-mcp/) | HTTP gateway (seller side) | `ag402-core`, `starlette`, `uvicorn` |
| `ag402-client-mcp` | [![PyPI](https://img.shields.io/pypi/v/ag402-client-mcp)](https://pypi.org/project/ag402-client-mcp/) | MCP client (buyer side) | `ag402-core`, `mcp` |

---

## Quick Start

### For AI Agents (non-interactive)

```bash
pip install ag402-core
ag402 init          # Creates test wallet + $100 USDC, zero prompts
ag402 demo          # Verify the full auto-pay flow
```

### For Humans (interactive wizard)

```bash
pip install ag402-core
ag402 setup         # Interactive wizard — password, role, network
ag402 demo          # Watch the full auto-pay flow
```

### For AI Tool Users (Claude Code / Cursor / OpenClaw)

```bash
pip install ag402-core ag402-client-mcp
ag402 install cursor        # or: claude-code / openclaw
# Restart your AI tool — Ag402 MCP tools appear automatically
```

---

## Integration Guide (Buyer Side)

### Method 1: Monkey-Patch (recommended — zero code changes)

```python
import ag402_core
ag402_core.enable()   # All HTTP 402 responses are auto-handled

# Your existing agent code — completely unchanged
response = httpx.get("https://paid-api.example.com/data")
```

Works with: **LangChain**, **AutoGen**, **CrewAI**, **any httpx/requests-based agent**.

### Method 2: Context Manager (scoped control)

```python
with ag402_core.enabled():
    result = requests.get("https://paid-api.example.com/search?q=AI")
# Outside the block, requests behave normally
```

### Method 3: CLI Runner (any Python script)

```bash
ag402 run -- python my_agent.py
```

### Method 4: MCP Client (for AI tools)

```bash
ag402 install cursor              # Auto-writes .cursor/mcp.json
# or: ag402 install claude-code   # Auto-writes .claude/settings.local.json
# or: ag402 install openclaw      # Auto-configures via mcporter
```

MCP Tools exposed:
| Tool | Description |
|------|-------------|
| `fetch_with_autopay(url, method, headers, body, max_amount)` | HTTP request with auto x402 payment |
| `wallet_status()` | Check balance and budget usage |
| `transaction_history(limit)` | View recent payment history |

### Method 5: Direct Python API

```python
from ag402_core.wallet.agent_wallet import AgentWallet
from ag402_core.payment.solana_adapter import SolanaAdapter  # or MockSolanaAdapter
from ag402_core.middleware.x402_middleware import X402PaymentMiddleware
from ag402_core.config import X402Config, RunMode

config = X402Config(mode=RunMode.TEST)
wallet = AgentWallet(db_path="x402_wallet.db")
await wallet.init_db()
await wallet.deposit(10.0, note="test funds")

provider = MockSolanaAdapter()
middleware = X402PaymentMiddleware(wallet, provider, config)
result = await middleware.handle_request("GET", "https://api.example.com/data")
```

### Platform Compatibility

| Platform | Method | Status |
|----------|--------|--------|
| OpenClaw | MCP Skill | ✅ Full support |
| Claude Code | MCP Client | ✅ Full support |
| Cursor | MCP Client | ✅ Full support |
| Claude Desktop | MCP Client | ✅ Full support |
| LangChain | Monkey-patch | ✅ Works automatically |
| AutoGen | Monkey-patch | ✅ Works automatically |
| CrewAI | Monkey-patch | ✅ Works automatically |
| Any `httpx`/`requests` agent | Monkey-patch / Runner | ✅ Works automatically |

---

## Integration Guide (Seller Side)

### Quick Setup

```bash
pip install ag402-core ag402-mcp
ag402 serve --target http://localhost:8000 --price 0.05 --address <YourSolanaAddress>
```

Requests without valid payment → **402**. Requests with valid x402 proof → **proxied to your API**.

### Seller Architecture (No Private Key Required)

Sellers only need a **public receiving address**. Ag402 verifies payments on-chain — no signing, no private key access.

### Deployment Options

| Option | Command |
|--------|---------|
| Local | `ag402 serve &` |
| Docker | See `docker-compose.yml` |
| Remote SSH | `ssh user@host "nohup ag402 serve ..."` |

### Verification Checklist

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:4020/  # → 402
ag402 pay http://127.0.0.1:4020/                                 # → 200 + JSON
curl -s http://127.0.0.1:4020/health                             # → {"status":"healthy"}
```

---

## CLI Reference

| Command | Description | Interactive? |
|---------|-------------|:------------:|
| `ag402 setup` | Interactive setup wizard | Yes |
| `ag402 init` | Non-interactive wallet init + test funds | No |
| `ag402 run <target>` | Launch agent with auto x402 payment | No |
| `ag402 mcp` | Start MCP payment server (stdio/SSE) | No |
| `ag402 install <tool>` | One-command MCP setup (claude-code, cursor, openclaw) | No |
| `ag402 mcp-config [tool]` | Generate MCP config JSON | No |
| `ag402 serve` | Start payment gateway (seller mode) | No |
| `ag402 demo` | Full E2E payment demo | No |
| `ag402 pay <url>` | Single request with x402 auto-payment | No |
| `ag402 status` | Dashboard: balance, budget, security, txns | No |
| `ag402 balance` | Quick balance + budget progress bars | No |
| `ag402 history` | Transaction history with stats | No |
| `ag402 tx <id>` | Single transaction detail (prefix match) | No |
| `ag402 config` | Safety limits and configuration | No |
| `ag402 env show` | Show current config and sources | No |
| `ag402 env set <k> <v>` | Set a config value | No |
| `ag402 info` | Protocol version, Python version, JSON schema | No |
| `ag402 doctor` | Environment health check | No |
| `ag402 upgrade` | Migrate test → production | Yes |
| `ag402 export` | Export history to JSON/CSV | No |
| `ag402 help` | Show categorized help | No |

---

## Configuration

### Environment Variables

All configurable via `~/.ag402/.env` or environment variables.

**Priority** (highest first): CLI arguments → Environment variables → `~/.ag402/.env` file

| Variable | Default | Description |
|----------|---------|-------------|
| `X402_MODE` | `test` | `test` = virtual funds, `production` = real Solana |
| `SOLANA_PRIVATE_KEY` | — | Base58 encoded Solana private key (buyer only) |
| `SOLANA_RPC_URL` | devnet | Solana RPC endpoint |
| `SOLANA_RPC_BACKUP_URL` | — | Backup RPC for automatic failover |
| `X402_SINGLE_TX_LIMIT` | `5.0` | Max per-transaction amount (USD) |
| `X402_DAILY_LIMIT` | `10.0` | Daily spend cap (USD, hard ceiling: $1000) |
| `X402_PER_MINUTE_LIMIT` | `2.0` | Per-minute dollar cap |
| `X402_PER_MINUTE_COUNT` | `5` | Per-minute transaction count |
| `X402_CIRCUIT_BREAKER_THRESHOLD` | `3` | Consecutive failures before circuit opens |
| `X402_CIRCUIT_BREAKER_COOLDOWN` | `60` | Cooldown seconds after circuit opens |
| `X402_WALLET_DB` | `~/.ag402/wallet.db` | SQLite database path |
| `X402_RATE_LIMIT` | `60` | Requests per minute (gateway) |
| `X402_FALLBACK_API_KEY` | — | Bearer token for non-x402 APIs (dual-mode) |
| `AG402_UNLOCK_PASSWORD` | — | Wallet unlock password for Docker/CI |

### Seller-Only Variables

| Variable | Description |
|----------|-------------|
| `AG402_TARGET_API` | Backend API URL to proxy |
| `AG402_API_PRICE` | Price per API call (USDC) |
| `AG402_RECEIVE_ADDRESS` | Solana public address for receiving payments |

---

## Security Architecture

### 6-Layer Budget Protection

| Layer | Protection | Default |
|-------|------------|---------|
| 1. Single-TX cap | Max amount per transaction | $5.00 |
| 2. Per-minute cap | Dollar + count rate limiting | $2.00 / 5 txns |
| 3. Daily cap | Daily spend ceiling | $10.00 |
| 4. Circuit breaker | Auto-stop on consecutive failures | 3 failures → 60s cooldown |
| 5. Auto-rollback | Failed payment reversal | Automatic |
| 6. Key filter | Private keys redacted from all logs | Always on |

### Security Features

| Feature | Description |
|---------|-------------|
| Non-custodial | Private keys stay on your machine — no central server |
| Wallet encryption | PBKDF2-HMAC-SHA256 (480K iterations) + Fernet/AES |
| Zero telemetry | No usage tracking, no IP logging, no analytics |
| Replay protection | Timestamp + nonce validation, persistent tx_hash dedup |
| Sender verification | On-chain balance validation prevents stolen tx_hash attacks |
| SSRF protection | Blocks private IPs, non-HTTPS, reserved ranges |
| Header whitelist | Strips Cookie, X-Forwarded-For, Authorization from proxied requests |
| Rate limiting | IP-based sliding window with bounded key set |
| Localhost detection | Complete loopback detection (IPv4, IPv6, `0.0.0.0`) |
| Mode-aware binding | Test binds to `127.0.0.1`, production to `0.0.0.0` |
| Private key isolation | Key never stored in `os.environ`, getter-only access |

### Automated CI Checks (Every PR)

- CodeQL — Automated code analysis
- Trivy — Dependency vulnerability scanning
- pip-audit — Python dependency audit
- Semgrep — Static application security testing
- 588+ unit tests with 90%+ coverage
- OpenSSF Scorecard — Monthly assessment

---

## Protocol Specification

HTTP 402 response from server:
```
HTTP/1.1 402 Payment Required
WWW-Authenticate: x402 chain="solana" token="USDC" amount="0.05" address="..."
```

Client retries with payment proof:
```
GET /data HTTP/1.1
Authorization: x402 <solana_tx_hash>
```

Compatible with the **Coinbase x402** standard. See [x402 Protocol Spec](docs/x402_protocol_spec.md).

---

## Project Structure

```
protocol/open402/                     ← x402 spec, headers, version negotiation (zero deps)
core/ag402_core/
├── config.py                         ← Configuration, auto-loads ~/.ag402/.env
├── cli.py                            ← CLI (20+ commands, colorized output)
├── monkey.py                         ← enable()/disable()/enabled() monkey-patch SDK
├── wallet/                           ← SQLite ledger, budget, payment order state machine
├── payment/                          ← Solana adapter, mock, registry, retry + failover
├── middleware/                       ← x402 interception, budget guard, circuit breaker
├── gateway/                          ← Server-side payment gate + auth
├── security/                         ← Key guard, encryption, rate limiter, replay guard
├── proxy/                            ← HTTP forward proxy (SSRF-safe)
├── runners/                          ← Agent runners (secure tmpdir injection)
├── setup_wizard.py                   ← Interactive setup wizard
├── env_manager.py                    ← Zero-dependency .env parser
├── friendly_errors.py                ← Human-readable CLI error messages
└── terminal.py                       ← ANSI color/formatting utilities
adapters/
├── mcp/ag402_mcp/                    ← HTTP gateway adapter (ag402-gateway CLI)
├── client_mcp/ag402_client_mcp/      ← MCP client adapter (stdio/SSE, 3 tools)
└── openclaw/                         ← OpenClaw bridge + skill + prepaid system
examples/                             ← Demo scripts
docs/                                 ← Guides (Claude Code, Cursor, OpenClaw, localnet)
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [llms.txt](llms.txt) | AI-readable CLI reference (for Claude Code, Cursor, etc.) |
| [Architecture](docs/architecture_state.md) | System architecture and state machine diagrams |
| [x402 Protocol Spec](docs/x402_protocol_spec.md) | Full protocol specification |
| [Claude Code Guide](docs/guide-claude-code.md) | Integration guide for Claude Code |
| [Cursor Guide](docs/guide-cursor.md) | Integration guide for Cursor |
| [OpenClaw Guide](docs/guide-openclaw.md) | Integration guide for OpenClaw |
| [Localnet Guide](docs/guide-localnet.md) | Local Solana validator setup |
| [OpenClaw Skill](adapters/openclaw/ag402-skill/) | OpenClaw skill definition |
| [CHANGELOG](CHANGELOG.md) | Version history and release notes |
| [SECURITY](SECURITY.md) | Security policy and audit history |
| [CONTRIBUTING](CONTRIBUTING.md) | Contribution guide |

---

## License

[MIT License](LICENSE)
