---
name: feature
description: Use when starting any new feature, bug fix, or significant change. Drives the full lifecycle: orientation → requirement clarification → design → implementation → multi-role review → fix → production readiness check. Runs autonomously until done; only pauses for genuine architectural forks or hard blockers that have exhausted the structured debugging protocol.
---

# Feature Development — Full Lifecycle Workflow

## Philosophy

Every feature goes through the complete cycle before it is considered done:

```
Orient → Clarify → Scale → Design → Implement → Review (3 roles) → Fix → Production check → Done
```

**Core principles (non-negotiable):**
- Elegant and minimal: zero unnecessary dependencies, zero over-engineering
- Security is a first-class citizen, not an afterthought
- Every feature must be production-ready, not prototype-ready
- UX matters: consider what real users will encounter, not just happy paths
- Observability is not optional: if you can't see it break, you can't fix it
- **Run autonomously to completion.** Every pause costs the user context-switching time. Interruptions are a last resort, not a default.

**Two categories of failure — different protocols:**
- **Diagnosable failures** (build error, test failure, lint, missing dep, config): resolve autonomously using the Structured Debugging Protocol. These must never reach the human.
- **Genuine forks** (two architecturally different paths with meaningfully different long-term consequences, or a security decision with no clear right answer): pause with a structured options presentation. This is the *only* valid interruption.

Attempting the same fix twice is not debugging — it is noise. Every attempt must falsify a specific hypothesis.

---

## Phase -1: Codebase Orientation

**Before writing a single line**, understand where this change lives.

Read selectively:
- Entry points that the feature will touch (CLI handler, API route, core module)
- Existing patterns for this type of operation (auth, storage, HTTP client, payment)
- Test structure: where do tests for this domain live? What fixtures exist?
- Recent commits on affected files: `git log --oneline -10 -- <file>` for surprise context
- **Language/runtime detection**: identify the stack early — linting, testing, building, and publishing commands differ completely across stacks

Answer these before moving on:
- Which files will change?
- What patterns does existing code use that I must match?
- Is there prior art I should reuse or mirror?
- Are there fragile areas nearby I must not disturb?
- Does this touch persistent state (DB schema, file format, config keys)? If yes, is there existing data that needs migration?

**Time-box.** Bug fix: 2–3 reads. New feature: 5–10 reads max.

---

## Phase 0: Requirement Clarification

**Ensure the requirement is unambiguous before writing anything.**

Ask yourself:
- Is the scope clear? What exactly changes, what stays the same?
- What is the user-visible outcome?
- What are the edge cases and failure modes?
- What is explicitly out of scope vs. deferred?
- Does this feature carry money, credentials, or user data? If yes, the security bar is higher.

**Scope boundary rule:**
- **Out of scope** = permanently excluded. Will not be built.
- **Deferred** = valuable but not now. Must be tracked with a TODO or issue — not listed and forgotten.

**When to pause:** Only if there are 2+ fundamentally different interpretations and the choice affects architecture. Otherwise, make a reasonable choice and document it.

Output a requirement summary before proceeding:
```
Feature: <one sentence>
Success criteria: <what done looks like, observable and testable>
Out of scope: <permanently excluded>
Deferred: <skipped now — tracked where?>
Key risks: <what could go wrong>
Carries money/credentials/PII: yes / no
Backward compatibility: <what existing behavior must not change>
NFR: latency=<target> | memory=<budget> | concurrency=<scale> | (or "no hot-path impact")
```

---

## Phase 0.5: Scale Assessment

| Task type | Definition | Phases to run |
|-----------|-----------|--------------|
| **Bug fix** | Single module, no interface change, no side-effect spread | -1, 0, 2, 3 (targeted), 4 |
| **Small feature** | 1–2 modules, clear boundary, no auth/security changes | All phases, abbreviated |
| **Complex feature** | Cross-module, interface changes, security-sensitive, or external deps | All phases, full depth |

For **Complex feature**: *Can this be delivered as a smaller working slice first?*

```
Classification: bug fix / small feature / complex feature
Rationale: <one sentence>
Data migration required: yes (<describe>) / no
MVP slice possible: yes (<describe>) / no
```

---

## Phase 1: Design — Options, Failure Modes, and Trade-offs

*(Skip for bug fixes. Abbreviate for small features with obvious design.)*

Generate 2–3 design options. For each option, answer four questions — not just "what does it do" but "what does it look like when it breaks."

**Option format:**
```
Option A: <name>
  Approach: <one paragraph>
  Failure modes: <what happens when this fails at 3am — silent data loss? user-facing error? cascading failure?>
  Blast radius: <if this component fails, what else fails with it?>
  Pros: <bullet list>
  Cons: <bullet list>
  Dependencies added: <none / list with version + last-published date>
  Backward compatible: yes / no / partial
  Data migration required: none / <describe>
  Rollback path: <exact steps to undo in prod>
```

**Evaluation criteria (in priority order):**
1. Security — does it introduce attack surface?
2. Blast radius — does failure isolate or cascade?
3. Backward compatibility — does it break existing callers?
4. Operability — can you diagnose failures without a debugger?
5. Simplicity — minimum code for the job
6. Dependency weight — prefer zero new deps; reuse existing
7. Testability — can it be verified automatically?

**For state-bearing features (anything that writes to DB, disk, or cache):**
Before choosing an option, draw the state machine — every state, every transition, every error transition. If a transition has no defined error path, it is incomplete. Do not proceed to implementation until the state machine is complete.

**ADR for complex features:**
```
ADR: <feature name>
Context: <why a decision was needed>
Decision: <what was chosen>
Failure handling: <how failures in this design are detected and recovered>
Consequences: <what this enables and what it forecloses>
```

**When to pause for human choice:**
- When blast radius profiles are meaningfully different (one option fails loudly and safely, another fails silently)
- When backward compatibility is broken in any option
- When the security profiles differ fundamentally

---

## Phase 2: Implementation

### Language-aware tooling — detect before running

| Stack | Lint | Test | Build | Audit |
|-------|------|------|-------|-------|
| Python | `python -m ruff check <files>` | `python -m pytest <files> -q` | — | `pip-audit` |
| TypeScript/Node | `npm run lint` or `tsc --noEmit` | `npm test` | `npm run build` | `npm audit` |
| TypeScript/Bun | `bun run lint` | `bun test` | `bun run build` | `bun audit` |
| Go | `go vet ./...` | `go test ./...` | `go build ./...` | `govulncheck ./...` |
| Rust | `cargo clippy` | `cargo test` | `cargo build` | `cargo audit` |

Never run Python commands on a TypeScript project and vice versa.

### Testing strategy — declare before writing code

**Timing:**
- **TDD**: use when the contract is well-defined upfront (parsing, validation, API shape, security invariants)
- **Test-after**: use when prototyping to discover the shape of the solution

Write tests at the same granularity as implementation chunks — not all at the end. "All code, then all tests" is test-after at the wrong granularity and defeats early feedback.

**Types:**
- **Unit**: pure logic, no I/O, fast, deterministic
- **Integration**: multiple components together
- **Contract**: verify an interface hasn't changed (CLI flags, API schema, wire format, file format)
- **Benchmark**: required when touching a hot path

Declare both axes upfront:
```
Testing: TDD / test-after  |  unit / integration / contract / benchmark
```

**Test quality requirements** (coverage is necessary but not sufficient):
- Every test must assert a meaningful invariant, not just "it didn't crash"
- Tests must be isolated: no shared mutable state between tests, no execution-order dependencies
- Tests must be deterministic: no `sleep()`, no wall-clock time assertions, no randomness without a fixed seed
- Error path tests are required for every new error path — a test suite that only covers the happy path will not catch regressions in error handling

### Commit discipline

Commit at logical boundaries, not at the end of the feature. Each commit should:
- Pass lint + tests independently (never commit a broken state)
- Represent one coherent unit of change (one function, one module, one config change)
- Have a message that explains *why*, not just *what*

Small commits make rollback surgical. One large commit makes rollback an all-or-nothing decision.

### Error message quality — write at implementation time, not at review time

Every new error path must answer three questions for the user:
1. **What happened?** (specific, not generic — "payment rejected: amount $5.01 exceeds per-call limit $5.00")
2. **Why did it happen?** (the condition that was violated)
3. **What should they do?** (actionable next step, or "contact support" as last resort)

Never write: "An error occurred." "Invalid input." "Request failed." These are useless in production.

### Code quality
- Match existing patterns in the codebase — read before writing
- No feature flags, no backwards-compatibility shims for new code
- Comments only where logic is non-obvious (protocol quirks, security invariants, non-obvious performance choices)
- Validate at system boundaries (user input, external APIs); trust internal code

### JavaScript/TypeScript-specific safety — these have caused production bugs
- [ ] `NaN` and `Infinity` are **not** caught by `< 0` or `> MAX` — use `!isFinite(x)` for all numeric validation
- [ ] After any irreversible operation (payment broadcast, file write, DB commit): ALL downstream code paths including catch/finally must handle partial state safely. Never throw after the point of no return.
- [ ] Variable names must not shadow browser/Node globals (`fetch`, `Response`, `Request`, `URL`, `crypto`, `process`, `Buffer`)
- [ ] Prototype pollution: never use user-controlled keys in `Object.assign`, spread operators, or direct property assignment without allowlist validation (`key in ALLOWED_KEYS`)

### Backward compatibility gate
Before modifying any public interface (function signature, CLI argument, API endpoint, config key, file format):
- [ ] Who calls this? (grep for usages)
- [ ] Will callers break?
- [ ] If breaking: is there an additive alternative (new param with default, new endpoint)?
- [ ] If unavoidably breaking: document in CHANGELOG as **Breaking Change**

### Supply chain — before adding any new dependency
- [ ] Is the exact package name correct? (typosquatting: `cros-fetch` vs `cross-fetch`, `lodash` vs `Lodash`)
- [ ] When was it last published? Abandoned packages (>2 years no release for active projects) are a risk.
- [ ] Pin the version or version range explicitly — never `*` or `latest` in production deps
- [ ] Run the language-appropriate audit command after adding: `npm audit` / `pip-audit` / `cargo audit`
- [ ] If the dep is added to solve a security audit warning, understand the full transitive impact before accepting

### Security by default
- No hardcoded secrets, credentials, or sensitive values
- Secrets must not be passed as CLI arguments (visible in `ps aux`) — use env vars or files
- Validate and sanitize all external inputs (length, format, character set)
- Use constant-time comparison for secrets (HMAC, tokens)
- File permissions: 0600 for credential/key files on Unix
- Atomic writes for any file that stores state (tempfile + rename)
- Log warnings, not secrets

### Observability — build in, not on top
For every new code path that can fail or users care about:
- [ ] One log line per operation on the happy path (not per sub-step)
- [ ] Error logs include enough context to diagnose without a debugger (operation ID, entity ID, error type, not stack trace)
- [ ] The single operational signal that "this feature is healthy" — what metric or log pattern tells you at a glance it's working?
- [ ] If this runs 100k/day, does log volume stay acceptable?

Rule: if diagnosing a failure requires reproducing it locally, the observability is insufficient.

### Performance hot-path awareness
When touching code called >1000x/sec, in a request handler, or in a tight loop:
- [ ] No synchronous I/O
- [ ] No repeated object construction that can be cached
- [ ] No O(n²) where O(n) or O(log n) is available
- [ ] Write a benchmark test; record before/after numbers in the commit message

### Deferred item tracking
```
// TODO: <description> (deferred from <feature>, <date>)
```
For cross-cutting deferrals, open an issue. Do not let deferred work disappear.

### After each commit-sized chunk:
```bash
<lint command>   # fix before continuing — never accumulate lint debt
<test command>   # fix failures before writing more code
```

---

## Phase 3: Multi-Role Review

Three consecutive reviews covering distinct territory. No finding may be duplicated across roles.

---

### Review 1: Security Engineer

**Owns:** Trust boundaries, crypto correctness, injection vectors, data leakage, auth/authz, supply chain.

**Input validation**
- [ ] All user inputs validated (type, length, format, character set)
- [ ] Numeric inputs: `NaN`, `Infinity`, `-Infinity` checked explicitly — `x < 0` does NOT catch NaN in JS/TS
- [ ] No injection vectors: SQL, header (CR/LF in values), path traversal (`../`), command injection
- [ ] Regex patterns anchored (`re.fullmatch` in Python; `/^...$/.test()` in JS — not partial match)
- [ ] JS/TS: no user-controlled keys used in `Object.assign`, spread, or dynamic property access (prototype pollution)
- [ ] SSRF: outbound HTTP/socket calls block private IPs (10.x, 172.16.x, 192.168.x), localhost, metadata endpoints (169.254.x), non-HTTPS schemes

**Post-irreversible-action safety**
- [ ] After any irreversible operation (payment, write, commit): ALL downstream code including catch/finally handles partial state safely
- [ ] No exception can leave the system in an inconsistent state after money/data has moved
- [ ] Idempotency: can the operation be safely retried if the response is lost?

**Authentication & authorization**
- [ ] No authentication bypass paths
- [ ] Privilege escalation not possible
- [ ] Sensitive operations require appropriate verification
- [ ] No secrets passed as CLI arguments (visible in process list)

**Data handling**
- [ ] No secrets in logs, error messages, or API responses
- [ ] Sensitive files have restrictive permissions (0600 on Unix)
- [ ] Atomic writes for state files (tempfile + rename)
- [ ] If feature introduces new credentials or signing keys: is the rotation procedure defined?

**Cryptography**
- [ ] HMAC/signature checks use constant-time comparison
- [ ] No timing oracles (early-return on first byte mismatch)
- [ ] Signing keys minimum 32 bytes of entropy; warn if shorter

**Concurrency**
- [ ] No TOCTOU races at trust boundaries
- [ ] Atomic DB operations use transactions or INSERT OR IGNORE

**Information leakage**
- [ ] Error responses reveal no internal state (stack traces, schema details, existence of resources)
- [ ] Logs truncate sensitive values (addresses, keys, hashes, tokens)
- [ ] Production health endpoints return minimal information

**Supply chain**
- [ ] All new dependencies have been audited (`npm audit` / `pip-audit` / `cargo audit`)
- [ ] No new dep with known CVEs introduced
- [ ] Versions are pinned or range-constrained (not `*` or `latest`)

**Hard gate:** Any Critical security finding must be fixed before Phase 4 proceeds. It may not be deferred. If it cannot be fixed, escalate to human with full context before continuing.

Output: findings with severity (Critical / High / Medium / Low) and file:line.

---

### Review 2: Architect

**Owns:** Correctness, state machine completeness, interface stability, backward compatibility, resource management, testability.

**Correctness**
- [ ] Logic handles all edge cases defined in Phase 0
- [ ] Error paths are complete — no silent failures
- [ ] All state machine transitions are handled (from the Phase 1 design map)
- [ ] Retry/recovery logic is sound and bounded (no infinite retry)

**Data migration**
- [ ] If persistent data format changed: is there a migration for existing data?
- [ ] If migration is needed: is it backward-compatible (old code can still read new data)?
- [ ] If schema changed: was it additive-only (new optional fields) or destructive (removed/renamed required fields)?

**Backward compatibility**
- [ ] Public interfaces unchanged or additive-only (new params have defaults)
- [ ] CLI flags, env vars, config keys not renamed without migration path
- [ ] Breaking changes explicitly documented in CHANGELOG as **Breaking Change**

**Robustness**
- [ ] Crash-safe: process dies mid-operation — what state is left? Is it recoverable?
- [ ] Idempotent where it should be: retrying produces the same result
- [ ] Resource cleanup guaranteed (DB connections, file handles, temp files, open sockets)
- [ ] Timeouts on all external calls — no unbounded wait

**Concurrency**
- [ ] Shared mutable state is protected (lock, queue, atomic)
- [ ] DB multi-step operations use transactions
- [ ] No unbounded resource accumulation (queues, caches, log files, temp files)

**Test quality**
- [ ] Tests assert meaningful invariants — not just "it didn't crash"
- [ ] Tests are isolated: no shared mutable state, no execution-order dependencies
- [ ] Tests are deterministic: no wall-clock time, no uncontrolled randomness
- [ ] Error paths have tests — not just happy paths
- [ ] If feature is concurrent: tests cover concurrent access, not just sequential

**Dependencies**
- [ ] No new dependency when an existing one suffices
- [ ] New dependencies are actively maintained
- [ ] No circular imports

Output: findings with severity and file:line.

---

### Review 3: UX Engineer

**Owns:** User-visible behavior, error messages, CLI/API ergonomics, documentation accuracy, example correctness.

**Error messages**
- [ ] Every error tells the user: what happened, why, and what to do next
- [ ] No generic messages ("An error occurred", "Invalid input", "Request failed")
- [ ] Error messages are consistent in format across the feature

**CLI / API interface**
- [ ] Commands and endpoints are discoverable and self-explanatory
- [ ] Argument names consistent with existing conventions
- [ ] All CLI commands shown in docs actually exist — grep the entrypoints to verify
- [ ] No removed or non-existent flags documented (grep to verify)

**Code examples — verify, do not assume**
- [ ] All import paths refer to published/available packages
- [ ] Variable names don't shadow language globals (`fetch`, `Response`, `URL`, etc. in JS)
- [ ] Protocol format examples match actual implementation — grep the wire format from source code, don't write from memory
- [ ] Package IDs, tier names, prices match the actual code constants — grep to verify
- [ ] ASCII diagrams fit within 80 characters per line

**Failure modes from the user's perspective**
- [ ] User gets clear guidance when something goes wrong
- [ ] No silent failures (operations that appear to succeed but don't)
- [ ] Recovery path is documented: what do you do if the operation is interrupted?
- [ ] Partial failures don't leave the user in an ambiguous state ("did it work or not?")

**Real-world scenarios**
- [ ] Network drops mid-operation: what happens?
- [ ] User runs the same command twice: what happens?
- [ ] User has no configuration set up: what happens?
- [ ] User is on the wrong version: is the error clear?

**Documentation cross-consistency**
- [ ] All package names, versions, feature descriptions consistent across README sections
- [ ] No duplicate content blocks (same code/prose repeated in 2+ places)
- [ ] No stale labels (🆕, "Coming Soon", roadmap items that shipped)
- [ ] Taglines consistent with table/detail content (e.g. "zero code changes" cannot follow a row saying "~2 lines")

**Changelog and README**
- [ ] README updated for any user-facing behavior change
- [ ] CHANGELOG entry drafted
- [ ] All examples in docs verified to work

Output: findings with severity and file:line.

---

## Phase 4: Fix and Re-verify

**Process all findings from all three reviews.**

Priority order:
1. Critical security findings — fix immediately; re-run the full Security Review on the changed code. **No Critical security finding may ship without being fixed or receiving explicit human sign-off.**
2. Critical architecture findings — fix; re-run Architect Review on changed code
3. High findings from any role
4. Medium findings
5. Low findings (fix if trivial; track as TODO/issue if not)

After fixing:
```bash
<lint command>
<full test suite command>
```

All tests must pass. A fix that causes a new test failure must be fixed before proceeding.

**Re-review rule:** A Critical finding that required significant code changes triggers a re-run of the relevant review role — not a full review, just the section that changed.

**Escalation rule:** A finding that cannot be resolved after exhausting the Structured Debugging Protocol (two falsified hypotheses, no applicable prior art, clear articulation of what's unknown) is escalated to the human using the escalation format. Never silently defer a Critical or High finding.

---

## Phase 5: Production Readiness Check

**"If this shipped to production right now, what would break?"**

Answer each question with evidence, not assumption.

### Operational scenarios
- Process restarts mid-operation: state recovers correctly? (check idempotency)
- Persistent store missing or corrupt: fails gracefully with clear error?
- 10 concurrent users hit the same endpoint simultaneously: safe? (check locking)
- External service (RPC, API, DB) is slow or down: timeout handled? request doesn't hang?
- Rate limit exhausted: clear error or silent hang?

### Degradation strategy
Not everything can be perfect under load or partial failure. Define explicitly:
- What degrades gracefully vs. what fails hard?
- Under what conditions does the feature become unavailable vs. degraded?
- Is degraded behavior observable (logged, metric)?

### Data scenarios
- Empty / zero-length inputs
- Max-length inputs: at boundary and boundary+1
- Malformed data: wrong type, missing fields, extra fields
- Data from a previous version of the software (backward compatibility)

### Security scenarios
- Attacker sends malformed input: clean error, no crash?
- Attacker replays a previous request: rejected?
- Attacker claims another user's resource: rejected with no information leak?
- Attacker passes `../` or null bytes in path inputs: sanitized?

### Performance (for hot-path changes only)
- Is the change O(1) per call, or does it scale with data size?
- Under 100 concurrent requests: degrades gracefully or fails hard?
- Benchmark numbers meet the NFR stated in Phase 0?

### Operator scenarios
- Feature fails silently at 3am: will on-call know within 5 minutes? (check log signal)
- What is the single log line or metric that unambiguously says "this feature is healthy"?
- Does failure of this feature blast-radius to unrelated features?
- Rollback procedure: exact steps. Any data migration needed in reverse?

```
Rollback path: <exact steps>
Data risk on rollback: none / <describe>
```

### Documentation final check
- README accurately describes new behavior?
- New commands/flags documented?
- CHANGELOG complete and accurate?
- All examples verified?
- All Deferred items tracked?

Output: explicit **READY** or list of remaining issues.

---

## Phase 6: Done

Only declare done when every item is checked:
- [ ] All three reviews completed, no unresolved Critical/High findings
- [ ] All Critical security findings fixed or have explicit human sign-off
- [ ] All tests pass: lint + full suite, using language-correct commands
- [ ] Tests are isolated, deterministic, and assert meaningful invariants
- [ ] Production readiness check: READY
- [ ] Rollback path documented with data risk assessment
- [ ] Observability verified: the "feature is healthy" signal exists
- [ ] Documentation updated and cross-consistent
- [ ] CHANGELOG entry drafted
- [ ] All Deferred items tracked with location (TODO or issue number)
- [ ] Supply chain: audit command run, no new CVEs introduced

**Do NOT declare done if:**
- A Critical security finding was deferred without explicit human decision
- Documentation is inaccurate (even if code is correct)
- An example references a package, command, or flag that does not exist
- Rollback path is "unknown" without human sign-off
- Any test asserts only "it didn't crash"

### Done Summary (always output this)

```
## Done: <Feature Name>

**Classification:** bug fix / small feature / complex feature
**Files changed:** <N> — <list key files>
**Tests:** <N> added/modified; suite: <X> passed
**Breaking changes:** none / <describe>
**Security:** no new CVEs | audit clean | Critical findings: <N fixed>

**What was built:**
<2–3 sentence user-visible description>

**What was NOT built:**
- Out of scope (permanent): <list or "none">
- Deferred (tracked): <list with TODO/issue location>

**Key decisions:**
<bullet list of non-obvious choices and rationale>

**State machine / data migration:**
<new states or transitions added, or "no state changes"> | <migration: none / <describe>>

**Observability:**
<the "feature is healthy" signal> | <new error log lines>

**Rollback path:**
<exact procedure> | Data risk: none / <describe>

**Risks and known limitations:**
<bullet list or "none identified">
```

---

## Autonomy Rules

**Run without interrupting the human when:**
- Implementation choices are clear
- Review findings are unambiguous and fixable
- Tests fail with an identifiable root cause — fix it using the Structured Debugging Protocol
- Lint errors need fixing
- Documentation needs updating
- CI/build errors occur — classify, hypothesize, fix
- A non-security dependency is missing — verify the exact package name on the registry, check last-published date, install, run audit, continue
- A non-security config file is missing — create with safe defaults; flag if the absence could indicate a security misconfiguration

**A dependency is NOT safe to install autonomously if:**
- It is a transitive version conflict (symptom of a deeper constraint problem — fix the constraint)
- It installs a globally-scoped tool that modifies PATH or shell config
- It is a dev-only package being added to production `dependencies`
- The package name is ambiguous or close to a known package name (possible typosquatting — verify manually)
- It is being added to resolve a security audit warning without understanding the transitive impact

**Pause and present options when:**
- Two design approaches have meaningfully different blast radius or long-term architectural consequences
- A security finding has no clear right answer (leakage vs. usability, strictness vs. compatibility)
- A fix requires a breaking change to a public interface
- The Structured Debugging Protocol has been exhausted — present the escalation format, not "I tried things"

**Never proceed without human approval when:**
- Deleting or migrating production data
- Force-pushing to protected branches
- Changing authentication mechanisms
- Removing or downgrading existing security controls
- Breaking a public interface with no additive alternative
- Bypassing a security check to make a test pass (`--no-verify`, disabling a lint security rule)
- Rollback requires manual data surgery

---

## Structured Debugging Protocol

When something fails, this protocol runs **before escalating to the human**. It is a decision tree. Each step must produce new information.

### Step 1 — Classify the failure

| Category | Signature | Resolution path |
|----------|-----------|-----------------|
| **Syntax / compile** | Parser error, type error, import not found | Fix in source, re-run |
| **Logic / assertion** | Test fails, wrong output, unexpected behavior | Hypothesize → isolate → fix |
| **Environment** | Missing binary, wrong runtime version, PATH issue | Check env, fix toolchain |
| **Dependency** | Package not found, version conflict, peer dep warning | Check registry, fix constraint |
| **Permission / auth** | 403, EACCES, credential missing, wrong scope | Check credentials and scope |
| **Flaky / race** | Passes sometimes, timing-dependent | Stabilize, add controlled timing |
| **Configuration** | Wrong flag, missing env var, bad config key | Read docs, check working config |

**Misclassifying is the most common cause of wasted attempts.** Spend 30 seconds on classification before touching anything. A "permission" error and a "dependency" error look similar on the surface but have completely different resolution paths.

### Step 2 — Form a falsifiable hypothesis

State explicitly: **"I believe the root cause is X. If I fix X, the error will change to Y or disappear."**

If you cannot state this sentence, you do not yet understand the failure. Read the full error message and stack trace again. Do not touch anything until you can state the hypothesis.

**Valid hypotheses:**
- "The 403 is because the token has repo scope but the endpoint requires org scope. If I use an org-level token, the response changes to 200."
- "The test fails because `NaN < 0` is `false` in JS. If I add `!isFinite(x)`, the assertion passes."
- "The import fails because this package is in devDependencies but the test runner resolves production deps only. Moving it to dependencies makes the error disappear."

**Invalid hypotheses — do not attempt:**
- "Let me try changing this and see what happens." (no prediction)
- "Maybe if I run it again." (retry, not hypothesis)
- "I'll try a different version." (no explanation of why that version would be different)

### Step 3 — Minimum viable fix

Apply the smallest possible change that tests the hypothesis. One change, one re-run. Do not refactor, clean up, or improve adjacent code while testing a hypothesis.

- Hypothesis confirmed: error gone or transformed as predicted → proceed with proper fix
- Hypothesis refuted: return to Step 2 with new information from the result

### Step 4 — Scope the fix properly

Once root cause is confirmed:
- Is this root cause present in other places? Fix all instances.
- Does this fix introduce new risk? (e.g., a type check that other code relied on)
- Does this fix need a regression test?
- Does this fix change observable behavior that documentation must reflect?

### Step 5 — Escalation gate

Escalate only when **all** of the following are true:
1. At least 2 genuinely different hypotheses have been formed and falsified (not variations of the same one)
2. The full error output and stack trace were read at each attempt
3. The codebase was searched for similar working patterns and none applied
4. You can articulate exactly what you know, what you have tried, and what information is missing to proceed

**Required escalation format:**
```
BLOCKER: <one sentence — what operation cannot proceed>

Failure classification: <category from Step 1>

Root cause analysis:
- Error: <exact error message, verbatim>
- Hypothesis 1: <what I believed> → Result: <what actually happened>
- Hypothesis 2: <what I believed> → Result: <what actually happened>
- Current understanding: <what I now know about the system state>
- Missing information: <what I need that I cannot determine autonomously>

Options to unblock:
A. <approach> — requires from human: <specific information or decision>
B. <approach> — requires from human: <specific information or decision>
```

Never escalate with "I tried things and none worked." That is not diagnostic information and provides nothing for the human to act on.

---

## Quick Reference

```
Phase -1:  Orient      — read before writing; detect stack; find fragile areas; identify data migration needs
Phase  0:  Clarify     — feature / scope / deferred / NFR / carries money?
Phase 0.5: Scale       — bug fix / small / complex; MVP slice?
Phase  1:  Design      — options with failure modes + blast radius + state machine; ADR for complex
Phase  2:  Implement   — test strategy declared; commit per chunk; lint+test per commit; error messages written at implementation time
Phase  3:  Review      — Security (injection/NaN/post-irrev/SSRF/supply-chain) → Architect (state/compat/migration/test-quality) → UX (examples/consistency/error-messages)
Phase  4:  Fix         — Critical security fixed or human sign-off; re-review Critical changes; escalation format if blocked
Phase  5:  Prod check  — ops/degradation/data/security/perf/operator/rollback
Phase  6:  Done        — Done Summary; observability signal named; rollback documented; supply chain clean
```

**Target interruptions:**
- Bug fix: 0
- Small feature: 0
- Complex feature: 0–1 (design fork with different blast radius / security profile)
- Security-sensitive change: 0–1 (only if breaking an existing auth mechanism)
