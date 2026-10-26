import { describe, it, expect } from 'vitest';
import { createX402Fetch, MockPaymentProvider } from '../fetch.ts';
import { InMemoryWallet } from '../wallet.ts';

const paymentHeader = 'authorization';
const headerReplacements: Record<string, string>[] = [{}, { 'X-New': 'replacement' }];
const challengeHeaders = {
  'WWW-Authenticate': 'x402 chain="solana" token="USDC" amount="0.05" address="SellerAddr1111111111111111111"',
};
const challengeBody = 'payment required';
function makeFetch(): typeof fetch {
  return createX402Fetch({ wallet: new InMemoryWallet(1), provider: new MockPaymentProvider() });
}

import { createServer, type IncomingHttpHeaders } from 'node:http';

type SeenRequest = { method: string | undefined; headers: IncomingHttpHeaders; body: string };

async function withTransport(implementation: typeof fetch, run: (apiFetch: typeof fetch) => Promise<void>): Promise<void> {
  await run(createX402Fetch({
    wallet: new InMemoryWallet(1),
    provider: new MockPaymentProvider(),
    fetchImpl: implementation,
  }));
}

describe('fetch transport compatibility', () => {

  it.each([
    { asRequest: false, paid: false }, { asRequest: true, paid: false },
    { asRequest: false, paid: true }, { asRequest: true, paid: true },
  ])('keeps headers deleted by the first transport absent: %j', async ({ asRequest, paid }) => {
    const nativeFetch = globalThis.fetch;
    let calls = 0;
    const implementation: typeof fetch = (input, init) => {
      if (++calls === 1 && init) delete init.headers;
      return nativeFetch(input, init);
    };
    await withTransport(implementation, async (apiFetch) => {
      await withServer(async (url, seen) => {
        const init = { headers: { 'X-Strip': 'remove' } } as RequestInit;
        const input = asRequest ? new Request(url, { headers: { 'X-Request': 'kept' } }) : url;
        const response = await apiFetch(input, init);
        expect(response.status).toBe(200);
        expect(seen).toHaveLength(paid ? 2 : 1);
        for (const request of seen) {
          expect(request.headers['x-strip']).toBeUndefined();
          expect(request.headers['x-request']).toBe(asRequest ? 'kept' : undefined);
        }
        expect(Object.hasOwn(init, 'headers')).toBe(false);
      }, paid ? [402, 200] : [200]);
    });
  });

  it.each([
    { method: 'GET', paid: false }, { method: 'POST', paid: false },
    { method: 'GET', paid: true }, { method: 'POST', paid: true },
  ])('replays Request headers added by the transport: %j', async ({ method, paid }) => {
    const nativeFetch = globalThis.fetch;
    const implementation: typeof fetch = (input, init) => {
      if (input instanceof Request) input.headers.set('X-Client-Token', 'kept');
      return nativeFetch(input, init);
    };
    await withTransport(implementation, async (apiFetch) => {
      await withServer(async (url, seen) => {
        const response = await apiFetch(new Request(url, {
          method, ...(method === 'POST' ? { body: 'payload' } : {}),
        }));
        expect(response.status).toBe(200);
        expect(seen).toHaveLength(paid ? 2 : 1);
        for (const request of seen) expect(request.headers['x-client-token']).toBe('kept');
      }, paid ? [402, 200] : [200]);
    });
  });


  it.each([false, true])('preserves Request default headers (init supplied=%s)', async (withInit) => {
    const nativeFetch = globalThis.fetch;
    const implementation: typeof fetch = (input, init) => nativeFetch(input, {
      headers: { 'X-Default': 'kept' }, ...init,
    });
    await withTransport(implementation, async (apiFetch) => {
      await withServer(async (url, seen) => {
        const response = await apiFetch(new Request(url), withInit ? {} : undefined);
        expect(response.status).toBe(200);
        expect(seen[0].headers['x-default']).toBe('kept');
      }, [200]);
    });
  });

  it.each([
    { asRequest: false, paid: false }, { asRequest: true, paid: false },
    { asRequest: false, paid: true }, { asRequest: true, paid: true },
  ])('observes headers assigned by the transport: %j', async ({ asRequest, paid }) => {
    const nativeFetch = globalThis.fetch;
    const implementation: typeof fetch = (input, init) => {
      if (init && !init.headers) init.headers = { 'X-Default': 'kept' };
      return nativeFetch(input, init);
    };
    await withTransport(implementation, async (apiFetch) => {
      await withServer(async (url, seen) => {
        const response = await apiFetch(asRequest ? new Request(url) : url, { method: 'GET' });
        expect(response.status).toBe(200);
        expect(seen).toHaveLength(paid ? 2 : 1);
        for (const request of seen) expect(request.headers['x-default']).toBe('kept');
      }, paid ? [402, 200] : [200]);
    });
  });

  it.each([false, true])('preserves writable options forwarded to transports (headers=%s)', async (withHeaders) => {
    const nativeFetch = globalThis.fetch;
    const implementation: typeof fetch = (input, init) => {
      if (init) {
        init.method = 'PUT';
        init.body = 'transport payload';
      }
      return nativeFetch(input, init);
    };
    await withTransport(implementation, async (apiFetch) => {
      await withServer(async (url, seen) => {
        const response = await apiFetch(url, {
          method: 'POST', body: 'original payload',
          ...(withHeaders ? { headers: { 'X-Custom': 'kept' } } : {}),
        });
        expect(response.status).toBe(200);
        expect(seen).toHaveLength(2);
        for (const request of seen) {
          expect(request.method).toBe('PUT');
          expect(request.body).toBe('transport payload');
        }
      });
    });
  });

  it('allows a reusable body override on an already consumed Request', async () => {
    await withServer(async (url, seen) => {
      const input = new Request(url, { method: 'POST', body: 'consumed payload' });
      await input.text();
      const response = await makeFetch()(input, { body: 'replacement payload' });
      expect(response.status).toBe(200);
      expect(seen).toHaveLength(2);
      for (const request of seen) expect(request.body).toBe('replacement payload');
    });
  });


  it('preserves absent headers so custom transports can supply defaults', async () => {
    const nativeFetch = globalThis.fetch;
    const implementation: typeof fetch = (input, init) => nativeFetch(input, {
      headers: { 'X-Default': 'kept' }, ...init,
    });
    await withTransport(implementation, async (apiFetch) => {
      await withServer(async (url, seen) => {
        const response = await apiFetch(url);
        expect(response.status).toBe(200);
        expect(seen[0].headers['x-default']).toBe('kept');
      }, [200]);
    });
  });


  it.each([
    { kind: 'iterator', paid: false }, { kind: 'iterator', paid: true },
    { kind: 'generator', paid: false }, { kind: 'generator', paid: true },
    { kind: 'record-getter', paid: false }, { kind: 'record-getter', paid: true },
  ])('normalizes headers once before either send: %j', async ({ kind, paid }) => {
    let reads = 0;
    let headers: RequestInit['headers'];
    if (kind === 'iterator') {
      headers = new Headers({ 'X-Single': 'kept' }).entries() as unknown as RequestInit['headers'];
    } else if (kind === 'generator') {
      headers = (function* () { yield ['X-Single', 'kept']; })() as unknown as RequestInit['headers'];
    } else {
      headers = {
        get 'X-Single'(): string {
          if (++reads > 1) throw new Error('Header value read twice');
          return 'kept';
        },
      };
    }
    await withServer(async (url, seen) => {
      const response = await makeFetch()(url, { headers });
      expect(response.status).toBe(200);
      expect(seen).toHaveLength(paid ? 2 : 1);
      for (const request of seen) expect(request.headers['x-single']).toBe('kept');
    }, paid ? [402, 200] : [200]);
    if (kind === 'record-getter') expect(reads).toBe(1);
  });

  it.each([false, true])('accepts Request implementations exposing a byte body (paid=%s)', async (paid) => {
    const NativeRequest = globalThis.Request;
    class BufferedRequest extends NativeRequest {
      constructor(input: string | URL | Request, init?: RequestInit) {
        super(input, init);
        Object.defineProperty(this, 'body', { value: new TextEncoder().encode('payload') });
      }
    }
    globalThis.Request = BufferedRequest;
    try {
      await withServer(async (url, seen) => {
        const response = await makeFetch()(new BufferedRequest(url, { method: 'POST', body: 'payload' }));
        expect(response.status).toBe(200);
        expect(seen).toHaveLength(paid ? 2 : 1);
        for (const request of seen) expect(request.body).toBe('payload');
      }, paid ? [402, 200] : [200]);
    } finally {
      globalThis.Request = NativeRequest;
    }
  });

  it.each([
    { method: 'GET', paid: false }, { method: 'POST', paid: false },
    { method: 'GET', paid: true }, { method: 'POST', paid: true },
  ])('preserves URL input for alternate fetch implementations: %j', async ({ method, paid }) => {
    const nativeFetch = globalThis.fetch;
    const implementation: typeof fetch = async (input, init) => {
      if (typeof input !== 'string' && !(input instanceof URL)) {
        throw new TypeError('This transport uses its own Request class');
      }
      return nativeFetch(input, init);
    };
    await withTransport(implementation, async (apiFetch) => {
      await withServer(async (url, seen) => {
        const response = await apiFetch(url, { method, body: method === 'POST' ? 'payload' : undefined });
        expect(response.status).toBe(200);
        expect(seen).toHaveLength(paid ? 2 : 1);
        expect(seen.every((request) => request.body === (method === 'POST' ? 'payload' : ''))).toBe(true);
      }, paid ? [402, 200] : [200]);
    });
  });

  it.each([
    { asRequest: false, paid: false }, { asRequest: true, paid: false },
    { asRequest: false, paid: true }, { asRequest: true, paid: true },
  ])('reads lazy body and headers once: %j', async ({ asRequest, paid }) => {
    let bodyReads = 0;
    let headerReads = 0;
    const init: RequestInit = {
      method: 'POST',
      get body() {
        if (++bodyReads > 1) throw new Error('body read twice');
        return 'lazy payload';
      },
      get headers() {
        if (++headerReads > 1) throw new Error('headers read twice');
        return { 'X-Lazy': 'kept' };
      },
    };
    await withServer(async (url, seen) => {
      const response = await makeFetch()(asRequest ? new Request(url) : url, init);
      expect(response.status).toBe(200);
      expect(seen).toHaveLength(paid ? 2 : 1);
      for (const request of seen) {
        expect(request.method).toBe('POST');
        expect(request.body).toBe('lazy payload');
        expect(request.headers['x-lazy']).toBe('kept');
      }
    }, paid ? [402, 200] : [200]);
    expect(bodyReads).toBe(1);
    expect(headerReads).toBe(1);
  });

  it('preserves inherited non-enumerable init getters and their receiver', async () => {
    const reads = { method: 0, body: 0, headers: 0 };
    class LazyInit {
      #value = 'inherited payload';
      get method() { reads.method++; return 'POST'; }
      get body() { reads.body++; return this.#value; }
      get headers() { reads.headers++; return { 'X-Lazy': this.#value }; }
    }
    await withServer(async (url, seen) => {
      const response = await makeFetch()(new Request(url), new LazyInit());
      expect(response.status).toBe(200);
      expect(seen).toHaveLength(2);
      for (const request of seen) {
        expect(request.method).toBe('POST');
        expect(request.body).toBe('inherited payload');
        expect(request.headers['x-lazy']).toBe('inherited payload');
      }
    });
    expect(reads).toEqual({ method: 1, body: 1, headers: 1 });
  });

  it.each([false, true])('does not evaluate unused option getters (Request=%s)', async (asRequest) => {
    const init: RequestInit & { unusedOption?: string } = {
      get unusedOption(): string { throw new Error('Unused option was evaluated'); },
    };
    await withServer(async (url, seen) => {
      const response = await makeFetch()(asRequest ? new Request(url) : url, init);
      expect(response.status).toBe(200);
      expect(seen).toHaveLength(2);
    });
  });

  it('cancels both unsent body branches when the transport rejects before reading', async () => {
    let cancellations = 0;
    let finishCancellation!: () => void;
    const cancelled = new Promise<void>((resolve) => { finishCancellation = resolve; });
    const stream = new ReadableStream<Uint8Array>({
      pull(controller) { controller.enqueue(Uint8Array.of(1)); },
      cancel() { cancellations++; finishCancellation(); },
    });
    const request = new Request('http://127.0.0.1/unused', {
      method: 'POST', body: stream, duplex: 'half',
    } as RequestInit & { duplex: 'half' });
    await withTransport(async () => { throw new Error('transport failed'); }, async (apiFetch) => {
      await expect(apiFetch(request)).rejects.toThrow('transport failed');
    });
    let timer: ReturnType<typeof setTimeout> | undefined;
    try {
      await Promise.race([
        cancelled,
        new Promise<never>((_, reject) => {
          timer = setTimeout(() => reject(new Error('Body was not cancelled')), 1000);
        }),
      ]);
    } finally {
      if (timer) clearTimeout(timer);
    }
    expect(cancellations).toBe(1);
  });
});


async function withServer(
  run: (url: string, seen: SeenRequest[]) => Promise<void>,
  statuses = [402, 200],
): Promise<void> {
  const seen: SeenRequest[] = [];
  const server = createServer(async (req, res) => {
    const chunks: Buffer[] = [];
    for await (const chunk of req) chunks.push(Buffer.from(chunk));
    seen.push({ method: req.method, headers: req.headers, body: Buffer.concat(chunks).toString() });
    const status = statuses[seen.length - 1] ?? 500;
    if (status === 402) {
      res.writeHead(402, challengeHeaders);
      res.end(challengeBody);
    } else {
      res.writeHead(status);
      res.end('result');
    }
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('Missing server address');
  try {
    await run('http://127.0.0.1:' + address.port + '/paid', seen);
  } finally {
    server.closeAllConnections();
    await new Promise<void>((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  }
}

describe('native fetch request replay', () => {
  it('forwards fetch transport options on both attempts', async () => {
    const transport = {};
    const observed: unknown[] = [];
    const nativeFetch = globalThis.fetch;
    const fetchImpl: typeof fetch = async (input, init) => {
      const { transportTag, ...requestInit } = (init ?? {}) as RequestInit & { transportTag?: unknown };
      observed.push(transportTag);
      return nativeFetch(input, requestInit);
    };

    await withServer(async (url) => {
      const apiFetch = createX402Fetch({
        wallet: new InMemoryWallet(1),
        provider: new MockPaymentProvider(),
        fetchImpl,
      });
      const init = { transportTag: transport } as RequestInit & { transportTag: object };
      const response = await apiFetch(url, init);
      expect(response.status).toBe(200);
      expect(observed).toEqual([transport, transport]);
    });
  });

  it('preserves Request headers on a paid GET', async () => {
    await withServer(async (url, seen) => {
      const response = await makeFetch()(new Request(url, { headers: { 'X-Tenant': 'tenant-a' } }));
      expect(response.status).toBe(200);
      expect(seen).toHaveLength(2);
      expect(seen[0].headers['x-tenant']).toBe('tenant-a');
      expect(seen[1].headers['x-tenant']).toBe('tenant-a');
      expect(seen[1].headers[paymentHeader]).toBeTruthy();
    });
  });

  it('replays a consumed POST Request with the same JSON bytes and content type', async () => {
    await withServer(async (url, seen) => {
      const body = JSON.stringify({ prompt: 'hello', count: 2 });
      const response = await makeFetch()(new Request(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Tenant': 'tenant-a' },
        body,
      }));
      expect(response.status).toBe(200);
      expect(seen).toHaveLength(2);
      for (const request of seen) {
        expect(request.method).toBe('POST');
        expect(request.body).toBe(body);
        expect(request.headers['content-type']).toBe('application/json');
        expect(request.headers['x-tenant']).toBe('tenant-a');
      }
    });
  });

  it.each(headerReplacements)('respects init.headers replacement: %j', async (headers) => {
    await withServer(async (url, seen) => {
      const request = new Request(url, { headers: { 'X-Old': 'discarded' } });
      const response = await makeFetch()(request, { headers });
      expect(response.status).toBe(200);
      expect(seen).toHaveLength(2);
      for (const entry of seen) {
        expect(entry.headers['x-old']).toBeUndefined();
        expect(entry.headers['x-new']).toBe(headers['X-New']);
      }
    });
  });

  it('preserves effective method and body overrides', async () => {
    await withServer(async (url, seen) => {
      const original = new Request(url, { method: 'POST', body: 'old body' });
      const response = await makeFetch()(original, {
        method: 'PUT', body: 'replacement body', headers: { 'Content-Type': 'text/plain' },
      });
      expect(response.status).toBe(200);
      expect(seen).toHaveLength(2);
      for (const request of seen) {
        expect(request.method).toBe('PUT');
        expect(request.body).toBe('replacement body');
        expect(request.headers['content-type']).toBe('text/plain');
      }
    });
  });

  it('replays a URL plus a one-shot stream body', async () => {
    await withServer(async (url, seen) => {
      const body = new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(new TextEncoder().encode('first-'));
          controller.enqueue(new TextEncoder().encode('second'));
          controller.close();
        },
      });
      const init = { method: 'POST', body, duplex: 'half' } as RequestInit & { duplex: 'half' };
      const response = await makeFetch()(url, init);
      expect(response.status).toBe(200);
      expect(seen.map((entry) => entry.body)).toEqual(['first-second', 'first-second']);
    });
  });

  it('keeps multipart boundaries and body bytes aligned when replaying a Request', async () => {
    await withServer(async (url, seen) => {
      const form = new FormData();
      form.set('prompt', 'hello');
      form.set('file', new Blob(['file contents'], { type: 'text/plain' }), 'input.txt');
      const response = await makeFetch()(new Request(url, { method: 'POST', body: form }));
      expect(response.status).toBe(200);
      expect(seen).toHaveLength(2);
      expect(seen[1].body).toBe(seen[0].body);
      expect(seen[1].headers['content-type']).toBe(seen[0].headers['content-type']);
      expect(seen[1].body).toContain('file contents');
    });
  });

  it('preserves URL plus init POST behavior', async () => {
    await withServer(async (url, seen) => {
      const response = await makeFetch()(url, {
        method: 'POST', body: 'plain body', headers: { 'X-Tenant': 'tenant-a' },
      });
      expect(response.status).toBe(200);
      expect(seen.map((entry) => entry.body)).toEqual(['plain body', 'plain body']);
      expect(seen[1].headers['x-tenant']).toBe('tenant-a');
    });
  });

  it('passes through a POST that needs no payment', async () => {
    await withServer(async (url, seen) => {
      const response = await makeFetch()(new Request(url, { method: 'POST', body: 'free body' }));
      expect(response.status).toBe(200);
      expect(seen).toHaveLength(1);
      expect(seen[0].body).toBe('free body');
      expect(seen[0].headers[paymentHeader]).toBeUndefined();
    }, [200]);
  });

  it('does not make another payment retry after a second 402', async () => {
    await withServer(async (url, seen) => {
      const response = await makeFetch()(new Request(url, { method: 'POST', body: 'body' }));
      expect(response.status).toBe(402);
      expect(seen).toHaveLength(2);
      expect(seen[1].body).toBe('body');
    }, [402, 402]);
  });
});
