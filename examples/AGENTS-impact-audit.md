# AGENTS.md Snippet

Add this to a target repository's `AGENTS.md` when impact audit should be mandatory.

```md
## Mandatory Legacy Impact Audit Gate

Before planning or implementing risky legacy Java changes, use `$legacy-impact-audit`.

This is mandatory when changing:
- service methods, public APIs, shared utilities, job entry points, workflow logic
- DAO/query/persistence behavior, DTO/table/JSON contracts
- financial calculation, scoring, approval, reconciliation, workflow, or other core business logic

Gate rules:
- Run the impact audit before finalizing the implementation plan.
- Run it again after code changes and before functional test case design or code review.
- Do not proceed if the audit returns `REFINE_REQUIRED`; narrow by owner class, package, module, or definition file first.
- Do not ask the LLM to analyze broad raw search results; use the generated audit report and packet.
- Test scope and regression scope must be derived from confirmed `real_dependency` and `possible_dependency` candidates.
- If no audit is needed, explicitly state the reason, such as docs-only change, isolated test-only change, or no Java/business behavior change.
```
