# No-Python Install Guide

`legacy-impact-audit` can be installed without Python because installation only copies files and, for some agents, writes an instruction block.

Python is still required to run the deterministic audit scripts:

- `legacy-impact-audit/scripts/impact_audit.py`
- `legacy-impact-audit/scripts/validate_impact_audit.py`

Use this guide when the target machine does not have Python yet, or when an agent needs to install the kit before checking runtime prerequisites.

## Option 1: Shell Installer

Use this on Linux, macOS, Git Bash, or WSL:

```bash
sh portable/install-kit.sh --agent codex --scope user --force
```

Install all supported user-level targets:

```bash
sh portable/install-kit.sh --agent all --scope user --force
```

Install project adapters:

```bash
sh portable/install-kit.sh \
  --agent claude,opencode,gemini,copilot,deepcode \
  --scope project \
  --project-root /path/to/target/repo \
  --force
```

## Option 2: PowerShell Installer

Use this on Windows PowerShell or PowerShell 7:

```powershell
powershell -ExecutionPolicy Bypass -File portable/install-kit.ps1 -Agent codex -Scope user -Force
```

Install all supported user-level targets:

```powershell
powershell -ExecutionPolicy Bypass -File portable/install-kit.ps1 -Agent all -Scope user -Force
```

Install project adapters:

```powershell
powershell -ExecutionPolicy Bypass -File portable/install-kit.ps1 `
  -Agent claude,opencode,gemini,copilot,deepcode `
  -Scope project `
  -ProjectRoot "<path-to-target-repo>" `
  -Force
```

## Option 3: Manual Copy

Copy the `legacy-impact-audit` directory to the agent's skill directory:

| Agent | User install | Project install |
| --- | --- | --- |
| Codex | `~/.codex/skills/legacy-impact-audit` or `$CODEX_HOME/skills/legacy-impact-audit` | Not used by this kit |
| Claude Code | `~/.claude/skills/legacy-impact-audit` | `.claude/skills/legacy-impact-audit` |
| opencode | `~/.config/opencode/skills/legacy-impact-audit` | `.opencode/skills/legacy-impact-audit` |
| Gemini CLI | `~/.agents/skills/legacy-impact-audit` | `.ai/legacy-impact-audit/skills/legacy-impact-audit` |
| GitHub Copilot | `~/.copilot/skills/legacy-impact-audit` | `.github/skills/legacy-impact-audit` |
| Deep Code | `~/.agents/skills/legacy-impact-audit` | `.deepcode/skills/legacy-impact-audit` |

For Gemini, opencode project installs, and Copilot project installs, also add the marked instruction block shown in `examples/AGENTS-impact-audit.md` or run one of the installers above so the block is written automatically.

## Runtime Requirement

After installation, a working audit gate still needs:

- Python 3 to run the deterministic audit and validation scripts.
- `rg` / ripgrep to perform low-cost workspace search.
- An LLM-capable agent only after `impact_audit.py` has generated the small `llm-packet.md`.

If Python is unavailable, the correct status is:

```text
Installed: yes
Audit execution: skipped, Python 3 unavailable
Gate status: not enforceable until Python 3 is available
```
