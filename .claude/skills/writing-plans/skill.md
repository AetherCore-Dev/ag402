---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** This should be run in a dedicated worktree (created by brainstorming skill).

**Save plans to:** `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`
- (User preferences for plan location override this default)

## Scope Check

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in.

- Design units with clear boundaries and well-defined interfaces. Each file should have one clear responsibility.
- You reason best about code you can hold in context at once, and your edits are more reliable when files are focused. Prefer smaller, focused files over large ones that do too much.
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If the codebase uses large files, don't unilaterally restructure - but if a file you're modifying has grown unwieldy, including a split in the plan is reasonable.

This structure informs the task decomposition. Each task should produce self-contained changes that make sense independently.

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

## Task Structure Contract

**This structure is a machine-readable contract between `writing-plans` and `subagent-driven-development`.**
`subagent-driven-development` parses tasks by looking for `### Task N:` headings. Any deviation breaks task extraction.

**Rules (never break these):**
- Each task starts with exactly `### Task N: [Name]` (H3, "Task", number, colon)
- Task numbering is sequential starting from 1: Task 1, Task 2, Task 3…
- Do NOT use `## Chunk N:` or `#### Step N:` or any other heading as the task boundary
- Each task ends where the next `### Task` begins
- Use `## Chunk N:` headings ONLY for grouping tasks into review batches — not as task boundaries

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## Security Guard Checklist (required for any task touching external SDK, financial logic, or public API)

Before finalising each task's test cases, walk through these attack surfaces. For any that apply, write an explicit failing test. **These are stack-agnostic patterns — substitute your domain's concrete types.**

**Numeric boundaries**
- Zero value: `amount = 0` or any input that rounds/truncates to zero
  - Always show the full calculation: `0.0000004 × 10^6 = 0.4 → round(0.4) = 0`. Pick the test value by working backwards from the expected truncated result, not by guessing.
- Negative value
- Sub-minimum: smallest value that passes type checks but produces a no-op (e.g. rounds to zero, truncates to empty, clamps to a minimum)
- Overflow: largest value that overflows the target type silently

**Self-reference**
- Source == destination (file src == dst, payer == recipient, src queue == dst queue)
- Self-referential configs (e.g. a service calling itself, a node pointing to itself in a graph)

**External API / SDK: success ≠ semantic success**
- Any async call that resolves/returns without throwing but carries a failure in the response body
  - Pattern: call resolves → check `response.error`, `result.value.err`, `status != "ok"`, etc.
  - Write an explicit test: mock "resolved with embedded failure" and assert the caller throws, not returns

**Configuration misuse**
- Wrong-environment config that silently targets the wrong resource (e.g. prod credentials pointing to staging, test token pointing to real network)
- Missing required config that fails at runtime (not startup) — guard should throw at construction, not at first use

**Output injection**
- Any string value that flows into HTTP headers, SQL, shell commands, file paths, log lines, or user-visible output: strip or escape the relevant control characters
- Do not assume upstream callers sanitised it — validate at the boundary

**Public API consistency**
- For every public method/function signature: verify docs, type annotations, and runtime behaviour agree
- If the docs show an option (`fromEnv({ x: ... })`), the type must accept it and the runtime must use it

**Package release artifacts**
- LICENSE, README, CHANGELOG present and included in published artifact
- Version number consistent across all manifests (package.json, pyproject.toml, Cargo.toml, etc.)

## Remember
- Exact file paths always
- Complete code in plan (not "add validation")
- Exact commands with expected output
- For numeric boundary tests: show the full calculation (`input × scale = y → round(y) = z`), then pick the test value from that math
- Reference relevant skills with @ syntax
- DRY, YAGNI, TDD, frequent commits

## Plan Review Loop

After completing each chunk of the plan:

1. Dispatch plan-document-reviewer subagent (see plan-document-reviewer-prompt.md) for the current chunk
   - Provide: chunk content, path to spec document
2. If ❌ Issues Found:
   - Fix the issues in the chunk
   - Re-dispatch reviewer for that chunk
   - Repeat until ✅ Approved
3. If ✅ Approved: proceed to next chunk (or execution handoff if last chunk)

**Chunk boundaries:** Use `## Chunk N: <name>` headings to delimit chunks. Each chunk should be ≤1000 lines and logically self-contained.

**Review loop guidance:**
- Same agent that wrote the plan fixes it (preserves context)
- If loop exceeds 5 iterations, surface to human for guidance
- Reviewers are advisory - explain disagreements if you believe feedback is incorrect

## Execution Handoff

After saving the plan:

**"Plan complete and saved to `docs/superpowers/plans/<filename>.md`. Ready to execute?"**

**Execution path depends on harness capabilities:**

**If harness has subagents (Claude Code, etc.):**
- **REQUIRED:** Use superpowers:subagent-driven-development
- Do NOT offer a choice - subagent-driven is the standard approach
- Fresh subagent per task + two-stage review

**If harness does NOT have subagents:**
- Execute plan in current session using superpowers:executing-plans
- Batch execution with checkpoints for review
