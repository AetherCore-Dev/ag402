# @ag402/solana

Real Solana USDC on-chain payment provider for [`@ag402/fetch`](https://www.npmjs.com/package/@ag402/fetch).

Broadcasts genuine SPL USDC `transfer_checked` transactions. Each payment includes a `Ag402-v1|{requestId}` Memo for server-side idempotency — matching the Python `ag402-core` SDK behavior exactly.

## Installation

```bash
npm install @ag402/solana @ag402/fetch
```

## Usage

```typescript
import { createX402Fetch, InMemoryWallet } from "@ag402/fetch";
import { SolanaPaymentProvider, fromEnv } from "@ag402/solana";

// From environment variable (recommended for agents)
const provider = fromEnv();  // reads SOLANA_PRIVATE_KEY

// Or explicit constructor
const provider = new SolanaPaymentProvider({
  privateKey: "your-base58-private-key",
  rpcUrl: "https://api.mainnet-beta.solana.com",          // default: devnet
  usdcMint: "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  // mainnet USDC
});

const wallet = new InMemoryWallet(10);  // $10 spend budget
const apiFetch = createX402Fetch({ wallet, provider });

const res = await apiFetch("https://api.example.com/paid-endpoint");
console.log("tx:", res.x402.txHash);
```

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `privateKey` | **required** | Base58-encoded Solana private key |
| `rpcUrl` | `https://api.devnet.solana.com` | Solana RPC endpoint |
| `usdcMint` | `4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU` | USDC mint (devnet default) |

**Mainnet USDC mint:** `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SOLANA_PRIVATE_KEY` | Base58-encoded private key, used by `fromEnv()` |

## How It Works

Each `pay()` call:

1. Validates `chain === "solana"` and `token === "USDC"` — throws immediately otherwise
2. Converts amount string → lamports (`BigInt(Math.round(amount × 10^6))`)
3. Gets/creates payer Associated Token Account (ATA) via SPL Token Program
4. Gets/creates recipient ATA
5. Builds `transfer_checked` SPL instruction
6. Attaches Memo instruction: `Ag402-v1|{requestId}`
7. Signs, broadcasts, and awaits `"confirmed"` commitment
8. Returns the base58 transaction signature as `tx_hash`

Any failure in steps 3–7 throws an error, triggering `@ag402/fetch`'s automatic rollback.

## License

MIT
