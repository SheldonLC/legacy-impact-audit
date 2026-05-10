#!/usr/bin/env bash
set -euo pipefail

# Local-only safety gate for private terms, paths, and project identifiers.
# The actual regex list should live outside tracked files, usually under
# .git/hooks, so publishing the kit does not publish private patterns.

mode="${1:-}"
shift || true

if [ -z "$mode" ]; then
  echo "Usage: sensitive-scan-gate.sh pre-commit|commit-msg|pre-push [args]" >&2
  exit 2
fi

repo_root="$(git rev-parse --show-toplevel)"
git_pattern_path="$(git rev-parse --git-path hooks/legacy-impact-audit-sensitive-patterns.txt)"
pattern_file="${LEGACY_IMPACT_AUDIT_SENSITIVE_PATTERNS:-$git_pattern_path}"
show_lines="${LEGACY_IMPACT_AUDIT_SHOW_SENSITIVE_LINES:-0}"

if [ ! -f "$pattern_file" ]; then
  echo "Sensitive scan pattern file missing: $pattern_file" >&2
  echo "Create it locally or set LEGACY_IMPACT_AUDIT_SENSITIVE_PATTERNS." >&2
  exit 1
fi

if ! grep -Ev '^[[:space:]]*(#|$)' "$pattern_file" >/dev/null; then
  echo "Sensitive scan pattern file contains no active patterns: $pattern_file" >&2
  exit 1
fi

tmp_dir="$(mktemp -d)"
active_patterns="$tmp_dir/patterns.txt"
grep -Ev '^[[:space:]]*(#|$)' "$pattern_file" > "$active_patterns"

violations=0
scan_counter=0

cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

report_match() {
  label="$1"
  line_no="$2"
  if [ "$show_lines" = "1" ]; then
    content="$3"
    printf '  %s:%s: %s\n' "$label" "$line_no" "$content" >&2
  else
    printf '  %s:%s\n' "$label" "$line_no" >&2
  fi
}

scan_text_file() {
  label="$1"
  file="$2"
  if matches="$(LC_ALL=C grep -I -n -i -E -f "$active_patterns" "$file" || true)" && [ -n "$matches" ]; then
    violations=1
    while IFS= read -r match_line; do
      line_no="${match_line%%:*}"
      content="${match_line#*:}"
      report_match "$label" "$line_no" "$content"
    done <<EOF
$matches
EOF
  fi
}

scan_label_value() {
  label="$1"
  value="$2"
  scan_counter="$((scan_counter + 1))"
  file="$tmp_dir/label-value-$scan_counter.txt"
  printf '%s\n' "$value" > "$file"
  scan_text_file "$label" "$file"
}

scan_staged_file() {
  path="$1"
  scan_label_value "path:$path" "$path"
  if git cat-file -e ":$path" 2>/dev/null; then
    scan_counter="$((scan_counter + 1))"
    file="$tmp_dir/staged-$scan_counter"
    git show ":$path" > "$file"
    scan_text_file "staged:$path" "$file"
  fi
}

scan_tree_file() {
  commit="$1"
  path="$2"
  scan_label_value "path:$path" "$path"
  if git cat-file -e "$commit:$path" 2>/dev/null; then
    scan_counter="$((scan_counter + 1))"
    file="$tmp_dir/tree-$scan_counter"
    git show "$commit:$path" > "$file"
    scan_text_file "$commit:$path" "$file"
  fi
}

scan_commit_messages() {
  range="$1"
  label="$2"
  scan_counter="$((scan_counter + 1))"
  file="$tmp_dir/commit-messages-$scan_counter"
  git log --format='%H %an <%ae>%n%B%n---END-COMMIT---' "$range" > "$file"
  scan_text_file "$label" "$file"
}

run_pre_commit() {
  cd "$repo_root"
  while IFS= read -r -d '' path; do
    scan_staged_file "$path"
  done < <(git diff --cached --name-only --diff-filter=ACMRT -z)
}

run_commit_msg() {
  msg_file="${1:-}"
  if [ -z "$msg_file" ] || [ ! -f "$msg_file" ]; then
    echo "commit-msg mode requires the commit message file path." >&2
    exit 2
  fi
  scan_text_file "commit-message" "$msg_file"
}

run_pre_push() {
  zero_oid="0000000000000000000000000000000000000000"
  cd "$repo_root"
  while read -r local_ref local_oid remote_ref remote_oid; do
    [ -n "${local_ref:-}" ] || continue
    if [ "$local_oid" = "$zero_oid" ]; then
      continue
    fi

    if [ "$remote_oid" = "$zero_oid" ]; then
      while IFS= read -r -d '' path; do
        scan_tree_file "$local_oid" "$path"
      done < <(git ls-tree -r -z --name-only "$local_oid")
      scan_commit_messages "$local_oid" "commits:$local_ref"
    else
      while IFS= read -r -d '' path; do
        scan_tree_file "$local_oid" "$path"
      done < <(git diff --name-only --diff-filter=ACMRT -z "$remote_oid..$local_oid")
      scan_commit_messages "$remote_oid..$local_oid" "commits:$local_ref"
    fi
  done
}

case "$mode" in
  pre-commit)
    run_pre_commit
    ;;
  commit-msg)
    run_commit_msg "$@"
    ;;
  pre-push)
    run_pre_push "$@"
    ;;
  *)
    echo "Unknown mode: $mode" >&2
    exit 2
    ;;
esac

if [ "$violations" -ne 0 ]; then
  echo "Sensitive scan blocked this Git operation." >&2
  echo "Matched file/line locations are listed above; line content is hidden by default." >&2
  echo "Set LEGACY_IMPACT_AUDIT_SHOW_SENSITIVE_LINES=1 locally if you need exact matched lines." >&2
  exit 1
fi
