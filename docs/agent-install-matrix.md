# Agent Install Matrix

| Agent | User install | Project install | Notes |
| --- | --- | --- | --- |
| Codex | `~/.codex/skills/legacy-impact-audit` or `$CODEX_HOME/skills/legacy-impact-audit` | Not used by this kit | Native Codex skill. |
| Claude Code | `~/.claude/skills/legacy-impact-audit` | `.claude/skills/legacy-impact-audit` | Native Agent Skill. |
| opencode | `~/.config/opencode/skills/legacy-impact-audit` | `.opencode/skills/legacy-impact-audit` plus `AGENTS.md` | Skill plus project instruction adapter. |
| Gemini CLI | `~/.agents/skills/legacy-impact-audit` plus `~/.gemini/GEMINI.md` | `.ai/legacy-impact-audit/skills/legacy-impact-audit` plus `GEMINI.md` | Instruction adapter pointing to deterministic scripts. |
| GitHub Copilot | `~/.copilot/skills/legacy-impact-audit` | `.github/skills/legacy-impact-audit` plus `.github/copilot-instructions.md` | Skill plus repository custom instructions. |
| Deep Code | `~/.agents/skills/legacy-impact-audit` | `.deepcode/skills/legacy-impact-audit` | Native Agent Skill. |

## Install All User-Level Targets

```bash
python3 portable/install-kit.py --agent all --scope user --force
```

## Install A Project Adapter

```bash
python3 portable/install-kit.py \
  --agent claude,opencode,gemini,copilot,deepcode \
  --scope project \
  --project-root /path/to/target/repo \
  --force
```

Use project adapters when a repository needs mandatory gate behavior for all coding agents.
