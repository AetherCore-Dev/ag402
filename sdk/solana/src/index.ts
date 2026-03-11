/**
 * @ag402/solana — Solana USDC PaymentProvider for @ag402/fetch
 *
 * Implements real on-chain USDC transfers via SPL Token Program.
 * Fully aligned with Python ag402_core.payment.solana_adapter.SolanaAdapter.
 *
 * Usage:
 *   import { SolanaPaymentProvider, fromEnv } from "@ag402/solana";
 *   const provider = new SolanaPaymentProvider({ privateKey: process.env.SOLANA_PRIVATE_KEY! });
 *   const apiFetch = createX402Fetch({ wallet, provider });
 */

import {
  Connection,
  Keypair,
  PublicKey,
  Transaction,
} from "@solana/web3.js";
import {
  createTransferCheckedInstruction,
  getOrCreateAssociatedTokenAccount,
  TOKEN_PROGRAM_ID,
} from "@solana/spl-token";
import { createMemoInstruction } from "@solana/spl-memo";
import bs58 from "bs58";
import type { PaymentProvider, X402PaymentChallenge } from "@ag402/fetch";

// ─── Constants ───────────────────────────────────────────────────────────────

const DEVNET_RPC = "https://api.devnet.solana.com";
const DEVNET_USDC_MINT = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU";
/** USDC has 6 decimal places */
const USDC_DECIMALS = 6;

// ─── Options ─────────────────────────────────────────────────────────────────

export interface SolanaPaymentProviderOptions {
  /** Base58-encoded Solana private key — mirrors Python SOLANA_PRIVATE_KEY env var */
  privateKey: string;
  /** Solana RPC endpoint. Defaults to devnet. */
  rpcUrl?: string;
  /** USDC mint address. Defaults to devnet USDC mint. */
  usdcMint?: string;
}

// ─── SolanaPaymentProvider ───────────────────────────────────────────────────

export class SolanaPaymentProvider implements PaymentProvider {
  private readonly connection: Connection;
  private readonly keypair: Keypair;
  private readonly usdcMint: PublicKey;

  constructor(options: SolanaPaymentProviderOptions) {
    const rpcUrl = options.rpcUrl ?? DEVNET_RPC;
    const mintAddress = options.usdcMint ?? DEVNET_USDC_MINT;

    // bs58.decode() throws for invalid input — do NOT use Buffer.from(..., "base58")
    // which silently falls back to UTF-8 and produces garbage bytes.
    this.keypair = Keypair.fromSecretKey(bs58.decode(options.privateKey));
    this.connection = new Connection(rpcUrl, "confirmed");
    this.usdcMint = new PublicKey(mintAddress);
  }

  /**
   * Returns the payer's base58 public key.
   * Guaranteed to not contain CR, LF, or quotes (header injection safety —
   * mirrors @ag402/fetch buildAuthorization protection).
   */
  getAddress(): string {
    const addr = this.keypair.publicKey.toBase58();
    return addr.replace(/[\r\n"]/g, "");
  }

  /**
   * Pay the x402 challenge by broadcasting a real USDC transfer on Solana.
   * Mirrors Python SolanaAdapter.pay() exactly.
   *
   * Steps:
   *   1. Validate chain + token
   *   2. Parse amount string → lamports (× 10^6)
   *   3. Get/create payer ATA
   *   4. Get/create recipient ATA
   *   5. Build transfer_checked instruction
   *   6. Attach Memo: "Ag402-v1|{requestId}"
   *   7. Fetch blockhash, build tx, sign, send, confirm
   *   8. Return base58 tx signature
   */
  async pay(challenge: X402PaymentChallenge, requestId: string): Promise<string> {
    // Step 1: Validate — throw immediately, no RPC calls
    if (challenge.chain !== "solana") {
      throw new Error(
        `Unsupported chain: "${challenge.chain}". @ag402/solana only supports "solana".`
      );
    }
    if (challenge.token !== "USDC") {
      throw new Error(
        `Unsupported token: "${challenge.token}". @ag402/solana only supports "USDC".`
      );
    }

    // Step 2: Parse amount → integer lamports (BigInt required by SPL Token)
    const amountFloat = parseFloat(challenge.amount);
    if (!isFinite(amountFloat) || amountFloat <= 0) {
      throw new Error(`Invalid payment amount: "${challenge.amount}"`);
    }
    const lamports = BigInt(Math.round(amountFloat * Math.pow(10, USDC_DECIMALS)));

    const recipientPubkey = new PublicKey(challenge.address);
    const payerPubkey = this.keypair.publicKey;

    // Step 3: Get/create payer ATA
    const payerAta = await getOrCreateAssociatedTokenAccount(
      this.connection,
      this.keypair,
      this.usdcMint,
      payerPubkey
    );

    // Step 4: Get/create recipient ATA
    const recipientAta = await getOrCreateAssociatedTokenAccount(
      this.connection,
      this.keypair,
      this.usdcMint,
      recipientPubkey
    );

    // Step 5: Build transfer_checked instruction
    const transferIx = createTransferCheckedInstruction(
      payerAta.address,
      this.usdcMint,
      recipientAta.address,
      payerPubkey,
      lamports,
      USDC_DECIMALS,
      [],
      TOKEN_PROGRAM_ID
    );

    // Step 6: Attach Memo — mirrors Python: f"Ag402-v1|{request_id}"
    const memoIx = createMemoInstruction(`Ag402-v1|${requestId}`, [payerPubkey]);

    // Step 7: Fetch blockhash, build tx, sign, send, confirm.
    // recentBlockhash + feePayer MUST be set before sendTransaction.
    // confirmTransaction uses BlockheightBasedTransactionConfirmationStrategy
    // (string-only overload is deprecated in @solana/web3.js v1.98).
    const { blockhash, lastValidBlockHeight } =
      await this.connection.getLatestBlockhash("confirmed");
    const tx = new Transaction();
    tx.recentBlockhash = blockhash;
    tx.feePayer = payerPubkey;
    tx.add(transferIx, memoIx);

    const signature = await this.connection.sendTransaction(tx, [this.keypair]);
    await this.connection.confirmTransaction(
      { blockhash, lastValidBlockHeight, signature },
      "confirmed"
    );

    // Step 8: Return tx hash
    return signature;
  }
}

// ─── fromEnv ─────────────────────────────────────────────────────────────────

/**
 * Construct SolanaPaymentProvider from environment variables.
 * Mirrors Python config.py: reads SOLANA_PRIVATE_KEY.
 *
 * @throws {Error} if SOLANA_PRIVATE_KEY is not set
 */
export function fromEnv(options?: { rpcUrl?: string }): SolanaPaymentProvider {
  const privateKey = process.env.SOLANA_PRIVATE_KEY;
  if (!privateKey) {
    throw new Error(
      "SOLANA_PRIVATE_KEY environment variable is not set. " +
        "Set it to your base58-encoded Solana private key."
    );
  }
  return new SolanaPaymentProvider({ privateKey, ...options });
}
