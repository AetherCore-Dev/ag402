"""Payment provider registry with lazy loading."""

from __future__ import annotations

from ag402_core.config import RunMode, X402Config, load_config
from ag402_core.payment.base import BasePaymentProvider


class PaymentProviderRegistry:
    """Lazy-loading payment provider registry.

    Resolves provider name to a concrete ``BasePaymentProvider`` instance
    while only importing heavy dependencies when they are actually needed.
    """

    @classmethod
    def get_provider(
        cls,
        name: str = "auto",
        config: X402Config | None = None,
    ) -> BasePaymentProvider:
        """Get a payment provider by *name*.

        ``"auto"`` — detect from environment / config:

        * ``X402_MODE=test``          -> ``MockSolanaAdapter``
        * ``SOLANA_PRIVATE_KEY`` set  -> ``SolanaAdapter``
        * ``STRIPE_SECRET_KEY`` set   -> ``NotImplementedError`` (V2)
        * otherwise                   -> ``ConfigError``

        Heavy crypto dependencies are only imported when their adapter is
        actually requested.
        """
        if config is None:
            config = load_config()

        if name == "auto":
            return cls._resolve_auto(config)

        if name == "mock":
            from ag402_core.payment.solana_adapter import MockSolanaAdapter
            return MockSolanaAdapter()

        if name == "solana":
            return cls._build_solana(config)

        if name == "stripe":
            raise NotImplementedError(
                "Stripe payment provider is planned for V2. Stay tuned!"
            )

        raise ValueError(f"Unknown payment provider: {name!r}")

    # -- private helpers ----------------------------------------------------

    @classmethod
    def _resolve_auto(cls, config: X402Config) -> BasePaymentProvider:
        """Auto-detect the best provider from the current config."""
        # 1. Test mode -> mock
        if config.mode == RunMode.TEST:
            from ag402_core.payment.solana_adapter import MockSolanaAdapter
            return MockSolanaAdapter()

        # 2. Solana key present -> real adapter
        if config.solana_private_key:
            return cls._build_solana(config)

        # 3. Stripe key (V2 placeholder)
        import os
        if os.getenv("STRIPE_SECRET_KEY"):
            raise NotImplementedError(
                "Stripe payment provider is planned for V2. Stay tuned!"
            )

        # 4. Nothing configured
        raise ConfigError(
            "No payment provider could be auto-detected. "
            "Set SOLANA_PRIVATE_KEY (or X402_MODE=test for testing)."
        )

    @classmethod
    def _build_solana(cls, config: X402Config) -> BasePaymentProvider:
        """Construct a real ``SolanaAdapter`` (lazy imports solana-py)."""
        from ag402_core.payment.solana_adapter import SolanaAdapter

        if not config.solana_private_key:
            raise ConfigError(
                "SOLANA_PRIVATE_KEY is required for the Solana payment provider."
            )

        return SolanaAdapter(
            private_key=config.solana_private_key,
            rpc_url=config.solana_rpc_url,
            usdc_mint=config.usdc_mint_address,
            rpc_backup_url=config.solana_rpc_backup_url,
        )


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""
