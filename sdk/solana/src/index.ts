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

  // pay() and fromEnv() are stubbed here — implemented in Task 5.
  // This keeps the TDD red-green cycle: tests written first (Task 3), then stubs
  // make constructor/getAddress tests green, then full pay() implemented in Task 5.
  async pay(_challenge: X402PaymentChallenge, _requestId: string): Promise<string> {
    throw new Error("pay() not implemented yet");
  }
}

// ─── fromEnv (stub — implemented in Task 5) ──────────────────────────────────
export function fromEnv(_options?: { rpcUrl?: string }): SolanaPaymentProvider {
  throw new Error("fromEnv() not implemented yet");
}
