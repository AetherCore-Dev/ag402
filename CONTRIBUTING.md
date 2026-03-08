# Contributing to Ag402

Thank you for your interest in contributing to Ag402! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.10+
- Git

### Install in Development Mode

```bash
git clone https://github.com/AetherCore-Dev/ag402.git
cd ag402
make install    # Installs all 4 packages in editable mode
```

### Running Tests

```bash
make test       # Run all 588+ tests
make lint       # Ruff code checks
make coverage   # Coverage report
```

> **macOS Note**: Use `--timeout-method=thread` with pytest to avoid signal-based timeout issues:
> ```bash
> python -m pytest core/tests/ -v --timeout=10 --timeout-method=thread
> ```

## How to Contribute

### Reporting Bugs

- Use the [GitHub Issues](https://github.com/AetherCore-Dev/ag402/issues) page
- Include steps to reproduce, expected vs actual behavior
- Include Python version and OS

### Suggesting Features

- Open a GitHub Issue with the "enhancement" label
- Describe the use case and why it would be valuable

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Ensure all tests pass: `make lint && make test`
5. Commit with a clear message following [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat: add new feature`
   - `fix: resolve bug`
   - `docs: update documentation`
   - `refactor: restructure code`
   - `test: add tests`
6. Push and open a Pull Request

### Code Style

- We use [Ruff](https://github.com/astral-sh/ruff) for linting
- Target Python 3.10+, line length 100
- Run `make lint` before committing

## Project Structure

```
protocol/open402/                     → open402 (zero-dependency protocol layer)
  spec.py                             → Constants, chain/token definitions, amount validation
  headers.py                          → x402 header parsing and building
  negotiation.py                      → Version negotiation

core/ag402_core/                      → ag402-core (payment engine + CLI)
  config.py                           → Configuration, mode system, SSRF validation
  cli.py                              → 20+ CLI commands with colorized output
  monkey.py                           → enable()/disable()/enabled() monkey-patch SDK
  wallet/                             → SQLite ledger, budget, payment order state machine
  payment/                            → Solana adapter, mock, registry, retry + failover
  middleware/                         → x402 interception, budget guard, circuit breaker
  gateway/                            → Server-side payment gate + auth + header whitelist
  security/                           → Key guard, encryption, rate limiter, replay guard
  proxy/                              → HTTP forward proxy (SSRF-safe)
  runners/                            → Agent runners (secure tmpdir injection)

adapters/mcp/ag402_mcp/               → ag402-mcp (HTTP gateway for sellers)
adapters/client_mcp/ag402_client_mcp/ → ag402-client-mcp (MCP client for AI tools)
adapters/openclaw/                    → OpenClaw bridge + skill + prepaid system

examples/                             → Demo scripts
docs/                                 → Integration guides (Claude Code, Cursor, OpenClaw, localnet)
```

## Security

If you find a security vulnerability, please **do NOT** open a public issue.
Instead, follow our [Security Policy](SECURITY.md).

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
