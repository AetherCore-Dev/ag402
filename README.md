<p align="center">
  <h1 align="center">Ag402</h1>
  <p align="center">
    <strong>Give your AI agent a wallet. It pays for APIs automatically.</strong>
  </p>
  <p align="center">
    <a href="https://github.com/AetherCore-Dev/ag402/stargazers"><img src="https://img.shields.io/github/stars/AetherCore-Dev/ag402?style=social" alt="GitHub Stars" /></a>&nbsp;
    <a href="https://pypi.org/project/ag402-core/"><img src="https://img.shields.io/pypi/dm/ag402-core?label=downloads" alt="PyPI Downloads" /></a>&nbsp;
    <a href="https://github.com/AetherCore-Dev/ag402/actions/workflows/ci.yml"><img src="https://github.com/AetherCore-Dev/ag402/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/tests-588%2B_passing-brightgreen" alt="Tests" />
    <img src="https://img.shields.io/badge/coverage-90%25+-brightgreen" alt="Coverage" />
    <img src="https://img.shields.io/badge/security_audits-4_rounds-blue" alt="Security Audits" />
    <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python" />
    <a href="https://pypi.org/project/ag402-core/"><img src="https://img.shields.io/pypi/v/ag402-core" alt="PyPI" /></a>
    <a href="https://github.com/AetherCore-Dev/ag402/blob/main/LICENSE"><img src="https://img.shields.io/github/license/AetherCore-Dev/ag402" alt="License" /></a>
    <a href="https://github.com/AetherCore-Dev/ag402/commits/main"><img src="https://img.shields.io/github/last-commit/AetherCore-Dev/ag402" alt="Last Commit" /></a>
  </p>
  <p align="center">
    <a href="https://colab.research.google.com/github/AetherCore-Dev/ag402/blob/main/examples/ag402_quickstart.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab" /></a>
  </p>
</p>

---

**Ag402** is the payment layer for the [Coinbase x402](https://github.com/coinbase/x402) protocol. It makes AI agents pay for API calls automatically — on Solana, in USDC, with zero code changes.

```
Agent calls API → 402 Payment Required → Ag402 auto-pays USDC on Solana → 200 OK
```

> **Non-custodial. Zero telemetry. Already in production.**

<!-- TODO: Add terminal GIF demo here — record with `vhs` or `asciinema` -->
<!-- ag402 init → ag402 demo — 15 seconds, shows the full colored payment flow -->

---

## Why Ag402

### Zero friction
- Zero code changes for buyers, sellers, and MCP developers
- Three CLI commands cover everything: `ag402 run`, `ag402 serve`, `ag402 install`
- No config files, no API keys, no accounts, no signup
- [Colab one-click demo](https://colab.research.google.com/github/AetherCore-Dev/ag402/blob/main/examples/ag402_quickstart.ipynb) — try it in your browser, zero install

### Open standard
- Implements [Coinbase x402](https://github.com/coinbase/x402) — the emerging HTTP payment standard
- MIT licensed, fully open source, extensible protocol layer (`open402`) with zero dependencies
- **AI-native docs** — ships with [`llms.txt`](llms.txt) so LLM agents can read the full CLI reference natively

### Battle-tested
- [Token RugCheck](https://github.com/AetherCore-Dev/token-rugcheck) — **live on Solana mainnet** with real USDC payments
- 588+ tests, 90%+ coverage, 4 security audits (24/24 issues fixed)
- Multi-endpoint RPC failover + circuit breaker + async delivery retry

### Blazing fast
- **~0.5s** standard payment (`confirmed` finality, not 13s `finalized`)
- **~1ms** prepaid payment (local HMAC, no on-chain call)
- Zero overhead on non-402 requests — no body read, no allocation
- Connection pooling, lazy imports, SQLite WAL mode

### Security-first
- 6-layer budget protection — per-tx / per-minute / daily / circuit breaker / rollback / key redaction
- Non-custodial — private keys never leave your machine
- Seller-No-Key — sellers only need a public address, zero private key risk
- Zero telemetry — no tracking, no IP logging, no analytics
- Wallet encryption: PBKDF2 (480K iter) + AES
- CI: CodeQL + Trivy + pip-audit + Semgrep + OpenSSF Scorecard

### Universal compatibility
- Claude Code, Cursor, Claude Desktop — MCP auto-config
- OpenClaw — **native Skill** (SKILL.md + TOOLS.md + skill.py), not just MCP
- LangChain, AutoGen, CrewAI, Semantic Kernel — works automatically
- Any Python agent using `httpx` or `requests` — zero changes

---

## Zero Code Changes. For Everyone.

| You are... | What you do | Code changes |
|:-----------|:------------|:-------------|
| **Agent user** (LangChain, CrewAI, AutoGen, any Python agent) | `pip install ag402-core && ag402 run -- python my_agent.py` | **Zero** — your agent code is untouched |
| **Claude Code / Cursor user** | `ag402 install claude-code` (or `cursor`) | **Zero** — MCP tools appear automatically |
| **OpenClaw user** | `ag402 install openclaw` | **Zero** — native Skill + MCP, auto-configured |
| **API seller** (monetize your API) | `ag402 serve --target http://your-api:8000 --price 0.05 --address <Addr>` | **Zero** — reverse proxy handles everything |
| **MCP server developer** | `ag402 serve --target http://your-mcp:3000 --price 0.01 --address <Addr>` | **Zero** — wrap your existing MCP server, instant paywall |

No config files. No API keys. No accounts. No code changes.

---

## Try It Now

```bash
pip install ag402-core
ag402 init       # Creates wallet + $100 test USDC — zero prompts
ag402 demo       # Watch the full payment flow end-to-end
```

Or zero install: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AetherCore-Dev/ag402/blob/main/examples/ag402_quickstart.ipynb)

---

## Already in Production

<table>
<tr>
<td width="55%">

### [Token RugCheck](https://github.com/AetherCore-Dev/token-rugcheck)

**Live on Solana mainnet.** AI agents pay **$0.02 USDC** per audit to detect rug pulls before purchasing tokens.

- Three-layer audit: machine verdict → LLM analysis → raw on-chain evidence
- **Seller**: `ag402 serve` — zero code changes to the audit API
- **Buyer**: `ag402_core.enable()` — agents auto-pay, zero code changes
- **Try it now**: `curl -I https://rugcheck.aethercore.dev/v1/audit/DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263`

</td>
<td width="45%">

```
Agent → GET /v1/audit/{token}
     ← 402 Payment Required ($0.02)
     → Ag402 pays USDC on Solana
     → Retries with tx_hash proof
     ← 200 OK + full audit report
```

</td>
</tr>
</table>

> Not a demo. Real USDC, real Solana mainnet, real users, already running.

---

## How It Works

### For Agent Users — Zero Code Changes

Your agent already uses `httpx` or `requests` under the hood. Ag402 patches them transparently:

```bash
# Option A: CLI wrapper (easiest — zero code changes)
ag402 run -- python my_agent.py

# Option B: One-liner in code
import ag402_core; ag402_core.enable()
```

That's it. Every HTTP 402 response is now intercepted → paid → retried automatically. Your agent code stays **completely untouched**.

Works with **LangChain**, **AutoGen**, **CrewAI**, **Semantic Kernel**, and any framework built on `httpx` or `requests`.

### For Claude Code / Cursor / OpenClaw — One Command

```bash
pip install ag402-core ag402-client-mcp
ag402 install claude-code    # or: cursor / claude-desktop / openclaw
```

Restart your tool. Three MCP tools appear:

| MCP Tool | What It Does |
|----------|-------------|
| `fetch_with_autopay` | HTTP request → auto-pays 402 APIs |
| `wallet_status` | Check USDC balance + budget usage |
| `transaction_history` | View recent payments |

**OpenClaw** gets the deepest integration — Ag402 ships as a **native OpenClaw Skill** (`SKILL.md` + `TOOLS.md` + `skill.py`), not a wrapper. The skill registers natively in OpenClaw's skill system, with full tool definitions, prepaid support, and auto-fallback.

### For API Sellers — Zero Code Changes

```bash
pip install ag402-core ag402-mcp
ag402 serve --target http://localhost:8000 --price 0.05 --address <YourSolanaAddress>
```

Your existing API runs untouched behind a reverse proxy. The proxy:
- Returns **402 + x402 challenge** to unpaid requests
- **Verifies payment on-chain** (no private key needed — seller only provides a public address)
- Proxies paid requests through to your API
- Handles replay protection, rate limiting, header sanitization

**MCP server developers**: same command, same result. Wrap your MCP server, get a paywall instantly.

---

## Performance

| Metric | Value | How |
|--------|-------|-----|
| **Payment latency** | **~0.5s** | `confirmed` finality — 26x faster than `finalized` (~13s) |
| **Prepaid latency** | **~1ms** | Local HMAC-SHA256 — no on-chain call at all |
| **Non-402 overhead** | **Zero** | Checks status code only — no body read, no allocation, no latency |
| **RPC resilience** | **Multi-endpoint** | Exponential backoff → auto-failover to backup RPC → circuit breaker |
| **Delivery guarantee** | **Async retry** | Payment succeeds but upstream fails? Background worker retries with backoff |

### Prepaid System — From 500ms to 1ms

```
Buy:  Agent → one Solana payment → gets HMAC credential (N calls / M days)
Use:  Agent → X-Prepaid-Credential → local HMAC verify → 200 OK   ← no chain, ~1ms
```

5 tiers from $1.50 (3d/100 calls) to $60 (730d/10K calls). Auto-fallback to standard x402 when exhausted.

---

## Security — Built for Real Money

Your agent holds private keys and moves real USDC. Security is not a feature — it's the foundation.

**4 rounds of security audits** · 24 issues found, **24 fixed** · **109 dedicated security TDD tests** · 588+ total tests · 90%+ coverage

### 6-Layer Budget Protection

| Layer | What It Does | Default |
|-------|-------------|---------|
| Per-transaction cap | Hard ceiling on single payment | **$5.00** |
| Per-minute rate limit | Dollar + count cap | **$2.00 / 5 txns** |
| Daily spend cap | Maximum daily spend | **$10.00** (ceiling: $1,000) |
| Circuit breaker | Auto-stop after consecutive failures | **3 fails → 60s cooldown** |
| Auto-rollback | Instant reversal on failed payments | Always on |
| Key redaction | Private keys scrubbed from all logs | Always on |

### Architecture Principles

| Principle | How |
|-----------|-----|
| **Non-custodial** | Private keys never leave your machine. No server. No account. |
| **Seller-No-Key** | Sellers only need a public address — zero private key risk |
| **Wallet encryption** | PBKDF2-HMAC-SHA256 (480K iterations) + Fernet/AES |
| **Zero telemetry** | No tracking, no IP logging, no analytics. Period. |
| **Replay protection** | Timestamp + nonce + persistent tx_hash dedup (SQLite) |
| **SSRF protection** | Blocks private IPs, non-HTTPS, reserved ranges |
| **Header sanitization** | Strips Cookie, X-Forwarded-For, Authorization before proxy |

### CI Pipeline (Every PR)

CodeQL · Trivy · pip-audit · Semgrep · 588+ tests · 90%+ coverage · OpenSSF Scorecard

---

## Protocol

```
HTTP/1.1 402 Payment Required
WWW-Authenticate: x402 chain="solana" token="USDC" amount="0.05" address="..."

→ Client pays on-chain, retries with:

GET /data HTTP/1.1
Authorization: x402 <solana_tx_hash>

→ Server verifies on-chain → 200 OK
```

Compatible with the [Coinbase x402](https://github.com/coinbase/x402) open payment standard.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Your Agent (LangChain / CrewAI / AutoGen / any Python)        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  ag402_core.enable()  ← monkey-patches httpx / requests  │   │
│  └──────────────┬───────────────────────────────────────────┘   │
│                 │ HTTP request                                   │
│                 ▼                                                │
│  ┌──────────────────────────┐    ┌────────────────────────┐     │
│  │  x402 Middleware         │───▶│  BudgetGuard (6 layers)│     │
│  │  Intercepts 402 response │    │  Circuit Breaker       │     │
│  └──────────┬───────────────┘    └────────────────────────┘     │
│             │ Pay                                                │
│             ▼                                                    │
│  ┌──────────────────────────┐    ┌────────────────────────┐     │
│  │  SolanaAdapter           │───▶│  RPC Failover          │     │
│  │  USDC transfer + verify  │    │  Exponential backoff   │     │
│  └──────────┬───────────────┘    └────────────────────────┘     │
│             │ tx_hash                                            │
│             ▼                                                    │
│  Retry original request with  Authorization: x402 <tx_hash>     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Seller Gateway  (ag402 serve)                                  │
│  ┌────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ 402 + x402 │  │ On-chain     │  │ Replay Guard           │  │
│  │ Challenge   │  │ Verification │  │ Rate Limiter           │  │
│  └────────────┘  └──────────────┘  │ Header Sanitization    │  │
│                                     └────────────────────────┘  │
│  → Proxies to your API (unchanged)                              │
└─────────────────────────────────────────────────────────────────┘
```

[Full architecture diagrams & state machines → docs/architecture_state.md](docs/architecture_state.md)

---

## Packages

| Package | PyPI | Role |
|---------|------|------|
| [`open402`](https://pypi.org/project/open402/) | [![PyPI](https://img.shields.io/pypi/v/open402)](https://pypi.org/project/open402/) | Protocol standard — **zero dependencies** |
| [`ag402-core`](https://pypi.org/project/ag402-core/) | [![PyPI](https://img.shields.io/pypi/v/ag402-core)](https://pypi.org/project/ag402-core/) | Payment engine + CLI + wallet (buyer) |
| [`ag402-mcp`](https://pypi.org/project/ag402-mcp/) | [![PyPI](https://img.shields.io/pypi/v/ag402-mcp)](https://pypi.org/project/ag402-mcp/) | Reverse-proxy gateway (seller) — **zero code changes** |
| [`ag402-client-mcp`](https://pypi.org/project/ag402-client-mcp/) | [![PyPI](https://img.shields.io/pypi/v/ag402-client-mcp)](https://pypi.org/project/ag402-client-mcp/) | MCP client for AI tools (buyer) |

---

## CLI Reference

| Command | Description |
|---------|-------------|
| `ag402 init` | Non-interactive setup — for AI agents (zero prompts) |
| `ag402 setup` | Interactive wizard — for humans |
| `ag402 demo` | Full E2E payment demo |
| `ag402 run -- <cmd>` | Run any script with automatic x402 payment |
| `ag402 pay <url>` | Single paid request |
| `ag402 serve` | Start payment gateway (seller) |
| `ag402 install <tool>` | One-command MCP setup (claude-code / cursor / openclaw) |
| `ag402 status` | Dashboard: balance, budget, security |
| `ag402 balance` | Quick balance check |
| `ag402 history` | Transaction history |
| `ag402 doctor` | Environment health check |
| `ag402 upgrade` | Migrate test → production |
| `ag402 export` | Export history (JSON/CSV) |

[Full CLI reference → llms.txt](llms.txt) (AI-readable, paste into your agent's context)

---

## Documentation

| Resource | Description |
|----------|-------------|
| **[llms.txt](llms.txt)** | AI-readable CLI reference — paste into your agent's context |
| **[Claude Code Guide](docs/guide-claude-code.md)** | Step-by-step MCP integration |
| **[Cursor Guide](docs/guide-cursor.md)** | Step-by-step MCP integration |
| **[OpenClaw Guide](docs/guide-openclaw.md)** | Native Skill + MCP integration |
| **[Architecture](docs/architecture_state.md)** | System diagrams & state machines |
| **[x402 Protocol Spec](docs/x402_protocol_spec.md)** | Full protocol specification |
| **[OpenClaw Skill](adapters/openclaw/ag402-skill/)** | Native OpenClaw skill definition |
| **[Localnet Guide](docs/guide-localnet.md)** | Local Solana validator setup |
| **[SECURITY](SECURITY.md)** | Security policy & audit history |
| **[CHANGELOG](CHANGELOG.md)** | Version history |
| **[CONTRIBUTING](CONTRIBUTING.md)** | Contribution guide |

---

## Quick Copy-Paste

**Agent user** (zero code changes):
```bash
pip install ag402-core && ag402 init && ag402 run -- python my_agent.py
```

**Claude Code / Cursor**:
```bash
pip install ag402-core ag402-client-mcp && ag402 install claude-code
```

**Sell your API** (zero code changes):
```bash
pip install ag402-core ag402-mcp && ag402 serve --target http://your-api:8000 --price 0.05 --address <Addr>
```

---

## Community

- [GitHub Discussions](https://github.com/AetherCore-Dev/ag402/discussions) — questions, ideas, show & tell
- [Issue Tracker](https://github.com/AetherCore-Dev/ag402/issues) — bug reports, feature requests
- [Contributing Guide](CONTRIBUTING.md) — PRs welcome, see "Good First Issues"

---

## License

[MIT](LICENSE) — Open source, free forever.
