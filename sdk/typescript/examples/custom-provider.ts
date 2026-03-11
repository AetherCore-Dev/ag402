/**
 * Custom payment provider example.
 *
 * Shows how to implement a real PaymentProvider by conforming to the
 * PaymentProvider interface. Swap the mock broadcast logic with a
 * real Solana USDC transfer using @solana/web3.js or @ag402/solana.
 *
 * Run with: npx tsx examples/custom-provider.ts
 */

import {
  createX402Fetch,
  InMemoryWallet,
  type PaymentProvider,
  type X402PaymentChallenge,
} from "../src/index.js";

// --- Implement your PaymentProvider ---

const myProvider: PaymentProvider = {
  /**
   * Broadcast the on-chain payment.
   *
   * @param challenge - parsed x402 challenge (chain, token, amount, address)
   * @param requestId - 32-char hex idempotency key; embed in tx memo for server dedup
   * @returns on-chain tx hash
   */
  async pay(challenge: X402PaymentChallenge, requestId: string): Promise<string> {
    console.log(
      `[provider] paying ${challenge.amount} ${challenge.token} ` +
      `on ${challenge.chain} to ${challenge.address} (requestId: ${requestId})`
    );

    // TODO: replace with real Solana USDC transfer:
    //   const tx = await buildAndSendUsdcTransfer({
    //     to: challenge.address,
    //     amount: parseFloat(challenge.amount),
    //     memo: requestId,
    //   });
    //   return tx.signature;

    // Simulated broadcast (remove in production):
    await new Promise((r) => setTimeout(r, 50));
    return `simulated_tx_${requestId.slice(0, 8)}`;
  },

  getAddress(): string {
    // Return your wallet's public key / payer address
    return "YourWalletPublicKeyHere";
  },
};

// --- Use the provider ---

async function main() {
  const wallet = new InMemoryWallet(50);

  const apiFetch = createX402Fetch({
    wallet,
    provider: myProvider,
    config: { maxAmountPerCall: 2.00, debug: true },
    paymentTimeoutMs: 15_000, // 15s timeout; wallet rolled back if exceeded
  });

  try {
    const res = await apiFetch("https://api.example.com/paid-data");
    console.log("Status:", res.status, "| paymentMade:", res.x402.paymentMade);
  } catch (err) {
    console.error("Fetch error:", err);
  }
}

main();
