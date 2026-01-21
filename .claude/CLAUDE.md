# CLAUDE.md

Instructions and guidelines for Claude Code when working on the BA-LoRA-Adapters project.

## Project Overview

This is a data pipeline for preparing customer-agent call transcripts for LoRA adapter training. The pipeline has 5 steps, and we're building it incrementally - one step at a time.

See [IMPLEMENTATION.md](../IMPLEMENTATION.md) for the detailed implementation plan with data models and algorithms.

---

## Git Workflow

### Branch Structure

```
main
 └── develop
      ├── feature/step-1-sanitization
      ├── feature/step-2-tagging
      ├── feature/step-3-exporting
      └── ...
```

- **`main`** - Stable releases only. Never commit directly to main.
- **`develop`** - Integration branch. All feature branches merge here first.
- **`feature/*`** - Individual feature branches for each step or piece of work.

### Development Process

1. **Starting work on a new step:**
   - First, ensure `develop` branch exists (branch off `main` if not)
   - Create a feature branch off `develop`:
     ```bash
     git checkout develop
     git pull origin develop
     git checkout -b feature/step-X-description
     ```

2. **While working:**
   - Make incremental commits with clear messages
   - Keep changes focused on the current step

3. **When the step is complete:**
   - Run type checks (see below)
   - Add minimal unit tests for new functionality
   - Ensure all tests pass
   - Open a PR from the feature branch to `develop`

4. **After PR is merged:**
   - Delete the feature branch
   - Pull latest `develop` before starting next step

### Before Opening Any PR

**Required checks:**

1. **Type checking** - Run `mypy` or `pyright` to catch type errors:
   ```bash
   mypy src/ scripts/
   # or
   pyright src/ scripts/
   ```

2. **Unit tests** - Add tests for new functionality and run:
   ```bash
   pytest tests/
   ```

3. **All tests must pass** before the PR can be merged.

---

## Implementation Order

We're building this step-by-step in order:

| Step | Name | Status |
|------|------|--------|
| 1 | Sanitization | ✅ Complete |
| 2 | Tagging (LLM) | ✅ Complete |
| 3 | Exporting (ShareGPT) | ⬜ Not started |
| 4 | Training (Llama-Factory) | ⬜ Future |
| 5 | Serving (vLLM) | ⬜ Future |

Update this table as steps are completed.

---

## Code Style & Conventions

- Use Pydantic models for all data structures (see `src/models/`)
- Type hints on all function signatures
- CLI scripts use `argparse` with clear help text
- Logging via `src/utils/logging_utils.py`

---

## Testing Guidelines

- Tests go in `tests/` directory
- Use `pytest` as the test runner
- Name test files `test_*.py`
- Minimal but meaningful tests - cover the happy path and key edge cases
- For Step 1: test noise filtering, role mapping, turn merging
- For Step 2: test LLM response parsing, rewrite threshold logic
- For Step 3: test ShareGPT format generation, cumulative history building
