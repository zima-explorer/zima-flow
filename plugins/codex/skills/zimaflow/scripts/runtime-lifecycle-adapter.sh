#!/usr/bin/env bash
set -euo pipefail

# Thin host adapter: package a candidate and discover its manifest. Lifecycle
# state, ownership and destructive operations intentionally live in the core.

RUNTIME_ADAPTER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIMAFLOW_DIR="$(cd "$RUNTIME_ADAPTER_DIR/.." && pwd)"

runtime_adapter_stage() {
  local host="$1" staging="$2" package_parent="$staging/package-output" generated=""
  mkdir -p "$package_parent"
  case "$host" in
    codex)
      "$ZIMAFLOW_DIR/scripts/package-codex-plugin.sh" --output "$package_parent" >&2
      generated="$package_parent/zimaflow"
      ;;
    workbuddy)
      "$ZIMAFLOW_DIR/scripts/package-workbuddy-adapter.sh" --skills-root "$ZIMAFLOW_DIR" --output "$package_parent" >&2
      generated="$package_parent/zimaflow-workbuddy"
      ;;
    claude-code)
      "$ZIMAFLOW_DIR/scripts/package-claude-code-adapter.sh" --mode plugin --skills-root "$ZIMAFLOW_DIR" --output "$package_parent" >&2
      generated="$package_parent/zimaflow-claude-code-plugin"
      ;;
    *) echo "Unsupported runtime host: $host" >&2; return 2 ;;
  esac
  [ -d "$generated" ] || { echo "Adapter did not generate runtime: $generated" >&2; return 1; }
  mv "$generated" "$staging/runtime"
}

runtime_adapter_manifest() {
  local runtime_path="$1"
  printf '%s/runtime-manifest.yaml' "$runtime_path"
}

runtime_adapter_validate() {
  local host="$1" runtime_path="$2" manifest
  manifest="$(runtime_adapter_manifest "$runtime_path")"
  [ "${ZIMAFLOW_RUNTIME_FAIL_VALIDATOR:-0}" != "1" ] || { echo "Injected runtime validator failure" >&2; return 1; }
  [ -f "$manifest" ] || { echo "Runtime manifest missing: $manifest" >&2; return 1; }
  grep -q "^host_id: $host$" "$manifest" || { echo "Runtime manifest host mismatch" >&2; return 1; }
  case "$host" in
    codex) test -f "$runtime_path/.codex-plugin/plugin.json" ;;
    workbuddy) test -f "$runtime_path/runtime-manifest.yaml" ;;
    claude-code) test -f "$runtime_path/.claude-plugin/plugin.json" ;;
  esac || { echo "Runtime validator rejected adapter layout for $host" >&2; return 1; }
}
