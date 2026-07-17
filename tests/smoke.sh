#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp_root="${TMPDIR:-/tmp}/zimaflow-install-test"
target_dir="$tmp_root/target"
bin_dir="$tmp_root/bin"
non_git_dir="$tmp_root/non-git"
shared_skill_root="$tmp_root/shared-skills"
claude_skill_root="$tmp_root/claude-skills"
codex_skill_root="$tmp_root/codex-skills"
workbuddy_skill_root="$tmp_root/workbuddy-skills"

rm -rf "$tmp_root"
mkdir -p "$target_dir" "$bin_dir" "$non_git_dir"

"$repo_root/scripts/install.sh" --help >/dev/null
"$repo_root/scripts/install.sh" --target "$target_dir" --bin-dir "$bin_dir" --force

test -f "$target_dir/skills/sdd-router.md"
test -f "$target_dir/rules/codex/zimaflow-session-close-gate.md"
test -f "$target_dir/references/workload-dict.md"
test -x "$bin_dir/zimaflow"

"$repo_root/scripts/install.sh" --target "$target_dir" --claude-code --codex --force
test -f "$target_dir/.claude/skills/zimaflow-sdd-router/SKILL.md"
test -f "$target_dir/.agents/skills/zimaflow-sdd-router/SKILL.md"
grep -q '^name: zimaflow-sdd-router$' "$target_dir/.claude/skills/zimaflow-sdd-router/SKILL.md"
grep -q '^name: zimaflow-sdd-router$' "$target_dir/.agents/skills/zimaflow-sdd-router/SKILL.md"

"$repo_root/scripts/install.sh" \
  --target "$target_dir" \
  --agent-skill-root "$shared_skill_root" \
  --claude-skill-root "$claude_skill_root" \
  --codex-skill-root "$codex_skill_root" \
  --workbuddy-skill-root "$workbuddy_skill_root" \
  --force
test -f "$shared_skill_root/zimaflow-sdd-router/SKILL.md"
test -f "$claude_skill_root/zimaflow-sdd-router/SKILL.md"
test -f "$codex_skill_root/zimaflow-sdd-router/SKILL.md"
test -f "$workbuddy_skill_root/zimaflow-sdd-router/SKILL.md"
grep -q '^name: zimaflow-sdd-router$' "$shared_skill_root/zimaflow-sdd-router/SKILL.md"
grep -q '^name: zimaflow-sdd-router$' "$claude_skill_root/zimaflow-sdd-router/SKILL.md"
grep -q '^name: zimaflow-sdd-router$' "$codex_skill_root/zimaflow-sdd-router/SKILL.md"
grep -q '^name: zimaflow-sdd-router$' "$workbuddy_skill_root/zimaflow-sdd-router/SKILL.md"

"$repo_root/bin/zimaflow" --version | grep -q '^zimaflow '

json_output="$(cd "$non_git_dir" && "$repo_root/bin/zimaflow" close --json || true)"
printf '%s\n' "$json_output" | grep -q '"git_status":"not_git_repo"'
printf '%s\n' "$json_output" | grep -q '"next_action":"need_manual_confirmation"'

echo "smoke tests passed"
