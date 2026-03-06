# ag402 Tools Documentation

This document describes the tools provided by the ag402 skill for AI agent payment integration.

## Available Tools

### Payment Management

| Tool | Description | Parameters |
|------|-------------|------------|
| `check_balance` | Query USDC balance for wallet | `address` (optional) |
| `get_balance` | Get balance with details | `address` (optional) |

### x402 Protocol

| Tool | Description | Parameters |
|------|-------------|------------|
| `handle_402` | Process HTTP 402 payment challenge | `response`, `original_request` |
| `build_payment_header` | Create x402 payment header | `recipient`, `amount`, `currency`, `payload` |
| `verify_payment_proof` | Validate payment verification | `proof`, `expected_amount` |

### Agent Integration

| Tool | Description | Parameters |
|------|-------------|------------|
| `enable_autopay` | Enable global 402 interceptor | `max_amount` (optional) |
| `disable_autopay` | Disable auto-pay | - |
| `get_payment_status` | Query payment by ID | `payment_id` |
| `list_transactions` | List payment history | `limit`, `offset`, `address` |

### Configuration

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_wallet_address` | Get current wallet address | - |
| `setup_wallet` | Initialize new wallet | `password` |
| `verify_wallet` | Verify wallet exists and is accessible | - |

## Tool Details

### check_balance

```python
# Check balance
check_balance(address="YourWalletAddress123...")
# Returns: {"balance": 100.50, "currency": "USDC"}
```

### handle_402

```python
# Process 402 response from API
handle_402(
    response={"status": 402, "headers": {...}},
    original_request={"url": "...", "method": "GET"}
)
# Returns: {"payment_id": "...", "status": "completed"}
```

### enable_autopay

```python
# Enable automatic payment for 402 responses
enable_autopay(max_amount=10.00)  # Max $10 per request
# Returns: {"enabled": true, "max_amount": 10.00}
```

## Usage in OpenClaw

The tools can be used in two modes:

### 1. Direct Tool Calls (via MCP)

The `client_mcp` provides these as callable functions in OpenClaw.

### 2. Bridge SDK (via Python)

```python
from ag402_openclaw import AG402Bridge

bridge = AG402Bridge()
balance = bridge.check_balance()
```

## Error Handling

| Error Code | Description | Action |
|------------|-------------|--------|
| 402 | Payment Required | Initiate payment flow |
| 403 | Payment Failed | Check balance/wallet |
| 404 | Invalid Recipient | Verify recipient address |
| 429 | Rate Limited | Retry after cooldown |

## Security Notes

1. **Never expose private keys** - Use wallet address only
2. **Set spending limits** - Use `max_amount` parameter
3. **Verify transactions** - Always confirm on-chain
4. **Log everything** - Audit trail for debugging
