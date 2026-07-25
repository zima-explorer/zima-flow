#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
zimaflow="$repo_root/bin/zimaflow"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

cd "$tmpdir"
git init >/dev/null

mkdir -p openspec/changes/add-login openspec/changes/old-thing

cat > openspec/changes/add-login/.zimaflow-state.yaml <<'YAML'
schema_version: 1
change_id: add-login
phase: build_started
mode: full
archive:
  status: not_archived
YAML

cat > openspec/changes/old-thing/.zimaflow-state.yaml <<'YAML'
schema_version: 1
change_id: old-thing
phase: closed
mode: full
archive:
  status: archived
YAML

json_output="$($zimaflow state --json)"
printf '%s' "$json_output" | grep -q '"active_count":1'
printf '%s' "$json_output" | grep -q '"change_id":"add-login"'
printf '%s' "$json_output" | grep -q '"phase":"build_started"'
printf '%s' "$json_output" | grep -q '"archive_status":"not_archived"'
printf '%s' "$json_output" | grep -q '"change_id":"old-thing"'

human_output="$($zimaflow state)"
printf '%s' "$human_output" | grep -q 'Zimaflow state'
printf '%s' "$human_output" | grep -q 'add-login'
printf '%s' "$human_output" | grep -q 'build_started'
printf '%s' "$human_output" | grep -q 'Active changes'

mkdir -p nested/openspec/changes/nested-change
cat > nested/openspec/changes/nested-change/.zimaflow-state.yaml <<'YAML'
schema_version: 1
change_id: nested-change
phase: spec_reviewed
mode: full
archive:
  status: not_archived
YAML

cd "$tmpdir/nested"
nested_json="$($zimaflow state --json)"
printf '%s' "$nested_json" | grep -q '"change_id":"nested-change"'
printf '%s' "$nested_json" | grep -q '"phase":"spec_reviewed"'

cd "$tmpdir"
mkdir -p docs
touch docs/Requirement.md docs/Decision.md docs/Handover.md

"$zimaflow" state init written-change \
  --phase contract_confirmed \
  --mode full \
  --contract "$tmpdir/docs/Requirement.md" \
  --decision "$tmpdir/docs/Decision.md" >/dev/null

test -f openspec/changes/written-change/.zimaflow-state.yaml
grep -q "^change_id: 'written-change'$" openspec/changes/written-change/.zimaflow-state.yaml
grep -q "^phase: 'contract_confirmed'$" openspec/changes/written-change/.zimaflow-state.yaml
grep -q "path: '$tmpdir/docs/Requirement.md'" openspec/changes/written-change/.zimaflow-state.yaml

"$zimaflow" state update written-change \
  --phase verified \
  --archive-status not_archived \
  --verify passed \
  --full-tests passed \
  --last-command "bash tests/state.sh" \
  --last-result passed \
  --evidence-path "$tmpdir/docs/verify.log" \
  --blocked-reason "" \
  --branch feat/written-change \
  --handover "$tmpdir/docs/Handover.md" >/dev/null

grep -q "^phase: 'verified'$" openspec/changes/written-change/.zimaflow-state.yaml
grep -q "^  branch: 'feat/written-change'$" openspec/changes/written-change/.zimaflow-state.yaml
grep -q "^  opsx_verify: 'passed'$" openspec/changes/written-change/.zimaflow-state.yaml
grep -q "^  full_tests: 'passed'$" openspec/changes/written-change/.zimaflow-state.yaml
grep -q "^  last_command: 'bash tests/state.sh'$" openspec/changes/written-change/.zimaflow-state.yaml
grep -q "^  last_result: 'passed'$" openspec/changes/written-change/.zimaflow-state.yaml
grep -q "  evidence_path: '$tmpdir/docs/verify.log'" openspec/changes/written-change/.zimaflow-state.yaml
grep -q "^  blocked_reason: ''$" openspec/changes/written-change/.zimaflow-state.yaml
grep -q "latest_path: '$tmpdir/docs/Handover.md'" openspec/changes/written-change/.zimaflow-state.yaml

"$zimaflow" state update written-change \
  --last-command "npm run test:unit # smoke" \
  --blocked-reason "waiting: reviewer approval" \
  --evidence-path "docs/reports/it's-ready.md" >/dev/null

grep -q "^  last_command: 'npm run test:unit # smoke'$" openspec/changes/written-change/.zimaflow-state.yaml
grep -q "^  blocked_reason: 'waiting: reviewer approval'$" openspec/changes/written-change/.zimaflow-state.yaml
grep -Fq "  evidence_path: 'docs/reports/it''s-ready.md'" openspec/changes/written-change/.zimaflow-state.yaml
edge_json="$($zimaflow recall --json --summary-lines 1)"
printf '%s' "$edge_json" | grep -q 'npm run test:unit # smoke'
"$zimaflow" state update written-change --last-result reviewed >/dev/null
grep -q "^  blocked_reason: 'waiting: reviewer approval'$" openspec/changes/written-change/.zimaflow-state.yaml
grep -Fq "  evidence_path: 'docs/reports/it''s-ready.md'" openspec/changes/written-change/.zimaflow-state.yaml

updated_json="$($zimaflow state --json)"
printf '%s' "$updated_json" | grep -q '"change_id":"written-change"'
printf '%s' "$updated_json" | grep -q '"phase":"verified"'

close_json="$($zimaflow close --json)"
printf '%s' "$close_json" | grep -q '"active_state_count":2'
printf '%s' "$close_json" | grep -q '"active_state_changes":'
printf '%s' "$close_json" | grep -q '"add-login"'
printf '%s' "$close_json" | grep -q '"written-change"'

echo "state tests passed"
