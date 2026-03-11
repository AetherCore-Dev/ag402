import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// ─── Mock @solana/web3.js ────────────────────────────────────────────────────
// Hoisted by Vitest. Factory runs once; vi.clearAllMocks() in beforeEach
// resets call history while preserving factory return values.
vi.mock("@solana/web3.js", () => {
  const mockPublicKey = {
    toBase58: vi.fn().mockReturnValue("PayerPubkey1111111111111111111111111111111"),
    toString: vi.fn().mockReturnValue("PayerPubkey1111111111111111111111111111111"),
  };
  const mockKeypair = {
    publicKey: mockPublicKey,
    secretKey: new Uint8Array(64),
  };
  return {
    Connection: vi.fn().mockImplementation(() => ({
      getLatestBlockhash: vi.fn().mockResolvedValue({
        blockhash: "EkSnNWid2cvwEVnVx9aBqawnmiCNiDgp3gUdkDPTKN1N",
        lastValidBlockHeight: 999999,
      }),
      sendTransaction: vi.fn().mockResolvedValue("5xFakeTxSignature111111111111111111111111111111"),
      confirmTransaction: vi.fn().mockResolvedValue({ value: { err: null } }),
    })),
    Keypair: {
      fromSecretKey: vi.fn().mockReturnValue(mockKeypair),
    },
    PublicKey: vi.fn().mockImplementation((addr: string) => ({
      toBase58: () => addr,
      toString: () => addr,
    })),
    Transaction: vi.fn().mockImplementation(() => ({
      add: vi.fn().mockReturnThis(),
    })),
    LAMPORTS_PER_SOL: 1_000_000_000,
  };
});

// ─── Mock bs58 ───────────────────────────────────────────────────────────────
vi.mock("bs58", () => ({
  default: {
    decode: vi.fn().mockReturnValue(new Uint8Array(64)),
  },
}));

// ─── Mock @solana/spl-token ──────────────────────────────────────────────────
vi.mock("@solana/spl-token", () => ({
  getOrCreateAssociatedTokenAccount: vi.fn().mockResolvedValue({
    address: {
      toBase58: () => "PayerATA1111111111111111111111111111111111",
      toString: () => "PayerATA1111111111111111111111111111111111",
    },
  }),
  createTransferCheckedInstruction: vi.fn().mockReturnValue({ programId: "tokenProg", data: new Uint8Array() }),
  TOKEN_PROGRAM_ID: { toBase58: () => "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA" },
}));

// ─── Mock @solana/spl-memo ───────────────────────────────────────────────────
vi.mock("@solana/spl-memo", () => ({
  createMemoInstruction: vi.fn().mockReturnValue({ programId: "memoProg", data: new Uint8Array() }),
}));

// ─── Import SUT (after mocks) ────────────────────────────────────────────────
import { SolanaPaymentProvider, fromEnv } from "../index.ts";

// ─── Shared reset ────────────────────────────────────────────────────────────
// vi.clearAllMocks() resets call history between tests while preserving
// factory mock return values (unlike vi.resetAllMocks() which removes them).
beforeEach(() => {
  vi.clearAllMocks();
});

// ─── Test: Constructor ───────────────────────────────────────────────────────
describe("SolanaPaymentProvider — constructor", () => {
  // A syntactically valid base58 string of appropriate length
  const VALID_KEY = "4NMwxzmYj2uvHuq8xoqhY8RXg63KSVJM1DXkpbmkUY7YQWoVrk7DqEDsomePvYKqU1h7H4P1DpxJnrZMHNF6Abt";

  it("constructs successfully with a valid base58 private key", () => {
    expect(() => new SolanaPaymentProvider({ privateKey: VALID_KEY })).not.toThrow();
  });

  it("uses devnet as default rpcUrl", async () => {
    const { Connection } = await import("@solana/web3.js");
    new SolanaPaymentProvider({ privateKey: VALID_KEY });
    expect(Connection).toHaveBeenCalledWith(
      "https://api.devnet.solana.com",
      expect.anything()
    );
  });

  it("uses custom rpcUrl when provided", async () => {
    const { Connection } = await import("@solana/web3.js");
    new SolanaPaymentProvider({
      privateKey: VALID_KEY,
      rpcUrl: "https://api.mainnet-beta.solana.com",
    });
    expect(Connection).toHaveBeenCalledWith(
      "https://api.mainnet-beta.solana.com",
      expect.anything()
    );
  });

  it("throws when given an invalid base58 private key", async () => {
    const bs58 = await import("bs58");
    // Simulate bs58.decode throwing on invalid input
    vi.mocked(bs58.default.decode).mockImplementationOnce(() => {
      throw new Error("Non-base58 character");
    });
    expect(() => new SolanaPaymentProvider({ privateKey: "not-valid-base58!!!" })).toThrow();
  });
});

// ─── Test: getAddress() ──────────────────────────────────────────────────────
describe("SolanaPaymentProvider — getAddress()", () => {
  const VALID_KEY = "4NMwxzmYj2uvHuq8xoqhY8RXg63KSVJM1DXkpbmkUY7YQWoVrk7DqEDsomePvYKqU1h7H4P1DpxJnrZMHNF6Abt";

  it("returns a base58 public key string", () => {
    const provider = new SolanaPaymentProvider({ privateKey: VALID_KEY });
    const addr = provider.getAddress();
    expect(typeof addr).toBe("string");
    expect(addr.length).toBeGreaterThan(0);
  });

  it("does not contain CR, LF, or quotes (header injection safety)", () => {
    const provider = new SolanaPaymentProvider({ privateKey: VALID_KEY });
    const addr = provider.getAddress();
    expect(addr).not.toMatch(/[\r\n"]/);
  });
});

// ─── Test: pay() happy path ──────────────────────────────────────────────────
describe("SolanaPaymentProvider — pay() happy path", () => {
  const VALID_KEY = "4NMwxzmYj2uvHuq8xoqhY8RXg63KSVJM1DXkpbmkUY7YQWoVrk7DqEDsomePvYKqU1h7H4P1DpxJnrZMHNF6Abt";
  const VALID_CHALLENGE: { chain: string; token: string; amount: string; address: string } = {
    chain: "solana",
    token: "USDC",
    amount: "0.05",
    address: "SellerAddr111111111111111111111111111111111",
  };
  const REQUEST_ID = "abcdef1234567890abcdef1234567890";

  it("returns a non-empty tx signature string", async () => {
    const provider = new SolanaPaymentProvider({ privateKey: VALID_KEY });
    const txHash = await provider.pay(VALID_CHALLENGE, REQUEST_ID);
    expect(typeof txHash).toBe("string");
    expect(txHash.length).toBeGreaterThan(0);
  });

  it("memo instruction is called with exactly 'Ag402-v1|{requestId}'", async () => {
    const { createMemoInstruction } = await import("@solana/spl-memo");
    const provider = new SolanaPaymentProvider({ privateKey: VALID_KEY });
    await provider.pay(VALID_CHALLENGE, REQUEST_ID);
    expect(createMemoInstruction).toHaveBeenCalledWith(
      `Ag402-v1|${REQUEST_ID}`,
      expect.any(Array)
    );
  });

  it("transfer_checked is called with correct lamport count (0.05 USDC = 50_000 lamports)", async () => {
    const { createTransferCheckedInstruction } = await import("@solana/spl-token");
    const provider = new SolanaPaymentProvider({ privateKey: VALID_KEY });
    await provider.pay(VALID_CHALLENGE, REQUEST_ID);
    expect(createTransferCheckedInstruction).toHaveBeenCalledWith(
      expect.anything(),  // payerAta.address
      expect.anything(),  // usdcMint
      expect.anything(),  // recipientAta.address
      expect.anything(),  // payerPubkey
      BigInt(50_000),     // lamports: 0.05 × 10^6
      6,                  // USDC_DECIMALS
      [],
      expect.anything()   // TOKEN_PROGRAM_ID
    );
  });

  it("getOrCreateAssociatedTokenAccount is called twice (payer ATA + recipient ATA)", async () => {
    const { getOrCreateAssociatedTokenAccount } = await import("@solana/spl-token");
    const provider = new SolanaPaymentProvider({ privateKey: VALID_KEY });
    await provider.pay(VALID_CHALLENGE, REQUEST_ID);
    expect(getOrCreateAssociatedTokenAccount).toHaveBeenCalledTimes(2);
  });
});

// ─── Test: pay() error handling ──────────────────────────────────────────────
describe("SolanaPaymentProvider — pay() error handling", () => {
  const VALID_KEY = "4NMwxzmYj2uvHuq8xoqhY8RXg63KSVJM1DXkpbmkUY7YQWoVrk7DqEDsomePvYKqU1h7H4P1DpxJnrZMHNF6Abt";
  const REQUEST_ID = "abcdef1234567890abcdef1234567890";

  it("throws immediately for chain !== 'solana', without calling RPC", async () => {
    const { Connection } = await import("@solana/web3.js");
    // Track the connection instance created for this provider
    const provider = new SolanaPaymentProvider({ privateKey: VALID_KEY });
    // Get the mock connection instance (Connection is called as constructor → result is last mock call's return)
    const mockConn = vi.mocked(Connection).mock.results.at(-1)?.value as {
      sendTransaction: ReturnType<typeof vi.fn>;
    };

    await expect(
      provider.pay({ chain: "base", token: "USDC", amount: "0.05", address: "Addr" }, REQUEST_ID)
    ).rejects.toThrow(/Unsupported chain/);

    expect(mockConn.sendTransaction).not.toHaveBeenCalled();
  });

  it("throws immediately for token !== 'USDC', without calling RPC", async () => {
    const { Connection } = await import("@solana/web3.js");
    const provider = new SolanaPaymentProvider({ privateKey: VALID_KEY });
    const mockConn = vi.mocked(Connection).mock.results.at(-1)?.value as {
      sendTransaction: ReturnType<typeof vi.fn>;
    };

    await expect(
      provider.pay({ chain: "solana", token: "BONK", amount: "0.05", address: "Addr" }, REQUEST_ID)
    ).rejects.toThrow(/Unsupported token/);

    expect(mockConn.sendTransaction).not.toHaveBeenCalled();
  });

  it("throws when sendTransaction fails", async () => {
    const { Connection } = await import("@solana/web3.js");
    // Override Connection mock for this test — must include getLatestBlockhash
    vi.mocked(Connection).mockImplementationOnce(() => ({
      getLatestBlockhash: vi.fn().mockResolvedValue({ blockhash: "FakeHash", lastValidBlockHeight: 1 }),
      sendTransaction: vi.fn().mockRejectedValue(new Error("RPC connection refused")),
      confirmTransaction: vi.fn(),
    }));

    const provider = new SolanaPaymentProvider({ privateKey: VALID_KEY });
    await expect(
      provider.pay({ chain: "solana", token: "USDC", amount: "0.05", address: "Addr" }, REQUEST_ID)
    ).rejects.toThrow("RPC connection refused");
  });

  it("throws when confirmTransaction fails", async () => {
    const { Connection } = await import("@solana/web3.js");
    vi.mocked(Connection).mockImplementationOnce(() => ({
      getLatestBlockhash: vi.fn().mockResolvedValue({ blockhash: "FakeHash", lastValidBlockHeight: 1 }),
      sendTransaction: vi.fn().mockResolvedValue("5xFakeSig"),
      confirmTransaction: vi.fn().mockRejectedValue(new Error("Confirmation timeout")),
    }));

    const provider = new SolanaPaymentProvider({ privateKey: VALID_KEY });
    await expect(
      provider.pay({ chain: "solana", token: "USDC", amount: "0.05", address: "Addr" }, REQUEST_ID)
    ).rejects.toThrow("Confirmation timeout");
  });
});

// ─── Test: fromEnv() ─────────────────────────────────────────────────────────
describe("fromEnv()", () => {
  const VALID_KEY = "4NMwxzmYj2uvHuq8xoqhY8RXg63KSVJM1DXkpbmkUY7YQWoVrk7DqEDsomePvYKqU1h7H4P1DpxJnrZMHNF6Abt";

  afterEach(() => {
    delete process.env.SOLANA_PRIVATE_KEY;
  });

  it("constructs provider from SOLANA_PRIVATE_KEY env var", () => {
    process.env.SOLANA_PRIVATE_KEY = VALID_KEY;
    expect(() => fromEnv()).not.toThrow();
  });

  it("throws a clear error when SOLANA_PRIVATE_KEY is not set", () => {
    delete process.env.SOLANA_PRIVATE_KEY;
    expect(() => fromEnv()).toThrow(/SOLANA_PRIVATE_KEY/);
  });

  it("passes custom rpcUrl to the underlying provider", async () => {
    const { Connection } = await import("@solana/web3.js");
    process.env.SOLANA_PRIVATE_KEY = VALID_KEY;
    fromEnv({ rpcUrl: "https://api.mainnet-beta.solana.com" });
    expect(Connection).toHaveBeenCalledWith(
      "https://api.mainnet-beta.solana.com",
      expect.anything()
    );
  });
});
