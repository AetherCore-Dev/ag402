---
name: releasing-to-pypi
description: Use when committing code changes that will be tagged and released to PyPI, before creating any git commits, to ensure lint, version bump, tag placement, and changelog are all correct in one shot
---

# Releasing to PyPI

## Overview

A release to PyPI in this project requires **all steps completed atomically before pushing**. The publish workflow triggers on GitHub Release creation and checks out the **tag's commit** — if that commit has wrong versions, stale lint, or missing changelog, the release fails and cannot be re-uploaded to PyPI (immutable filenames).

**Core principle:** The tag must point to a commit where every file is release-ready. Work backwards from that constraint.

## When to Use

- Committing code that will be tagged for release
- Bumping versions for a new PyPI publish
- Creating any git tag prefixed with `v`

## The Checklist

**MANDATORY: Execute every step in order. Do not skip. Do not reorder.**

### Step 1: Lint BEFORE Committing

```bash
ruff check protocol/ core/ adapters/
```

If lint fails, fix it. **Never commit code that fails lint** — fixing lint after commit requires either amend (breaks protected branches) or an extra commit (splits changes, tag placement becomes error-prone).

### Step 2: Run Tests BEFORE Committing

```bash
cd core && python -m pytest tests/ --timeout=60 \
  --ignore=tests/test_onchain_localnet.py \
  --ignore=tests/test_onchain_devnet.py \
  --ignore=tests/test_devnet_e2e.py
```

All tests must pass. Do not commit with known failures.

### Step 3: Version Bump — ALL 10 Files in ONE Commit

Determine the next version. Check existing tags:

```bash
git tag -l 'v*' --sort=-v:refname | head -3
```

Update **all 10 files** in a single commit:

| File | Field |
|------|-------|
| `core/pyproject.toml` | `version = "X.Y.Z"` |
| `protocol/pyproject.toml` | `version = "X.Y.Z"` |
| `adapters/mcp/pyproject.toml` | `version = "X.Y.Z"` |
| `adapters/client_mcp/pyproject.toml` | `version = "X.Y.Z"` |
| `core/ag402_core/__init__.py` | `__version__ = "X.Y.Z"` |
| `protocol/open402/__init__.py` | `__version__ = "X.Y.Z"` |
| `adapters/mcp/ag402_mcp/__init__.py` | `__version__ = "X.Y.Z"` |
| `adapters/client_mcp/ag402_client_mcp/__init__.py` | `__version__ = "X.Y.Z"` |
| `adapters/client_mcp/tests/test_server.py` | `assert __version__ == "X.Y.Z"` |
| `CHANGELOG.md` | Add `## [X.Y.Z]` section at top |

**Never split version bump and code changes into separate commits before tagging.** The tag must land on a commit that has both the code changes AND the correct version numbers.

### Step 4: Tag the FINAL Commit

```bash
git tag -a vX.Y.Z -m "vX.Y.Z: short description"
```

**The tag MUST point to the commit containing the version bump.** Verify:

```bash
git log --oneline -1 vX.Y.Z
# Must show the version bump commit, NOT an earlier commit
```

### Step 5: Push Commit + Tag Together

```bash
git push -u origin main && git push origin vX.Y.Z
```

### Step 6: Create GitHub Release

```bash
gh release create vX.Y.Z --title "vX.Y.Z" --notes "$(cat <<'EOF'
## What's Changed
...
EOF
)"
```

The publish workflow (`.github/workflows/publish.yml`) triggers on `release: types: [published]` and checks out the tag's ref. Since the tag points to the version-bumped commit, the build produces correctly versioned packages.

## Mistakes This Skill Prevents

| Mistake | Consequence | Prevention |
|---------|-------------|------------|
| Commit code, then fix lint separately | Extra commit; tag placed on wrong commit | Step 1: lint before commit |
| Tag on code commit, version bump in later commit | CI checks out tag → builds old version → PyPI rejects duplicate filename | Step 3-4: version bump + tag on same commit |
| Forget `__init__.py` or test assertion | `__version__` mismatches `pyproject.toml`; test fails in CI | Step 3: all 10 files checklist |
| Forget CHANGELOG.md | Release notes incomplete | Step 3: CHANGELOG in same commit |
| `git push --force` on protected branch | Push rejected; requires extra fixup commits | Never amend pushed commits; get it right first time |
| Tag points to wrong commit | CI builds wrong version; PyPI upload fails with "File already exists" | Step 4: verify tag target |

## Red Flags — STOP and Recheck

- About to `git commit` but haven't run `ruff check` → STOP
- About to `git tag` but version bump is in a different commit → STOP
- About to `git push --force` on main → STOP (protected branch)
- About to `gh release create` but `git log --oneline -1 vX.Y.Z` doesn't show version bump → STOP
- About to `git commit --amend` on an already-pushed commit → STOP

## Quick Reference: Ideal Single-Shot Flow

```bash
# 1. Lint
ruff check protocol/ core/ adapters/

# 2. Test
cd core && python -m pytest tests/ --timeout=60 --ignore=tests/test_onchain_localnet.py --ignore=tests/test_onchain_devnet.py --ignore=tests/test_devnet_e2e.py

# 3. Bump versions (all 10 files), commit
git add -A && git commit -m "chore: bump all package versions to X.Y.Z for PyPI publish"

# 4. Tag the version-bumped commit
git tag -a vX.Y.Z -m "vX.Y.Z: description"

# 5. Push together
git push -u origin main && git push origin vX.Y.Z

# 6. Create GitHub Release (triggers PyPI publish)
gh release create vX.Y.Z --title "vX.Y.Z" --notes "..."
```
