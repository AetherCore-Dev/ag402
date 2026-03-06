# ag402 OpenClaw Integration Guide

This directory contains additional documentation for integrating ag402 with OpenClaw.

## Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Integration Steps](#integration-steps)
- [Security](#security)

## Overview

The ag402 skill enables OpenClaw agents to make autonomous payments for API calls using the x402 payment protocol. 

## Architecture

### Components

1. **ag402 Skill** (`ag402-skill/`)
   - Skill metadata and management
   - Tool definitions
   - Documentation

2. **ag402-openclaw Bridge** (`../ag402_openclaw/`)
   - Python SDK for OpenClaw integration
   - Bridge between OpenClaw and ag402 core

3. **Client MCP** (`../client_mcp/`)
   - MCP server providing tools to OpenClaw
   - Function definitions for payment operations

### Data Flow

```
OpenClaw Agent
      │
      ▼
ag402 Skill (selects/routes)
      │
      ▼
MCP Tools (function calls)
      │
      ▼
ag402-openclaw Bridge (SDK)
      │
      ▼
ag402 Core (protocol logic)
      │
      ▼
Solana/USDC (on-chain settlement)
```

## Integration Steps

### 1. Install Dependencies

```bash
pip install ag402-core
```

### 2. Setup Wallet

```bash
ag402 setup
```

This creates a wallet and funds it with test USDC.

### 3. Configure OpenClaw

Add the skill to your OpenClaw configuration:

```json
{
  "skills": ["ag402"]
}
```

### 4. Verify Integration

```python
from ag402_openclaw import AG402Bridge

bridge = AG402Bridge()
balance = bridge.check_balance()
print(f"Balance: {balance}")
```

## Security

### Best Practices

1. **Dedicated Payment Wallet** - Don't use your main wallet
2. **Spending Limits** - Set max amount per transaction
3. **Transaction Verification** - Always verify on-chain
4. **Logging** - Maintain audit trail

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AG402_WALLET_PATH` | Path to wallet file | Yes |
| `AG402_RPC_URL` | Solana RPC endpoint | No (devnet default) |
| `AG402_MCP_SERVER` | MCP server URL | No (local default) |

## Troubleshooting

### Common Issues

1. **Insufficient Balance**
   - Check balance: `bridge.check_balance()`
   - Fund wallet: `ag402 setup` or transfer USDC

2. **Transaction Failed**
   - Verify network connectivity
   - Check Solana RPC status
   - Review transaction logs

3. **Wallet Not Found**
   - Run `ag402 setup` to initialize
   - Check `AG402_WALLET_PATH` environment variable

## Examples

### Basic Payment

```python
from ag402_openclaw import AG402Bridge

bridge = AG402Bridge()

# Check balance before payment
balance = bridge.check_balance()
print(f"Current balance: {balance}")

# Make payment (handled automatically for 402 responses)
# Enable auto-pay mode
bridge.enable_autopay(max_amount=5.0)
```

### Handle 402 Manually

```python
# If auto-pay is disabled
if response.status_code == 402:
    result = bridge.handle_402_response(response, original_request)
    print(f"Payment completed: {result}")
```

## Resources

- [ag402 Main README](../../README.md)
- [Protocol Documentation](../../docs/)
- [Solana Docs](https://docs.solana.com/)
- [x402 Protocol](https://github.com/402protocol)
