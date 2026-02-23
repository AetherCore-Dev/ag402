"""
Interactive setup wizard for Ag402.

Guides developers through first-time configuration with a step-by-step
terminal UI. Handles role selection (consumer/provider/both), encryption,
budget limits, and test-fund deposit.

Design principles:
- Even test mode walks through the full encryption flow (security perception)
- No manual env var editing required — everything saved to ~/.ag402/.env
- Friendly, non-technical language throughout
"""

from __future__ import annotations

import getpass
import os
import sys
import time
import uuid

from ag402_core.terminal import (
    bold,
    cyan,
    dim,
    green,
    red,
    yellow,
)

# ─── Input helpers ───────────────────────────────────────────────────


def _prompt_choice(prompt: str, options: list[str], default: int = 1) -> int:
    """Prompt user to choose from numbered options. Returns 1-based index."""
    while True:
        for i, opt in enumerate(options, 1):
            marker = cyan(f"[{i}]")
            print(f"  {marker} {opt}")
        print()
        raw = input("  > ").strip()
        if not raw:
            return default
        try:
            choice = int(raw)
            if 1 <= choice <= len(options):
                return choice
        except ValueError:
            pass
        print(f"  {red('✗')} Please enter a number between 1-{len(options)}\n")


def _prompt_password(prompt: str, confirm: bool = True) -> str:
    """Prompt for a password with optional confirmation."""
    while True:
        pw = getpass.getpass(f"  {prompt}: ")
        if len(pw) < 8:
            print(f"  {red('✗')} Password must be at least 8 characters\n")
            continue
        if not confirm:
            return pw
        pw2 = getpass.getpass("  Confirm password: ")
        if pw == pw2:
            return pw
        print(f"  {red('✗')} Passwords do not match, please try again\n")


def _prompt_input(prompt: str, default: str = "") -> str:
    """Prompt for text input with optional default."""
    suffix = f" [{default}]" if default else ""
    raw = input(f"  {prompt}{suffix}: ").strip()
    return raw if raw else default


def _progress_bar(label: str, duration: float = 1.0, width: int = 20) -> None:
    """Show a fake progress bar for perceived security/work."""
    sys.stdout.write(f"  {label} ")
    sys.stdout.flush()
    for _i in range(width):
        time.sleep(duration / width)
        sys.stdout.write("█")
        sys.stdout.flush()
    print(f" {green('✓')}")


# ─── Setup wizard ────────────────────────────────────────────────────


class SetupResult:
    """Collects all data from the setup wizard."""

    def __init__(self) -> None:
        self.role: str = "consumer"  # consumer | provider | both
        self.mode: str = "test"  # test | production
        self.password: str = ""
        self.private_key: str = ""
        self.daily_limit: float = 10.0
        self.single_tx_limit: float = 5.0
        self.per_minute_limit: float = 2.0
        self.per_minute_count: int = 5
        # Provider-specific
        self.receive_address: str = ""
        self.api_price: str = "0.02"
        self.target_api_url: str = ""


def run_setup_wizard() -> SetupResult:
    """Run the interactive setup wizard. Returns a SetupResult.

    This is a synchronous function (terminal I/O is blocking).
    """
    result = SetupResult()

    _print_setup_banner()

    # ── Step 1: Role selection ──
    _print_step(1, 5, "What do you want to do?")
    role_choice = _prompt_choice("", [
        "🛒 Consumer — My Agent needs to call paid APIs (buy services)",
        "💰 Service Provider — I have an API and want to charge per call (sell services)",
        "🔄 Both — Consumer and provider",
    ])
    result.role = {1: "consumer", 2: "provider", 3: "both"}[role_choice]
    role_label = {1: "Consumer", 2: "Service Provider", 3: "Both"}[role_choice]
    print(f"  {green('✓')} Selected: {role_label}")
    print()

    # ── Step 2: Mode selection ──
    _print_step(2, 5, "Run mode")
    mode_choice = _prompt_choice("", [
        "🧪 Test mode (recommended for beginners) — virtual funds, safe to experiment",
        "🚀 Production mode — real Solana USDC",
    ])
    result.mode = "test" if mode_choice == 1 else "production"
    mode_label = "Test mode" if mode_choice == 1 else "Production mode"
    print(f"  {green('✓')} Selected: {mode_label}")
    print()

    # ── Step 3: Wallet / Key setup ──
    if result.role in ("consumer", "both"):
        _print_step(3, 5, "Wallet configuration")
        _setup_wallet(result)
    elif result.role == "provider":
        _print_step(3, 5, "Payment receiving setup")
        _setup_provider(result)

    # ── Step 4: Budget limits ──
    if result.role in ("consumer", "both"):
        _print_step(4, 5, "Safety limits")
        _setup_budget(result)
    else:
        _print_step(4, 5, "Gateway configuration")
        _setup_gateway_config(result)

    # ── Step 5: Save & finish ──
    _print_step(5, 5, "Save configuration")
    _save_configuration(result)

    _print_completion(result)
    return result


# ─── Step implementations ────────────────────────────────────────────


def _setup_wallet(result: SetupResult) -> None:
    """Configure wallet (both test and production modes)."""
    if result.mode == "test":
        # Generate mock private key
        mock_key = f"test_key_{uuid.uuid4().hex}"
        result.private_key = mock_key
        print(f"  Generating test key pair... {green('✓')}")
    else:
        # Production: user provides real private key
        print("  Please enter your Solana private key (base58 encoded):")
        print(f"  {dim('(Private key will not be shown on screen)')}")
        result.private_key = getpass.getpass("  Private key: ")
        if not result.private_key.strip():
            print(f"  {red('✗')} No private key provided, cannot continue")
            raise SystemExit(1)
        print(f"  {green('✓')} Private key received")

    print()
    print(f"  🔐 {bold('Encryption Protection')}")
    result.password = _prompt_password("Set wallet password (to encrypt private key)")
    print()

    # Encrypt private key (real encryption, even in test mode)
    try:
        from ag402_core.security.wallet_encryption import (
            encrypt_private_key,
            save_encrypted_wallet,
        )

        _progress_bar("Encrypting key (PBKDF2 480K rounds + AES)", duration=2.0)

        encrypted = encrypt_private_key(result.password, result.private_key)
        wallet_path = os.path.expanduser("~/.ag402/wallet.key")
        save_encrypted_wallet(wallet_path, encrypted)

        print(f"  {green('✓')} Private key encrypted and saved: {dim(wallet_path)}")
        print(f"  {green('✓')} File permissions: owner-only (600)")
    except ImportError:
        print(f"  {yellow('⚠')} cryptography not installed, skipping encryption step")
        print(f"  {dim('  Run: pip install cryptography')}")
    print()


def _setup_provider(result: SetupResult) -> None:
    """Configure provider-specific settings."""
    result.receive_address = _prompt_input(
        "Your Solana USDC receiving address",
        default="(skip for test mode)" if result.mode == "test" else "",
    )
    if result.receive_address == "(skip for test mode)":
        # Generate a valid Solana base58 test address (no 0, O, I, l)
        import random
        _b58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        result.receive_address = "Test" + "".join(random.choices(_b58, k=40))
        print(f"  {green('✓')} Using test receiving address")
    else:
        print(f"  {green('✓')} Receiving address set")

    result.api_price = _prompt_input("Price per API call (USDC)", default="0.02")
    print(f"  {green('✓')} Pricing: ${result.api_price} USDC/call")

    result.target_api_url = _prompt_input("Your API URL", default="http://localhost:8000")
    print(f"  {green('✓')} API URL: {result.target_api_url}")
    print()


def _setup_budget(result: SetupResult) -> None:
    """Configure budget limits."""
    print("  Use recommended safety limits?")
    print(f"  • Daily limit:     ${result.daily_limit:.2f} {dim('(hard ceiling: $1,000)')}")
    print(f"  • Single TX limit: ${result.single_tx_limit:.2f}")
    print(f"  • Per minute:      ${result.per_minute_limit:.2f} / {result.per_minute_count} txns")
    print()
    choice = _prompt_choice("", [
        f"{green('✓')} Use recommended values (suitable for most use cases)",
        "Customize limits",
    ])
    if choice == 2:
        raw = _prompt_input("Daily limit ($)", default=str(result.daily_limit))
        result.daily_limit = min(float(raw), 1000.0)
        raw = _prompt_input("Single TX limit ($)", default=str(result.single_tx_limit))
        result.single_tx_limit = min(float(raw), 5.0)
        raw = _prompt_input("Per-minute amount limit ($)", default=str(result.per_minute_limit))
        result.per_minute_limit = min(float(raw), 10.0)
        raw = _prompt_input("Per-minute TX count limit", default=str(result.per_minute_count))
        result.per_minute_count = min(int(raw), 50)
    print(f"  {green('✓')} Safety limits configured")
    print()


def _setup_gateway_config(result: SetupResult) -> None:
    """Minimal gateway config for pure providers."""
    print("  Gateway will start on default port 4020")
    print(f"  {green('✓')} Using default gateway configuration")
    print()


def _save_configuration(result: SetupResult) -> None:
    """Save all configuration to ~/.ag402/.env and initialize wallet DB."""
    from ag402_core.env_manager import save_env_file

    env_entries: dict[str, str] = {
        "X402_MODE": result.mode,
        "AG402_ROLE": result.role,
    }

    # Consumer/both settings
    if result.role in ("consumer", "both"):
        env_entries.update({
            "X402_DAILY_LIMIT": str(result.daily_limit),
            "X402_SINGLE_TX_LIMIT": str(result.single_tx_limit),
            "X402_PER_MINUTE_LIMIT": str(result.per_minute_limit),
            "X402_PER_MINUTE_COUNT": str(result.per_minute_count),
        })

    # Provider/both settings
    if result.role in ("provider", "both"):
        env_entries.update({
            "AG402_RECEIVE_ADDRESS": result.receive_address,
            "AG402_API_PRICE": result.api_price,
            "AG402_TARGET_API": result.target_api_url,
        })

    # Network settings for production
    if result.mode == "production":
        env_entries["SOLANA_RPC_URL"] = "https://api.mainnet-beta.solana.com"
    else:
        env_entries["SOLANA_RPC_URL"] = "https://api.devnet.solana.com"

    save_env_file(env_entries, merge=False)
    print(f"  {green('✓')} Configuration saved: {dim('~/.ag402/.env')}")


def _print_setup_banner() -> None:
    print()
    print(bold("  ╔══════════════════════════════════════════════════════╗"))
    print(bold("  ║") + cyan("  Ag402 Setup Wizard") + "                                " + bold("║"))
    print(bold("  ║") + "  Payment Engine for AI Agents — Powered by Open402    " + bold("║"))
    print(bold("  ╚══════════════════════════════════════════════════════╝"))
    print()


def _print_step(current: int, total: int, title: str) -> None:
    print(f"  {bold(f'Step {current}/{total}')}: {title}")
    print("  " + "─" * 40)


def _print_completion(result: SetupResult) -> None:
    print()
    print("  ═" * 28)
    print(f"  🎉 {bold('Ag402 is ready!')}")
    print()

    if result.role in ("consumer", "both"):
        print("  ┌─────────── Next Steps ────────────────────────┐")
        print("  │                                                │")
        print("  │  Try it out:                                   │")
        print(f"  │  $ {cyan('ag402 demo')}           Run a live demo     │")
        print("  │                                                │")
        print("  │  Integrate your Agent:                         │")
        print(f"  │  $ {cyan('ag402 run -- python my_agent.py')}         │")
        print("  │                                                │")
        print("  │  Learn more:                                   │")
        print(f"  │  $ {cyan('ag402 help')}           View all commands   │")
        print("  │                                                │")
        print("  └────────────────────────────────────────────────┘")

    if result.role in ("provider", "both"):
        print()
        print("  ┌─────────── Service Provider ──────────────────┐")
        print("  │                                                │")
        print("  │  Start payment gateway:                        │")
        print(f"  │  $ {cyan('ag402 serve')}                              │")
        print("  │                                                │")
        print("  │  Verify (in another terminal):                 │")
        print(f"  │  $ {cyan('ag402 pay http://127.0.0.1:4020/')}        │")
        print(f"  │  {dim('→ Auto-pays and displays the result')}              │")
        print("  │                                                │")
        print("  └────────────────────────────────────────────────┘")

    print()


async def init_wallet_after_setup(result: SetupResult) -> None:
    """Initialize wallet DB and deposit test funds after setup completes."""
    from ag402_core.wallet.agent_wallet import AgentWallet

    db_path = os.path.expanduser("~/.ag402/wallet.db")
    wallet = AgentWallet(db_path=db_path)
    await wallet.init_db()

    if result.mode == "test" and result.role in ("consumer", "both"):
        balance = await wallet.get_balance()
        if balance == 0:
            await wallet.deposit(100.0, note="Setup wizard — test funds")
            print(f"  {green('✓')} Deposited $100.00 test funds")

    await wallet.close()
