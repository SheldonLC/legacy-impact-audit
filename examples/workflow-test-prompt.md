# Workflow Test Prompt

Give this prompt to another AI agent to validate the full `legacy-impact-audit` workflow.

```text
Read `AI-SELF-INSTALL.md` and `docs/workflow-test-guide.md`.

Use the mock project at `examples/mock-legacy-java` to validate the `legacy-impact-audit` workflow. Do not modify production code outside the mock project and audit artifact files.

Tasks:
1. Confirm `legacy-impact-audit/scripts/impact_audit.py` and `legacy-impact-audit/scripts/validate_impact_audit.py` exist.
2. Run Test 1 from `docs/workflow-test-guide.md` for `ArcadeScoreService.recomputePlayerScore`.
3. Read the generated `impact-report.md` and `llm-packet.md`; do not perform broad full-project semantic analysis first.
4. Produce semantic verdicts for the candidates and write them to `examples/mock-legacy-java/.ai/legacy-impact-audit/semantic-verdict.md`.
5. Run Test 2 for generic method `execute` using the documented `/tmp/legacy-impact-audit-generic-gate` output directory and confirm it returns `REFINE_REQUIRED`.
6. Run Test 4 validator with `--require-verdicts`.
7. Report:
   - commands executed
   - gate statuses and counts
   - top candidates and semantic verdicts
   - whether L2 expansion is needed
   - test/regression scope derived from real/possible dependencies
   - any workflow failures or residual risks

Expected high-level result:
- `recomputePlayerScore` audit passes and identifies real callers in `TournamentJob` and `ScoreConsoleController`.
- generic `execute` audit is blocked by `REFINE_REQUIRED`.
- validator passes after `semantic-verdict.md` is written.
```
