# Install Samples

Install into the default Codex skills directory:

```bash
python3 portable/install-kit.py --agent codex --scope user
```

Overwrite an existing installation:

```bash
python3 portable/install-kit.py --agent codex --scope user --force
```

Install into a custom skills directory:

```bash
python3 portable/install-kit.py --agent codex --skills-dir "$HOME/.codex/skills"
```

Install for all supported user-level agents:

```bash
python3 portable/install-kit.py --agent all --scope user --force
```

Install project adapters for non-Codex agents:

```bash
python3 portable/install-kit.py \
  --agent claude,opencode,gemini,copilot,deepcode \
  --scope project \
  --project-root /path/to/target/repo \
  --force
```

Run a scan from a Java repository:

```bash
python3 "$HOME/.codex/skills/legacy-impact-audit/scripts/impact_audit.py" scan \
  --root . \
  --symbol METHOD_NAME \
  --owner-class OWNER_CLASS \
  --owner-package OWNER_PACKAGE \
  --definition-file path/to/OwnerClass.java
```

Validate audit artifacts for staged changes:

```bash
python3 "$HOME/.codex/skills/legacy-impact-audit/scripts/validate_impact_audit.py" \
  --root . \
  --mode staged
```
