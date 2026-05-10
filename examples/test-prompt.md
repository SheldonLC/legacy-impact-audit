# Test Prompt

Use this prompt in a fresh Codex session after installing the skill.

```text
Use $legacy-impact-audit.

Run a read-only impact audit for a legacy Java method. Do not modify code. Do not perform broad full-code LLM analysis.

Repository root:
`/path/to/repo`

Target:
- Method: `METHOD_NAME`
- Owner class: `OWNER_CLASS`
- Owner package: `com.example.package`
- Definition file: `/path/to/repo/path/to/OwnerClass.java`
- Search scope/module: `/path/to/repo/path/to/module`

Required output:
- command executed
- gate status and raw/filtered/candidate counts
- top candidate table
- semantic verdicts for the generated candidate packet
- L1-only vs L2 decision
- recommended functional and regression tests
- residual risks
```
