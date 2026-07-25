#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
zimaflow="$repo_root/bin/zimaflow"

old_iso() {
  date -d '40 days ago' '+%Y-%m-%dT%H:%M:%S%z' 2>/dev/null \
    || date -v-40d '+%Y-%m-%dT%H:%M:%S%z'
}

now_iso() {
  date '+%Y-%m-%dT%H:%M:%S%z'
}

days_ago_iso() {
  date -d "$1 days ago" '+%Y-%m-%dT%H:%M:%S%z' 2>/dev/null \
    || date -v-"$1"d '+%Y-%m-%dT%H:%M:%S%z'
}

tmpA="$(mktemp -d)"
tmpB=""
tmpC=""
tmpD=""
tmpE=""
trap 'rm -rf "$tmpA" "$tmpB" "$tmpC" "$tmpD" "$tmpE"' EXIT

cd "$tmpA"
git init >/dev/null
mkdir -p openspec/changes/done
cat > openspec/changes/done/.zimaflow-state.yaml <<'YAML'
schema_version: 1
change_id: done
phase: closed
mode: full
archive:
  status: archived
YAML

jsonA="$($zimaflow recall --json)"
printf '%s' "$jsonA" | grep -q '"active_count":0'
printf '%s' "$jsonA" | grep -q '"next_action":"no_active_change"'
humanA="$($zimaflow recall)"
printf '%s' "$humanA" | grep -q 'no active change'

tmpB="$(mktemp -d)"
cd "$tmpB"
git init >/dev/null
mkdir -p openspec/changes/fresh-change
cat > openspec/changes/fresh-change/.zimaflow-state.yaml <<YAML
schema_version: 1
change_id: fresh-change
phase: build_completed
mode: full
verification:
  opsx_verify: passed
  full_tests: passed
  verified_at: "$(now_iso)"
archive:
  status: not_archived
handover:
  latest_path: ""
  updated_at: "$(now_iso)"
YAML

jsonB="$($zimaflow recall --json)"
printf '%s' "$jsonB" | grep -q '"active_count":1'
printf '%s' "$jsonB" | grep -q '"change_id":"fresh-change"'
printf '%s' "$jsonB" | grep -q '"phase":"build_completed"'
printf '%s' "$jsonB" | grep -q '"status":"fresh"'
printf '%s' "$jsonB" | grep -q '"next_action":"continue"'

humanB="$($zimaflow recall)"
printf '%s' "$humanB" | grep -q 'fresh-change'
printf '%s' "$humanB" | grep -q 'phase=build_completed'
printf '%s' "$humanB" | grep -q 'Next action: continue'

tmpC="$(mktemp -d)"
cd "$tmpC"
git init >/dev/null
mkdir -p openspec/changes/stale-verify
cat > openspec/changes/stale-verify/.zimaflow-state.yaml <<YAML
schema_version: 1
change_id: stale-verify
phase: verified
mode: full
verification:
  opsx_verify: passed
  full_tests: passed
  verified_at: "$(old_iso)"
archive:
  status: not_archived
handover:
  latest_path: ""
  updated_at: ""
YAML

jsonC="$($zimaflow recall --json)"
printf '%s' "$jsonC" | grep -q '"status":"stale"'
printf '%s' "$jsonC" | grep -q '"reason":"verified_at"'
printf '%s' "$jsonC" | grep -q '"stale_count":1'
printf '%s' "$jsonC" | grep -q '"next_action":"run_tests"'
humanC="$($zimaflow recall)"
printf '%s' "$humanC" | grep -q 'stale'

tmpD="$(mktemp -d)"
cd "$tmpD"
git init >/dev/null
mkdir -p openspec/changes/sum-change docs
cat > docs/handover.md <<'MD'
# sum-change

## 遗留与下一步

- [ ] 补充 refresh token 单测
- [ ] 前端错误提示文案待确认

## Guardrail 承接

- release readiness：release-check next_action=need_verify
- secrets 处理状态：命中 src/config.ts:12，待 revoke/rotate
- API_KEY = "sk-abcdef1234567890zzz"
MD
cat > openspec/changes/sum-change/.zimaflow-state.yaml <<YAML
schema_version: 1
change_id: sum-change
phase: build_started
mode: full
verification:
  verified_at: "$(now_iso)"
handover:
  latest_path: "docs/handover.md"
  updated_at: "$(now_iso)"
archive:
  status: not_archived
YAML

jsonD="$($zimaflow recall --json)"
printf '%s' "$jsonD" | grep -q '"handover_summary":\['
printf '%s' "$jsonD" | grep -q '补充 refresh token 单测'
printf '%s' "$jsonD" | grep -q 'release-check next_action=need_verify'
if printf '%s' "$jsonD" | grep -q 'sk-abcdef1234567890'; then
  echo "FAIL: secret value leaked into summary" >&2
  exit 1
fi
printf '%s' "$jsonD" | grep -q 'redacted secret-like line'
"$zimaflow" recall --summary-lines 2 --json \
  | python3 -c 'import json,sys; assert len(json.load(sys.stdin)["changes"][0]["handover_summary"]) == 2'

tmpE="$(mktemp -d)"
cd "$tmpE"
git init >/dev/null
mkdir -p openspec/changes/param-change
cat > openspec/changes/param-change/.zimaflow-state.yaml <<YAML
schema_version: 1
change_id: param-change
phase: build_started
mode: full
verification:
  verified_at: "$(days_ago_iso 20)"
archive:
  status: not_archived
YAML

jsonE_default="$($zimaflow recall --json)"
printf '%s' "$jsonE_default" | grep -q '"threshold_days":30'
printf '%s' "$jsonE_default" | grep -q '"status":"fresh"'

jsonE_14="$($zimaflow recall --days 14 --json)"
printf '%s' "$jsonE_14" | grep -q '"threshold_days":14'
printf '%s' "$jsonE_14" | grep -q '"status":"stale"'

for bad in "--days 0" "--summary-lines 0" "--days abc" "--days" "--summary-lines" "--bogus" "--all" "--project demo"; do
  read -r -a bad_args <<< "$bad"
  if "$zimaflow" recall "${bad_args[@]}" >/dev/null 2>&1; then
    echo "FAIL: 'recall $bad' should have failed" >&2
    exit 1
  fi
done

echo "recall tests passed"
