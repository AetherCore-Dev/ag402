"""CLI entry point for ag402-core.

Provides a rich set of commands for wallet management, status monitoring,
transaction inspection, health diagnostics, and demo execution.
Cross-platform compatible (macOS, Linux, Windows).

Ag402: Powered by the Open402 standard.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from ag402_core.terminal import (
    _c,
)
from ag402_core.terminal import (
    bold as _bold,
)
from ag402_core.terminal import (
    cyan as _cyan,
)
from ag402_core.terminal import (
    dim as _dim,
)
from ag402_core.terminal import (
    green as _green,
)
from ag402_core.terminal import (
    red as _red,
)
from ag402_core.terminal import (
    yellow as _yellow,
)

_DEFAULT_DB = str(Path.home() / ".ag402" / "wallet.db")
from ag402_core import __version__ as _VERSION

# ─── CLI-specific display helpers ────────────────────────────────────


def _bar(used: float, total: float, width: int = 20) -> str:
    """Render a progress bar."""
    used, total = float(used), float(total)
    if total <= 0:
        return " " * width
    ratio = min(used / total, 1.0)
    filled = int(ratio * width)
    empty = width - filled
    pct = ratio * 100
    color = "32" if pct < 60 else ("33" if pct < 85 else "31")
    bar_str = "█" * filled + "░" * empty
    return _c(color, bar_str) + f" {pct:.0f}%"


def _short_addr(addr: str, max_len: int = 20) -> str:
    """Shorten a blockchain address for display."""
    if not addr or len(addr) <= max_len:
        return addr or "-"
    return addr[:8] + "..." + addr[-8:]


def _time_ago(ts: float) -> str:
    """Human-readable time-ago string."""
    diff = time.time() - ts
    if diff < 60:
        return f"{diff:.0f}s ago"
    if diff < 3600:
        return f"{diff / 60:.0f}m ago"
    if diff < 86400:
        return f"{diff / 3600:.0f}h ago"
    return f"{diff / 86400:.0f}d ago"


# ─── Parser ──────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser (exposed for testing)."""
    parser = argparse.ArgumentParser(
        prog="ag402",
        description="Ag402 — Payment Engine for AI Agents (Powered by the Open402 standard)",
        add_help=False,  # We provide our own 'help' subcommand
    )
    parser.add_argument("--version", action="version", version=f"ag402 {_VERSION}")
    parser.add_argument("-h", "--help", action="store_true", dest="show_help",
                        help="Show help and exit")
    sub = parser.add_subparsers(dest="command")

    # --- setup (NEW — interactive wizard) ---
    sub.add_parser("setup", help="Interactive setup wizard (recommended for first use)")

    # --- init (legacy, still works) ---
    init_p = sub.add_parser("init", help="Initialize wallet + deposit test funds")
    init_p.add_argument("--db", default=_DEFAULT_DB, help="Wallet database path")

    # --- run (NEW — launch Agent with payment injection) ---
    run_p = sub.add_parser("run", help="Launch an Agent with automatic x402 payment")
    run_p.add_argument("target", nargs="?", default=None,
                       help="Target command, or use '--' prefix for arbitrary commands")
    run_p.add_argument("extra_args", nargs=argparse.REMAINDER, default=[],
                       help="Arguments to pass to the target command")

    # --- env (NEW — .env file management) ---
    env_p = sub.add_parser("env", help="Manage configuration (.env file)")
    env_sub = env_p.add_subparsers(dest="env_action")
    env_sub.add_parser("init", help="Create .env file interactively")
    env_sub.add_parser("show", help="Show current configuration and sources")
    env_set_p = env_sub.add_parser("set", help="Set a single config value")
    env_set_p.add_argument("key", help="Config key (e.g. X402_DAILY_LIMIT)")
    env_set_p.add_argument("value", help="Config value")

    # --- mcp (NEW — MCP client server for Claude Code / Cursor / OpenClaw) ---
    mcp_p = sub.add_parser("mcp", help="Start MCP payment server (for Claude Code / Cursor / OpenClaw)")
    mcp_p.add_argument("--sse", action="store_true", help="Use SSE transport instead of stdio")
    mcp_p.add_argument("--port", type=int, default=14021, help="SSE server port (default: 14021)")
    mcp_p.add_argument("--host", type=str, default="127.0.0.1", help="SSE server host (default: 127.0.0.1)")

    # --- mcp-config (NEW — generate MCP configuration for AI tools) ---
    mcp_cfg_p = sub.add_parser("mcp-config", help="Generate MCP config for Claude Code / Cursor / OpenClaw")
    mcp_cfg_p.add_argument("tool", nargs="?", default=None,
                           help="Target tool: claude, cursor, openclaw (default: show all)")

    # --- install (NEW — one-command MCP setup for AI tools) ---
    install_p = sub.add_parser("install", help="One-command MCP setup for AI tools (zero config)")
    install_p.add_argument("tool", help="Target tool: claude-code, cursor, openclaw")
    install_p.add_argument("--global", dest="global_scope", action="store_true",
                           help="Install globally instead of project-local")

    # --- serve (NEW — provider mode gateway) ---
    serve_p = sub.add_parser("serve", help="Start payment gateway (provider mode)")
    serve_p.add_argument("--target", default="", help="Backend API URL")
    serve_p.add_argument("--port", type=int, default=4020, help="Gateway port")
    serve_p.add_argument("--price", default="0.02", help="Price per API call (USDC)")
    serve_p.add_argument("--address", default="", help="Receiving wallet address")

    # --- upgrade (NEW — test → production migration) ---
    sub.add_parser("upgrade", help="Upgrade from test mode to production")

    # --- help (NEW — beautiful help page) ---
    sub.add_parser("help", help="Show all commands with descriptions")

    # --- status ---
    sub.add_parser("status", help="Show comprehensive status dashboard")

    # --- balance ---
    bal_p = sub.add_parser("balance", help="Check wallet balance and budget usage")
    bal_p.add_argument("--db", default=_DEFAULT_DB, help="Wallet database path")

    # --- history ---
    hist_p = sub.add_parser("history", help="Show transaction history with stats")
    hist_p.add_argument("--db", default=_DEFAULT_DB, help="Wallet database path")
    hist_p.add_argument("-n", "--limit", type=int, default=20, help="Number of transactions")
    hist_p.add_argument(
        "--format", choices=["table", "json", "csv"], default="table",
        help="Output format (default: table)",
    )
    hist_p.add_argument(
        "--output", default="", help="Output file path (for json/csv export)",
    )

    # --- tx ---
    tx_p = sub.add_parser("tx", help="View single transaction details")
    tx_p.add_argument("tx_id", help="Transaction ID (or prefix)")
    tx_p.add_argument("--db", default=_DEFAULT_DB, help="Wallet database path")

    # --- config ---
    sub.add_parser("config", help="Show safety limits and configuration")

    # --- info ---
    sub.add_parser("info", help="Show protocol and version info")

    # --- doctor ---
    sub.add_parser("doctor", help="Run environment health checks")

    # --- demo ---
    sub.add_parser("demo", help="Run E2E payment demo (test mode, zero config)")

    # --- pay (NEW — single request with auto-payment) ---
    pay_p = sub.add_parser("pay", help="Send a single request with auto-payment")
    pay_p.add_argument("url", help="Target URL (e.g. http://127.0.0.1:4020/weather?city=Tokyo)")
    pay_p.add_argument("-X", "--method", default="GET", help="HTTP method (default: GET)")
    pay_p.add_argument("--db", default=_DEFAULT_DB, help="Wallet database path")

    # --- export ---
    exp_p = sub.add_parser("export", help="Export transaction history to file")
    exp_p.add_argument("--db", default=_DEFAULT_DB, help="Wallet database path")
    exp_p.add_argument(
        "--format", choices=["json", "csv"], default="json",
        help="Export format (default: json)",
    )
    exp_p.add_argument(
        "--output", default="", help="Output file path (default: ag402_history.<fmt>)",
    )

    return parser


# ─── Main dispatch ───────────────────────────────────────────────────────

def main() -> None:
    from ag402_core.friendly_errors import friendly_cli_wrapper

    @friendly_cli_wrapper
    def _main_inner():
        parser = _build_parser()
        args = parser.parse_args()

        if getattr(args, "show_help", False) or args.command is None:
            if args.command is None:
                _print_banner()
                _cmd_help()
            else:
                _cmd_help()
            sys.exit(0)

        dispatch = {
            "setup": lambda: _cmd_setup(),
            "init": lambda: asyncio.run(_cmd_init(args.db)),
            "run": lambda: _cmd_run(args),
            "env": lambda: _cmd_env(args),
            "mcp": lambda: _cmd_mcp(args),
            "mcp-config": lambda: _cmd_mcp_config(args),
            "install": lambda: _cmd_install(args),
            "serve": lambda: _cmd_serve(args),
            "upgrade": lambda: _cmd_upgrade(),
            "help": lambda: _cmd_help(),
            "status": lambda: asyncio.run(_cmd_status()),
            "balance": lambda: asyncio.run(_cmd_balance(args.db)),
            "history": lambda: asyncio.run(_cmd_history(args.db, args.limit, args.format, args.output)),
            "tx": lambda: asyncio.run(_cmd_tx(args.db, args.tx_id)),
            "config": _cmd_config,
            "info": _cmd_info,
            "doctor": _cmd_doctor,
            "demo": lambda: asyncio.run(_cmd_demo()),
            "pay": lambda: asyncio.run(_cmd_pay(args.url, args.method, args.db)),
            "export": lambda: asyncio.run(_cmd_export(args.db, args.format, args.output)),
        }

        handler = dispatch.get(args.command)
        if handler:
            handler()
        else:
            _cmd_help()

    _main_inner()


# ─── Banner ──────────────────────────────────────────────────────────────

def _print_banner() -> None:
    print()
    print(_bold("  ╔══════════════════════════════════════════════════════╗"))
    print(_bold("  ║") + _cyan("  Ag402") + f" v{_VERSION}" + " — Payment Engine for AI Agents  " + _bold("║"))
    print(_bold("  ║") + "  Powered by the Open402 standard                    " + _bold("║"))
    print(_bold("  ╚══════════════════════════════════════════════════════╝"))
    print()


# ─── NEW Commands ────────────────────────────────────────────────────────


def _cmd_help() -> None:
    """Beautiful help page — categorized with usage hints."""
    print()
    print(f"  {_bold('Ag402')} v{_VERSION} — Payment Engine for AI Agents")
    print("  " + "─" * 50)
    print()
    print(f"  {_bold('Quick Start')}")
    print(f"    {'setup':<24s} Interactive setup wizard (recommended for first use)")
    print(f"    {'demo':<24s} Run a full payment demo")
    print(f"    {'pay <url>':<24s} Send a single request with auto-payment")
    print()
    print(f"  {_bold('Agent Integration')}")
    print(f"    {'run <command>':<24s} Launch an Agent with payment injection")
    print(f"    {'run -- python ...':<24s} Any Python script or agent")
    print(f"    {'mcp':<24s} Start MCP payment server (Claude Code / Cursor / OpenClaw)")
    print(f"    {'install <tool>':<24s} One-command MCP setup (claude-code, cursor, openclaw)")
    print(f"    {'mcp-config [tool]':<24s} Generate MCP config for AI tools")
    print()
    print(f"  {_bold('Wallet')}")
    print(f"    {'status':<24s} Full status dashboard")
    print(f"    {'balance':<24s} Quick balance check")
    print(f"    {'history':<24s} Transaction history")
    print(f"    {'tx <id>':<24s} Transaction details")
    print()
    print(f"  {_bold('Configuration')}")
    print(f"    {'config':<24s} View safety limits")
    print(f"    {'env show':<24s} Show current configuration")
    print(f"    {'env set <key> <val>':<24s} Set a config value")
    print(f"    {'doctor':<24s} Environment health check")
    print(f"    {'info':<24s} Protocol and version info")
    print()
    print(f"  {_bold('Service Provider')}")
    print(f"    {'serve':<24s} Start payment gateway")
    print(f"    {'upgrade':<24s} Switch from test to production mode")
    print()
    print(f"  {_bold('Examples')}")
    print(f"    $ {_cyan('ag402 setup')}")
    print(f"    $ {_cyan('ag402 install cursor')}")
    print(f"    $ {_cyan('ag402 run -- python my_agent.py')}")
    print(f"    $ {_cyan('ag402 pay http://127.0.0.1:4020/')}")
    print()
    print(f"  Use {_cyan('ag402 <command> --help')} for command details")
    print()


def _cmd_install(args) -> None:
    """One-command MCP setup — auto-write config for Claude Code, Cursor, OpenClaw."""
    try:
        from ag402_client_mcp.config_examples import install_for_tool
    except ImportError:
        print(f"\n  {_red('✗')} ag402-client-mcp not installed")
        print("  → Run: pip install ag402-client-mcp")
        print("  → Or:  pip install -e adapters/client_mcp/")
        print()
        return

    tool = args.tool
    scope = "global" if getattr(args, "global_scope", False) else "project"

    print()
    print(f"  Installing Ag402 MCP for {_bold(tool)}...")

    success, message = install_for_tool(tool, scope=scope)

    if success:
        print(f"  {_green('✓')} {message}")
        print()
        print(f"  {_bold('What happens next:')}")
        print(f"    1. Restart {tool} (or reload MCP config)")
        print("    2. The 'fetch_with_autopay' tool will appear in your AI tool")
        print("    3. Ask your AI to call a paid API — Ag402 handles the rest")
        print()
        print(f"  {_dim('Test it:')} Ask your AI: \"Check my Ag402 wallet balance\"")
    else:
        print(f"  {_red('✗')} {message}")

    print()


def _cmd_mcp(args) -> None:
    """Start the MCP client payment server for Claude Code / Cursor / OpenClaw."""
    try:
        from ag402_client_mcp.server import main as mcp_main
    except ImportError:
        print(f"\n  {_red('✗')} ag402-client-mcp not installed")
        print("  → Run: pip install ag402-client-mcp")
        print("  → Or:  pip install -e adapters/client_mcp/")
        print()
        return

    import sys as _sys
    original_argv = _sys.argv
    new_argv = ["ag402-mcp-client"]
    if getattr(args, "sse", False):
        new_argv.append("--sse")
        new_argv.extend(["--port", str(args.port)])
        new_argv.extend(["--host", str(args.host)])

    try:
        _sys.argv = new_argv
        mcp_main()
    finally:
        _sys.argv = original_argv


def _cmd_mcp_config(args) -> None:
    """Generate MCP configuration for various AI tools."""
    try:
        from ag402_client_mcp.config_examples import print_all_configs, print_config_for_tool
    except ImportError:
        print(f"\n  {_red('✗')} ag402-client-mcp not installed")
        print("  → Run: pip install ag402-client-mcp")
        print("  → Or:  pip install -e adapters/client_mcp/")
        print()
        return

    tool = getattr(args, "tool", None)
    if tool:
        result = print_config_for_tool(tool)
        print(result)
    else:
        print_all_configs()


def _cmd_setup() -> None:
    """Launch the interactive setup wizard."""
    from ag402_core.setup_wizard import init_wallet_after_setup, run_setup_wizard

    result = run_setup_wizard()
    # Initialize wallet DB and deposit test funds
    asyncio.run(init_wallet_after_setup(result))


def _cmd_run(args) -> None:
    """Launch an Agent process with x402 payment proxy injection."""
    import shutil
    import subprocess

    target = args.target
    extra = args.extra_args or []

    # Strip leading '--' from extra args
    if extra and extra[0] == "--":
        extra = extra[1:]

    if not target and not extra:
        print()
        print(f"  {_bold('ag402 run')} — Launch an Agent with x402 payment injection")
        print()
        print("  Usage:")
        print("    ag402 run -- python my_agent.py    Generic mode")
        print("    ag402 run -- <any command>          Generic proxy mode")
        print()
        print(f"  {_dim('HTTP requests that receive 402 will be auto-paid by Ag402.')}")
        print()
        return

    # Determine the actual command to run
    if target and target != "--":
        cmd = [target, *extra]
        label = target
    else:
        cmd = extra
        label = extra[0] if extra else "command"

    # Verify command exists
    if not shutil.which(cmd[0]):
        print(f"\n  {_red('✗')} Command not found: {cmd[0]}")
        print("  → Make sure it is installed and available in PATH\n")
        return

    # Load config for status display
    from ag402_core.config import load_config
    config = load_config()
    mode_str = _yellow("TEST") if config.is_test_mode else _red("PRODUCTION")

    print()
    print(f"  {_green('✓')} Ag402 payment engine active ({mode_str} mode)")
    print(f"  {_green('✓')} Python HTTP auto-pay: ag402.enable() injected")
    print(f"  {_green('✓')} Starting {label}...")
    print("  " + "─" * 50)
    print()

    # Build environment with AG402_ENABLED=1 + sitecustomize injection
    env = os.environ.copy()
    env["AG402_ENABLED"] = "1"

    # For Python commands, inject via sitecustomize.py + PYTHONPATH
    # (PYTHONSTARTUP only works for interactive shells, NOT for scripts)
    import tempfile
    tmpdir = None
    if _is_python_command(cmd):
        tmpdir = tempfile.mkdtemp(prefix="ag402_")
        sc_path = os.path.join(tmpdir, "sitecustomize.py")
        with open(sc_path, "w") as f:
            f.write(
                "try:\n"
                "    import ag402_core; ag402_core.enable()\n"
                "except Exception:\n"
                "    pass\n"
            )
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{tmpdir}{os.pathsep}{existing}" if existing else tmpdir

    # Print proxy mode info for non-Python commands
    if not _is_python_command(cmd):
        print(f"  {_yellow('⚠')} Proxy mode active for HTTP only.")
        print(f"  {_dim('For HTTPS auto-pay, use Python SDK injection: ag402_core.enable()')}")
        print()

    try:
        result = subprocess.run(cmd, env=env)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print(f"\n  {_yellow('⚠')} Stopped")
        sys.exit(130)
    finally:
        if tmpdir:
            import shutil as _shutil
            _shutil.rmtree(tmpdir, ignore_errors=True)


def _is_python_command(cmd: list[str]) -> bool:
    """Check if a command is a Python interpreter."""
    if not cmd:
        return False
    base = os.path.basename(cmd[0])
    return base.startswith("python")


def _cmd_env(args) -> None:
    """Manage .env configuration file."""
    from ag402_core.env_manager import get_env_path, parse_env_file, set_env_value

    action = getattr(args, "env_action", None)

    if action is None or action == "show":
        # Show current config
        env_path = get_env_path()
        entries = parse_env_file()

        print()
        print(_bold("  Ag402 Configuration"))
        print(f"  {_dim(f'File: {env_path}')}")
        print("  " + "─" * 45)
        print()

        if not entries:
            print(f"  {_yellow('⚠')} Config file is empty or does not exist")
            print(f"  → Run {_cyan('ag402 setup')} to generate configuration")
        else:
            for key, value in sorted(entries.items()):
                # Mask sensitive values
                if any(s in key.lower() for s in ("key", "password", "secret")):
                    display = "********" if value else "(empty)"
                else:
                    display = value
                # Show if overridden by env var
                env_val = os.environ.get(key)
                source = ""
                if env_val and env_val != value:
                    source = f" {_yellow('← env override')}"
                print(f"  {key:<35s} {display}{source}")
        print()

    elif action == "init":
        # Same as setup but only the env part
        _cmd_setup()

    elif action == "set":
        key = args.key
        value = args.value
        set_env_value(key, value)
        print(f"\n  {_green('✓')} {key} = {value}\n")
        print(f"  {_dim('Saved to ~/.ag402/.env')}\n")


def _check_port_available(host: str, port: int) -> bool:
    """Check if a port is available (nothing listening)."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) != 0


def _cmd_serve(args) -> None:
    """Start the payment gateway in provider mode."""
    target = args.target
    port = args.port
    price = args.price
    address = args.address

    if not target:
        # Try to load from .env
        from ag402_core.env_manager import parse_env_file
        entries = parse_env_file()
        target = entries.get("AG402_TARGET_API", "")
        price = entries.get("AG402_API_PRICE", price)
        address = entries.get("AG402_RECEIVE_ADDRESS", address)

    if not target:
        print(f"\n  {_red('✗')} No backend API URL specified")
        print(f"  → Use {_cyan('ag402 serve --target http://localhost:8000')}")
        print(f"  → Or run {_cyan('ag402 setup')} to configure\n")
        return

    # Detect if the backend is reachable; if not, offer built-in demo API
    use_builtin_backend = False
    try:
        from urllib.parse import urlparse
        parsed = urlparse(target)
        backend_host = parsed.hostname or "localhost"
        backend_port = parsed.port or 80
        if _check_port_available(backend_host, backend_port):
            use_builtin_backend = True
    except Exception:
        pass

    print()
    print(f"  {_bold('Ag402 Gateway')} — Service Provider Mode")
    print("  " + "═" * 55)
    print()

    try:
        import uvicorn
        from ag402_mcp.gateway import X402Gateway

        from ag402_core.gateway.auth import PaymentVerifier

        builtin_server = None
        if use_builtin_backend:
            # Start built-in demo API since the configured backend is not running
            from starlette.applications import Starlette
            from starlette.responses import JSONResponse as StarletteJSON
            from starlette.routing import Route

            async def _demo_api_handler(request):
                """Built-in demo API that returns sample data."""
                path = request.url.path
                params = dict(request.query_params)
                return StarletteJSON({
                    "service": "Ag402 Demo API",
                    "message": "This response was paid for via x402!",
                    "path": path,
                    "params": params,
                    "price": f"${price} USDC",
                })

            demo_app = Starlette(routes=[Route("/{path:path}", _demo_api_handler)])
            parsed = urlparse(target)
            backend_port_int = parsed.port or 8000
            demo_cfg = uvicorn.Config(
                demo_app, host="127.0.0.1", port=backend_port_int,
                log_level="error", lifespan="off",
            )
            builtin_server = uvicorn.Server(demo_cfg)
            builtin_server.install_signal_handlers = lambda: None

            import threading
            threading.Thread(target=builtin_server.run, daemon=True).start()
            # Wait for it to start
            for _ in range(30):
                time.sleep(0.1)
                if builtin_server.started:
                    break

            print(f"  {_yellow('⚠')} Backend {_cyan(target)} not running — auto-started built-in Demo API")
            print()

        print(f"  {_bold('Configuration')}")
        if use_builtin_backend:
            print(f"    Backend:    {_cyan(target)} {_dim('(built-in demo)')}")
        else:
            print(f"    Backend:    {_cyan(target)}")
        print(f"    Price:      {_green(f'${price} USDC')}/call")
        print(f"    Address:    {_dim(address[:20] + '...' if len(address) > 20 else address)}")
        print(f"    Port:       {_bold(str(port))}")
        print()

        verifier = PaymentVerifier()
        gateway = X402Gateway(
            target_url=target,
            price=price,
            chain="solana",
            token="USDC",
            address=address,
            verifier=verifier,
        )
        app = gateway.create_app()

        # Add pretty request logging middleware
        @app.middleware("http")
        async def _serve_log_middleware(request, call_next):
            _method = request.method
            _path = request.url.path
            _qs = str(request.url.query)
            _url = _path + (f"?{_qs}" if _qs else "")
            _client = request.client.host if request.client else "?"

            _t = time.monotonic()
            response = await call_next(request)
            _elapsed = time.monotonic() - _t

            sc = response.status_code
            if sc == 402:
                tag = _yellow("402 PAYMENT REQUIRED")
                icon = "💰"
            elif sc == 200:
                tag = _green("200 OK")
                icon = "✓"
            elif sc == 403:
                tag = _red("403 FORBIDDEN")
                icon = "✗"
            elif sc >= 500:
                tag = _red(f"{sc} ERROR")
                icon = "✗"
            else:
                tag = f"{sc}"
                icon = "·"
            print(f"  {icon} {_dim(_client)} {_bold(_method)} {_url} → {tag} {_dim(f'({_elapsed:.2f}s)')}")
            return response

        print(f"  {_green('✓')} Gateway started: {_cyan(f'http://127.0.0.1:{port}')}")
        print()
        print(f"  {_bold('Workflow')}")
        print(f"    Client → {_yellow('402 Payment Required')} → Client pays → Gateway verifies → {_green('200 OK')}")
        print()
        print("  " + "─" * 55)
        print(f"  {_bold('Try it')} (open another terminal):")
        print()
        gw_url = f"http://127.0.0.1:{port}/"
        print(f"    {_green('▶')} {_cyan('ag402 pay ' + gw_url)}")
        print(f"      {_dim('↑ Buyer view: discover price → pay → get data')}")
        print()
        print("  " + "─" * 55)
        print(f"  {_dim('Press Ctrl+C to stop')}")
        print()
        print(f"  {_bold('Request log:')}")
        print()

        # Suppress default uvicorn access logs; we handle logging above
        try:
            uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
        finally:
            # Ensure built-in demo server stops cleanly on exit
            if builtin_server is not None:
                builtin_server.should_exit = True

    except ImportError:
        print(f"  {_red('✗')} Missing dependency: ag402-mcp")
        print("  → Run: pip install ag402-mcp")
        print()


def _cmd_upgrade() -> None:
    """Guide user through test → production migration."""
    import getpass

    from ag402_core.config import load_config
    from ag402_core.env_manager import save_env_file

    config = load_config()
    if not config.is_test_mode:
        print(f"\n  {_yellow('⚠')} Already in production mode\n")
        return

    print()
    print(_bold("  Ag402 — Upgrade to Production Mode"))
    print("  " + "─" * 40)
    print()
    print(f"  Current mode: {_yellow('TEST')}")
    print()
    print("  Switching to production mode requires:")
    print("  1. A Solana wallet (private key)")
    print("  2. Some USDC deposited (recommended $5-10 to start)")
    print()

    confirm = input("  Continue? [Y/n] ").strip().lower()
    if confirm and confirm != "y":
        print(f"\n  {_yellow('⚠')} Cancelled\n")
        return

    print()
    private_key = getpass.getpass("  Enter Solana private key (base58): ")
    if not private_key.strip():
        print(f"\n  {_red('✗')} No private key provided\n")
        return

    # Encrypt the key
    try:
        from ag402_core.security.wallet_encryption import (
            encrypt_private_key,
            save_encrypted_wallet,
        )

        password = getpass.getpass("  Set wallet password: ")
        password2 = getpass.getpass("  Confirm password: ")
        if password != password2:
            print(f"\n  {_red('✗')} Passwords do not match\n")
            return

        encrypted = encrypt_private_key(password, private_key)
        wallet_path = os.path.expanduser("~/.ag402/wallet.key")
        save_encrypted_wallet(wallet_path, encrypted)
        print(f"  {_green('✓')} Private key encrypted and saved: {wallet_path}")
    except ImportError:
        print(f"  {_yellow('⚠')} cryptography not installed, skipping encryption")

    # Set daily limit
    raw_limit = input("\n  Set daily spending limit: [$10] ").strip()
    try:
        daily_limit = float(raw_limit) if raw_limit else 10.0
    except ValueError:
        print(f"  {_yellow('⚠')} Invalid number '{raw_limit}', using default $10.00")
        daily_limit = 10.0
    daily_limit = min(daily_limit, 1000.0)
    print(f"  {_green('✓')} Daily limit: ${daily_limit:.2f}")

    # Save to .env
    save_env_file({
        "X402_MODE": "production",
        "SOLANA_RPC_URL": "https://api.mainnet-beta.solana.com",
        "X402_DAILY_LIMIT": str(daily_limit),
    }, merge=True)

    print()
    print(f"  {_green('✓')} Production mode enabled!")
    print(f"  {_yellow('⚠')} Reminder: This is a hot wallet. Only deposit small amounts.")
    print()


# ─── Original Commands ───────────────────────────────────────────────────

async def _cmd_init(db_path: str) -> None:
    from ag402_core.config import load_config
    from ag402_core.wallet.agent_wallet import AgentWallet

    config = load_config()
    is_test = config.is_test_mode

    _print_banner()

    print(f"  [INIT] Creating wallet at {_cyan(db_path)} ... ", end="", flush=True)
    wallet = AgentWallet(db_path=db_path)
    await wallet.init_db()
    print(_green("✓"))

    mode_str = _yellow("TEST") + " (no real money, safe to experiment)" if is_test else _red("PRODUCTION")
    print(f"  [INIT] Mode: {mode_str}")

    # Auto-deposit test funds
    if is_test:
        balance = float(await wallet.get_balance())
        if balance == 0:
            await wallet.deposit(100.0, note="Test mode auto-fund")
            print(f"  [INIT] Depositing {_green('$100.00')} test funds ... {_green('✓')}")
        else:
            print(f"  [INIT] Wallet already funded: ${balance:.2f}")

    balance = float(await wallet.get_balance())
    daily = float(await wallet.get_daily_spend())

    print()
    print("  ┌─────────────── Wallet Status ───────────────┐")
    print(f"  │  Balance:       {_green(f'${balance:.4f}'):>37s}│")
    print(f"  │  Daily Limit:   ${config.daily_spend_limit:.2f} (used: ${daily:.2f})      │")
    print(f"  │  Per-Minute:    ${config.per_minute_limit:.2f} / {config.per_minute_count} txns             │")
    print(f"  │  Network:       {'solana-devnet (mock)' if is_test else config.solana_rpc_url[:25]:25s}│")
    print(f"  │  Security:      {_green('6 layers active ✓'):>37s}│")
    print("  └─────────────────────────────────────────────┘")
    print()
    print(f"  Next: Run {_cyan('ag402 demo')} to see an AI agent auto-pay for an API call!")
    print(f"        Run {_cyan('ag402 status')} to view the full dashboard.")
    print()

    await wallet.close()


async def _cmd_status() -> None:
    from ag402_core.config import MAX_SINGLE_TX, load_config
    from ag402_core.middleware.budget_guard import BudgetGuard
    from ag402_core.wallet.agent_wallet import AgentWallet

    config = load_config()
    is_test = config.is_test_mode
    db_path = config.wallet_db_path
    daily_limit = config.daily_spend_limit

    print()
    print(_bold("  Ag402 Status Dashboard"))
    print("  " + "═" * 50)
    print()

    mode_str = _yellow("TEST 🧪") + " (safe, no real funds)" if is_test else _red("PRODUCTION")
    print(f"  Mode:        {mode_str}")
    print(f"  Wallet:      {_dim(db_path)}")

    if not os.path.exists(db_path):
        print()
        print(f"  {_yellow('⚠')}  Wallet not initialized. Run: {_cyan('ag402 init')}")
        print()
        return

    wallet = AgentWallet(db_path=db_path)
    await wallet.init_db()

    balance = float(await wallet.get_balance())
    daily = float(await wallet.get_daily_spend())
    minute = float(await wallet.get_minute_spend())
    minute_count = await wallet.get_minute_count()

    print(f"  Balance:     {_green(f'${balance:.4f}')}")
    print()

    # Budget bars
    print(f"  Daily Budget    {_bar(daily, daily_limit)}  ${daily:.2f} / ${daily_limit:.2f}")
    print(f"  Minute Budget   {_bar(minute, config.per_minute_limit)}  ${minute:.2f} / ${config.per_minute_limit:.2f}")
    print(f"  Minute TXs      {_bar(minute_count, config.per_minute_count)}  {minute_count} / {config.per_minute_count}")
    print()

    # Security layers
    cb_open = BudgetGuard.is_circuit_open(
        config.circuit_breaker_threshold, config.circuit_breaker_cooldown
    )
    cb_failures = BudgetGuard._consecutive_failures

    print("  Security Layers:")
    print(f"    {_green('✓')}  Single-TX cap:        ${MAX_SINGLE_TX:.2f}")
    print(f"    {_green('✓')}  Per-minute cap:       ${config.per_minute_limit:.2f} / {config.per_minute_count} txns")
    print(f"    {_green('✓')}  Daily cap:            ${daily_limit:.2f}")
    if cb_open:
        print(f"    {_red('✗')}  Circuit breaker:      {_red('OPEN')} ({cb_failures}/{config.circuit_breaker_threshold} failures)")
    else:
        print(f"    {_green('✓')}  Circuit breaker:      OK ({cb_failures}/{config.circuit_breaker_threshold} failures)")
    print(f"    {_green('✓')}  Replay guard:         Active ({config.replay_window_seconds}s window)")
    print(f"    {_green('✓')}  Private key filter:   Active")
    print()

    # Recent transactions
    txs = await wallet.get_transactions(limit=5)
    if txs:
        print("  Recent Transactions (last 5):")
        for tx in txs:
            sign = "+" if tx.type == "deposit" else "-"
            color = "32" if tx.type == "deposit" else "31"
            addr = _short_addr(tx.to_address) if tx.to_address else "(faucet)" if tx.type == "deposit" else "-"
            ago = _time_ago(tx.timestamp)
            print(f"    {_c(color, f'{sign}${tx.amount:.4f}'):>20s}  {tx.type:<12s} → {addr:<25s} {_dim(ago)}")
    else:
        print(f"  No transactions yet. Run {_cyan('ag402 demo')} to create some!")
    print()

    await wallet.close()


async def _cmd_balance(db_path: str) -> None:
    from ag402_core.config import load_config
    from ag402_core.wallet.agent_wallet import AgentWallet

    config = load_config()
    daily_limit = config.daily_spend_limit

    wallet = AgentWallet(db_path=db_path)
    await wallet.init_db()
    balance = float(await wallet.get_balance())
    daily = float(await wallet.get_daily_spend())
    minute = float(await wallet.get_minute_spend())

    print()
    print(f"  Balance:      {_green(f'${balance:.4f}')}")
    print(f"  Daily spend:  {_bar(daily, daily_limit)}  ${daily:.4f} / ${daily_limit:.2f}")
    print(f"  Minute spend: {_bar(minute, config.per_minute_limit)}  ${minute:.4f} / ${config.per_minute_limit:.2f}")
    print()

    await wallet.close()


async def _cmd_history(db_path: str, limit: int, fmt: str, output: str) -> None:
    from ag402_core.wallet.agent_wallet import AgentWallet

    wallet = AgentWallet(db_path=db_path)
    await wallet.init_db()

    if fmt in ("json", "csv") and output:
        await wallet.export_history(output, format=fmt)
        print(f"  {_green('✓')} Exported {fmt.upper()} to: {output}")
        await wallet.close()
        return

    txs = await wallet.get_transactions(limit=limit)
    if not txs:
        print()
        print(f"  No transactions yet. Run {_cyan('ag402 demo')} to create some!")
        print()
        await wallet.close()
        return

    print()
    print(_bold("  Transaction History"))
    print("  " + "─" * 70)
    print(f"  {'':>2} {'Amount':>10}  {'Type':<12} {'Status':<12} {'Address':<25} {'When'}")
    print(f"  {'':>2} {'------':>10}  {'----':<12} {'------':<12} {'-------':<25} {'----'}")
    for tx in txs:
        sign = "+" if tx.type == "deposit" else "-"
        color = "32" if tx.type == "deposit" else "31"
        addr = _short_addr(tx.to_address) if tx.to_address else "-"
        ago = _time_ago(tx.timestamp)
        print(f"  {_c(color, f'{sign}${tx.amount:>9.4f}')}  {tx.type:<12} {tx.status:<12} {addr:<25} {_dim(ago)}")

    # Summary stats
    stats = await wallet.get_summary_stats()
    by_addr = await wallet.get_spend_by_address()

    print()
    print("  ─── Summary ───")
    bal = stats["balance"]
    today = stats["today_spend"]
    total = stats["total_spend"]
    count = stats["tx_count"]
    print(f"  Balance:     {_green(f'${bal:.4f}')}")
    print(f"  Today spend: ${today:.4f}")
    print(f"  Total spend: ${total:.4f}")
    print(f"  TX count:    {count}")

    if by_addr:
        print()
        print("  ─── Spend by Address ───")
        for addr, total in sorted(by_addr.items(), key=lambda x: -x[1]):
            print(f"    ${total:>9.4f}  {_short_addr(addr)}")

    print()
    await wallet.close()


async def _cmd_tx(db_path: str, tx_id: str) -> None:
    from ag402_core.wallet.agent_wallet import AgentWallet

    wallet = AgentWallet(db_path=db_path)
    await wallet.init_db()

    matches = await wallet.find_transactions_by_prefix(tx_id)

    if not matches:
        print(f"\n  {_red('✗')} Transaction not found: {tx_id}\n")
        await wallet.close()
        return

    tx = matches[0]
    ts_str = datetime.fromtimestamp(tx.timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    color = "32" if tx.type == "deposit" else "31"

    print()
    print(_bold("  Transaction Detail"))
    print("  " + "═" * 50)
    print(f"  ID:          {_cyan(tx.id)}")
    print(f"  Type:        {tx.type}")
    print(f"  Amount:      {_c(color, f'${tx.amount:.4f}')}")
    print(f"  Status:      {_green(tx.status) if tx.status == 'confirmed' else _yellow(tx.status)}")
    print(f"  To Address:  {tx.to_address or '-'}")
    print(f"  TX Hash:     {tx.tx_hash or '-'}")
    print(f"  Timestamp:   {ts_str} ({_time_ago(tx.timestamp)})")
    if tx.note:
        print(f"  Note:        {tx.note}")
    print()

    await wallet.close()


def _cmd_config() -> None:
    from ag402_core.config import (
        MAX_DAILY_SPEND_HARD_CEILING,
        MAX_SINGLE_TX,
        load_config,
    )

    config = load_config()
    is_test = config.is_test_mode

    print()
    print(_bold("  Ag402 Safety Configuration"))
    print("  " + "═" * 45)
    print()

    mode_str = _yellow("TEST") if is_test else _red("PRODUCTION")
    print(f"  Mode:                      {mode_str}")
    print()
    print("  ─── Budget Limits ───")
    print(f"  MAX_SINGLE_TX (hard):      ${MAX_SINGLE_TX:.2f}")
    print(f"  single_tx_limit (config):  ${config.single_tx_limit:.2f}")
    print(f"  daily_limit (env):         ${config.daily_spend_limit:.2f}  (hard ceiling: ${MAX_DAILY_SPEND_HARD_CEILING:.2f})")
    print(f"  per_minute_limit (env):    ${config.per_minute_limit:.2f}")
    print(f"  per_minute_count (env):    {config.per_minute_count}")
    print()
    print("  ─── Circuit Breaker ───")
    print(f"  threshold (env):           {config.circuit_breaker_threshold} failures")
    print(f"  cooldown (env):            {config.circuit_breaker_cooldown}s")
    print()
    print("  ─── Environment Variables ───")
    print("  X402_DAILY_LIMIT                 daily spend cap (default: $10)")
    print("  X402_PER_MINUTE_LIMIT            per-minute $ cap (default: $2)")
    print("  X402_PER_MINUTE_COUNT            per-minute TX count (default: 5)")
    print("  X402_CIRCUIT_BREAKER_THRESHOLD   failure threshold (default: 3)")
    print("  X402_CIRCUIT_BREAKER_COOLDOWN    cooldown seconds (default: 60)")
    print("  AG402_UNLOCK_PASSWORD         wallet unlock password (Docker)")
    print()
    print("  ─── Paths & Network ───")
    print(f"  wallet_db_path:            {config.wallet_db_path}")
    print(f"  solana_rpc_url:            {config.solana_rpc_url}")
    if config.solana_rpc_backup_url:
        print(f"  solana_rpc_backup_url:     {config.solana_rpc_backup_url}")
    print()
    print("  ─── Trust ───")
    if config.trusted_addresses:
        print(f"  trusted_addresses:         {config.trusted_addresses}")
    else:
        print("  trusted_addresses:         (any)")
    if config.fallback_api_key:
        print(f"  fallback_api_key:          {'*' * 8}...{config.fallback_api_key[-4:]}")
    print()


def _cmd_info() -> None:
    from open402.negotiation import CURRENT_VERSION
    from open402.spec import get_json_schema

    from ag402_core import __version__

    print()
    print(_bold("  Ag402 Protocol Info"))
    print(_dim("  Powered by the Open402 standard"))
    print("  " + "═" * 40)
    print(f"  ag402-core:    v{__version__}")
    print(f"  open402:          v{CURRENT_VERSION}")
    print(f"  Python:           {platform.python_version()}")
    print(f"  Platform:         {platform.system()} {platform.machine()}")
    print()
    print("  JSON Schema:")
    schema_str = json.dumps(get_json_schema(), indent=2)
    for line in schema_str.split("\n"):
        print(f"    {line}")
    print()


def _cmd_doctor() -> None:
    from ag402_core.config import load_config

    config = load_config()
    issues = []
    warnings = []

    print()
    print(_bold("  Ag402 Doctor — Environment Check"))
    print("  " + "═" * 45)
    print()

    # Python version
    py_ver = platform.python_version()
    py_ok = sys.version_info >= (3, 10)
    print(f"  {_green('✓') if py_ok else _red('✗')}  Python {py_ver}" +
          ("" if py_ok else " (requires >= 3.10)"))
    if not py_ok:
        issues.append("Python >= 3.10 required")

    # Core package
    try:
        from ag402_core import __version__
        print(f"  {_green('✓')}  ag402-core {__version__}")
    except ImportError:
        print(f"  {_red('✗')}  ag402-core NOT installed")
        issues.append("ag402-core not installed")

    # Protocol package
    try:
        import open402
        ver = getattr(open402, "__version__", "installed")
        print(f"  {_green('✓')}  open402 {ver}")
    except ImportError:
        print(f"  {_red('✗')}  open402 NOT installed")
        issues.append("open402 not installed")

    # cryptography
    try:
        import cryptography
        print(f"  {_green('✓')}  cryptography {cryptography.__version__}")
    except ImportError:
        print(f"  {_yellow('⚠')}  cryptography NOT installed (wallet encryption unavailable)")
        warnings.append("cryptography not installed")

    # httpx
    try:
        import httpx
        print(f"  {_green('✓')}  httpx {httpx.__version__}")
    except ImportError:
        print(f"  {_red('✗')}  httpx NOT installed")
        issues.append("httpx not installed")

    # aiosqlite
    try:
        import aiosqlite
        print(f"  {_green('✓')}  aiosqlite {aiosqlite.__version__}")
    except ImportError:
        print(f"  {_red('✗')}  aiosqlite NOT installed")
        issues.append("aiosqlite not installed")

    # Solana dependencies (optional)
    try:
        import solana  # noqa: F401
        import solders  # noqa: F401
        print(f"  {_green('✓')}  Solana dependencies installed")
    except ImportError:
        if config.is_test_mode:
            print(f"  {_yellow('⚠')}  Solana dependencies: NOT installed (ok for test mode)")
            warnings.append("Solana deps not installed (ok for test)")
        else:
            print(f"  {_red('✗')}  Solana dependencies: NOT installed (required for production)")
            issues.append("Solana deps required for production: pip install 'ag402-core[crypto]'")

    print()

    # Wallet DB
    db_path = config.wallet_db_path
    if os.path.exists(db_path):
        size_kb = os.path.getsize(db_path) / 1024
        print(f"  {_green('✓')}  Wallet DB exists: {db_path} ({size_kb:.1f} KB)")
    else:
        print(f"  {_yellow('⚠')}  Wallet DB not found: {db_path}")
        warnings.append("Wallet not initialized — run: ag402 init")

    # Encrypted wallet
    enc_path = config.encrypted_wallet_path
    if os.path.exists(enc_path):
        print(f"  {_green('✓')}  Encrypted wallet found: {enc_path}")
    else:
        print(f"  {_yellow('⚠')}  Encrypted wallet not found: {enc_path}")

    # Mode
    mode_str = _yellow("TEST") if config.is_test_mode else _red("PRODUCTION")
    print(f"  {_green('✓')}  Mode: {mode_str}")

    # Private key
    if config.solana_private_key:
        print(f"  {_green('✓')}  SOLANA_PRIVATE_KEY: set")
    else:
        if not config.is_test_mode:
            print(f"  {_red('✗')}  SOLANA_PRIVATE_KEY: not set (required for production)")
            issues.append("SOLANA_PRIVATE_KEY not set")
        else:
            print(f"  {_yellow('⚠')}  SOLANA_PRIVATE_KEY: not set (ok for test mode)")
            warnings.append("No private key (ok for test)")

    print()

    # Summary
    total_issues = len(issues)
    total_warnings = len(warnings)
    if total_issues == 0:
        status = _green("HEALTHY ✓")
        if total_warnings > 0:
            status += f" ({total_warnings} warning{'s' if total_warnings > 1 else ''})"
        print(f"  Overall: {status}")
    else:
        print(f"  Overall: {_red('UNHEALTHY ✗')} ({total_issues} issue{'s' if total_issues > 1 else ''}, {total_warnings} warning{'s' if total_warnings > 1 else ''})")
        print()
        for issue in issues:
            print(f"    {_red('✗')} {issue}")

    print()


async def _cmd_pay(url: str, method: str, db_path: str) -> None:
    """Send a single HTTP request with automatic x402 payment.

    Manually performs each protocol step (instead of using middleware)
    so we can display the full negotiation flow to the user.
    """
    import httpx
    from open402.headers import build_authorization, parse_www_authenticate
    from open402.negotiation import get_version_header
    from open402.spec import X402PaymentProof

    from ag402_core.config import load_config
    from ag402_core.payment.registry import PaymentProviderRegistry
    from ag402_core.security.replay_guard import generate_replay_headers
    from ag402_core.wallet.agent_wallet import AgentWallet

    config = load_config()
    mode_str = _yellow("TEST") if config.is_test_mode else _green("LIVE")

    print()
    print(f"  {_bold('Ag402 Pay')} — Buyer-side single request ({mode_str})")
    print("  " + "═" * 55)
    print()

    # ── Step 1: Wallet ──
    print(f"  {_bold('① Wallet')}")
    wallet = AgentWallet(db_path=db_path)
    await wallet.init_db()

    balance_before = float(await wallet.get_balance())
    if balance_before < 0.01:
        print(f"     {_red('✗')} Insufficient balance: ${balance_before:.4f}")
        print(f"     → Run {_cyan('ag402 setup')} to add test funds")
        print()
        await wallet.close()
        return

    print(f"     Balance: {_green(f'${balance_before:.4f}')}")
    print()

    provider = PaymentProviderRegistry.get_provider(config=config)

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # ── Step 2: First request ──
            print(f"  {_bold('② Request')}")
            print(f"     {_cyan(method)} {url}")

            req_headers: dict[str, str] = {}
            req_headers.update(get_version_header())
            req_headers.update(generate_replay_headers())

            t0 = time.monotonic()
            response = await client.request(method.upper(), url, headers=req_headers)
            t1 = time.monotonic()

            if response.status_code != 402:
                # Not a paid API — show result directly
                elapsed = t1 - t0
                print(f"     Response: {_green(str(response.status_code))} ({elapsed:.2f}s)")
                print()
                print(f"  {_dim('This API did not require payment (non-x402), returned result directly.')}")
                _print_response_body(response.content, response.status_code)
                await wallet.close()
                print()
                return

            # ── Step 3: 402 received — show challenge ──
            print(f"     Response: {_yellow('402 Payment Required')} ({t1 - t0:.2f}s)")
            print()

            print(f"  {_bold('③ Payment Challenge')}  {_dim('← Server 402 response')}")
            www_auth = response.headers.get("www-authenticate", "")
            challenge = parse_www_authenticate(www_auth)

            if challenge is None:
                print(f"     {_red('✗')} Non-standard 402 response (not x402), cannot auto-pay")
                await wallet.close()
                print()
                return

            print("     Protocol: x402")
            print(f"     Chain:    {_cyan(challenge.chain)}")
            print(f"     Token:    {challenge.token}")
            print(f"     Amount:   {_green(f'${challenge.amount} {challenge.token}')}")
            print(f"     Payee:    {_dim(challenge.address[:24])}...")
            print()

            amount = challenge.amount_float

            # ── Step 4: Pay ──
            print(f"  {_bold('④ Auto-Pay')}  {_dim('← Wallet deduction + on-chain transfer')}")

            # Deduct from wallet
            deduction_tx = await wallet.deduct(
                amount=amount,
                to_address=challenge.address,
            )

            # Pay on-chain
            pay_result = await provider.pay(
                to_address=challenge.address,
                amount=amount,
                token=challenge.token,
            )

            if not pay_result.success:
                print(f"     {_red('✗')} On-chain payment failed: {pay_result.error}")
                await wallet.rollback(deduction_tx.id)
                print(f"     {_yellow('↩')} Wallet deduction rolled back")
                await wallet.close()
                print()
                return

            print(f"     TX Hash:  {_cyan(pay_result.tx_hash[:44])}")
            print(f"     Amount:   {_green(f'${amount:.4f} {challenge.token}')}")
            print(f"     Status:   {_green('✓ Success')}")
            print()

            # ── Step 5: Retry with proof ──
            print(f"  {_bold('⑤ Retry with Proof')}  {_dim('← Send payment proof, get data')}")

            proof = X402PaymentProof(
                tx_hash=pay_result.tx_hash,
                chain=challenge.chain,
                payer_address=provider.get_address(),
            )
            retry_headers = dict(req_headers)
            retry_headers["Authorization"] = build_authorization(proof)

            t2 = time.monotonic()
            retry_response = await client.request(method.upper(), url, headers=retry_headers)
            t3 = time.monotonic()

            status_code = retry_response.status_code
            if status_code == 200:
                status_display = _green(f"{status_code} OK")
            elif status_code >= 500:
                status_display = _red(f"{status_code} Server Error")
            elif status_code >= 400:
                status_display = _yellow(f"{status_code}")
            else:
                status_display = f"{status_code}"

            print(f"     Response: {status_display} ({t3 - t2:.2f}s)")

            if retry_response.status_code >= 400:
                # Retry failed — rollback
                await wallet.rollback(deduction_tx.id)
                print(f"     {_yellow('↩')} Server returned error, auto-refunded")
            else:
                # Update deduction with tx_hash
                pass

            # Show response body
            _print_response_body(retry_response.content, retry_response.status_code)

            # ── Step 6: Balance summary ──
            final = float(await wallet.get_balance())
            spent = balance_before - final
            elapsed = t3 - t0

            print()
            print(f"  {_bold('⑥ Settlement')}")
            print(f"     Total time: {elapsed:.2f}s (negotiate + pay + fetch)")
            print(f"     Balance:    ${balance_before:.4f} → {_green(f'${final:.4f}')}", end="")
            if spent > 0:
                print(f"  ({_red(f'-${spent:.4f}')})")
            elif spent < 0:
                print(f"  ({_green(f'+${abs(spent):.4f}')} refunded)")
            else:
                print("  (no change)")

        except httpx.ConnectError:
            print(f"\n     {_red('✗')} Cannot connect to {url}")
            print(f"     {_dim('Make sure the target service is running')}")
        except Exception as exc:
            print(f"\n  {_red('✗')} Request failed: {exc}")
        finally:
            await wallet.close()

    print()
    print("  " + "═" * 55)
    print(f"  {_dim('Use')} {_cyan('ag402 history')} {_dim('to view all transactions')}")
    print()


def _print_response_body(body: bytes, status_code: int) -> None:
    """Pretty-print response body (JSON or text), used by _cmd_pay."""
    if status_code != 200 or not body:
        if status_code >= 500:
            print(f"     {_yellow('Hint')}: Backend returned an error — check if the backend is running")
        return

    body_str = body.decode("utf-8", errors="replace")

    # Try JSON first
    try:
        body_json = json.loads(body_str)
        body_display = json.dumps(body_json, indent=2, ensure_ascii=False)
        lines = body_display.split("\n")
        if len(lines) > 10:
            lines = lines[:10] + [f"... ({len(lines) - 10} more lines)"]
        print("     Response Body (JSON):")
        for line in lines:
            print(f"       {_dim(line)}")
        return
    except (json.JSONDecodeError, TypeError):
        pass

    # Plain text / HTML
    lines = body_str.strip().split("\n")
    total = len(lines)
    show = min(total, 6)
    print(f"     Response Body ({total} lines):")
    for line in lines[:show]:
        print(f"       {_dim(line.rstrip()[:80])}")
    if total > show:
        print(f"       {_dim(f'... {total - show} more lines omitted')}")


async def _cmd_demo() -> None:
    """Run a self-contained E2E payment demo.

    Uses the persistent wallet (~/.ag402/wallet.db) so demo transactions
    show up in `ag402 status` and `ag402 history`.
    """
    from ag402_core.config import RunMode, X402Config
    from ag402_core.middleware.x402_middleware import X402PaymentMiddleware
    from ag402_core.payment.solana_adapter import MockSolanaAdapter
    from ag402_core.wallet.agent_wallet import AgentWallet

    _print_banner()
    print(f"  {_bold('E2E Payment Demo')} — Full AI Agent auto-payment flow")
    print("  " + "═" * 55)
    print()

    # Check if gateway dependencies are available
    try:
        from ag402_mcp.gateway import X402Gateway  # noqa: F401

        from ag402_core.gateway.auth import PaymentVerifier  # noqa: F401
        has_gateway = True
    except ImportError:
        has_gateway = False

    # Use persistent wallet so demo txns appear in status/history
    print(f"  {_bold('① Initialize')}")
    print("     Opening wallet ... ", end="", flush=True)
    wallet = AgentWallet(db_path=_DEFAULT_DB)
    await wallet.init_db()

    # Ensure there's enough balance for the demo
    balance = float(await wallet.get_balance())
    if balance < 0.10:
        await wallet.deposit(100.0, note="Demo faucet top-up")
        balance = float(await wallet.get_balance())
    print(_green("✓"))
    print(f"     Balance: {_green(f'${balance:.2f}')}")
    print("     Mode: Mock Solana (test environment, zero risk)")
    print()

    provider = MockSolanaAdapter(balance=balance)
    config = X402Config(mode=RunMode.TEST, single_tx_limit=1.0)
    middleware = X402PaymentMiddleware(wallet=wallet, provider=provider, config=config)

    weather_server = None
    gw_server = None
    weather_task = None
    gw_task = None
    gateway = None  # Track gateway for cleanup

    try:
        if has_gateway:
            # Full E2E with local gateway
            import uvicorn
            from starlette.applications import Starlette
            from starlette.responses import JSONResponse
            from starlette.routing import Route

            async def weather_handler(request):
                city = request.query_params.get("city", "Tokyo")
                return JSONResponse({"city": city, "temp": 22, "condition": "Sunny", "source": "Ag402 Demo"})

            weather_app = Starlette(routes=[Route("/weather", weather_handler)])

            weather_port = 18100
            gateway_port = 18101

            # Start weather server
            print(f"  {_bold('② Start Services')}")
            print(f"     Starting Weather API (:{weather_port}) ... ", end="", flush=True)
            weather_config = uvicorn.Config(
                weather_app, host="127.0.0.1", port=weather_port,
                log_level="error", lifespan="off",
            )
            weather_server = uvicorn.Server(weather_config)
            # Prevent uvicorn from installing its own signal handlers
            weather_server.install_signal_handlers = lambda: None
            weather_task = asyncio.create_task(weather_server.serve())
            for _ in range(50):
                await asyncio.sleep(0.1)
                if weather_server.started:
                    break
            print(_green("✓"))

            # Start gateway
            print(f"     Starting x402 Gateway (:{gateway_port}) ... ", end="", flush=True)
            verifier = PaymentVerifier()
            recipient = "DemoRecipientWa11et11111111111111111111"
            gateway = X402Gateway(
                target_url=f"http://127.0.0.1:{weather_port}",
                price="0.02", chain="solana", token="USDC", address=recipient,
                verifier=verifier,
            )
            gateway_app = gateway.create_app()
            gw_config = uvicorn.Config(
                gateway_app, host="127.0.0.1", port=gateway_port,
                log_level="error", lifespan="off",
            )
            gw_server = uvicorn.Server(gw_config)
            gw_server.install_signal_handlers = lambda: None
            gw_task = asyncio.create_task(gw_server.serve())
            for _ in range(50):
                await asyncio.sleep(0.1)
                if gw_server.started:
                    break
            print(_green("✓"))
            print()

            # Make payment request
            url = f"http://127.0.0.1:{gateway_port}/weather?city=Tokyo"
            print(f"  {_bold('③ Send Request')}")
            print(f"     GET {_cyan(url)}")
            print()

            t0 = time.monotonic()
            result = await middleware.handle_request("GET", url)
            elapsed = time.monotonic() - t0

            print(f"  {_bold('④ Payment Negotiation')}")
            if result.payment_made:
                print(f"     Server returned {_yellow('402')} → Ag402 auto-paid {_green('✓')}  ({elapsed:.2f}s)")
                print(f"     TX Hash: {_cyan(result.tx_hash[:44])}...")
                print(f"     Amount:  {_green(f'${result.amount_paid:.4f} USDC')}")
            print()

            print(f"  {_bold('⑤ Fetch Data')}")
            if result.status_code == 200:
                data = json.loads(result.body)
                print(f"     Status: {_green('200 OK')}")
                print(f"     City:   {data['city']}")
                print(f"     Temp:   {data['temp']}°C")
                print(f"     Weather: {data['condition']}")
            else:
                print(f"     Status: {_red(str(result.status_code))}")
                if result.error:
                    print(f"     Error:  {result.error}")

            final = float(await wallet.get_balance())
            spent = balance - final
            print()
            print(f"  {_bold('⑥ Balance Change')}")
            print(f"     Before: ${balance:.4f}  →  After: {_green(f'${final:.4f}')}  ({_red(f'-${spent:.4f}')})")
            print()

        else:
            # Simplified demo without gateway (no ag402-mcp installed)
            print(f"  {_yellow('⚠')} ag402-mcp not installed — running simplified demo")
            print()

            print(f"  {_bold('② Simulated Payment')}")
            print("     Paying $0.02 USDC ... ", end="", flush=True)
            pay_result = await provider.pay("DemoRecipient1111111111111111111111", 0.02, "USDC")
            await wallet.deduct(0.02, to_address="DemoRecipient1111111111111111111111", tx_hash=pay_result.tx_hash)
            print(_green("✓"))
            print(f"     TX Hash: {_cyan(pay_result.tx_hash[:44])}...")
            print(f"     Amount:  {_green('$0.02 USDC')}")

            final = float(await wallet.get_balance())
            print(f"     Balance: {_green(f'${final:.2f}')}")
            print()

    except KeyboardInterrupt:
        print(f"\n  {_yellow('⚠')} Demo interrupted")

    finally:
        # Graceful shutdown: signal servers to stop, then await their tasks
        if gw_server is not None:
            gw_server.should_exit = True
        if weather_server is not None:
            weather_server.should_exit = True

        # Await server tasks with timeout so uvicorn fully shuts down
        # (prevents dangling threads that block process exit)
        for task in (gw_task, weather_task):
            if task is not None:
                try:
                    await asyncio.wait_for(task, timeout=3.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task

        # Close gateway's persistent replay guard (opened via lazy init
        # since lifespan="off" means FastAPI lifespan doesn't run)
        if gateway is not None:
            with contextlib.suppress(Exception):
                await gateway._persistent_guard.close()

        await middleware.close()
        await wallet.close()

    print()
    print("  " + "═" * 55)
    print(f"  {_green('✓')} Demo complete! The AI Agent auto-paid for an API call.")
    print(f"  {_dim('Use')} {_cyan('ag402 history')} {_dim('to view transaction history')}")
    print()


async def _cmd_export(db_path: str, fmt: str, output: str) -> None:
    from ag402_core.wallet.agent_wallet import AgentWallet

    if not output:
        output = f"ag402_history.{fmt}"

    wallet = AgentWallet(db_path=db_path)
    await wallet.init_db()

    await wallet.export_history(output, format=fmt)
    print(f"\n  {_green('✓')} Exported {fmt.upper()} to: {output}\n")

    await wallet.close()


if __name__ == "__main__":
    main()
