#!/usr/bin/env bash
set -euo pipefail

RUNTIME_CORE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIMAFLOW_DIR="$(cd "$RUNTIME_CORE_DIR/../.." && pwd)"
source "$ZIMAFLOW_DIR/scripts/lib/packaging-common.sh"
source "$ZIMAFLOW_DIR/scripts/runtime-lifecycle-adapter.sh"

runtime_json_escape() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }
runtime_json() { printf '"%s"' "$(runtime_json_escape "$1")"; }
runtime_yaml_value() { awk -F': ' -v key="$2" '$1 == key {sub(/^[^:]*: /, ""); print; exit}' "$1"; }
runtime_target() { printf '%s/runtimes/%s' "$1" "$2"; }
runtime_receipt() { printf '%s/.zimaflow-runtime-receipt.yaml' "$1"; }
runtime_log() { printf '%s/.zimaflow-runtime-transactions/%s.yaml' "$1" "$2"; }

runtime_safe_root() {
  local root="$1" home_root
  [ -n "$root" ] && [ -d "$root" ] || { echo "Install root must be an existing directory" >&2; return 2; }
  root="$(cd "$root" && pwd -P)"
  [ -n "${HOME:-}" ] && [ -d "$HOME" ] || { echo "HOME must be an existing directory" >&2; return 2; }
  home_root="$(cd "$HOME" && pwd -P)"
  case "$root" in
    /|"$home_root"|"$home_root"/*|*/.codex|*/.codex/*|*/.workbuddy|*/.workbuddy/*|*/.claude|*/.claude/*)
      echo "Unsafe install root: $root" >&2; return 2 ;;
  esac
  printf '%s' "$root"
}

runtime_assert_layout_safe() {
  local root="$1" host="$2" path
  for path in "$root/runtimes" "$root/runtimes/$host" "$root/.zimaflow-runtime-staging" "$root/.zimaflow-runtime-backups" "$root/.zimaflow-runtime-transactions" "$root/.zimaflow-runtime-doctor-project"; do
    [ ! -L "$path" ] || { echo "Unsafe runtime lifecycle symlink: $path" >&2; return 2; }
  done
}

runtime_detect_state() {
  local root="$1" host="$2" target receipt manifest fingerprint profile
  target="$(runtime_target "$root" "$host")"
  [ -e "$target" ] || { printf absent; return; }
  [ -d "$target" ] || { printf unmanaged; return; }
  receipt="$(runtime_receipt "$target")"; manifest="$(runtime_adapter_manifest "$target")"
  [ -f "$receipt" ] || { [ -f "$manifest" ] && printf corrupt || printf unmanaged; return; }
  [ "$(runtime_yaml_value "$receipt" ownership)" = "zimaflow-runtime" ] || { printf corrupt; return; }
  [ "$(runtime_yaml_value "$receipt" schema_version)" = "1" ] || { printf corrupt; return; }
  [ "$(runtime_yaml_value "$receipt" host_id)" = "$host" ] || { printf corrupt; return; }
  [ -f "$manifest" ] || { printf corrupt; return; }
  profile="$(packaging_sha256_file "$ZIMAFLOW_DIR/references/host-capabilities.yaml")"
  fingerprint="$(runtime_yaml_value "$manifest" source_fingerprint)"
  [ "$(runtime_yaml_value "$receipt" fingerprint)" = "$fingerprint" ] || { printf corrupt; return; }
  [ "$fingerprint" = "$profile" ] || { printf drift; return; }
  printf healthy
}

runtime_write_log() {
  local root="$1" host="$2" phase="$3" previous="$4" result="$5" rollback="$6" resume="$7" log
  log="$(runtime_log "$root" "$host")"; mkdir -p "$(dirname "$log")"
  printf 'schema_version: 1\nhost_id: %s\ntransaction_phase: %s\nprevious_state: %s\nresult: %s\nrollback_outcome: %s\nresume_intent: %s\n' "$host" "$phase" "$previous" "$result" "$rollback" "$resume" > "$log"
}

runtime_write_receipt() {
  local target="$1" host="$2" root="$3" desired="$4" previous="$5" manifest fingerprint
  manifest="$(runtime_adapter_manifest "$target")"
  fingerprint="$(runtime_yaml_value "$manifest" source_fingerprint)"
  printf 'schema_version: 1\nownership: zimaflow-runtime\nhost_id: %s\ninstall_root: %s\ndesired_version: %s\nruntime_version: %s\nfingerprint: %s\nruntime_manifest: runtime-manifest.yaml\ntransaction_phase: committed\nprevious_state: %s\nresult: healthy\n' "$host" "$root" "$desired" "$desired" "$fingerprint" "$previous" > "$(runtime_receipt "$target")"
}

runtime_doctor_validate() {
  local host="$1" root="$2" runtime_path="$3" project="$root/.zimaflow-runtime-doctor-project"
  mkdir -p "$project/openspec" "$project/.zimaflow"
  [ -d "$project/.git" ] || git -C "$project" init -q
  printf 'schema: specification\n' > "$project/openspec/config.yaml"
  printf 'schema_version: 1\nname: runtime-doctor-project\ndocs_root: docs/zimaflow\n' > "$project/.zimaflow/project.yaml"
  ZIMAFLOW_HOME="$ZIMAFLOW_DIR" "$ZIMAFLOW_DIR/bin/zimaflow" doctor "$host" --json --project "$project" --runtime-manifest "$(runtime_adapter_manifest "$runtime_path")" | grep -q '"overall_status":"ready"'
}

runtime_version_is_downgrade() {
  awk -v current="$1" -v wanted="$2" 'BEGIN { split(current,a,"."); split(wanted,b,"."); for (i=1;i<=3;i++) { x=a[i]+0; y=b[i]+0; if (y<x) exit 0; if (y>x) exit 1 } exit 1 }'
}

runtime_print_result() {
  local operation="$1" host="$2" root="$3" desired="$4" previous="$5" state="$6" result="$7" remediation="$8" resume="$9" rollback="${10}" path="${11}" fingerprint=""
  [ -f "$path/runtime-manifest.yaml" ] && fingerprint="$(runtime_yaml_value "$path/runtime-manifest.yaml" source_fingerprint)"
  printf '{"schema_version":1,"operation":'; runtime_json "$operation"
  printf ',"host_id":'; runtime_json "$host"
  printf ',"install_root":'; runtime_json "$root"
  printf ',"desired_version":'; runtime_json "$desired"
  printf ',"runtime_version":'; runtime_json "$desired"
  printf ',"fingerprint":'; runtime_json "$fingerprint"
  printf ',"ownership":"zimaflow-runtime","transaction_phase":'; runtime_json "$state"
  printf ',"previous_state":'; runtime_json "$previous"
  printf ',"lifecycle_state":'; runtime_json "$state"
  printf ',"result":'; runtime_json "$result"
  printf ',"remediation":'; runtime_json "$remediation"
  printf ',"resume_intent":'; runtime_json "$resume"
  printf ',"rollback_outcome":'; runtime_json "$rollback"
  printf ',"runtime_path":'; runtime_json "$path"; printf '}\n'
}

runtime_replace() {
  local host="$1" root="$2" desired="$3" previous="$4" target staging backup resume rollback
  target="$(runtime_target "$root" "$host")"; staging="$root/.zimaflow-runtime-staging/$host-$$"; backup="$root/.zimaflow-runtime-backups/$host-$$"; resume="zimaflow runtime repair $host --install-root $root"
  rm -rf -- "$staging" "$backup"; mkdir -p "$staging"
  runtime_write_log "$root" "$host" staging "$previous" pending not_needed "$resume"
  if ! runtime_adapter_stage "$host" "$staging"; then
    runtime_write_log "$root" "$host" failed "$previous" failed not_needed "$resume"; rm -rf -- "$staging"; return 1
  fi
  runtime_write_receipt "$staging/runtime" "$host" "$root" "$desired" "$previous"
  if [ -e "$target" ]; then mkdir -p "$(dirname "$backup")"; mv "$target" "$backup"; fi
  mkdir -p "$(dirname "$target")"; mv "$staging/runtime" "$target"
  if runtime_adapter_validate "$host" "$target" && runtime_doctor_validate "$host" "$root" "$target"; then
    rm -rf -- "$backup" "$staging"; runtime_write_log "$root" "$host" committed "$previous" healthy not_needed "$resume"; return 0
  fi
  rm -rf -- "$target"
  if [ -e "$backup" ]; then mv "$backup" "$target"; rollback=rolled_back; else rollback=not_needed; fi
  rm -rf -- "$staging"; runtime_write_log "$root" "$host" failed "$previous" failed "$rollback" "$resume"; return 1
}

runtime_main() {
  local operation="${1:-}" host="${2:-}" root="" desired="${ZIMAFLOW_RUNTIME_VERSION:-1.20.0}"
  shift 2 || true
  case "$operation" in install|upgrade|repair|remove) ;; *) echo "Invalid runtime operation: $operation" >&2; return 2 ;; esac
  case "$host" in codex|workbuddy|claude-code) ;; *) echo "Invalid runtime host: $host" >&2; return 2 ;; esac
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --install-root) [ "$#" -ge 2 ] || { echo 'Missing --install-root value' >&2; return 2; }; root="$2"; shift 2 ;;
      --desired-version) [ "$#" -ge 2 ] || { echo 'Missing --desired-version value' >&2; return 2; }; desired="$2"; shift 2 ;;
      --json) shift ;;
      *) echo "Unknown runtime option: $1" >&2; return 2 ;;
    esac
  done
  root="$(runtime_safe_root "$root")" || return $?
  runtime_assert_layout_safe "$root" "$host" || return $?
  local target previous existing
  target="$(runtime_target "$root" "$host")"; previous="$(runtime_detect_state "$root" "$host")"
  case "$operation:$previous" in
    install:absent)
      runtime_replace "$host" "$root" "$desired" "$previous" || { runtime_print_result "$operation" "$host" "$root" "$desired" "$previous" failed failed repair_required "zimaflow runtime repair $host --install-root $root" rolled_back "$target"; return 1; }
      runtime_print_result "$operation" "$host" "$root" "$desired" "$previous" healthy installed none '' not_needed "$target" ;;
    install:healthy) runtime_print_result "$operation" "$host" "$root" "$desired" "$previous" healthy already_healthy none '' not_needed "$target" ;;
    install:*) echo "Refusing install over $previous runtime; run repair only for managed drift/corruption" >&2; return 1 ;;
    upgrade:healthy)
      existing="$(runtime_yaml_value "$(runtime_receipt "$target")" desired_version)"
      if runtime_version_is_downgrade "$existing" "$desired"; then echo "Downgrade is not supported" >&2; return 2; fi
      if [ "$existing" = "$desired" ]; then runtime_print_result "$operation" "$host" "$root" "$desired" "$previous" healthy already_healthy none '' not_needed "$target"; return; fi
      runtime_replace "$host" "$root" "$desired" "$previous" || { runtime_print_result "$operation" "$host" "$root" "$desired" "$previous" failed failed repair_required "zimaflow runtime repair $host --install-root $root" rolled_back "$target"; return 1; }
      runtime_print_result "$operation" "$host" "$root" "$desired" "$previous" healthy upgraded none '' not_needed "$target" ;;
    upgrade:*) echo "Upgrade requires a healthy managed runtime" >&2; return 1 ;;
    repair:healthy) runtime_print_result "$operation" "$host" "$root" "$desired" "$previous" healthy already_healthy none '' not_needed "$target" ;;
    repair:unmanaged) echo "Refusing repair of unmanaged runtime" >&2; return 1 ;;
    repair:*)
      runtime_replace "$host" "$root" "$desired" "$previous" || { runtime_print_result "$operation" "$host" "$root" "$desired" "$previous" failed failed repair_required "zimaflow runtime repair $host --install-root $root" rolled_back "$target"; return 1; }
      runtime_print_result "$operation" "$host" "$root" "$desired" "$previous" healthy repaired none '' not_needed "$target" ;;
    remove:absent) runtime_print_result "$operation" "$host" "$root" "$desired" "$previous" absent already_absent none '' not_needed "$target" ;;
    remove:unmanaged) echo "Refusing remove of unmanaged runtime" >&2; return 1 ;;
    remove:*)
      [ "$(runtime_yaml_value "$(runtime_receipt "$target")" ownership)" = "zimaflow-runtime" ] || { echo "Refusing remove without Zimaflow ownership receipt" >&2; return 1; }
      rm -rf -- "$target"; runtime_write_log "$root" "$host" removed "$previous" removed not_needed ''
      runtime_print_result "$operation" "$host" "$root" "$desired" "$previous" absent removed none '' not_needed "$target" ;;
  esac
}
