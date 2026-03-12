# Pipeline Routing Guide

When starting any development work, use this guide to choose the right pipeline. The wrong pipeline wastes time.

---

## Decision Tree

```
Is the requirement clear and unambiguous?
├── No → brainstorming first (clarify before building)
└── Yes ↓

Is this a bug fix or a small, well-scoped change (1-3 files, no new interfaces)?
├── Yes → feature skill (Phase -1 to 6, self-contained, no planning overhead)
└── No ↓

Does this require multiple independent implementation tasks across 3+ files?
├── No  → feature skill (still manageable in one coherent session)
└── Yes ↓

Is there a written spec / design document already?
├── No  → brainstorming → writing-plans → subagent-driven-development
└── Yes → writing-plans → subagent-driven-development
```

---

## Pipeline A: `feature` skill (self-contained)

**Use when:**
- Bug fixes (any size)
- Small, well-scoped features: 1–3 files, clear requirement, no new public interfaces
- Changes where you can hold the full scope in one session without context pollution
- Tight iteration needed (no planning overhead wanted)

**Not suited for:**
- Features requiring 5+ independent tasks (context accumulates; subagents are cleaner)
- Features where design alternatives need human approval before writing code
- Features where multiple people/agents work in parallel

**Flow:**
```
feature (Phase -1 → 6)
```

---

## Pipeline B: `brainstorming → writing-plans → subagent-driven-development` (collaborative)

**Use when:**
- New features with non-obvious design decisions
- Cross-module changes touching 5+ files
- Security-sensitive features (auth, payments, cryptography) where design needs explicit review
- Features where the approach is not yet decided
- Features that benefit from a written spec as a durable artifact

**Flow:**
```
brainstorming
    ↓ (produces: docs/superpowers/specs/YYYY-MM-DD-<name>-design.md)
writing-plans
    ↓ (produces: docs/superpowers/plans/YYYY-MM-DD-<name>.md)
subagent-driven-development
    ↓ (per task: implement → spec review → quality review)
multi-role-review
    ↓ (parallel: security / architecture / DX / production)
finishing-a-development-branch
```

---

## Quality gates that apply to BOTH pipelines

These are not optional and not pipeline-specific:

| Gate | When | Skill |
|------|------|-------|
| Tests pass | Before any merge/PR | `finishing-a-development-branch` Step 1 |
| Production readiness | Before any merge/PR | `finishing-a-development-branch` Step 2 |
| Multi-role review | Before finishing (non-trivial features) | `multi-role-review` |
| Debugging protocol | When tests fail unexpectedly | `systematic-debugging` |
| Verification before claiming done | Any time | `verification-before-completion` |

---

## Common mistakes

**Using `brainstorming` for bug fixes**
Brainstorming is for design decisions. A bug fix with a clear root cause doesn't need a design doc.

**Using `feature` for a 10-task cross-module feature**
`feature` accumulates context linearly. At task 8, the LLM may forget constraints from task 2. Use subagents.

**Skipping `writing-plans` after `brainstorming`**
The design doc is not a plan. A plan has exact file paths, complete code snippets, and step-by-step TDD cycles. These are different artifacts.

**Running `multi-role-review` before all tasks are complete**
Multi-role review reviews the whole feature. Running it mid-way wastes time — findings will be invalid after remaining tasks change the code.
