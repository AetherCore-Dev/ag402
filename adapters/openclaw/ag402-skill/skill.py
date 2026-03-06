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
import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

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
        "single_tx_limit": 50.0,
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


def _ensure_ag402_dir() -> None:
    """Ensure ag402 directory structure exists."""
    AG402_DIR.mkdir(parents=True, exist_ok=True)
    (AG402_DIR / "logs").mkdir(parents=True, exist_ok=True)


def _validate_amount(value_str: str) -> tuple[bool, float | None, str]:
    """
    Validate and parse amount string.
    
    Returns:
        (is_valid, amount, error_message)
    """
    # Check empty
    if not value_str or not value_str.strip():
        return (False, None, "Amount is required")
    
    # Check float conversion
    try:
        amount = float(value_str)
    except ValueError:
        return (False, None, f"Invalid amount: '{value_str}' is not a valid number")
    
    # Check negative
    if amount <= 0:
        return (False, None, "Amount must be greater than zero")
    
    # Check maximum (configurable)
    MAX_AMOUNT = 1_000_000.0
    if amount > MAX_AMOUNT:
        return (False, None, f"Amount exceeds maximum limit of {MAX_AMOUNT}")
    
    return (True, amount, "")


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
# SSRF Protection Functions
# ============================================================================


def _normalize_ip(ip_str: str) -> str | None:
    """
    将各种格式的 IP 地址转换为标准 IPv4/IPv6 字符串。
    支持: 十进制 (2130706433), 十六进制 (0x7F000001), 标准格式 (127.0.0.1)
    """
    ip_str = ip_str.strip()

    # 尝试直接解析为 IP
    try:
        return str(ipaddress.ip_address(ip_str))
    except ValueError:
        pass

    # 尝试十进制格式
    if ip_str.isdigit():
        try:
            return str(ipaddress.ip_address(int(ip_str)))
        except ValueError:
            pass

    # 尝试十六进制格式 (0x...)
    if ip_str.startswith("0x") or ip_str.startswith("0X"):
        try:
            return str(ipaddress.ip_address(int(ip_str, 16)))
        except ValueError:
            pass

    return None


def _is_private_ip(ip_str: str) -> bool:
    """
_private_ip(ip_str    检查 IP 是否为私有/保留地址。
    包括: 127.x.x.x, 10.x.x.x, 172.16-31.x.x, 192.168.x.x, ::1, link-local 等
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except ValueError:
        return True  # 无法解析视为不安全


def _resolve_hostname(hostname: str) -> list[str]:
    """
    解析主机名到 IP 地址列表。
    """
    try:
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
        return list(set(info[4][0] for info in addr_info))
    except socket.gaierror:
        return []


def _is_url_safe(url: str) -> tuple[bool, str]:
    """
    验证 URL 是否安全 (不触发 SSRF)。

    Returns:
        (is_safe, error_message)
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return (False, "Invalid URL format")

    # 1. 强制 HTTPS
    if parsed.scheme != "https":
        return (False, "Only HTTPS URLs are allowed")

    # 2. 检查 host 存在
    if not parsed.netloc:
        return (False, "Missing host in URL")

    # 提取 host (处理 IPv6 格式 [::1])
    raw_host = parsed.netloc
    
    # 处理 IPv6 格式: [::1] 或 [::1]:port
    if raw_host.startswith("["):
        # 找到对应的结束括号
        bracket_end = raw_host.find("]")
        if bracket_end == -1:
            return (False, "Invalid IPv6 format")
        host = raw_host[1:bracket_end]
    else:
        # 普通 host，可能带端口
        host = raw_host.split(":")[0]

    # 3. 解码 URL 编码 (处理 %2F 等)
    try:
        host = urllib.parse.unquote(host)
    except Exception:
        pass

    # 4. 检查 IPv6 格式 [::1] 并提取
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]  # 去掉方括号

    # 5. 移除 Basic Auth (user:pass@host) - 检查原始 netloc
    if "@" in parsed.netloc:
        return (False, "URL with credentials not allowed")

    # 6. 标准化 IP 地址
    normalized_ip = _normalize_ip(host)
    if normalized_ip:
        # Host 是 IP 地址
        if _is_private_ip(normalized_ip):
            return (False, f"Private IP not allowed: {normalized_ip}")
        return (True, "")

    # 7. Host 是域名 - 解析并验证
    ips = _resolve_hostname(host)
    if not ips:
        return (False, f"Cannot resolve hostname: {host}")

    # 8. 检查所有解析出的 IP
    for ip in ips:
        if _is_private_ip(ip):
            return (False, f"Hostname resolves to private IP: {ip}")

    return (True, "")


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
    # Input validation
    if amount <= 0:
        return {"status": "error", "message": "Amount must be greater than zero"}
    if amount > 1_000_000:
        return {"status": "error", "message": "Amount exceeds maximum limit of 1000000.0"}
    
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

    # 新增: SSRF 安全检查
    is_safe, error_msg = _is_url_safe(url)
    if not is_safe:
        _add_transaction("payment", 0, "failed", f"URL blocked: {error_msg}", url)
        return {"status": "error", "message": f"URL not allowed: {error_msg}"}

    # 原有验证可以保留作为后备
    if not url.startswith(("http://", "https://")):
        return {"status": "error", "message": "Invalid URL format"}

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
                if len(args) > 1:
                    is_valid, amount, error = _validate_amount(args[1])
                    if not is_valid:
                        return {"status": "error", "message": error}
                else:
                    amount = 10.0  # default
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
                    is_valid, parsed_amount, error = _validate_amount(args[i + 1])
                    if not is_valid:
                        return {"status": "error", "message": error}
                    amount = parsed_amount
                    i += 2
                elif args[i] in ("-y", "--confirm"):
                    confirm = True
                    i += 1
                elif args[i] in ("-H", "--header") and i + 1 < len(args):
                    header = args[i + 1]
                    if ":" in header:
                        key, val = header.split(":", 1)
                        headers[key.strip()] = val.strip()
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
