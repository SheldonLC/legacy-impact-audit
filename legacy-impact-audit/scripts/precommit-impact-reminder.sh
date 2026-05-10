#!/usr/bin/env bash
set -euo pipefail

# Lightweight safety hook. It does not infer Java methods or call an LLM.
# Prefer the Python validator when installed; keep a shell fallback so copied
# hooks still fail safely.

skill_home="${LEGACY_IMPACT_AUDIT_HOME:-${CODEX_HOME:-$HOME/.codex}/skills/legacy-impact-audit}"
validator="$skill_home/scripts/validate_impact_audit.py"
if [ -f "$validator" ]; then
  python3 "$validator" \
    --root . \
    --mode staged \
    --max-age-minutes "${LEGACY_IMPACT_AUDIT_MAX_REPORT_AGE_MINUTES:-240}"
  exit $?
fi

changed_source="$(git diff --cached --name-only -- '*.java' '*.xml' '*.properties' '*.sql' | head -n 1 || true)"
if [ -z "$changed_source" ]; then
  exit 0
fi

report=".ai/legacy-impact-audit/impact-report.md"
if [ ! -f "$report" ]; then
  echo "Impact report missing. Run legacy-impact-audit before committing risky Java changes." >&2
  exit 1
fi

now="$(date +%s)"
mtime="$(stat -c %Y "$report")"
age_minutes="$(( (now - mtime) / 60 ))"
if [ "$age_minutes" -gt "${LEGACY_IMPACT_AUDIT_MAX_REPORT_AGE_MINUTES:-240}" ]; then
  echo "Impact report is older than ${LEGACY_IMPACT_AUDIT_MAX_REPORT_AGE_MINUTES:-240} minutes. Re-run legacy-impact-audit if scope changed." >&2
  exit 1
fi
