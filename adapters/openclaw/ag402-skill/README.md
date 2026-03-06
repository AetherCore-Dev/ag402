# ag402 OpenClaw Skill

Integrates ag402 AI Agent Payment Protocol with OpenClaw.

## Features

### Core Functions
- **setup**: Initialize wallet and configuration
- **wallet status**: Check balance and budget
- **wallet deposit**: Add test USDC
- **wallet history**: View transaction history
- **pay <url>**: Make payment to API endpoint
- **gateway start/stop**: Control payment gateway
- **doctor**: Health check and diagnostics

### Security Features

| Feature | Description |
|---------|-------------|
| SSRF Protection | Blocks localhost, private IPs, dangerous ports |
| Race Condition Fix | File locking for atomic balance operations |
| API Key Auth | Support for AG402_API_KEY environment variable |
| Header Filtering | Blocks dangerous headers (authorization, cookie, x-api-key) |
| Method Whitelist | Only safe HTTP methods allowed |
| Budget Limits | $50 single / $20 min / $100 daily |
| Payment Confirm | $10 threshold for user confirmation |

## Quick Start

### Installation

```bash
# Automated install
./scripts/install-auto.sh

# Interactive wizard
./scripts/install-wizard.sh

# Verify installation
./scripts/verify-install.sh
```

### Usage

```bash
# Initialize
setup

# Check balance
wallet status

# Make payment
pay https://api.example.com/data

# View history
wallet history

# Health check
doctor
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| AG402_API_KEY | API key for authentication | (none) |
| AG402_DAILY_LIMIT | Daily budget limit | 100.0 |
| AG402_SINGLE_TX_LIMIT | Single transaction limit | 50.0 |
| AG402_PER_MINUTE_LIMIT | Per-minute limit | 20.0 |

## Security

- Wallet file permissions: 600 (chmod required)
- All payments require confirmation for amounts >= $10
- Built-in budget limits prevent overspending
- Audit logging for all transactions

## Version

v0.1.10 - 2026-03-06
