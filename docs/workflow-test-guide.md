# Workflow Test Guide

Use this guide to validate `legacy-impact-audit` with another AI agent. The test uses the mock project in `examples/mock-legacy-java` and does not require a real enterprise codebase.

## Test Goals

Verify that the agent can:

- Install or use `legacy-impact-audit`.
- Run the deterministic scan before broad semantic analysis.
- Respect `REFINE_REQUIRED` for generic method names.
- Distinguish real Java callers from string/config/build noise.
- Use generated `llm-packet.md` for semantic confirmation.
- Validate audit artifacts before test planning or review.

## Fixture

Mock project root:

```text
examples/mock-legacy-java
```

Primary target:

```text
Method: recomputePlayerScore
Owner class: ArcadeScoreService
Owner package: com.example.sandbox.arcade
Definition file: src/main/java/com/example/sandbox/arcade/ArcadeScoreService.java
```

Expected semantic results:

| Candidate | Expected Verdict | Reason |
| --- | --- | --- |
| `TournamentJob.java` | `real_dependency` | Imports owner class and calls `arcadeScoreService.recomputePlayerScore(...)`. |
| `ScoreConsoleController.java` | `real_dependency` | Imports owner class and calls `service.recomputePlayerScore(...)`. |
| `ArcadeScoreService.java` | `not_dependency` or definition-only | It is the owner definition, not an external caller. |
| `ScoreTemplateRegistry.java` | `not_dependency` | String-only reference. |
| `workflow.xml` | `needs_manual_check` | XML config may represent dynamic wiring. |
| `ArcadeScoreServiceTest.java` | `possible_dependency` | Test-only reference; useful for regression scope, not production L1 caller. |
| `build.xml` | Should not appear | Build file is excluded by scanner defaults. |

## Test 1: L1 Impact Audit

Run from the repository root:

```bash
python3 legacy-impact-audit/scripts/impact_audit.py scan \
  --root examples/mock-legacy-java \
  --symbol recomputePlayerScore \
  --owner-class ArcadeScoreService \
  --owner-package com.example.sandbox.arcade \
  --definition-file src/main/java/com/example/sandbox/arcade/ArcadeScoreService.java \
  --max-candidates 20
```

Expected:

- `gate=PASS`
- `impact-report.md`, `llm-packet.md`, and `impact-scan.json` are written under `examples/mock-legacy-java/.ai/legacy-impact-audit/`.
- Top production candidates include `TournamentJob.java` and `ScoreConsoleController.java`.
- `build.xml` is excluded.

## Test 2: Generic Method Gate

Run:

```bash
python3 legacy-impact-audit/scripts/impact_audit.py scan \
  --root examples/mock-legacy-java \
  --symbol execute \
  --max-candidates 10 \
  --raw-limit 9999 \
  --generic-limit 2 \
  --output-dir /tmp/legacy-impact-audit-generic-gate \
  --fail-on-refine
```

Expected:

- Exit code `2`.
- `gate=REFINE_REQUIRED`.
- Output is written to `/tmp/legacy-impact-audit-generic-gate` so it does not overwrite the successful L1 audit artifacts.
- The agent must not perform LLM semantic analysis on raw results.
- The agent should propose narrowing with `--owner-class`, `--owner-package`, `--module-path`, or `--definition-file`.

## Test 3: Semantic Verdict Artifact

After Test 1, write a verdict file:

```text
examples/mock-legacy-java/.ai/legacy-impact-audit/semantic-verdict.md
```

Minimum expected content:

```md
# Semantic Verdict

- TournamentJob.java: real_dependency, high confidence.
- ScoreConsoleController.java: real_dependency, high confidence.
- ScoreTemplateRegistry.java: not_dependency, high confidence.
- workflow.xml: needs_manual_check, medium confidence.
- ArcadeScoreServiceTest.java: possible_dependency for regression scope.
```

## Test 4: Validator Gate

Run:

```bash
python3 legacy-impact-audit/scripts/validate_impact_audit.py \
  --root examples/mock-legacy-java \
  --mode worktree \
  --always-require \
  --require-verdicts
```

Expected:

- `PASS: impact audit artifacts are present, fresh, and gate status is PASS`

## Agent Acceptance Criteria

The agent passes the workflow test only if it:

- Runs `impact_audit.py scan` before semantic analysis.
- Does not inspect the whole mock project before the scan.
- Uses `llm-packet.md` or the ranked report for semantic confirmation.
- Treats `execute` as blocked by `REFINE_REQUIRED`.
- Produces a test scope derived from `real_dependency` and `possible_dependency`.
- Reports residual risks for XML/dynamic wiring.
