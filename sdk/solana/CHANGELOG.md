# Changelog

## [0.1.0] — 2026-03-12

### Added
- `SolanaPaymentProvider` — implements `PaymentProvider` from `@ag402/fetch` for real Solana USDC on-chain payments
- `fromEnv()` — construct provider from `SOLANA_PRIVATE_KEY` environment variable
- `confirmationLevel` option — `"confirmed"` (default) or `"finalized"` for high-value payments
- SPL Token `transfer_checked` instruction with `Ag402-v1|{requestId}` Memo for server-side idempotency
- Full TypeScript types exported: `SolanaPaymentProviderOptions`, `SolanaPaymentProvider`, `fromEnv`
- ESM + CJS dual build

### Security
- On-chain transaction failure detection: `confirmTransaction().value.err` checked; throws on failure to prevent wallet deduction without USDC transfer
- ATA creation order: recipient ATA created first to minimise wasted SOL on failure
- `getAddress()` strips CR/LF/quotes to prevent HTTP header injection
