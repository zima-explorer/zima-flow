#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
zimaflow="$repo_root/bin/zimaflow"

export GIT_AUTHOR_NAME="Zimaflow Test"
export GIT_AUTHOR_EMAIL="zimaflow@example.com"
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

new_repo() {
  local name="$1"
  local dir="$tmpdir/$name"
  mkdir -p "$dir"
  git -C "$dir" init >/dev/null
  printf 'demo\n' > "$dir/README.md"
  git -C "$dir" add README.md
  git -C "$dir" commit -m "init" >/dev/null
  printf '%s\n' "$dir"
}

write_state() {
  local repo="$1"
  local change="$2"
  local phase="${3:-implementation}"
  local verify="${4:-not_run}"
  local tests="${5:-not_run}"
  local archive="${6:-not_archived}"
  local handover="${7:-}"
  local state_dir="$repo/openspec/changes/$change"
  mkdir -p "$state_dir"
  cat > "$state_dir/.zimaflow-state.yaml" <<YAML
schema_version: 1
change_id: "$change"
phase: "$phase"
mode: "full"

verification:
  opsx_verify: "$verify"
  full_tests: "$tests"

archive:
  status: "$archive"
  docs_synced: false

handover:
  latest_path: "$handover"
YAML
}

ready_repo="$(new_repo ready-empty)"
json="$(cd "$ready_repo" && "$zimaflow" release-check --json)"
printf '%s' "$json" | grep -q '"git_status":"clean"'
printf '%s' "$json" | grep -q '"active_count":0'
printf '%s' "$json" | grep -q '"verification_readiness":"no_active_change"'
printf '%s' "$json" | grep -q '"secrets_readiness":"clear"'
printf '%s' "$json" | grep -q '"next_action":"ready"'
[ "$(printf '%s' "$json" | grep -o '"requires_human_confirmation":true' | wc -l | tr -d ' ')" = "4" ]
human="$(cd "$ready_repo" && "$zimaflow" release-check)"
printf '%s' "$human" | grep -q 'never deploys'
printf '%s' "$human" | grep -q 'never reads release secrets'

verify_repo="$(new_repo verify-gap)"
write_state "$verify_repo" "add-demo" "implementation" "not_run" "not_run" "not_archived" ""
git -C "$verify_repo" add openspec
git -C "$verify_repo" commit -m "add state" >/dev/null
json="$(cd "$verify_repo" && "$zimaflow" release-check --json)"
printf '%s' "$json" | grep -q '"verification_readiness":"incomplete"'
printf '%s' "$json" | grep -q '"next_action":"need_verify"'

archive_repo="$(new_repo archive-gap)"
write_state "$archive_repo" "add-demo" "implementation" "passed" "passed" "not_archived" ""
git -C "$archive_repo" add openspec
git -C "$archive_repo" commit -m "add state" >/dev/null
json="$(cd "$archive_repo" && "$zimaflow" release-check --json)"
printf '%s' "$json" | grep -q '"archive_readiness":"unarchived_present"'
printf '%s' "$json" | grep -q '"next_action":"need_archive"'

handover_repo="$(new_repo handover-gap)"
write_state "$handover_repo" "add-demo" "implementation" "passed" "passed" "archived" "docs/Handover/missing.md"
git -C "$handover_repo" add openspec
git -C "$handover_repo" commit -m "add state" >/dev/null
json="$(cd "$handover_repo" && "$zimaflow" release-check --json)"
printf '%s' "$json" | grep -q '"handover_readiness":"missing"'
printf '%s' "$json" | grep -q '"next_action":"need_handover"'

secret_repo="$(new_repo secret-gap)"
mkdir -p "$secret_repo/config"
pfx="sk-abcdef"
sfx="1234567890"
printf 'api_key = "%s%s"\n' "$pfx" "$sfx" > "$secret_repo/config/local.conf"
git -C "$secret_repo" add config/local.conf
json="$(cd "$secret_repo" && "$zimaflow" release-check --json)"
printf '%s' "$json" | grep -q '"secrets_readiness":"suspected"'
printf '%s' "$json" | grep -q '"secrets_hits":\["config/local.conf:1"\]'
printf '%s' "$json" | grep -q '"next_action":"need_secret_review"'
if printf '%s' "$json" | grep -q "${pfx}${sfx}"; then
  echo "release-check JSON leaked a secret value" >&2
  exit 1
fi
human="$(cd "$secret_repo" && "$zimaflow" release-check)"
printf '%s' "$human" | grep -q 'config/local.conf:1'
if printf '%s' "$human" | grep -q "${pfx}${sfx}"; then
  echo "release-check human output leaked a secret value" >&2
  exit 1
fi

dirty_repo="$(new_repo dirty-tree)"
printf 'dirty\n' >> "$dirty_repo/README.md"
json="$(cd "$dirty_repo" && "$zimaflow" release-check --json)"
printf '%s' "$json" | grep -q '"git_status":"dirty"'
printf '%s' "$json" | grep -q '"next_action":"need_manual_confirmation"'

active_ready_repo="$(new_repo active-ready)"
mkdir -p "$active_ready_repo/docs/Handover"
printf 'handover\n' > "$active_ready_repo/docs/Handover/latest.md"
write_state "$active_ready_repo" "add-demo" "implementation" "passed" "passed" "archived" "docs/Handover/latest.md"
git -C "$active_ready_repo" add docs openspec
git -C "$active_ready_repo" commit -m "add ready state" >/dev/null
json="$(cd "$active_ready_repo" && "$zimaflow" release-check --json)"
printf '%s' "$json" | grep -q '"active_count":1'
printf '%s' "$json" | grep -q '"verification_readiness":"ready"'
printf '%s' "$json" | grep -q '"archive_readiness":"ready"'
printf '%s' "$json" | grep -q '"handover_readiness":"ready"'
printf '%s' "$json" | grep -q '"next_action":"ready"'

echo "release-check tests passed"
