# Hook Patterns

Hooks should enforce the impact funnel's gates and produce small artifacts. Do not run LLM calls inside hooks unless a user explicitly accepts the cost and latency.

## Recommended Modes

### Interactive skill-first mode

Use this by default. Before changing a risky Java method, the agent runs:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/legacy-impact-audit/scripts/impact_audit.py" scan \
  --root . \
  --symbol METHOD_NAME \
  --owner-class OWNER_CLASS \
  --owner-package OWNER_PACKAGE \
  --definition-file PATH_TO_OWNER_CLASS.java
```

The agent then reads `.ai/legacy-impact-audit/llm-packet.md` and performs semantic confirmation.

### Pre-commit validator mode

Use this when the repo often receives Java changes without impact notes. The hook should fail only when watched source/config files changed and no fresh passing `.ai/legacy-impact-audit/impact-scan.json` exists.

Example `.git/hooks/pre-commit`:

```bash
#!/usr/bin/env bash
set -euo pipefail

python3 "${CODEX_HOME:-$HOME/.codex}/skills/legacy-impact-audit/scripts/validate_impact_audit.py" \
  --root . \
  --mode staged \
  --max-age-minutes 240
```

For repositories where semantic confirmation must be captured before review, add `--require-verdicts` and write `.ai/legacy-impact-audit/semantic-verdict.md` during the review/test-planning step.

### Target-file mode

Use this when teams want deterministic blocking on known risky methods. Keep `.ai/legacy-impact-audit/targets.json` in the repo:

```json
{
  "targets": [
    {
      "symbol": "recomputePlayerScore",
      "ownerClass": "ArcadeScoreService",
      "ownerPackage": "com.example.sandbox.arcade",
      "definitionFile": "src/main/java/com/example/sandbox/arcade/ArcadeScoreService.java"
    }
  ]
}
```

A local hook can read the target file and run `impact_audit.py scan --fail-on-refine` for each item. This is safer than trying to infer every changed method from a Java diff.

## Hook Boundaries

- Block on `REFINE_REQUIRED`; do not block on medium/low heuristic confidence.
- Keep hook runtime under a few seconds by narrowing root/module where possible.
- Do not scan the whole monorepo for generic names like `execute` without owner class/package.
- Prefer validation hooks over auto-scan hooks. Auto-scan hooks cannot know the correct owner class/package for legacy overloads.
- Do not commit cache entries unless the team wants dependency verdicts shared.
- Treat hook output as a safety net. The agent still owns semantic confirmation and test planning.
