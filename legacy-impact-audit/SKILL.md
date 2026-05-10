---
name: legacy-impact-audit
description: Low-token impact audit for legacy Java or mixed enterprise repositories where full knowledge graphs are unavailable, stale, or too expensive. Use before changing a method, service API, shared utility, job entry point, mapper, DTO contract, persistence query, financial calculation, or business-rule logic; use when the user asks for change impact, caller analysis, blast radius, regression risk, dependency confirmation, impact audit, or safe L1/L2 impact review.
---

# Legacy Impact Audit

## Purpose

Run a cheap-to-expensive impact funnel before editing risky legacy code. Prefer deterministic search and ranking first; call the LLM only on a small candidate packet.

## Required Workflow

1. Identify the target symbol: method name, owner class, package, file path, and intended change type.
2. Run `scripts/impact_audit.py scan` from the target repo root before opening broad code areas.
3. Treat `REFINE_REQUIRED` as a hard stop. Narrow by owner class, package, module, or file path before semantic analysis.
4. Review only the top-ranked candidate snippets, not whole directories.
5. Use LLM semantic confirmation only after the script has reduced candidates to a small packet.
6. Analyze direct callers only by default. Expand to L2 only when a confirmed L1 dependency is a public interface, shared service/util, job entry point, persistence boundary, DTO contract, or core business rule.
7. Save confirmed dependency results into `.ai/legacy-impact-audit/cache.json` when the change is important or likely to recur.
8. Report residual uncertainty explicitly: dynamic reflection, XML wiring, overloaded methods, same-name methods, and generated code can defeat text search.

## Quick Start

From the target repository:

```bash
impact_home="${LEGACY_IMPACT_AUDIT_HOME:-${CODEX_HOME:-$HOME/.codex}/skills/legacy-impact-audit}"
python3 "$impact_home/scripts/impact_audit.py" scan \
  --root . \
  --symbol recomputePlayerScore \
  --owner-class ArcadeScoreService \
  --owner-package com.example.sandbox.arcade \
  --definition-file src/main/java/com/example/sandbox/arcade/ArcadeScoreService.java \
  --encoding utf-8
```

Prerequisites: Python 3 and `rg` / ripgrep must be available in PATH. If the skill is installed outside the Codex default path, set `LEGACY_IMPACT_AUDIT_HOME` to the installed `legacy-impact-audit` directory. For legacy source files, pass `--encoding gbk` or another Python/ripgrep-supported encoding; use `--encoding auto` to let ripgrep use its default detection while snippets fall back to UTF-8 replacement decoding.

Read the generated files in `.ai/legacy-impact-audit/`:

- `impact-report.md` for the ranked human review.
- `llm-packet.md` for the small semantic-confirmation prompt.
- `impact-scan.json` for machine-readable candidates and cache keys.

## Funnel Rules

### Layer 1: Full Retrieval

Use `rg` through the bundled script. It excludes hidden directories, `.git`, `node_modules`, build outputs, generated dependency folders, `build.xml`, and obvious logging/comment noise.

Do not run broad LLM analysis on raw search results.

### Layer 2: Heuristic Grouping

Rank candidates higher when they:

- Import the owner class or statically import the target method.
- Share the owner package or module path.
- Contain Java call shapes like `.methodName(` or `methodName(` outside a declaration.
- Reference the owner class near the match.

Rank candidates lower when they:

- Only match strings or XML attributes.
- Are comments, log statements, generated/build files, or generic config.
- Are tests rather than production call paths.

### Layer 3: LLM Semantic Confirmation

Give the LLM only:

- The method definition or changed diff.
- The ranked candidate snippets from `llm-packet.md`.
- The requested classification format from `references/llm-verification-template.md`.

Ask whether each candidate is a real logical dependency under Java semantics, not merely a text match.

## Gate Logic

### Signature Uniqueness

If the symbol is generic, short, or high-frequency, do not continue with raw results. Examples: `get`, `set`, `execute`, `run`, `process`, `handle`, `save`, `update`, `query`, `validate`.

When the script returns `REFINE_REQUIRED`, narrow the query with at least one of:

- `--owner-class`
- `--owner-package`
- `--module-path`
- `--definition-file`
- A more specific method overload or surrounding class name

### Depth Control

Default to L1 direct callers. Trigger L2 only when the L1 change is confirmed and one of these is true:

- Public API or interface behavior changes.
- Shared utility/base service behavior changes.
- Financial calculation, workflow, job scheduling, approval, or persistence semantics change.
- DTO/table/query shape changes.
- Error handling or transaction boundary changes.

### Cache Control

Use cache hits only when the script reports the same cache key and candidate hashes. Revalidate if:

- `git diff` changes the target definition or candidate file.
- The method signature or owner class changes.
- A candidate file hash changes.
- The prior confidence was below `high`.

Use `cache-put --cache-max-entries` and `--cache-ttl-days` when a long-running repository needs local cache pruning.

## Optional Hooks

Hooks should enforce the funnel, not replace judgment. Read `references/hook-patterns.md` before installing any hook into a repo.

Recommended setup:

- Use the skill as the default interactive workflow.
- Add a pre-commit or CI validator only for high-risk repos to block when Java/config changes lack a fresh passing impact report.
- Avoid automatic LLM calls inside hooks. Hooks should generate or validate the candidate packet; the agent performs semantic confirmation.

## Report Contract

Every impact analysis should include:

- Target method/class/package and intended change.
- Raw match count, filtered match count, candidate file count, and gate status.
- Top candidate table with score, priority, file, line numbers, and reasons.
- LLM semantic verdicts: `real_dependency`, `possible_dependency`, `not_dependency`, or `needs_manual_check`.
- L1-only or L2-expanded scope decision.
- Recommended regression tests and manual checks.
- Cache status and residual risks.

## Resources

- `scripts/impact_audit.py`: deterministic search, ranking, report, packet, and cache-key generator.
- `scripts/validate_impact_audit.py`: deterministic hook/CI validator for audit artifacts.
- `references/llm-verification-template.md`: semantic confirmation prompt and output schema.
- `references/hook-patterns.md`: safe optional hook patterns.
