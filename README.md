<p align="center">
  <h1 align="center">Ag402</h1>
  <p align="center">
    <strong>Give AI Agents the ability to autonomously pay for API calls</strong><br/>
    HTTP 402 standard · Solana USDC on-chain settlement · Two lines of code
  </p>
  <p align="center">
    <a href="https://github.com/AetherCore-Dev/ag402/actions/workflows/ci.yml"><img src="https://github.com/AetherCore-Dev/ag402/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
    <img src="https://img.shields.io/badge/tests-500%2B_passing-brightgreen" alt="Tests" />
    <img src="https://img.shields.io/badge/coverage-90%25-brightgreen" alt="Coverage" />
    <img src="https://img.shields.io/pypi/v/ag402-core" alt="PyPI" />
    <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python" />
    <a href="https://github.com/AetherCore-Dev/ag402/blob/main/LICENSE"><img src="https://img.shields.io/github/license/AetherCore-Dev/ag402" alt="License" /></a>
  </p>
</p>

---

## In One Sentence

Your AI Agent calls an API. The server returns **HTTP 402 "Payment Required"**. Ag402 **automatically completes the on-chain payment** in the middle layer, then hands the normal 200 response back to your Agent. The entire process requires **zero changes to your existing code**.

```
Agent sends request ──▶ API returns 402 ──▶ Ag402 auto-pays ──▶ Retries request ──▶ 200 ✓
                                              ↑ Completely transparent to your code
```

---

## ⚡ 30-Second Quick Start

```bash
pip install ag402-core
ag402 setup        # Interactive wizard — set a wallet password, get 100 USDC test funds
ag402 demo         # Watch the full auto-pay flow in action
```

That's it. No Solana wallet needed. No config files to edit. No environment variables to set.

### 🔍 Hands-on Protocol Walkthrough (Recommended)

Want to see every step of the x402 protocol? Open two terminals:

```bash
# Terminal 1: Start the seller gateway (auto-launches built-in Demo API)
ag402 serve

# Terminal 2: Buyer view — watch the 6-step x402 negotiation
ag402 pay http://127.0.0.1:4020/
```

`ag402 pay` shows each step: Send request → Receive 402 → Parse payment challenge → On-chain transfer → Retry with proof → Get 200 data.

### 🧪 Local Solana Validator (No Network Required)

Run real on-chain transactions locally — zero network dependency, 100% stability:

```bash
# Install Solana CLI (one-time)
sh -c "$(curl -sSfL https://release.anza.xyz/stable/install)"

# Terminal 1: Start local validator
solana-test-validator --reset

# Terminal 2: Run on-chain demo
ag402 demo --localnet
```

See the [Local Validator Guide](docs/guide-localnet.md) for full details.

### 🎯 Demo Modes

| Mode | Command | Description |
|------|---------|-------------|
| Mock (default) | `ag402 demo` | Simulated payments, zero risk |
| Localnet | `ag402 demo --localnet` | Real on-chain via local validator |
| Devnet | `ag402 demo --devnet` | Real on-chain via Solana devnet |

---

## 🔌 Minimal Integration — Two Lines, Zero Intrusion

No need to refactor your Agent code. Works with any Python framework using `httpx` or `requests` (LangChain, AutoGen, CrewAI, etc.):

```python
import ag402_core
ag402_core.enable()   # One line — all HTTP 402 responses are auto-handled

# Your existing code stays exactly the same ↓
response = httpx.get("https://paid-api.example.com/data")
# If the server returns 402, Ag402 auto-pays and retries
# You always get the final 200 response
```

**Need finer control?** Use the context manager:

```python
with ag402_core.enabled():
    # Only requests inside this block are auto-paid
    result = requests.get("https://paid-api.example.com/search?q=AI")

# Requests outside the block are unaffected
requests.get("https://free-api.example.com/status")
```

**Command-line mode?** One command:

```bash
ag402 run -- python my_agent.py    # Any Python agent
```

**Using Claude Code, Cursor, or OpenClaw?** One command:

```bash
pip install ag402-client-mcp
ag402 install cursor            # Auto-writes .cursor/mcp.json
# or: ag402 install claude-code   # Auto-writes .claude/settings.local.json
# or: ag402 install openclaw      # Auto-configures via mcporter
```

That's it — restart your AI tool and Ag402 tools will appear automatically.

> **📖 Detailed tutorials**: [Claude Code Guide](docs/guide-claude-code.md) · [Cursor Guide](docs/guide-cursor.md) · [OpenClaw Guide](docs/guide-openclaw.md)

<details>
<summary>Manual configuration (if you prefer)</summary>

```bash
ag402 mcp-config cursor         # Print config JSON to copy manually
```

Add to your tool's MCP config (e.g. `.cursor/mcp.json` or `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "ag402": {
      "command": "python",
      "args": ["-m", "ag402_client_mcp.server"]
    }
  }
}
```

Your AI tool can now call `fetch_with_autopay` to access any x402 paid API, `wallet_status` to check balance, and `transaction_history` to review payments — all with zero code changes.

Generate configs for all supported tools:

```bash
ag402 mcp-config           # Show configs for Claude Code, Cursor, OpenClaw
ag402 mcp-config cursor    # Show config for a specific tool
```

</details>

---

## 💰 Monetize Your API — Service Provider View

Have a high-value API (advanced search, quantitative data, AI inference) and want agents to pay per call?

No Stripe. No user registration. Just mount the Ag402 gateway:

```bash
pip install ag402-mcp
ag402 serve --target http://localhost:8000 --price 0.05 --address <YourSolanaAddress>
```

> **Out of the box**: If the `--target` backend is not running, `ag402 serve` auto-starts a built-in Demo API for quick testing.

All requests **without valid on-chain payment proof** → automatic `402 Payment Required`.
Requests with valid proof → proxied to your backend, you return data as usual.

---

## 🛡️ Security Commitment — Security First

We understand the sensitivity of handling private keys and funds. Ag402's architecture is built with **defense in depth** as the first principle:

### 🔒 Fully Non-custodial

Your private key **stays 100% on your local machine**. There is no central server. We store nothing. Code is the service — there is no "Ag402 goes down" risk.

### 🔑 Local Strong Encryption (PBE)

Even test-mode private keys are **never stored in plaintext**. Keys are encrypted via `PBKDF2-HMAC-SHA256 + AES (Fernet)` and stored locally at `~/.ag402/wallet.key`. Decrypted in memory only when you enter your password.

### 🛑 Hardware-grade Circuit Breaker — 6 Safety Layers

Budget ceilings are **hardcoded** in the source. Even if your Agent code goes into an infinite loop, it cannot drain your wallet:

| Layer | Default | Description |
|-------|---------|-------------|
| Single-TX cap | $5.00 | Per-transaction ceiling, hardcoded |
| Per-minute cap | $2.00 / 5 txns | Rate + amount dual limits |
| Daily cap | $10.00 | Configurable, **hard ceiling $1,000** (code-enforced) |
| Circuit breaker | 3 failures / 60s cooldown | Auto-stops on consecutive failures |
| Auto-rollback | Always on | Failed payment → wallet deduction auto-reversed |
| Key filter | Always on | All logs auto-redacted, keys never leak |

### 🕵️ Zero Telemetry

**We collect no data.** No call logs, no IP tracking, no usage analytics. 100% open source, MIT license. Security audits welcome.

---

## 🧠 How It Works — The Open402 Flow

Ag402 follows the standard [HTTP 402 protocol](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/402), compatible with the [Coinbase x402 specification](https://github.com/coinbase/x402):

```
Your AI Agent              Ag402 Middleware           Target API
     │                             │                          │
     │── GET /api/data ──────────▶│                          │
     │                             │── GET /api/data ───────▶│
     │                             │◀── 402 + challenge ─────│
     │                             │                          │
     │                             │  ① Parse payment terms   │
     │                             │  ② Check budget ($0.02 ✓)│
     │                             │  ③ Solana on-chain tx    │
     │                             │  ④ Retry with proof      │
     │                             │                          │
     │                             │── GET /api/data ───────▶│
     │                             │   Authorization: x402    │
     │                             │◀── 200 OK + data ───────│
     │◀── 200 OK + data ──────────│                          │
     │                             │                          │
```

**From the Agent's perspective, steps ①②③④ are completely transparent.** It always sees a normal 200 response.

---

## 🏗️ Architecture

Four composable layers — each can be used independently:

```
┌───────────────────────────────────────────────────┐
│  ag402-client-mcp   MCP client adapter (buyer) │
│  (adapters/client_mcp) Claude Code·Cursor·OpenClaw│
├───────────────────────────────────────────────────┤
│  ag402-mcp        HTTP gateway adapter (seller)│
│  (adapters/mcp)      Wraps any API → x402 paywall │
├───────────────────────────────────────────────────┤
│  ag402-core       Payment engine                │
│  (core/)             Wallet · Limits · Retry · CLI │
│                      Monkey-patch · Proxy · Runner │
├───────────────────────────────────────────────────┤
│  open402             Protocol standard             │
│  (protocol/)         Spec · Header parsing · Nego  │
│                      Zero dependencies · Pure types│
└───────────────────────────────────────────────────┘
```

| Package | Description | Install |
|---------|-------------|---------|
| `open402` | x402 protocol types, header parsing, version negotiation. **Zero dependencies.** | `pip install open402` |
| `ag402-core` | Payment engine: wallet (SQLite), budget guard, Solana adapter, middleware, CLI | `pip install ag402-core` |
| `ag402-mcp` | HTTP gateway adapter: add an x402 paywall to any API (seller side) | `pip install ag402-mcp` |
| `ag402-client-mcp` | MCP client adapter: x402 auto-payment for Claude Code, Cursor, OpenClaw (buyer side) | `pip install ag402-client-mcp` |

---

## 📖 CLI Quick Reference

### 🚀 Quick Start

```bash
ag402 setup              # Interactive setup wizard (recommended for first use)
ag402 demo               # Run the full payment demo (mock mode)
ag402 demo --localnet    # Run demo on local Solana validator
ag402 demo --devnet      # Run demo on Solana devnet
```

### 🔌 Agent Integration

```bash
ag402 run -- python ...  # Any Python agent
ag402 mcp                # Start MCP server for Claude Code / Cursor / OpenClaw
ag402 mcp --sse          # Start MCP server in SSE mode (for web/remote)
ag402 install <tool>     # One-command setup: claude-code, cursor, openclaw
ag402 mcp-config         # Generate MCP configs for AI tools
```

### 🛒 Buyer / Seller

```bash
ag402 serve              # Start payment gateway (auto-starts built-in demo backend)
ag402 serve --localnet   # Start gateway using local Solana validator
ag402 pay <url>          # Buyer view: 6-step x402 negotiation visualization
```

### 💰 Wallet Management

```bash
ag402 status             # Full dashboard
ag402 balance            # Quick balance check
ag402 history            # Transaction history (supports --format json/csv)
ag402 tx <id>            # Transaction details
```

### 🔧 Configuration & Diagnostics

```bash
ag402 config             # View safety limit configuration
ag402 env show           # View current config file
ag402 env set KEY VALUE  # Modify a single config value
ag402 doctor             # Environment health check
ag402 info               # Protocol version info
```

### 🏪 Service Provider

```bash
ag402 serve              # Start payment gateway (auto-starts built-in demo backend)
ag402 serve --target http://localhost:8000 --price 0.10  # Custom backend
ag402 upgrade            # Switch from test mode to production
```

---

## ⚙️ Configuration Reference

All settings are managed via environment variables or the `~/.ag402/.env` file (auto-generated by `ag402 setup`):

| Variable | Default | Description |
|----------|---------|-------------|
| `X402_MODE` | `test` | `test` = virtual funds, `production` = real on-chain payments |
| `X402_NETWORK` | `mock` | Network mode: `mock`, `localnet`, `devnet`, `mainnet` |
| `SOLANA_PRIVATE_KEY` | — | Solana wallet private key (base58), required for production |
| `SOLANA_RPC_URL` | `devnet` | Solana RPC endpoint |
| `X402_SINGLE_TX_LIMIT` | `5.0` | Per-transaction cap (USD) |
| `X402_DAILY_LIMIT` | `10.0` | Daily spending cap (hard ceiling $1,000) |
| `X402_PER_MINUTE_LIMIT` | `2.0` | Per-minute amount cap (hard ceiling $10) |
| `X402_PER_MINUTE_COUNT` | `5` | Per-minute transaction count (hard ceiling 50) |
| `X402_CIRCUIT_BREAKER_THRESHOLD` | `3` | Consecutive failure threshold for circuit breaker |
| `X402_FALLBACK_API_KEY` | — | Bearer token (dual-mode for non-x402 APIs) |
| `AG402_UNLOCK_PASSWORD` | — | Wallet unlock password (for Docker/CI automation) |

---

## 🐳 Docker

```bash
docker compose up
# Starts mock weather API (port 18000) + x402 payment gateway (port 18001)
```

Encrypted wallet support:
```bash
docker run -e AG402_UNLOCK_PASSWORD=my_password ...
```

---

## 🧩 V1 Compatibility

| Agent Framework | Compatibility | Integration Method |
|----------------|---------------|-------------------|
| Generic Python Agent | ★★★★★ | `ag402 run -- python xxx` |
| Python SDK | ★★★★★ | `ag402_core.enable()` — two lines of code |
| LangChain / AutoGen / CrewAI | ★★★★★ | Based on httpx/requests, auto-compatible |
| Claude Code | ★★★★★ | `ag402 install claude-code` |
| Cursor | ★★★★★ | `ag402 install cursor` |
| OpenClaw | ★★★★☆ | `ag402 install openclaw` (requires mcporter) |

> **V1 Focus**: 100% Python ecosystem. Node.js / desktop integrations are planned for V2 with native plugin support.

---

## 🧪 Testing

> **Development Mode Install** (for contributors or pre-PyPI):
> ```bash
> git clone https://github.com/AetherCore-Dev/ag402.git && cd ag402
> make install     # Installs all packages in editable mode
> ```

```bash
make install        # Install all packages (dev mode)
make test           # Run all unit/mock tests (fast, no network)
make test-localnet  # Run localnet integration tests (requires solana-test-validator)
make test-devnet    # Run devnet integration tests (requires funded keypair)
make test-full      # Run all tests: unit + localnet + devnet
make test-perf      # Run devnet tests with performance regression comparison
make lint           # Ruff code checks
make coverage       # Coverage report
```

### Unit & Mock Tests

| Module | Tests | Coverage |
|--------|-------|----------|
| open402 protocol layer | 27 | 100% |
| Wallet + transactions | 10 | 96% |
| Payment adapters + registry | 18 | 94% |
| Middleware + stateful orders | 16 | 97% |
| Security (crypto/replay/rate/key_guard) | 62 | 98% |
| Payment order state machine | 20 | 98% |
| CLI (18 commands) | 61 | 75% |
| .env manager | 30 | 98% |
| Monkey-patch SDK | 11 | 90% |
| Budget enhanced + solana enhanced | 22 | 95% |
| Integration (phase4 + decimal + verifier) | 31 | 92% |
| Gateway adapter (MCP) | 5 | -- |
| MCP Client adapter (buyer) | 39 | 95% |
| Solana resilience (network errors, retries, timeouts) | 28 | -- |
| Security TDD P0 (LIKE injection, amount validation, crypto, breaker) | 30 | 98% |
| Security TDD P1 (clock rollback, replay, traversal, fuzzing, SSRF) | 56 | 95% |
| Security TDD P2 (persistent replay, exhaustion, fault injection, gateway) | 23 | 92% |
| **Subtotal** | **500+** | **90%+** |

### On-chain Integration Tests

| Test Suite | Tests | Environment | CI |
|------------|-------|-------------|-----|
| Localnet (solana-test-validator) | 23 | Local chain | ✅ Every PR |
| Devnet (Solana public testnet) | 26 | devnet RPC | ✅ Nightly |
| **Subtotal** | **49** | | |

> **Total: 77 on-chain + 430+ unit + 109 security TDD = 500+ tests**

### Test Infrastructure

- **CI**: GitHub Actions runs unit tests on every PR (Python 3.10/3.11/3.12), localnet integration on every PR, devnet integration nightly
- **Flaky test handling**: Network-sensitive devnet tests use `@pytest.mark.flaky(reruns=2)` via `pytest-rerunfailures`
- **Performance baseline**: `conftest_perf.py` plugin records test durations to `.perf-baseline.json`; use `--perf-compare` to detect latency regressions

---

## 🤝 Contributing

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Run `make lint && make test` to ensure all checks pass
4. Submit a Pull Request

All PRs go through CI (lint + unit tests on Python 3.10/3.11/3.12 + localnet integration + build).

---

## 📄 License

[MIT](LICENSE) — Free to use, modify, and distribute.
