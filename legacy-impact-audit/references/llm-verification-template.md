# LLM Verification Template

Use this template only after `impact_audit.py scan` has generated a small candidate packet.

## Prompt

You are doing semantic impact analysis for a legacy Java change.

Target method:

- Method: `{symbol}`
- Owner class: `{owner_class}`
- Owner package: `{owner_package}`
- Definition or diff: `{definition_or_diff}`

Candidate snippets are ranked by cheap heuristics. For each candidate, decide whether it is a real logical dependency under Java semantics.

Classify each candidate as one of:

- `real_dependency`: The code directly calls or relies on the target behavior.
- `possible_dependency`: The code may depend on it, but overloads, dynamic wiring, inheritance, or incomplete context prevent certainty.
- `not_dependency`: It is a string match, unrelated same-name method, log/comment/config noise, or different class.
- `needs_manual_check`: Reflection, XML wiring, dynamic proxy, generated code, or runtime dispatch requires human/project-specific verification.

Return this schema:

```json
{
  "target": "Class.method",
  "scope_decision": "L1_only | expand_L2",
  "scope_reason": "why L2 is or is not required",
  "candidates": [
    {
      "candidate": 1,
      "verdict": "real_dependency | possible_dependency | not_dependency | needs_manual_check",
      "confidence": "high | medium | low",
      "reason": "short Java-semantic reason",
      "impact": "what could break if the target changes",
      "recommended_check": "unit/integration/manual check"
    }
  ],
  "residual_risks": ["risk"],
  "recommended_tests": ["test"]
}
```

## Decision Rules

- Prefer `possible_dependency` over `real_dependency` when the owner class is not imported or visible in the snippet.
- Treat same-name methods in different classes as `not_dependency` unless import/type context ties them to the owner.
- Treat XML/config matches as `needs_manual_check` when they may represent Spring, Struts, MyBatis, job, or workflow wiring.
- Trigger `expand_L2` only for public APIs, shared utilities/base services, job entry points, persistence boundaries, DTO/table/query shape changes, or core business logic.
- Keep the explanation short enough to paste into an impact report.
