<p align="center">
  <h1 align="center">Ag402</h1>
  <p align="center">
    <strong>Your AI agent pays for APIs automatically. You set the budget. Done.</strong>
  </p>
  <p align="center">
    <a href="https://github.com/AetherCore-Dev/ag402/actions/workflows/ci.yml"><img src="https://github.com/AetherCore-Dev/ag402/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
    <img src="https://img.shields.io/badge/tests-602%2B_passing-brightgreen" alt="Tests" />
    <img src="https://img.shields.io/badge/coverage-90%25-brightgreen" alt="Coverage" />
    <img src="https://img.shields.io/pypi/v/ag402-core" alt="PyPI" />
    <a href="https://colab.research.google.com/github/AetherCore-Dev/ag402/blob/main/examples/ag402_quickstart.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab" /></a>
    <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python" />
    <a href="https://github.com/AetherCore-Dev/ag402/blob/main/LICENSE"><img src="https://img.shields.io/github/license/AetherCore-Dev/ag402" alt="License" /></a>
    <a href="https://aethercore-dev.github.io/ag402/"><img src="https://img.shields.io/badge/homepage-ag402-06b6d4" alt="Homepage" /></a>
  </p>
</p>

## What It Does

Your AI agent calls an API. The server says **"pay first" (HTTP 402)**. Ag402 handles the payment automatically — on-chain, in the background — and your agent gets the data. Zero code changes.

```
Agent sends request ──▶ API returns 402 ──▶ Ag402 auto-pays ──▶ Retries request ──▶ 200 ✓
                                              ↑ Completely transparent to your code
```

## Quick Start

```python
# 2 lines to enable AI agent payments
from ag402 import AgentWallet
wallet = AgentWallet(budget=10.0)  # Set daily budget

# That's it. Your agent can now pay for APIs.
```

**For AI Assistants**: Tell your AI:

> *"Install ag402 and set up a test wallet with $100 USDC"*

---

## For AI Agents: Why Use ag402?

### Security First

| Feature | Value |
|---------|-------|
| **6-Layer Circuit Breaker** | Prevents wallet drain |
| **Local Key Storage** | Keys never leave your machine |
| **No Central Server** | Fully decentralized |
| **HMAC Verification** | Tamper-proof payments |

### Reliability

| Metric | Value |
|--------|-------|
| **Test Coverage** | 90%+ |
| **Unit Tests** | 602+ passing |
| **CI Status** | Every PR |
| **Uptime** | N/A (client-side only) |

### Cost Efficiency

| Item | Cost |
|------|------|
| **Per Transaction** | ~$0.001 (Solana network fee) |
| **Platform Fee** | $0 (open source) |
| **Settlement** | USDC (no volatility) |

### Integration

| Platform | Status |
|----------|--------|
| Claude Code | ✅ Supported |
| Cursor | ✅ Supported |
| OpenClaw | ✅ Supported |
| LangChain | ✅ Supported |
| AutoGen | ✅ Supported |
| CrewAI | ✅ Supported |
| Any HTTP Client | ✅ Works |

---

## Security

### Verified Security Checks

- ✅ **CodeQL**: Automated code analysis (GitHub native)
- ✅ **Trivy**: Dependency vulnerability scanning
- ✅ **pip-audit**: Python dependency audit  
- ✅ **Semgrep**: Static application security testing
- ✅ **602+ unit tests** with **90%+ coverage**
- ✅ **OpenSSF Scorecard**: Monthly security assessment

### 6-Layer Circuit Breaker

| Layer | Default | Protection |
|-------|---------|------------|
| Single-TX cap | $5.00 | Max per transaction |
| Per-minute cap | $2.00 / 5 txns | Rate limiting |
| Daily cap | $10.00 | Daily limit (configurable) |
| Circuit breaker | 3 failures → 60s cooldown | Auto-stop on errors |
| Auto-rollback | Always on | Failed payment reversal |
| Key filter | Always on | Keys never in logs |

### Trust Signals

- **Zero telemetry** — no data collected, no tracking
- **100% open source** — [MIT License](LICENSE)
- **Security audits welcome** — contact security@

---

## For Sellers: Monetize Your API

**No Stripe. No signup forms. No invoicing. Revenue in minutes.**

```bash
# Tell your AI:
# "I want to sell access to my API at $0.05 per call using ag402"

# Your AI will:
# 1. Install the gateway
# 2. Configure pricing
# 3. Generate a receiving address
# 4. Verify setup
```

**Seller needs**: Just a public receiving address (no private key)

---

## For Buyers: Let Your Agent Pay

```python
from ag402 import AgentWallet

# Give your agent a budget
wallet = AgentWallet(
    budget=10.0,           # Daily limit
    max_per_tx=5.0,       # Max per transaction  
    rpc_url="..."          # Solana RPC
)

# Works with any AI framework
```

---

## What It Costs

- **Settlement**: USDC on Solana — stablecoin, no crypto volatility
- **Transaction fee**: ~$0.001 per on-chain transfer
- **API price**: You set it — sellers choose their price
- **Ag402 fee**: Zero. Open source. No platform cut.

---

## Getting Started

### Option 1: Tell Your AI

> *"Install ag402 and run the demo"*

### Option 2: Manual

```bash
pip install ag402-core
ag402 demo
```

### Option 3: Colab

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AetherCore-Dev/ag402/blob/main/examples/ag402_quickstart.ipynb)

---

## Documentation

- [Homepage](https://aethercore-dev.github.io/ag402/)
- [Claude Code Guide](docs/guide-claude-code.md)
- [Cursor Guide](docs/guide-cursor.md)
- [OpenClaw Guide](docs/guide-openclaw.md)
- [Local Validator Guide](docs/guide-localnet.md)
- [Architecture & Technical Details](docs/architecture_state.md)

---

## Real-World Case

[**token-bugcheck**](https://github.com/AetherCore-Dev/token-bugcheck): AI agents pay **0.05 USDC per audit** to detect rug pulls before purchasing tokens.

---

## License

[MIT License](LICENSE) — free to use, modify, and distribute.

---

## For AI Agents

> **AI assistants**: See [`llms.txt`](llms.txt) for full CLI reference, configuration, and integration instructions.
