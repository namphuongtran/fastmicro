# AGENTS.md — Rules for AI Coding Agents

This file defines **mandatory rules** that all AI coding agents (GitHub Copilot,
Copilot Chat, Copilot Workspace, or any custom agent) **must follow** when
working in this repository.

---

## 1. Lint Before Every Commit

> **MANDATORY — zero exceptions.**

Before committing **any** code change, the agent **must** run the project linter
and ensure the output is clean (`All checks passed!`).

### Commands

```bash
# Shared library
cd shared && uv run ruff check src/ tests/

# Individual service (example)
cd services/audit-service && uv run ruff check src/ tests/

# Auto-fix safe violations first, then verify
uv run ruff check src/ tests/ --fix
uv run ruff check src/ tests/          # must show "All checks passed!"
```

### Workflow

1. **Write / edit code.**
2. **Run `ruff check`** on the changed package(s).
3. **If violations exist** — fix them (auto-fix first, then manual).
4. **Re-run `ruff check`** — confirm `All checks passed!`.
5. **Run tests** — confirm all tests pass.
6. **Only then commit.**

If `ruff check` reports any error, **do not commit**. Fix the errors first.

---

## 2. Ruff Configuration Reference

The project ruff config lives in each package's `pyproject.toml` under
`[tool.ruff]`. Key settings for the shared library:

| Setting | Value |
|---------|-------|
| `line-length` | 100 |
| `target-version` | `py312` |
| Selected rules | A, E, W, F, I, B, C4, UP, SIM, PTH, RUF |
| `__init__.py` ignores | F401 (re-exports), E402 (conditional imports) |
| Test file ignores | S101, PLR2004, B017, F841 |

### Common Violations to Watch For

| Rule | Description | Fix |
|------|-------------|-----|
| **RUF002/RUF003** | EN DASH (`–`) in docstrings/comments | Replace with HYPHEN-MINUS (`-`) |
| **F401** | Unused import | Remove the import or add `# noqa: F401` if re-exporting |
| **I001** | Unsorted imports | Run `ruff check --fix` (auto-fixable) |
| **E402** | Import not at top of file | Move import or add `# noqa: E402` with justification |
| **SIM117** | Nested `with` statements | Combine into single `with` using `, \\` continuation |
| **B007** | Unused loop variable | Rename to `_` |
| **W292** | Missing newline at end of file | Add trailing newline |
| **RUF100** | Unused `# noqa` comment | Remove the stale noqa |

### When `# noqa` Is Acceptable

Only suppress a rule when the violation is **intentional and documented**:

```python
# Backward-compat re-export — keep the import for downstream consumers
from shared.dbs.repository import PageResponse  # noqa: E402
```

Never use blanket `# noqa` (without a rule code). Always specify the rule:
`# noqa: E402`.

---

## 3. Format Check

After lint, also verify formatting:

```bash
uv run ruff format --check src/ tests/
```

If formatting drifts, fix with:

```bash
uv run ruff format src/ tests/
```

---

## 4. Test Before Commit

After lint and format pass, run the test suite:

```bash
# Shared library
cd shared && uv run pytest tests/ -x -q

# Expected: all tests pass, zero failures
```

---

## 5. Commit Message Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

<optional body>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `perf`.

For multi-line commit messages, write the message to a temp file and use
`git commit -F <file>` to avoid shell escaping issues in terminals.

---

## 6. Pre-Commit Checklist

Before every `git commit`, verify **all** of the following:

- [ ] `ruff check src/ tests/` — `All checks passed!`
- [ ] `ruff format --check src/ tests/` — no formatting issues
- [ ] `pytest tests/ -x -q` — all tests pass
- [ ] No `# type: ignore` without explanation
- [ ] No hardcoded secrets or credentials
- [ ] Commit message follows conventional commits format

---

## 7. Unicode in Docstrings and Comments

**Never use typographic/smart punctuation** in Python source code:

| Bad (Unicode) | Good (ASCII) |
|---------------|-------------|
| `–` (EN DASH, U+2013) | `-` (HYPHEN-MINUS, U+002D) |
| `—` (EM DASH, U+2014) | ` - ` or `--` |
| `'` `'` (smart quotes) | `'` (ASCII apostrophe) |
| `"` `"` (smart quotes) | `"` (ASCII double quote) |
| `…` (ellipsis) | `...` |

Ruff rules RUF001/RUF002/RUF003 enforce this.

---

## 8. Import Ordering

Imports must follow isort conventions (enforced by `I001`):

1. Standard library
2. Third-party packages
3. First-party (`shared`, service modules)

Within each group, imports are sorted alphabetically. Use `ruff check --fix`
to auto-sort.

---

## Summary

```
Code change → ruff check → ruff format --check → pytest → commit
```

**No exceptions. No "I'll fix lint later." Lint must be clean before commit.**
