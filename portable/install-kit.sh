#!/usr/bin/env sh
set -eu

SKILL_NAME="legacy-impact-audit"
MARKER_START="<!-- legacy-impact-audit:start -->"
MARKER_END="<!-- legacy-impact-audit:end -->"

agent_arg="codex"
scope="user"
project_root="."
skills_dir=""
source_dir=""
force=0

usage() {
  cat <<'EOF'
Install legacy-impact-audit without Python.

Usage:
  sh portable/install-kit.sh [options]

Options:
  --agent NAME           codex, claude, opencode, gemini, copilot, deepcode, all, or comma-separated list
  --scope SCOPE          user or project
  --project-root PATH    target repository for project-scope installs
  --skills-dir PATH      explicit Codex skills directory
  --source PATH          source legacy-impact-audit skill directory
  --force                overwrite existing installation
  -h, --help             show this help
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --agent)
      agent_arg="${2:?missing --agent value}"
      shift 2
      ;;
    --scope)
      scope="${2:?missing --scope value}"
      shift 2
      ;;
    --project-root)
      project_root="${2:?missing --project-root value}"
      shift 2
      ;;
    --skills-dir)
      skills_dir="${2:?missing --skills-dir value}"
      shift 2
      ;;
    --source)
      source_dir="${2:?missing --source value}"
      shift 2
      ;;
    --force)
      force=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ "$scope" != "user" ] && [ "$scope" != "project" ]; then
  echo "--scope must be user or project" >&2
  exit 2
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
kit_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
if [ -z "$source_dir" ]; then
  source_dir="$kit_root/$SKILL_NAME"
fi
source_dir=$(CDPATH= cd -- "$source_dir" && pwd)
project_root=$(CDPATH= cd -- "$project_root" && pwd)

if [ ! -f "$source_dir/SKILL.md" ]; then
  echo "Source skill not found: $source_dir" >&2
  exit 1
fi

copy_skill() {
  src="$1"
  parent="$2"
  dest="$parent/$SKILL_NAME"

  if [ -e "$dest" ]; then
    if [ "$force" -ne 1 ]; then
      echo "Destination exists: $dest. Re-run with --force to overwrite." >&2
      exit 1
    fi
    rm -rf "$dest"
  fi

  mkdir -p "$dest"
  (
    cd "$src"
    tar --exclude='./__pycache__' --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' --exclude='.DS_Store' -cf - .
  ) | (
    cd "$dest"
    tar -xf -
  )
  printf '%s\n' "$dest"
}

make_instruction_block() {
  script_path="$1"
  cat <<EOF
$MARKER_START
## Legacy Impact Audit

Before planning or implementing risky legacy Java changes, run a legacy impact audit.

Mandatory triggers:
- service methods, public APIs, shared utilities, job entry points, workflow logic
- DAO/query/persistence behavior, DTO/table/JSON contracts
- financial calculation, scoring, approval, reconciliation, workflow, or other core business logic

Gate rules:
- Run impact audit before finalizing the implementation plan.
- Run it again after code changes and before functional test case design or code review.
- Do not proceed if the audit returns \`REFINE_REQUIRED\`; narrow by owner class, package, module, or definition file first.
- Do not ask an LLM to analyze broad raw search results; use the generated audit report and packet.
- Test scope and regression scope must be derived from confirmed \`real_dependency\` and \`possible_dependency\` candidates.

Command pattern:

\`\`\`bash
python3 "$script_path" scan \\
  --root . \\
  --symbol METHOD_NAME \\
  --owner-class OWNER_CLASS \\
  --owner-package OWNER_PACKAGE \\
  --definition-file path/to/OwnerClass.java
\`\`\`
$MARKER_END
EOF
}

append_marked_block() {
  path="$1"
  script_path="$2"
  dir=$(dirname -- "$path")
  mkdir -p "$dir"
  block_file=$(mktemp)
  tmp_file=$(mktemp)
  make_instruction_block "$script_path" > "$block_file"
  [ -f "$path" ] || : > "$path"

  awk -v start="$MARKER_START" -v end="$MARKER_END" -v block="$block_file" '
    BEGIN {
      while ((getline line < block) > 0) {
        replacement = replacement line ORS
      }
      skipping = 0
      replaced = 0
    }
    index($0, start) {
      printf "%s", replacement
      skipping = 1
      replaced = 1
      next
    }
    skipping && index($0, end) {
      skipping = 0
      next
    }
    !skipping {
      print
    }
    END {
      if (!replaced) {
        if (NR > 0) {
          print ""
        }
        printf "%s", replacement
      }
    }
  ' "$path" > "$tmp_file"
  cat "$tmp_file" > "$path"
  rm -f "$block_file" "$tmp_file"
}

home_dir=${HOME:?HOME is not set}

user_parent() {
  agent="$1"
  case "$agent" in
    codex)
      if [ -n "${CODEX_HOME:-}" ]; then
        printf '%s\n' "$CODEX_HOME/skills"
      else
        printf '%s\n' "$home_dir/.codex/skills"
      fi
      ;;
    claude) printf '%s\n' "$home_dir/.claude/skills" ;;
    opencode) printf '%s\n' "$home_dir/.config/opencode/skills" ;;
    copilot) printf '%s\n' "$home_dir/.copilot/skills" ;;
    deepcode) printf '%s\n' "$home_dir/.agents/skills" ;;
    *) return 1 ;;
  esac
}

project_parent() {
  agent="$1"
  case "$agent" in
    claude) printf '%s\n' "$project_root/.claude/skills" ;;
    opencode) printf '%s\n' "$project_root/.opencode/skills" ;;
    copilot) printf '%s\n' "$project_root/.github/skills" ;;
    deepcode) printf '%s\n' "$project_root/.deepcode/skills" ;;
    *) return 1 ;;
  esac
}

install_agent() {
  agent="$1"

  if [ "$agent" = "codex" ] && [ -n "$skills_dir" ]; then
    installed=$(copy_skill "$source_dir" "$skills_dir")
    echo "Installed/updated: $installed"
    return
  fi

  if [ "$agent" = "gemini" ]; then
    if [ "$scope" = "user" ]; then
      installed=$(copy_skill "$source_dir" "$home_dir/.agents/skills")
      append_marked_block "$home_dir/.gemini/GEMINI.md" "$installed/scripts/impact_audit.py"
      echo "Installed/updated: $installed"
      echo "Installed/updated: $home_dir/.gemini/GEMINI.md"
    else
      installed=$(copy_skill "$source_dir" "$project_root/.ai/legacy-impact-audit/skills")
      append_marked_block "$project_root/GEMINI.md" "$installed/scripts/impact_audit.py"
      echo "Installed/updated: $installed"
      echo "Installed/updated: $project_root/GEMINI.md"
    fi
    return
  fi

  if [ "$scope" = "user" ]; then
    parent=$(user_parent "$agent") || {
      echo "User-scope install is not defined for $agent" >&2
      exit 1
    }
    installed=$(copy_skill "$source_dir" "$parent")
    echo "Installed/updated: $installed"
    return
  fi

  parent=$(project_parent "$agent") || {
    echo "Project-scope install is not defined for $agent" >&2
    exit 1
  }
  installed=$(copy_skill "$source_dir" "$parent")
  echo "Installed/updated: $installed"

  if [ "$agent" = "opencode" ]; then
    append_marked_block "$project_root/AGENTS.md" "$installed/scripts/impact_audit.py"
    echo "Installed/updated: $project_root/AGENTS.md"
  elif [ "$agent" = "copilot" ]; then
    append_marked_block "$project_root/.github/copilot-instructions.md" "$installed/scripts/impact_audit.py"
    echo "Installed/updated: $project_root/.github/copilot-instructions.md"
  fi
}

if [ "$agent_arg" = "all" ]; then
  agents="codex claude opencode gemini copilot deepcode"
else
  agents=$(printf '%s' "$agent_arg" | tr ',' ' ')
fi

for agent in $agents; do
  case "$agent" in
    codex|claude|opencode|gemini|copilot|deepcode)
      install_agent "$agent"
      ;;
    *)
      echo "Unknown agent: $agent" >&2
      exit 2
      ;;
  esac
done
