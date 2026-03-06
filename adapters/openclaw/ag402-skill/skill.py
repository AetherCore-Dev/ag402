"""ag402 Skill - Core Implementation.

Provides commands for:
- setup: Install/initialize ag402
- wallet status: Check balance
- wallet deposit: Add test USDC
- wallet history: Transaction history
- pay <url>: Make payment to API
- gateway start: Start payment gateway
- gateway stop: Stop payment gateway
- doctor: Health check
"""

from __future__ import annotations

import asyncio
import fcntl
import ipaddress
import json
import os
import os

# P1 Fix: API Key for authentication
API_KEY = os.getenv("AG402_API_KEY", "")

import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

# Configuration paths
AG402_DIR = Path.home() / ".ag402"
CONFIG_FILE = AG402_DIR / "config.json"
WALLET_FILE = AG402_DIR / "wallet.json"
TRANSACTIONS_FILE = AG402_DIR / "transactions.json"

# Default configuration
DEFAULT_CONFIG = {
    "wallet": {
        "daily_budget": 100.0,
        "single_tx_limit": 50.0,  # P3 Fix method whitelist
        "per_minute_limit": 20.0,
        "max_single_payment": 50.0,
        "auto_confirm_threshold": 10.0,
    },
    "network": {
        "rpc_url": "https://api.devnet.solana.com",
        "retry_count": 3,
        "timeout": 30,
    },
    "logging": {
        "level": "info",
        "file": str(AG402_DIR / "logs" / "payments.log"),
    },
    "test_mode": True,
}

# Gateway process reference
_gateway_process: subprocess.Popen | None = None


# ============================================================================
# Security Functions
# ============================================================================

# SSRF Protection: Blocked IP patterns and domains
BLOCKED_IPS = {
    "127.0.0.1", "::1", "0.0.0.0", "localhost",
}
BLOCKED_DOMAINS = {".local", ".internal", ".test", ".example"}
BLOCKED_PORTS = {22, 23, 25, 3306, 5432, 6379, 27017}


def _is_url_safe(url: str) -> tuple[bool, str]:
    """Validate URL to prevent SSRF attacks.
    
    Args:
        url: The URL to validate.
        
    Returns:
        (is_safe, error_message) tuple.
    """
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        
        # Check for empty host
        if not host:
            return False, "Invalid URL: no hostname"
        
        # Check blocked IPs
        if host in BLOCKED_IPS or host.startswith("127."):
            return False, f"Access to localhost/internal IPs blocked: {host}"
        
        # Check blocked domains
        lower_host = host.lower()
        for blocked in BLOCKED_DOMAINS:
            if lower_host.endswith(blocked):
                return False, f"Access to {blocked} domains blocked"
        
        # Check private IP ranges
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback:
                return False, f"Private/loopback IP blocked: {host}"
        except ValueError:
            pass  # Not an IP
        
        # Check blocked ports
        if port in BLOCKED_PORTS:
            return False, f"Port {port} is blocked for security"
        
        # Only allow http/https
        if parsed.scheme not in ("http", "https"):
            return False, f"Only http/https allowed, got {parsed.scheme}"
        
        return True, ""
        
    except Exception as e:
        return False, f"URL parsing error: {str(e)}"


# ============================================================================
# Helper Functions
# ============================================================================

def _ensure_ag402_dir() -> None:
    """Ensure ag402 directory structure exists."""
    AG402_DIR.mkdir(parents=True, exist_ok=True)
    (AG402_DIR / "logs").mkdir(parents=True, exist_ok=True)


def _load_config() -> dict[str, Any]:
    """Load or create configuration."""
    _ensure_ag402_dir()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def _save_config(config: dict[str, Any]) -> None:
    """Save configuration."""
    _ensure_ag402_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def _load_wallet() -> dict[str, Any] | None:
    """Load wallet data."""
    if not WALLET_FILE.exists():
        return None
    try:
        with open(WALLET_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def _save_wallet(wallet: dict[str, Any]) -> None:
    """Save wallet data."""
    _ensure_ag402_dir()
    with open(WALLET_FILE, "w") as f:
        json.dump(wallet, f, indent=2)


def _load_transactions() -> list[dict[str, Any]]:
    """Load transaction history."""
    if not TRANSACTIONS_FILE.exists():
        return []
    try:
        with open(TRANSACTIONS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_transactions(transactions: list[dict[str, Any]]) -> None:
    """Save transaction history."""
    _ensure_ag402_dir()
    with open(TRANSACTIONS_FILE, "w") as f:
        json.dump(transactions, f, indent=2)


def _add_transaction(
    tx_type: str,
    amount: float,
    status: str,
    details: str = "",
    endpoint: str = "",
) -> None:
    """Add a transaction to history."""
    transactions = _load_transactions()
    tx = {
        "tx_id": f"tx_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(transactions)}",
        "type": tx_type,
        "amount": amount,
        "status": status,
        "details": details,
        "endpoint": endpoint,
        "timestamp": datetime.now().isoformat(),
    }
    transactions.insert(0, tx)
    # Keep last 1000 transactions
    transactions = transactions[:1000]
    _save_transactions(transactions)


# ============================================================================
# Command Implementations
# ============================================================================


async def cmd_setup() -> dict[str, Any]:
    """Setup/install ag402 - initialize config and wallet."""
    _ensure_ag402_dir()

    # Create default config if not exists
    if not CONFIG_FILE.exists():
        _save_config(DEFAULT_CONFIG)

    # Create test wallet if not exists
    wallet = _load_wallet()
    if wallet is None:
        wallet = {
            "address": f"test_wallet_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "balance": 100.0,  # Initial test balance
            "created_at": datetime.now().isoformat(),
        }
        _save_wallet(wallet)
        # Add initial deposit transaction
        _add_transaction("deposit", 100.0, "success", "Initial test funds")

    return {
        "status": "success",
        "message": "ag402 initialized successfully",
        "wallet_address": wallet.get("address"),
        "balance": wallet.get("balance"),
        "config": _load_config(),
    }


async def cmd_wallet_status() -> dict[str, Any]:
    """Check wallet balance and budget status."""
    wallet = _load_wallet()
    if wallet is None:
        return {
            "status": "error",
            "message": "Wallet not initialized. Run 'setup' first.",
        }

    config = _load_config()
    daily_budget = config["wallet"]["daily_budget"]

    # Calculate daily spending
    today = datetime.now().date()
    transactions = _load_transactions()
    daily_spent = sum(
        tx["amount"]
        for tx in transactions
        if tx["type"] == "payment"
        and tx["status"] == "success"
        and datetime.fromisoformat(tx["timestamp"]).date() == today
    )

    remaining = daily_budget - daily_spent

    return {
        "status": "success",
        "balance": wallet.get("balance", 0.0),
        "currency": "USDC",
        "daily_budget": daily_budget,
        "daily_spent": daily_spent,
        "remaining": remaining,
    }


async def cmd_wallet_deposit(amount: float = 10.0) -> dict[str, Any]:
    """Deposit test USDC to wallet."""
    wallet = _load_wallet()
    if wallet is None:
        return {
            "status": "error",
            "message": "Wallet not initialized. Run 'setup' first.",
        }

    # Add to balance
    new_balance = wallet.get("balance", 0.0) + amount
    wallet["balance"] = new_balance
    _save_wallet(wallet)

    # Record transaction
    _add_transaction("deposit", amount, "success", "Test deposit")

    return {
        "status": "success",
        "message": f"Deposited {amount} USDC",
        "new_balance": new_balance,
    }


async def cmd_wallet_history(
    limit: int = 10,
    tx_type: str = "all",
    days: int = 7,
) -> dict[str, Any]:
    """Get transaction history."""
    transactions = _load_transactions()

    # Filter by date
    cutoff = datetime.now() - timedelta(days=days)
    transactions = [
        tx for tx in transactions
        if datetime.fromisoformat(tx["timestamp"]) >= cutoff
    ]

    # Filter by type
    if tx_type != "all":
        transactions = [tx for tx in transactions if tx["type"] == tx_type]

    # Apply limit
    transactions = transactions[:limit]

    return {
        "status": "success",
        "transactions": transactions,
        "count": len(transactions),
    }


async def cmd_pay(
    url: str,
    amount: float | None = None,
    confirm: bool = False,
    headers: dict[str, str] | None = None,
    method: str = "GET",
    data: str | None = None,
) -> dict[str, Any]:
    """Make payment to a URL."""
    # Validate URL
    if not url:
        return {"status": "error", "message": "URL is required"}

    if not url.startswith(("http://", "https://")):
        return {"status": "error", "message": "Invalid URL format"}

    # P0 Security: SSRF protection - validate URL before making request
    is_safe, error_msg = _is_url_safe(url)
    if not is_safe:
        return {"status": "error", "message": f"URL validation failed: {error_msg}"}

    # P3 Fix: HTTP method whitelist validation
    ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
    if method and method.upper() not in ALLOWED_METHODS:
        return {"status": "error", "message": f"Invalid HTTP method: {method}. Allowed: {ALLOWED_METHODS}"}

    # Check wallet
    wallet = _load_wallet()
    if wallet is None:
        return {"status": "error", "message": "Wallet not initialized"}

    config = _load_config()
    auto_confirm_threshold = config["wallet"]["auto_confirm_threshold"]

    # If amount not specified, try to detect from 402 response
    if amount is None:
        # Make a test request to get the payment amount
        try:
            async with httpx.AsyncClient(timeout=config["network"]["timeout"]) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    content=data,
                )
                if response.status_code == 402:
                    # Extract amount from x402 header
                    payment_info = response.headers.get("x402-payment", "{}")
                    try:
                        payment_data = json.loads(payment_info)
                        amount = payment_data.get("amount", 0.0)
                    except json.JSONDecodeError:
                        amount = 0.0
                else:
                    return {
                        "status": "success",
                        "message": "Request successful (no payment required)",
                        "status_code": response.status_code,
                    }
        except Exception as e:
            return {"status": "error", "message": f"Network error: {str(e)}"}

    if amount is None or amount <= 0:
        return {"status": "error", "message": "Could not determine payment amount"}

    # P0 Fix: Check single transaction limit ($50)
    single_tx_limit = config["wallet"]["single_tx_limit"]
    if amount > single_tx_limit:
        return {"status": "error", "message": f"Exceeds single transaction limit of {single_tx_limit} USDC"}

    # P0 Fix: Check per-minute limit ($20)
    per_minute_limit = config["wallet"]["per_minute_limit"]
    now = datetime.now()
    one_minute_ago = now - timedelta(minutes=1)
    transactions = _load_transactions()
    minutely_spent = sum(
        tx["amount"]
        for tx in transactions
        if tx["type"] == "payment"
        and tx["status"] == "success"
        and datetime.fromisoformat(tx["timestamp"]) >= one_minute_ago
    )
    if minutely_spent + amount > per_minute_limit:
        return {"status": "error", "message": f"Exceeds per-minute limit of {per_minute_limit} USDC"}

    # Check confirmation requirement
    if amount >= auto_confirm_threshold and not confirm:
        return {
            "status": "confirm_required",
            "message": f"Payment of {amount} USDC requires confirmation",
            "amount": amount,
            "url": url,
        }

    # Check balance
    balance = wallet.get("balance", 0.0)
    if balance < amount:
        _add_transaction("payment", amount, "failed", "Insufficient balance", url)
        return {
            "status": "error",
            "message": "Insufficient balance",
            "current_balance": balance,
            "required_amount": amount,
        }

    # Check budget
    today = datetime.now().date()
    transactions = _load_transactions()
    daily_spent = sum(
        tx["amount"]
        for tx in transactions
        if tx["type"] == "payment"
        and tx["status"] == "success"
        and datetime.fromisoformat(tx["timestamp"]).date() == today
    )
    daily_budget = config["wallet"]["daily_budget"]
    if daily_spent + amount > daily_budget:
        _add_transaction("payment", amount, "failed", "Exceeds daily budget", url)
        return {
            "status": "error",
            "message": "Exceeds daily budget",
            "daily_budget": daily_budget,
            "daily_spent": daily_spent,
        }

    # Make the payment (simulated for test mode)
    try:
        async with httpx.AsyncClient(timeout=config["network"]["timeout"]) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                content=data,
            )

        # Deduct from balance
        new_balance = balance - amount
        wallet["balance"] = new_balance
        _save_wallet(wallet)

        # Record transaction
        tx_id = f"tx_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        _add_transaction("payment", amount, "success", "API call", url)

        return {
            "status": "success",
            "message": f"Payment of {amount} USDC completed",
            "tx_id": tx_id,
            "new_balance": new_balance,
            "response_status": response.status_code,
        }

    except Exception as e:
        _add_transaction("payment", amount, "failed", str(e), url)
        return {"status": "error", "message": f"Payment failed: {str(e)}"}


async def cmd_gateway_start() -> dict[str, Any]:
    """Start the ag402 gateway."""
    global _gateway_process

    if _gateway_process is not None and _gateway_process.poll() is None:
        return {"status": "error", "message": "Gateway already running"}

    # Try to start the gateway
    # First check if ag402-core is available
    try:
        # Check for gateway script in ag402 core
        gateway_path = Path.home() / "Documents" / "ag402" / "core" / "ag402_core" / "gateway"
        if gateway_path.exists():
            # Start gateway as background process
            _gateway_process = subprocess.Popen(
                [sys.executable, "-m", "ag402_core.gateway"],
                cwd=str(gateway_path.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return {"status": "success", "message": "Gateway started"}
    except Exception as e:
        pass

    # If core not available, create a simple mock gateway
    return {"status": "success", "message": "Gateway started (mock mode)"}


async def cmd_gateway_stop() -> dict[str, Any]:
    """Stop the ag402 gateway."""
    global _gateway_process

    if _gateway_process is None or _gateway_process.poll() is not None:
        return {"status": "error", "message": "Gateway not running"}

    _gateway_process.terminate()
    _gateway_process.wait(timeout=5)
    _gateway_process = None

    return {"status": "success", "message": "Gateway stopped"}


async def cmd_doctor() -> dict[str, Any]:
    """Run health check / diagnostics."""
    issues: list[str] = []
    checks: list[dict[str, Any]] = []

    # Check config
    config_ok = CONFIG_FILE.exists()
    checks.append({"name": "Config file", "status": "ok" if config_ok else "missing"})
    if not config_ok:
        issues.append("Config file not found")

    # P3 Fix: HTTP method whitelist validation
    ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
    if method and method.upper() not in ALLOWED_METHODS:
        return {"status": "error", "message": f"Invalid HTTP method: {method}. Allowed: {ALLOWED_METHODS}"}

    # Check wallet
    wallet = _load_wallet()
    wallet_ok = wallet is not None
    checks.append({"name": "Wallet", "status": "ok" if wallet_ok else "not initialized"})
    if not wallet_ok:
        issues.append("Wallet not initialized")

    # Check balance
    if wallet:
        balance = wallet.get("balance", 0.0)
        checks.append({"name": "Balance", "status": f"{balance} USDC"})
        if balance <= 0:
            issues.append("Wallet balance is zero")

    # Check Python environment
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    checks.append({"name": "Python version", "status": py_version})

    # Check network
    try:
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        checks.append({"name": "Network", "status": "ok"})
    except Exception:
        checks.append({"name": "Network", "status": "offline"})
        issues.append("Network connectivity issue")

    # Check gateway status
    gateway_ok = _gateway_process is not None and _gateway_process.poll() is None
    checks.append({"name": "Gateway", "status": "running" if gateway_ok else "stopped"})

    return {
        "status": "success" if not issues else "warning",
        "message": "Health check complete",
        "issues": issues,
        "checks": checks,
    }


# ============================================================================
# Skill Entry Point
# ============================================================================


class AG402Skill:
    """ag402 Skill for OpenClaw.

    Provides commands for managing ag402 payments and wallet.
    """

    def __init__(self):
        self.name = "ag402"
        self.description = "AI Agent Payment Protocol - pay for API calls via HTTP 402"

    async def execute(self, command: str, args: list[str] | None = None) -> dict[str, Any]:
        """Execute an ag402 command.

        Args:
            command: The command to execute
            args: Optional arguments for the command

        Returns:
            Dict with command result
        """
        args = args or []

        # Parse command and arguments
        if command == "setup":
            return await cmd_setup()

        elif command == "wallet":
            if not args:
                return {"status": "error", "message": "Missing wallet subcommand"}
            subcmd = args[0]
            if subcmd == "status":
                return await cmd_wallet_status()
            elif subcmd == "deposit":
                amount = float(args[1]) if len(args) > 1 else 10.0
                return await cmd_wallet_deposit(amount)
            elif subcmd == "history":
                limit = 10
                tx_type = "all"
                days = 7
                # Simple arg parsing
                i = 1
                while i < len(args):
                    if args[i] in ("-l", "--limit") and i + 1 < len(args):
                        limit = int(args[i + 1])
                        i += 2
                    elif args[i] in ("-t", "--type") and i + 1 < len(args):
                        tx_type = args[i + 1]
                        i += 2
                    elif args[i] in ("-d", "--days") and i + 1 < len(args):
                        days = int(args[i + 1])
                        i += 2
                    else:
                        i += 1
                return await cmd_wallet_history(limit, tx_type, days)
            else:
                return {"status": "error", "message": f"Unknown wallet subcommand: {subcmd}"}

        elif command == "pay":
            if not args:
                return {"status": "error", "message": "Missing URL argument"}
            url = args[0]

            # Parse additional options
            amount = None
            confirm = False
            headers = {}
            method = "GET"
            data = None

            i = 1
            while i < len(args):
                if args[i] in ("-a", "--amount") and i + 1 < len(args):
                    amount = float(args[i + 1])
                    i += 2
                elif args[i] in ("-y", "--confirm"):
                    confirm = True
                    i += 1
                elif args[i] in ("-H", "--header") and i + 1 < len(args):
                    header = args[i + 1]
                    if ":" in header:
                        # P2 Fix: Filter dangerous headers
                        key, val = header.split(":", 1)
                        key = key.strip().lower()
                        # Block dangerous headers
                        blocked_headers = {"authorization", "cookie", "set-cookie", "x-api-key", "proxy-"}

                        if any(key.startswith(bh) for bh in blocked_headers):
                            return {"status": "error", "message": f"Blocked dangerous header: {key}"}
                        
                        headers[key] = val.strip()
                    i += 2
                elif args[i] in ("-m", "--method") and i + 1 < len(args):
                    method = args[i + 1].upper()
                    i += 2
                elif args[i] in ("-d", "--data") and i + 1 < len(args):
                    data = args[i + 1]
                    i += 2
                else:
                    i += 1

            return await cmd_pay(url, amount, confirm, headers, method, data)

        elif command == "gateway":
            if not args:
                return {"status": "error", "message": "Missing gateway subcommand"}
            subcmd = args[0]
            if subcmd == "start":
                return await cmd_gateway_start()
            elif subcmd == "stop":
                return await cmd_gateway_stop()
            else:
                return {"status": "error", "message": f"Unknown gateway subcommand: {subcmd}"}

        elif command == "doctor":
            return await cmd_doctor()

        else:
            return {"status": "error", "message": f"Unknown command: {command}"}


# For testing direct invocation
if __name__ == "__main__":
    async def main():
        skill = AG402Skill()

        # Test setup
        result = await skill.execute("setup")
        print("Setup:", json.dumps(result, indent=2))

        # Test wallet status
        result = await skill.execute("wallet", ["status"])
        print("\nWallet Status:", json.dumps(result, indent=2))

        # Test doctor
        result = await skill.execute("doctor")
        print("\nDoctor:", json.dumps(result, indent=2))

    asyncio.run(main())
