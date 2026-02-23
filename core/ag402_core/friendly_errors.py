"""
Friendly error messages — translates technical errors into human-readable
guidance with actionable next steps.

Wraps the CLI entry point to catch common exceptions and display
"what went wrong" + "what to do next" instead of raw tracebacks.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable

from ag402_core.terminal import red, yellow

# ─── Error pattern registry ─────────────────────────────────────────

_ERROR_HANDLERS: list[tuple[type, str, str]] = []


def _register(exc_type: type, message: str, hint: str) -> None:
    _ERROR_HANDLERS.append((exc_type, message, hint))


# FileNotFoundError for wallet
_register(
    FileNotFoundError,
    "Wallet file not found",
    "Run `ag402 setup` to create a wallet",
)


def _match_error(exc: BaseException) -> tuple[str, str] | None:
    """Match an exception to a friendly message + hint."""
    exc_str = str(exc).lower()

    # Special patterns by message content
    if isinstance(exc, FileNotFoundError):
        if "wallet" in exc_str or ".ag402" in exc_str:
            return "Wallet file not found", "Run `ag402 setup` to create a wallet"
        return None

    if isinstance(exc, ConnectionError) or "connection" in exc_str:
        if "solana" in exc_str or "rpc" in exc_str:
            return (
                "Cannot connect to Solana network",
                "Check your network connection, or run `ag402 doctor` to diagnose",
            )
        return (
            "Network connection failed",
            "Check your network connection, or run `ag402 doctor` to diagnose",
        )

    if isinstance(exc, PermissionError):
        return (
            "Permission denied",
            "Check file permissions for ~/.ag402/ directory",
        )

    if isinstance(exc, ImportError):
        module = str(exc).split("'")[1] if "'" in str(exc) else str(exc)
        return (
            f"Missing dependency: {module}",
            f"Run `pip install ag402-core` or `pip install {module}`",
        )

    if "insufficient balance" in exc_str or "balance" in exc_str and "low" in exc_str:
        return (
            "Insufficient wallet balance",
            "Run `ag402 balance` to check balance, or run `ag402 setup` to add test funds",
        )

    if "daily limit" in exc_str or "daily_limit" in exc_str:
        return (
            "Daily spending limit reached",
            "Run `ag402 config` to view current limits, or modify X402_DAILY_LIMIT",
        )

    if "password" in exc_str and ("wrong" in exc_str or "invalid" in exc_str):
        return (
            "Incorrect wallet password",
            "Verify your password, or set it via AG402_UNLOCK_PASSWORD environment variable",
        )

    return None


def friendly_cli_wrapper(main_func: Callable) -> Callable:
    """Wrap a CLI main() function with friendly error handling.

    Usage::

        @friendly_cli_wrapper
        def main():
            ...
    """
    def wrapper(*args, **kwargs):
        try:
            return main_func(*args, **kwargs)
        except KeyboardInterrupt:
            print(f"\n  {yellow('⚠')} Operation cancelled")
            sys.exit(130)
        except SystemExit:
            raise  # Don't catch SystemExit
        except Exception as exc:
            matched = _match_error(exc)
            if matched:
                message, hint = matched
                print()
                print(f"  {red('✗')} {message}")
                print(f"  → {hint}")
                print()
            else:
                # Unknown error: show a condensed traceback
                print()
                print(f"  {red('✗')} Unexpected error: {type(exc).__name__}: {exc}")
                print("  → Run `ag402 doctor` to diagnose")
                print("  → If the issue persists, please file an issue on GitHub")
                print()

                # Show traceback if DEBUG
                if os.getenv("AG402_DEBUG"):
                    import traceback
                    traceback.print_exc()

            sys.exit(1)

    return wrapper
