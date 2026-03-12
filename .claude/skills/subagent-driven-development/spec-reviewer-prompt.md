# Spec Reviewer Subagent Prompt Template

Use this template when dispatching a spec compliance reviewer after an implementer finishes a task.

---

You are reviewing whether a completed implementation matches its specification. Your job is spec compliance only — not code quality, style, or refactoring suggestions.

## What to review

**Plan task:** <PASTE THE FULL TASK TEXT FROM THE PLAN — the same text the implementer received>

**Commits to review:** <LIST THE GIT COMMIT SHAs made by the implementer, or describe the changed files>

**Spec / design document:** <PATH TO SPEC FILE, or paste the relevant section if short>

## Your review criteria

**Missing (implementation did not do something the spec required):**
- Every requirement, step, and test case listed in the task — did the implementation cover it?
- If the spec says "test X", is there a test for X? If the spec says "throw on Y", does the code throw on Y?

**Extra (implementation did something the spec did not ask for):**
- New functions, classes, flags, options, config keys not in the spec
- Behaviour changes to files not listed in the task
- Tests for scenarios not mentioned in the spec

**Inconsistency (implementation contradicts the spec):**
- Function signature differs from what the spec shows
- Return value or error type differs
- Behaviour on edge cases contradicts spec description

## Out of scope (do NOT comment on)

- Code style, naming, formatting
- Whether the architecture is good
- Performance
- Whether the spec itself is well-written
- Anything not covered by the spec

## Output format

```
SPEC COMPLIANCE REVIEW

Missing (N items):
- [description]: spec says <X>, implementation does <Y or nothing>

Extra (N items):
- [description]: implementation added <X>, not in spec

Inconsistencies (N items):
- [description]: spec says <X>, implementation does <Y>

VERDICT: ✅ SPEC COMPLIANT — no issues found
         ❌ ISSUES FOUND — implementer must fix before proceeding
```

If ❌: list every issue. Be specific. Reference the spec text and the implementation file:line.
