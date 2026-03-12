---
name: multi-role-review
description: Use before finishing any development branch — dispatches parallel security, architecture, DX, and production-readiness reviewers, then synthesizes findings and iterates until all critical issues are resolved
---

# Multi-Role Review

Dispatch parallel reviewers covering Security, Architecture, Developer Experience, and Production Readiness. Synthesize findings, fix all critical issues, and iterate until clean.

**Announce at start:** "I'm using the multi-role-review skill."

**Core principle:** Four independent reviewers in parallel → synthesize → fix → repeat until zero critical issues.

---

## When to Use

- **Required:** Before `finishing-a-development-branch` on any non-trivial feature
- **Required:** Before any npm/PyPI/crates publish
- **Optional:** After a large refactor or security-sensitive change

**Called by:** `subagent-driven-development` (Step 6, before finishing)

---

## The Process

```
Round N
├── Dispatch 4 reviewer subagents IN PARALLEL
│   ├── Security Reviewer
│   ├── Architecture Reviewer
│   ├── Developer Experience Reviewer
│   └── Production Readiness Reviewer
├── Synthesize all findings
│   ├── CRITICAL  — must fix before proceeding
│   ├── IMPORTANT — fix now unless strong reason not to
│   └── MINOR     — log, skip for now
├── Any CRITICAL or IMPORTANT issues?
│   ├── yes → dispatch implementer, fix, re-run Round N+1
│   └── no  → ✅ Done, proceed to finishing-a-development-branch
└── Max 5 rounds → escalate to human if still failing
```

---

## Reviewer Roles

### Role 1: Security Reviewer

Focus exclusively on security attack surfaces. Do NOT comment on architecture or DX.

**Checklist (always cover all):**

**Input validation**
- [ ] Are all user/external inputs validated before use?
- [ ] Are numeric boundaries tested (zero, negative, overflow, sub-minimum)?
- [ ] Are string inputs sanitised (injection, header injection, path traversal `../`, null bytes)?
- [ ] Can any input cause silent wrong-result (e.g. `Math.round(0.5) = 1`, not 0)?
- [ ] JS/TS: `NaN`, `Infinity`, `-Infinity` are NOT caught by `x < 0` — is `!isFinite(x)` used for all numeric validation?
- [ ] Are regex patterns anchored? (`re.fullmatch` in Python; `/^...$/.test()` in JS — partial match allows bypass)
- [ ] JS/TS: no user-controlled keys in `Object.assign`, spread, or dynamic property access (prototype pollution)

**Cryptographic / key handling**
- [ ] Are private keys decoded with a library that throws on invalid input (not silent fallback)?
- [ ] Are secrets never logged or included in error messages?
- [ ] Are HMAC/signature verifications constant-time (no early return on first mismatch — timing oracle)?
- [ ] Are new signing keys at least 32 bytes of entropy?

**Financial / transactional logic**
- [ ] Is every "success" response from an external SDK verified (e.g. `confirmTransaction().value.err`)?
- [ ] Can a transaction succeed externally but fail internally, causing deduction with no value delivered?
- [ ] Is zero-value transfer possible (sends nothing but costs fees)?
- [ ] Is self-transfer possible (src == dst)?
- [ ] After any irreversible operation (payment broadcast, DB write, file commit): do ALL downstream paths — including catch/finally — handle partial state safely? No exception may leave the system inconsistent after money/data has moved.
- [ ] Is the operation idempotent? Can it be safely retried if the response is lost?

**Network / SSRF**
- [ ] Are network failures handled without leaving state inconsistent?
- [ ] Are RPC/API success responses checked for application-level errors (not just HTTP 200)?
- [ ] Do outbound HTTP/socket calls block private IPs (10.x, 172.16.x, 192.168.x), localhost, metadata endpoints (169.254.x), and non-HTTPS schemes? (SSRF)

**Configuration misuse**
- [ ] Can a valid-looking config silently target the wrong environment (e.g. mainnet RPC + testnet token, prod key + staging endpoint)?
- [ ] Are misconfiguration errors detected at startup (constructor/init), not at first runtime use?
- [ ] Are secrets passed via env vars or files, not CLI arguments (visible in `ps aux`)?

**Concurrency**
- [ ] No TOCTOU (check-then-act) races at trust boundaries?
- [ ] Multi-step DB operations use transactions or atomic operations (INSERT OR IGNORE)?
- [ ] Shared mutable state is protected (lock, queue, atomic)?

**Output safety**
- [ ] Can any output value flow into HTTP headers, SQL, shell commands, file paths, or log lines without escaping?
- [ ] Does `getAddress()` / equivalent strip control characters (`\r`, `\n`, `"`, `'`)?

**Supply chain**
- [ ] All new dependencies audited (`npm audit` / `pip-audit` / `cargo audit`)?
- [ ] No new dep with known CVEs?
- [ ] Versions pinned or range-constrained (not `*` or `latest`)?
- [ ] No new dep whose name is suspiciously close to a well-known package (typosquatting)?

**Verdict format:**
```
SECURITY REVIEW — Round N

CRITICAL (must fix):
- [issue]: [exact code location] — [attack scenario]

IMPORTANT (fix now):
- [issue]: [exact code location] — [risk]

MINOR (optional):
- [issue]

VERDICT: ❌ CRITICAL ISSUES / ⚠️ IMPORTANT ONLY / ✅ CLEAN
```

---

### Role 2: Architecture Reviewer

Focus on design quality, boundaries, and maintainability. Do NOT comment on security or DX.

**Checklist:**

**Boundaries and responsibilities**
- [ ] Does each module/class have one clear responsibility?
- [ ] Are public interfaces minimal — only what callers need?
- [ ] Are internals hidden (private fields, unexported functions)?

**Error handling**
- [ ] Do errors surface at the right level (not swallowed, not over-propagated)?
- [ ] Are error messages actionable (include what went wrong AND what to do)?
- [ ] Are all error paths tested?

**State management**
- [ ] Is mutable state minimised? Are there race conditions?
- [ ] Is state consistent after partial failures?

**Abstraction quality**
- [ ] Are there premature abstractions (one-use utilities, over-engineered factories)?
- [ ] Are there missing abstractions (repeated logic that belongs together)?
- [ ] YAGNI: is everything present actually needed now?

**Testability**
- [ ] Can units be tested in isolation (no hidden global state, injectable deps)?
- [ ] Are side effects (network, filesystem, time) isolated or mockable?

**Verdict format:**
```
ARCHITECTURE REVIEW — Round N

CRITICAL:
IMPORTANT:
MINOR:
VERDICT: ❌ / ⚠️ / ✅
```

---

### Role 3: Developer Experience Reviewer

Focus on how developers use this code. Do NOT comment on security or internals.

**Checklist:**

**Public API**
- [ ] Do README examples actually work with the current implementation?
- [ ] Do TypeScript types / Python type hints match what the runtime code accepts?
- [ ] Are default values safe and unsurprising?
- [ ] Are required vs optional parameters clear?

**Error messages**
- [ ] Do errors tell the developer what went wrong AND how to fix it?
- [ ] Are error messages free of internal jargon?
- [ ] Does the most common misconfiguration produce a clear error immediately (not at runtime hours later)?

**Documentation**
- [ ] Is the README accurate for the current version?
- [ ] Are there working quickstart examples?
- [ ] Are non-obvious behaviours (e.g. "confirmTransaction resolves even on failure") explained?
- [ ] Are exported constants/types documented?

**Onboarding**
- [ ] Can a new user go from zero to working in < 5 minutes?
- [ ] Are environment variable names consistent between docs and code?

**Verdict format:**
```
DX REVIEW — Round N

CRITICAL:
IMPORTANT:
MINOR:
VERDICT: ❌ / ⚠️ / ✅
```

---

### Role 4: Production Readiness Reviewer

Focus on what breaks in real deployments. Do NOT comment on architecture or DX.

**Checklist:**

**Release artifacts**
- [ ] Does `package.json` / `pyproject.toml` include all required files (LICENSE, README, CHANGELOG)?
- [ ] Is the version number correct and consistent across all manifests?
- [ ] Is the build (ESM+CJS, wheels, etc.) reproducible from source?
- [ ] Are all peer/runtime dependencies explicitly declared with correct version ranges?

**Environment parity**
- [ ] Do devnet defaults prevent accidental mainnet use?
- [ ] Are there runtime guards that catch wrong-environment config at startup?
- [ ] Are there differences between test environment and production that could mask bugs?

**Observability**
- [ ] Are failures logged with enough context to debug?
- [ ] Does the library surface the root cause (not just "payment failed")?

**Dependency risk**
- [ ] Are transitive dependencies pinned or bounded to prevent supply-chain surprises?
- [ ] Are optional/peer dependencies clearly marked?

**CI / publishing**
- [ ] Does CI run tests before publish?
- [ ] Is the publish workflow gated on test pass + lint pass?
- [ ] Is the release trigger (tag, workflow_dispatch, release event) documented?

**Verdict format:**
```
PRODUCTION READINESS REVIEW — Round N

CRITICAL:
IMPORTANT:
MINOR:
VERDICT: ❌ / ⚠️ / ✅
```

---

## Synthesis Step (after each round)

After all 4 reviewers complete, synthesize:

```
═══════════════════════════════════════
MULTI-ROLE REVIEW — Round N — SYNTHESIS
═══════════════════════════════════════

CRITICAL (N issues — MUST FIX):
1. [Source: Security] [description] — [file:line]
2. [Source: Architecture] ...

IMPORTANT (N issues — FIX NOW):
1. [Source: DX] ...

MINOR (N issues — skipping):
1. ...

OVERALL VERDICT: ❌ BLOCKING / ⚠️ FIXABLE / ✅ APPROVED
```

**Routing after synthesis:**
- Any CRITICAL → dispatch implementer, fix, re-run full round
- Only IMPORTANT → dispatch implementer, fix, re-run full round
- Only MINOR → ✅ proceed to `finishing-a-development-branch`
- Round > 5 → escalate to human: "Review loop exceeded 5 rounds. Human input needed."

---

## Dispatch Instructions

**All 4 reviewers launch IN PARALLEL** (single message, 4 Agent tool calls).

Each reviewer subagent receives:
- Their specific role prompt (from the Role sections above)
- The list of files to review (extract from git diff or provide explicitly)
- The spec/design document path
- The round number
- Explicit instruction: "Review only your assigned role. Do not comment on other roles."

**Model selection:**
- All 4 reviewers: most capable model (review requires judgment)
- Implementer fixing issues: standard model

---

## Integration with Full Pipeline

```
brainstorming
    ↓
writing-plans
    ↓
subagent-driven-development (per task: implement → spec review → quality review)
    ↓
multi-role-review  ← THIS SKILL (replaces ad-hoc review)
    ↓
finishing-a-development-branch
```

**In `subagent-driven-development`:** After all tasks complete and final code reviewer approves, invoke `multi-role-review` before `finishing-a-development-branch`.

---

## Red Flags

**Never:**
- Run reviewers sequentially (wastes time — they're independent)
- Let one reviewer comment on another's domain (dilutes focus)
- Skip a review role ("probably fine" is how bugs ship)
- Mark CRITICAL issues as MINOR to move faster
- Proceed to `finishing-a-development-branch` with open CRITICAL or IMPORTANT issues
- Count the same issue twice across roles in synthesis

**Always:**
- Provide exact file paths and line numbers in findings
- Include the attack scenario / risk description (not just "this is bad")
- Run the full test suite after fixing issues before re-reviewing
