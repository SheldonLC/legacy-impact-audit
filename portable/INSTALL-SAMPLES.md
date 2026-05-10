# Install Samples

Install into the default Codex skills directory:

```bash
python3 portable/install-kit.py --agent codex --scope user
```

Install into the default Codex skills directory without Python:

```bash
sh portable/install-kit.sh --agent codex --scope user
```

```powershell
powershell -ExecutionPolicy Bypass -File portable/install-kit.ps1 -Agent codex -Scope user
```

Overwrite an existing installation:

```bash
python3 portable/install-kit.py --agent codex --scope user --force
```

No-Python overwrite:

```bash
sh portable/install-kit.sh --agent codex --scope user --force
```

```powershell
powershell -ExecutionPolicy Bypass -File portable/install-kit.ps1 -Agent codex -Scope user -Force
```

Install into a custom skills directory:

```bash
python3 portable/install-kit.py --agent codex --skills-dir "$HOME/.codex/skills"
```

No-Python custom skills directory:

```bash
sh portable/install-kit.sh --agent codex --skills-dir "$HOME/.codex/skills"
```

```powershell
powershell -ExecutionPolicy Bypass -File portable/install-kit.ps1 -Agent codex -SkillsDir "$HOME/.codex/skills"
```

Install for all supported user-level agents:

```bash
python3 portable/install-kit.py --agent all --scope user --force
```

No-Python all-agent install:

```bash
sh portable/install-kit.sh --agent all --scope user --force
```

```powershell
powershell -ExecutionPolicy Bypass -File portable/install-kit.ps1 -Agent all -Scope user -Force
```

Install project adapters for non-Codex agents:

```bash
python3 portable/install-kit.py \
  --agent claude,opencode,gemini,copilot,deepcode \
  --scope project \
  --project-root /path/to/target/repo \
  --force
```

No-Python project adapter install:

```bash
sh portable/install-kit.sh \
  --agent claude,opencode,gemini,copilot,deepcode \
  --scope project \
  --project-root /path/to/target/repo \
  --force
```

```powershell
powershell -ExecutionPolicy Bypass -File portable/install-kit.ps1 `
  -Agent claude,opencode,gemini,copilot,deepcode `
  -Scope project `
  -ProjectRoot /path/to/target/repo `
  -Force
```

Installation can run without Python. The scan and validation commands below still require Python 3.

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
