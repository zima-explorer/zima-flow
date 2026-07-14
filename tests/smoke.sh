#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp_root="${TMPDIR:-/tmp}/zimaflow-install-test"
target_dir="$tmp_root/target"
bin_dir="$tmp_root/bin"
non_git_dir="$tmp_root/non-git"

rm -rf "$tmp_root"
mkdir -p "$target_dir" "$bin_dir" "$non_git_dir"

"$repo_root/scripts/install.sh" --help >/dev/null
"$repo_root/scripts/install.sh" --target "$target_dir" --bin-dir "$bin_dir" --force

test -f "$target_dir/skills/sdd-router.md"
test -f "$target_dir/rules/codex/zimaflow-session-close-gate.md"
test -f "$target_dir/references/workload-dict.md"
test -x "$bin_dir/zimaflow"

"$repo_root/bin/zimaflow" --version | grep -q '^zimaflow '

json_output="$(cd "$non_git_dir" && "$repo_root/bin/zimaflow" close --json || true)"
printf '%s\n' "$json_output" | grep -q '"git_status":"not_git_repo"'
printf '%s\n' "$json_output" | grep -q '"next_action":"need_manual_confirmation"'

echo "smoke tests passed"
