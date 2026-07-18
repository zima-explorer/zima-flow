#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp_root="${TMPDIR:-/tmp}/zimaflow-install-test"
target_dir="$tmp_root/target"
bin_dir="$tmp_root/bin"
non_git_dir="$tmp_root/non-git"
shared_skill_root="$tmp_root/shared-skills"
claude_skill_root="$tmp_root/claude-skills"
second_adapter_root="$tmp_root/second-adapter"

rm -rf "$tmp_root"
mkdir -p "$target_dir" "$bin_dir" "$non_git_dir"

help_output="$("$repo_root/scripts/install.sh" --help)"
printf '%s\n' "$help_output" | grep -q -- '--adapter-dir <dir>'
if printf '%s\n' "$help_output" | grep -q -- '--codex'; then
  echo "--codex should not be advertised" >&2
  exit 1
fi
"$repo_root/scripts/install.sh" --target "$target_dir" --bin-dir "$bin_dir" --force

test -f "$target_dir/skills/sdd-router.md"
test -f "$target_dir/rules/codex/zimaflow-session-close-gate.md"
test -f "$target_dir/references/workload-dict.md"
test -x "$bin_dir/zimaflow"

"$repo_root/scripts/install.sh" --target "$target_dir" --claude-code --force
test -f "$target_dir/.claude/skills/zimaflow-sdd-router/SKILL.md"
grep -q '^name: zimaflow-sdd-router$' "$target_dir/.claude/skills/zimaflow-sdd-router/SKILL.md"

"$repo_root/scripts/install.sh" \
  --target "$target_dir" \
  --adapter-dir "$shared_skill_root" \
  --adapter-dir "$claude_skill_root" \
  --adapter-dir "$second_adapter_root" \
  --force
test -f "$shared_skill_root/zimaflow-sdd-router/SKILL.md"
test -f "$claude_skill_root/zimaflow-sdd-router/SKILL.md"
test -f "$second_adapter_root/zimaflow-sdd-router/SKILL.md"
grep -q '^name: zimaflow-sdd-router$' "$shared_skill_root/zimaflow-sdd-router/SKILL.md"
grep -q '^name: zimaflow-sdd-router$' "$claude_skill_root/zimaflow-sdd-router/SKILL.md"
grep -q '^name: zimaflow-sdd-router$' "$second_adapter_root/zimaflow-sdd-router/SKILL.md"

if "$repo_root/scripts/install.sh" --target "$target_dir" --codex --force >/dev/null 2>&1; then
  echo "--codex should be rejected" >&2
  exit 1
fi

"$repo_root/bin/zimaflow" --version | grep -q '^zimaflow '

json_output="$(cd "$non_git_dir" && "$repo_root/bin/zimaflow" close --json || true)"
printf '%s\n' "$json_output" | grep -q '"git_status":"not_git_repo"'
printf '%s\n' "$json_output" | grep -q '"next_action":"need_manual_confirmation"'

echo "smoke tests passed"
