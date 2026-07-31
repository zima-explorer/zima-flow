#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
zimaflow="$repo_root/bin/zimaflow"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

mkdir -p "$tmpdir/docs/.zimaflow" "$tmpdir/docs/Designs" "$tmpdir/repo/openspec/changes/demo"
touch "$tmpdir/docs/Designs/Architecture-Overview.md"
touch "$tmpdir/docs/Designs/Module-Map.md"
touch "$tmpdir/docs/Designs/Test-Entry-Points.md"
touch "$tmpdir/docs/handover.md"
touch "$tmpdir/repo/openspec/changes/demo/.zimaflow-state.yaml"

cat > "$tmpdir/docs/.zimaflow/context-index.yaml" <<YAML
schema_version: 1
project:
  name: demo
  code_path: $tmpdir/repo
  docs_path: $tmpdir/docs
baseline:
  architecture_overview: Designs/Architecture-Overview.md
  module_map: Designs/Module-Map.md
  interface_inventory: Designs/Missing-Interface.md
  data_model_er: ""
  test_entry_points: Designs/Test-Entry-Points.md
workflow:
  latest_handover: handover.md
  latest_state: ../repo/openspec/changes/demo/.zimaflow-state.yaml
updated_at: "2026-07-31T12:00:00+0800"
YAML

json="$(cd "$tmpdir/docs" && "$zimaflow" context-check --json)"
printf '%s' "$json" | grep -q '"context_index_status":"present"'
printf '%s' "$json" | grep -q '"checked_count":6'
printf '%s' "$json" | grep -q '"missing_count":1'
printf '%s' "$json" | grep -q '"next_action":"refresh_baseline"'
printf '%s' "$json" | grep -q '"key":"interface_inventory"'
printf '%s' "$json" | grep -q '"status":"missing"'

human="$(cd "$tmpdir/docs/Designs" && "$zimaflow" context-check)"
printf '%s' "$human" | grep -q 'Context check'
printf '%s' "$human" | grep -q 'Missing references: 1'
printf '%s' "$human" | grep -q 'refresh baseline'
printf '%s' "$human" | grep -q 'read-only'
printf '%s' "$human" | grep -q 'never creates context-index'

mkdir -p "$tmpdir/clean/.zimaflow" "$tmpdir/clean/Designs"
touch "$tmpdir/clean/Designs/Architecture-Overview.md"
cat > "$tmpdir/clean/.zimaflow/context-index.yaml" <<'YAML'
schema_version: 1
baseline:
  architecture_overview: Designs/Architecture-Overview.md
workflow:
  latest_handover: ""
  latest_state: ""
YAML

clean_json="$(cd "$tmpdir/clean" && "$zimaflow" context-check --json)"
printf '%s' "$clean_json" | grep -q '"missing_count":0'
printf '%s' "$clean_json" | grep -q '"next_action":"ok"'

missing_json="$(cd "$tmpdir" && "$zimaflow" context-check --json)"
printf '%s' "$missing_json" | grep -q '"context_index_status":"missing"'
printf '%s' "$missing_json" | grep -q '"next_action":"create_context_index"'

echo "context-check tests passed"
