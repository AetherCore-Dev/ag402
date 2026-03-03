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
  </p>
</p>

## What It Does

Your AI agent calls an API. The server says **"pay first" (HTTP 402)**. Ag402 handles the payment automatically — on-chain, in the background — and your agent gets the data. Zero code changes.

```
Agent sends request ──▶ API returns 402 ──▶ Ag402 auto-pays ──▶ Retries request ──▶ 200 ✓
                                              ↑ Completely transparent to your code
```

## For Sellers: Monetize Your API

**No Stripe. No signup forms. No invoicing. Revenue in minutes.**

You set a price. AI agents pay per call. USDC arrives directly in your wallet. That's the whole model.

**Tell your AI assistant:**

> *"I want to sell access to my API at $0.05 per call using ag402."*

Your AI will install the gateway, configure pricing, and verify the setup.

## For Buyers: Let Your Agent Pay

**Your agent pays $0.01 per call. You get data. Done.**

Give your AI agent a wallet with a budget. It encounters a paid API, pays automatically, and keeps working. Works with Claude Code, Cursor, LangChain, AutoGen, CrewAI — anything that makes HTTP requests.

**Tell your AI assistant:**

> *"Set up ag402 so my agent can pay for x402 APIs."*

Your AI will install ag402, create a test wallet with $100 test USDC, and configure your tool.

## Security Promise

Your private key **never leaves your machine**. There is no central server. No account. No custody. Keys are encrypted locally with industry-standard encryption — never stored in plaintext, even in test mode.

### 6-Layer Circuit Breaker

Even if your agent loops, it cannot drain your wallet:

| Layer | Default | What it does |
|-------|---------|--------------|
| Single-TX cap | $5.00 | Per-transaction ceiling, hardcoded |
| Per-minute cap | $2.00 / 5 txns | Rate + amount dual limit |
| Daily cap | $10.00 | Configurable, **hard ceiling $1,000** |
| Circuit breaker | 3 failures → 60s cooldown | Auto-stops on consecutive failures |
| Auto-rollback | Always on | Failed payment → wallet deduction reversed |
| Key filter | Always on | All logs auto-redacted, keys never leak |

## Trust Signals

- **602+ tests** passing, 90%+ coverage, CI on every PR
- **Zero telemetry** — no data collected, no tracking, no analytics
- **100% open source** — [MIT License](LICENSE), security audits welcome

## Real-World Case: Token RugCheck

[**token-bugcheck**](https://github.com/AetherCore-Dev/token-bugcheck) is a production Solana token safety audit service. AI agents pay **0.05 USDC per audit** to detect rug pulls before purchasing tokens.

- Seller wraps their audit API with an ag402 gateway — one prompt to their AI
- Buyer's agent calls the API — ag402 auto-pays, gets the audit report
- **Zero changes to business logic on either side**

## What It Costs

- **Settlement**: USDC on Solana — stablecoin, no crypto volatility
- **Transaction fee**: ~$0.001 per on-chain transfer (Solana network fee)
- **API price**: You set it — sellers choose their price per call
- **Ag402 fee**: Zero. Open source. No platform cut

## Getting Started

**Tell your AI assistant:**

> *"Install ag402 and run the demo so I can see how x402 payments work."*

Or try it in your browser with zero install:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AetherCore-Dev/ag402/blob/main/examples/ag402_quickstart.ipynb)

## Links

- [Interactive Colab Notebook](https://colab.research.google.com/github/AetherCore-Dev/ag402/blob/main/examples/ag402_quickstart.ipynb) — see it work in your browser
- [Claude Code Guide](docs/guide-claude-code.md) · [Cursor Guide](docs/guide-cursor.md) · [OpenClaw Guide](docs/guide-openclaw.md)
- [Local Validator Guide](docs/guide-localnet.md) — run real on-chain transactions locally
- [Architecture & Technical Details](docs/architecture_state.md)
- [Contributing](CONTRIBUTING.md) — fork, branch, `make lint && make test`, PR
- [License: MIT](LICENSE) — free to use, modify, and distribute

> **AI assistants**: see [`llms.txt`](llms.txt) for full CLI reference, configuration, and integration instructions.
