---
name: ag402
description: "Native OpenClaw Skill for ag402 AI Agent Payment Protocol. Provides commands: setup (install/initialize), wallet status/deposit/history, pay <url> (make payments), gateway start/stop, doctor (health check). Use when managing payments for API calls via HTTP 402 with Solana USDC."
---

# ag402 - AI Agent Payment Protocol

Native OpenClaw Skill providing command-line interface for ag402 payment protocol.

## When to Use This Skill

**Use ag402 when:**
- Building paid AI agents that need to purchase API access
- Integrating with x402-compatible APIs
- Managing payment flows for agent services
- Setting up prepaid credit systems for agent operations

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      OpenClaw Agent                         │
│                          │                                  │
│                    ag402 Skill                              │
│              (Skill Management Layer)                       │
│                          │                                  │
│            ┌─────────────┴─────────────┐                    │
│            │                           │                    │
│    ┌───────▼───────┐         ┌────────▼────────┐          │
│    │ ag402 MCP     │         │ ag402-openclaw  │          │
│    │ (Tools/Functions)        │ (Bridge/SDK)    │          │
│    └───────────────┘         └─────────────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │   ag402 Protocol              │
              │   (HTTP 402 + Solana USDC)    │
              └───────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install ag402-core
```

### 2. Setup Wallet

```bash
ag402 setup
```

### 3. Configure in OpenClaw

The skill integrates with:
- `~/Documents/ag402/adapters/openclaw/ag402_openclaw/` - Bridge SDK
- `~/Documents/ag402/adapters/client_mcp/` - MCP tools

## Features

### Payment Operations
- **Check Balance** - Query USDC balance
- **Make Payment** - Execute on-chain payment
- **Verify Payment** - Confirm transaction success

### x402 Protocol
- **Handle 402 Response** - Auto-process payment challenges
- **Build Payment Header** - Construct x402 payment headers
- **Verify Payment Proof** - Validate payment verification

### Agent Integration
- **Enable Auto-Pay** - Global 402 interceptor
- **Get Payment Status** - Query pending/confirmed payments
- **List Transactions** - History of payments

## Security Principles

1. **Validate First** - Always verify payment recipient before sending
2. **Minimal Permissions** - Use dedicated payment wallet, not main wallet
3. **Transaction Verification** - Confirm on-chain before delivering service
4. **Audit Trail** - Log all payment attempts (success/failure)

## File Structure

```
ag402-skill/
├── SKILL.md           # This file
├── TOOLS.md           # Tool documentation
├── references/        # Additional docs
│   └── README.md      # Integration guide
└── scripts/           # Helper scripts (future)
```

## Dependencies

- `ag402-core` - Core protocol implementation
- `solana` - Blockchain interaction (optional, for on-chain)
- `httpx` / `requests` - HTTP client integration

## See Also

- [ag402 README](../README.md) - Full protocol documentation
- [ag402-openclaw adapter](../ag402_openclaw/) - Bridge implementation
- [client_mcp](../client_mcp/) - MCP tools for OpenClaw

## Commands

### setup
Initialize ag402 - creates config and test wallet with 100 USDC.

```python
await skill.execute("setup")
```

### wallet status
Check wallet balance and daily budget status.

```python
await skill.execute("wallet", ["status"])
```

### wallet deposit [amount]
Deposit test USDC (default: 10 USDC).

```python
await skill.execute("wallet", ["deposit"])       # Deposit 10 USDC
await skill.execute("wallet", ["deposit", "50"]) # Deposit 50 USDC
```

### wallet history [options]
View transaction history.

Options:
- `-l, --limit N` - Number of records (default: 10)
- `-t, --type TYPE` - Filter: all, payment, deposit, refund
- `-d, --days N` - Days to look back (default: 7)

```python
await skill.execute("wallet", ["history"])
await skill.execute("wallet", ["history", "-l", "20", "-t", "payment"])
```

### pay <url> [options]
Make payment to a URL. Supports x402 protocol.

Options:
- `-a, --amount N` - Payment amount in USDC
- `-y, --confirm` - Confirm large payments
- `-H, --header "Key: Value"` - Custom headers
- `-m, --method METHOD` - HTTP method (GET, POST, etc.)
- `-d, --data JSON` - Request body

```python
await skill.execute("pay", ["https://api.example.com/premium"])
await skill.execute("pay", ["https://api.example.com/generate", "-a", "2.50", "-m", "POST", "-d", '{"prompt":"hello"}'])
```

### gateway start
Start the ag402 payment gateway.

### gateway stop
Stop the ag402 payment gateway.

### doctor
Run health check - validates config, wallet, network, and gateway status.
