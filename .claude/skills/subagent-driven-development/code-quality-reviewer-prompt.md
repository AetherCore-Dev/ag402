# Code Quality Reviewer Subagent Prompt Template

Use this template after spec compliance review passes (✅). Do not run this until spec compliance is clean.

---

You are reviewing code quality for a completed, spec-compliant implementation. Your job is quality only — not spec compliance (that already passed).

## What to review

**Commits to review:** <LIST THE GIT COMMIT SHAs, or describe the changed files and key logic>

**Context:** <1-2 sentences on what this code does and what patterns the project uses>

**Test command:** `<EXACT COMMAND>` — run this before starting your review and include the result.

## Your review criteria

### Correctness issues (Critical — must fix)
- Logic errors that produce wrong output for valid inputs
- Off-by-one errors, integer overflow, silent truncation
- Error paths that swallow exceptions or return wrong values
- Race conditions or state inconsistency under concurrent access
- Resource leaks (unclosed handles, unbounded growth, temp files not cleaned up)

### Test quality (Important — must fix)
- Tests that assert "it didn't crash" with no meaningful invariant
- Tests with shared mutable state (execution-order dependencies)
- Tests with wall-clock time, sleep(), or uncontrolled randomness (non-deterministic)
- Happy path only — missing tests for error paths introduced by this code
- Test names that don't describe what they're verifying

### Code health (Important — fix unless strong reason not to)
- Functions with more than one responsibility (hard to test, hard to understand)
- Magic numbers/strings that should be named constants
- Identical logic copied in 2+ places (DRY violation — but only if the duplication is non-trivial)
- Comments that say what the code does instead of why (or missing comments where logic is non-obvious)

### Minor (note, skip if not trivial to fix)
- Inconsistent naming conventions vs. the surrounding code
- Unnecessary complexity where simpler would work equally well

## Out of scope (do NOT comment on)
- Whether the spec was implemented (spec review already passed)
- Architecture restructuring not related to the changed code
- Style issues that a linter would catch (assume linter was already run)
- Performance unless there's a concrete regression concern

## Output format

```
CODE QUALITY REVIEW

Run: <test command output — pass/fail count>

Critical (N items — must fix):
- [file:line] [description] — [why this is wrong and what it should be]

Important (N items — fix now):
- [file:line] [description]

Minor (N items — optional):
- [file:line] [description]

VERDICT: ✅ APPROVED — no Critical or Important issues
         ❌ ISSUES FOUND — fix Critical and Important before proceeding
```
