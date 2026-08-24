#!/usr/bin/env bash
set -euo pipefail

# Standalone verifier for an immutable Zimaflow plugin release bundle.
#
# It is intentionally self-contained: it sources nothing, invokes no packager or
# builder, and reads nothing outside the root it is given. That is what makes it
# safe to ship in a public distribution repository, where a builder must never
# exist.
#
# THREAT MODEL - read this before quoting the hashes as a guarantee.
#
#   What this detects: drift between a snapshot and the manifest recorded when
#   that snapshot was built. Accidental edits, partial copies, lost file modes,
#   truncated transfers, an injected symlink, a stale promotion, a hand-patched
#   runtime - all of these change a tree hash, a mode, or the payload hash and
#   are reported.
#
#   What this does NOT establish: authenticity. `release-manifest.yaml` is
#   excluded from `payload_sha256` (it cannot hash itself) and it is not signed.
#   Anyone who can rewrite the snapshot can also rewrite the manifest and
#   recompute every hash in it. The verifier therefore refuses to take the
#   manifest's word for what must be checked: the schema-2 inventories below are
#   fixed in this script, and a manifest that omits, empties, duplicates or
#   invents an entry is rejected rather than obeyed. That closes the "delete the
#   declaration to disarm the check" path, but it is still integrity against
#   mistakes, not cryptographic proof against a determined rewriter.
#
#   Getting the latter needs a signature over the manifest from a key the
#   verifier does not carry - a signed tag or a detached signature published
#   separately. That is deliberately out of scope here and must not be implied.
#
# Usage:
#   verify-release.sh <bundle-root>
#   verify-release.sh --distribution <distribution-repository-root>

BUNDLED_VERIFIER_NAME="verify-release.sh"

EXPECTED_ARTIFACT_NAMES="claude codex workbuddy shared_runtime"
EXPECTED_LICENSE_FILES="LICENSE
THIRD_PARTY_NOTICES
plugins/claude/LICENSE
plugins/claude/THIRD_PARTY_NOTICES
plugins/codex/LICENSE
plugins/codex/THIRD_PARTY_NOTICES
runtime/zimaflow/LICENSE
runtime/zimaflow/THIRD_PARTY_NOTICES"
EXPECTED_REQUIRED_EXECUTABLES="plugins/claude/bin/zimaflow
plugins/claude/runtime/zimaflow/bin/zimaflow
plugins/codex/skills/zimaflow/bin/zimaflow
runtime/zimaflow/bin/zimaflow"
EXPECTED_WORKBUDDY_SHARED_RUNTIME_PATH="../../runtime/zimaflow"
EXPECTED_FORBIDDEN_PATH_GLOBS=".git
tests
installer
rollback
knowledge-usage-ledger.jsonl
projects.yaml"
EXPECTED_LICENSE="MIT"
EXPECTED_REPRODUCIBLE_BUILD="true"
EXPECTED_OWNERSHIP_SOURCE="private_zimaflow_repository"
EXPECTED_OWNERSHIP_RELEASE_BUNDLE="generated_from_shared_source"
EXPECTED_OWNERSHIP_PUBLIC_RELEASE="promotes_this_bundle_without_rebuild"
EXPECTED_CONSTRAINT_SYMLINKS="forbidden"
EXPECTED_CONSTRAINT_DEVELOPMENT_PATHS="forbidden"
EXPECTED_CONSTRAINT_PRIVATE_RUNTIME_DATA="forbidden"
EXPECTED_WORKBUDDY_SCHEMA="1"
EXPECTED_WORKBUDDY_DOCTOR_CONTRACT="1"
EXPECTED_WORKBUDDY_HOST_ID="workbuddy"
EXPECTED_WORKBUDDY_PACKAGING_MODE="direct_source"
PROVENANCE_FILE="release-provenance.txt"

usage() {
  echo "Usage: verify-release.sh <bundle-root>" >&2
  echo "       verify-release.sh --distribution <distribution-repository-root>" >&2
}

fail() {
  echo "verify-release: FAIL: $*" >&2
  exit 1
}

sha256_file() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{ print $1 }'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{ print $1 }'
  else
    fail 'SHA256 command required: shasum or sha256sum'
  fi
}

tree_hash() {
  local root="$1"
  local excluded_path="${2:-}"
  local ignore_top_git="${3:-false}"
  [ -d "$root" ] || fail "hash root is not a directory: $root"
  (
    cd "$root"
    while IFS= read -r path; do
      if [ "$ignore_top_git" = true ]; then
        case "$path" in
          ./.git|./.git/*) continue ;;
        esac
      fi
      if [ -f "$path" ]; then
        [ "${path#./}" = "$excluded_path" ] && continue
        printf '%s  %s\n' "$(sha256_file "$path")" "${path#./}"
      fi
    done < <(find . -type f -print | LC_ALL=C sort)
  ) | sha256_file /dev/stdin
}

find_bundle_paths() {
  local bundle_root="$1" allow_top_git="$2"
  shift 2
  if [ "$allow_top_git" = true ]; then
    find "$bundle_root" \( -path "$bundle_root/.git" -o -path "$bundle_root/.git/*" \) -prune -o "$@"
  else
    find "$bundle_root" "$@"
  fi
}

expected_artifact_path() {
  case "$1" in
    claude) printf 'plugins/claude\n' ;;
    codex) printf 'plugins/codex\n' ;;
    workbuddy) printf 'adapters/workbuddy\n' ;;
    shared_runtime) printf 'runtime/zimaflow\n' ;;
    *) return 1 ;;
  esac
}

# The generated manifests are written by this project's own builder, so they are
# not arbitrary YAML: they are a fixed, schema-specific generated syntax. This
# verifier reads them line by line, which is only sound if that is genuinely
# what they are - so it is enforced, in two layers, before anything is read.
#
# Layer 1, lexical. A line is exactly one of:
#
#   * blank (spaces only)
#   * a comment: optional spaces, then `#`
#   * a list item:   <indent>`- `<value>
#   * a mapping key: <indent><key>`:` , optionally followed by ` `<value>
#
# A key is `[A-Za-z_][A-Za-z0-9_]*`. A value is `[A-Za-z0-9_.][A-Za-z0-9_./-]*`.
# That token set is the complete character inventory the builder actually emits
# (letters, digits, `_`, `.`, `/`, and interior `-`), and it is an allowlist, not
# a blacklist of YAML indicators. Because `:` and a leading `-` are simply not in
# it, a value can never reopen block structure (`key: - injected`) or start a
# nested mapping (`key: a: b`) - both of which a real YAML reader refuses
# outright while a first-character check waves them through. Indentation must be
# a multiple of two, and the whole file must be printable ASCII, which also rules
# out tabs, CR and any non-ASCII byte.
#
# Layer 2, structural and schema. Lexically valid lines are then checked against
# the exact shape of the named schema: which keys may appear, at which depth,
# under which parent, whether they carry a value, and that every required key is
# present. A scalar may not have children, a list may hold only list items, a
# list item may not have children, indentation may not skip a level, and an
# unknown key is an error rather than harmless extra content. This is what stops
# structure the line reader would never look at - a child mapping under a scalar
# changes what a YAML reader sees while leaving every line this verifier reads
# untouched.
#
# This is deliberately not YAML support. It is a refusal to accept any input
# whose meaning to a standard reader could differ from its meaning here.
assert_manifest_grammar() {
  local file="$1"
  local label="$2"
  local schema="$3"
  local report

  report="$(LC_ALL=C grep -n '[^ -~]' "$file" | head -n 3 || true)"
  if [ -n "$report" ]; then
    printf '%s\n' "$report" | while IFS= read -r offending; do
      echo "verify-release: FAIL: $label has a non-printable or non-ASCII character at $offending" >&2
    done
    echo "verify-release: FAIL: $label must be printable ASCII; tabs, CR and non-ASCII bytes are not permitted" >&2
    exit 1
  fi

  report="$(
    awk -v schema="$schema" '
      function declare(names, k,   n, i, parts) {
        n = split(names, parts, " ")
        for (i = 1; i <= n; i++) {
          shape[parts[i]] = k
          required[parts[i]] = 1
        }
      }
      function problem(reason) {
        printf("line %d: %s: %s\n", NR, reason, $0)
        bad = 1
      }
      BEGIN {
        KEY = "^[A-Za-z_][A-Za-z0-9_]*$"
        VALUE = "^[A-Za-z0-9_.][A-Za-z0-9_./-]*$"
        if (schema == "release-manifest-2") {
          declare("schema_version zimaflow_version source_commit host_capability_fingerprint build_id reproducible_build promotion license payload_sha256", "scalar")
          declare("ownership constraints artifacts", "map")
          declare("license_files required_executables forbidden_path_globs", "list")
          declare("ownership.source ownership.release_bundle ownership.public_release", "scalar")
          declare("constraints.symlinks constraints.development_machine_paths constraints.private_runtime_data", "scalar")
          declare("artifacts.claude artifacts.codex artifacts.workbuddy artifacts.shared_runtime", "map")
          declare("artifacts.claude.path artifacts.claude.sha256", "scalar")
          declare("artifacts.codex.path artifacts.codex.sha256", "scalar")
          declare("artifacts.workbuddy.path artifacts.workbuddy.sha256", "scalar")
          declare("artifacts.shared_runtime.path artifacts.shared_runtime.sha256", "scalar")
        } else if (schema == "workbuddy-runtime-1") {
          declare("schema_version doctor_contract_schema_version source_fingerprint host_id packaging_mode shared_runtime_path shared_runtime_sha256", "scalar")
        } else {
          printf("unknown schema: %s\n", schema)
          bad = 1
          exit 1
        }
        open_depth = 0
      }
      {
        if ($0 ~ /^ *$/) next
        if ($0 ~ /^ *#/) next
        match($0, /^ */)
        indent = RLENGTH
        rest = substr($0, indent + 1)
        if (indent % 2 != 0) { problem("indentation must be a multiple of two spaces"); next }
        depth = indent / 2

        is_item = 0
        key = ""
        value = ""
        has_value = 0
        if (substr(rest, 1, 2) == "- ") {
          is_item = 1
          value = substr(rest, 3)
          has_value = 1
        } else if (rest ~ /^[A-Za-z_][A-Za-z0-9_]*:$/) {
          key = substr(rest, 1, length(rest) - 1)
        } else if (rest ~ /^[A-Za-z_][A-Za-z0-9_]*: /) {
          key = substr(rest, 1, index(rest, ": ") - 1)
          value = substr(rest, index(rest, ": ") + 2)
          has_value = 1
        } else {
          problem("expected a blank line, a comment, a list item, or an unquoted ASCII mapping key")
          next
        }
        if (key != "" && key !~ KEY) { problem("key is outside the generated token set"); next }
        if (has_value && value !~ VALUE) { problem("value is outside the generated token set"); next }

        if (depth > open_depth) { problem("indentation skips a level"); next }
        parent_kind = (depth == 0) ? "root" : stack_kind[depth - 1]
        parent_path = ""
        if (depth > 0) {
          parent_path = stack_path[depth - 1]
          if (parent_kind == "scalar") { problem("a scalar key may not have children"); next }
          if (parent_kind == "item") { problem("a list item may not have children"); next }
        }

        if (is_item) {
          if (parent_kind != "list") { problem("a list item may only appear under a declared list"); next }
          stack_path[depth] = parent_path ".-"
          stack_kind[depth] = "item"
          open_depth = depth + 1
          next
        }

        if (parent_kind == "list") { problem("a list may only contain list items"); next }
        path = (depth == 0) ? key : parent_path "." key
        if (!(path in shape)) { problem("unknown key for this schema: " path); next }
        expected = shape[path]
        if (expected == "scalar" && !has_value) { problem("scalar key " path " must carry a value"); next }
        if (expected != "scalar" && has_value) { problem(expected " key " path " must not carry a value"); next }
        seen[path] = 1
        stack_path[depth] = path
        stack_kind[depth] = expected
        open_depth = depth + 1
      }
      END {
        for (path in required) {
          if (!(path in seen)) {
            printf("missing required key for this schema: %s\n", path)
            bad = 1
          }
        }
        exit bad ? 1 : 0
      }
    ' "$file"
  )" || true
  if [ -n "$report" ]; then
    printf '%s\n' "$report" | while IFS= read -r offending; do
      echo "verify-release: FAIL: $label is outside the $schema generated grammar at $offending" >&2
    done
    echo "verify-release: FAIL: $label must match the $schema generated grammar exactly; this verifier reads it line by line" >&2
    exit 1
  fi
}

# A YAML mapping key must appear once. This verifier reads with awk and takes
# the first occurrence; common YAML loaders take the last, and some reject
# duplicates outright. A manifest with a repeated key can therefore report one
# source_commit to this tool and another to a standard reader, for the same
# snapshot. Reject the ambiguity instead of picking a side, and name the key so
# the manifest can be fixed.
#
# Indentation is tracked so nested keys are distinguished by their full path
# (`artifacts.claude.path`), and list items are not treated as keys. The
# generated manifests contain no block scalars or flow mappings, and any line
# that looks like one is refused rather than parsed loosely.
assert_unique_keys() {
  local file="$1"
  local label="$2"
  local report

  report="$(
    awk '
      /^[[:space:]]*$/ { next }
      /^[[:space:]]*#/ { next }
      /^[[:space:]]*-[[:space:]]/ { next }
      {
        line = $0
        match(line, /^ */)
        indent = RLENGTH
        key = substr(line, indent + 1)
        # assert_manifest_grammar has already refused anything that is not a
        # blank line, a comment, a list item or an unquoted ASCII mapping key,
        # so there is nothing left to skip here.
        if (key !~ /^[A-Za-z_][A-Za-z0-9_]*:/) next
        sub(/:.*$/, "", key)
        while (depth > 0 && indents[depth] >= indent) depth--
        depth++
        indents[depth] = indent
        names[depth] = key
        full = names[1]
        for (i = 2; i <= depth; i++) full = full "." names[i]
        if (full in seen) print full
        seen[full] = 1
      }
    ' "$file"
  )"
  if [ -n "$report" ]; then
    printf '%s\n' "$report" | while IFS= read -r duplicated; do
      echo "verify-release: FAIL: $label declares a duplicate key: $duplicated" >&2
    done
    echo "verify-release: FAIL: $label must declare each key once; readers disagree on duplicates" >&2
    exit 1
  fi
}

manifest_scalar() {
  awk -v key="$2" '
    $0 ~ "^" key ":[[:space:]]" {
      sub("^" key ":[[:space:]]*", "")
      print
      exit
    }
  ' "$1"
}

manifest_nested_scalar() {
  awk -v parent="$2" -v key="$3" '
    $0 == parent ":" { inside = 1; next }
    inside && $0 ~ "^  " key ":[[:space:]]" {
      sub("^  " key ":[[:space:]]*", "")
      print
      exit
    }
    inside && /^[^[:space:]]/ { exit }
  ' "$1"
}

assert_manifest_value() {
  local label="$1"
  local actual="$2"
  local expected="$3"
  [ "$actual" = "$expected" ] \
    || fail "$label must be $expected, manifest declares: ${actual:-<missing>}"
}

assert_source_commit_value() {
  local value="$1"
  printf '%s\n' "$value" | LC_ALL=C grep -Eq '^[0-9a-f]{40}$' \
    || fail "source_commit must be a lowercase 40-character Git commit, got: ${value:-<missing>}"
}

# Returns the declared items of a top-level list, one per line, with surrounding
# quotes stripped. A missing section returns nothing, which is why every caller
# goes through assert_declared_set instead of iterating this directly.
manifest_list() {
  awk -v key="$2" '
    $0 ~ "^" key ":[[:space:]]*$" { inside = 1; next }
    inside && /^[[:space:]]+-[[:space:]]*/ {
      sub(/^[[:space:]]*-[[:space:]]*/, "")
      gsub(/^"|"$/, "")
      print
      next
    }
    inside { exit }
  ' "$1"
}

manifest_has_section() {
  grep -qE "^$2:[[:space:]]*\$" "$1"
}

manifest_artifact_names() {
  awk '
    $0 == "artifacts:" { inside = 1; next }
    inside && /^  [A-Za-z_][A-Za-z0-9_]*:[[:space:]]*$/ {
      sub(/^  /, "")
      sub(/:[[:space:]]*$/, "")
      print
      next
    }
    inside && /^[^[:space:]]/ { exit }
  ' "$1"
}

manifest_artifact_field() {
  awk -v name="$2" -v field="$3" '
    $0 == "artifacts:" { in_artifacts = 1; next }
    in_artifacts && $0 ~ "^  " name ":[[:space:]]*$" { in_artifact = 1; next }
    in_artifact && $0 ~ "^    " field ":[[:space:]]" {
      sub("^    " field ":[[:space:]]*", "")
      print
      exit
    }
    in_artifact && /^  [^[:space:]]/ { exit }
  ' "$1"
}

# A declared inventory must match the schema-2 inventory exactly: present, not
# empty, no duplicates, nothing missing, nothing unknown.
assert_declared_set() {
  local label="$1"
  local expected="$2"
  local actual="$3"
  local item seen count

  [ -n "$actual" ] || fail "release manifest declares no $label; schema 2 requires the full inventory"
  seen=""
  while IFS= read -r item; do
    [ -n "$item" ] || fail "release manifest declares an empty $label entry"
    case "$seen" in
      *"|$item|"*) fail "release manifest declares a duplicate $label entry: $item" ;;
    esac
    seen="$seen|$item|"
    case "$(printf '%s\n' "$expected" | grep -Fxc -- "$item" || true)" in
      0) fail "release manifest declares an unknown $label entry: $item" ;;
    esac
  done <<EOF
$actual
EOF
  while IFS= read -r item; do
    [ -n "$item" ] || continue
    case "$seen" in
      *"|$item|"*) ;;
      *) fail "release manifest is missing a required $label entry: $item" ;;
    esac
  done <<EOF
$expected
EOF
  count="$(printf '%s\n' "$actual" | grep -c . || true)"
  [ "$count" = "$(printf '%s\n' "$expected" | grep -c . || true)" ] \
    || fail "release manifest declares the wrong number of $label entries"
}

# Manifest-driven paths must be normalized relative paths. Absolute paths, empty
# paths, and `.` or `..` segments are rejected outright rather than normalized,
# so a path can never be argued back inside the bundle after the fact.
assert_normalized_relative() {
  local label="$1"
  local candidate="$2"
  local segment rest

  [ -n "$candidate" ] || fail "$label must be a normalized relative path, got an empty value"
  case "$candidate" in
    /*) fail "$label must be a normalized relative path, got an absolute path: $candidate" ;;
    */) fail "$label must be a normalized relative path, got a trailing separator: $candidate" ;;
    *//*) fail "$label must be a normalized relative path, got an empty segment: $candidate" ;;
  esac
  rest="$candidate"
  while [ -n "$rest" ]; do
    segment="${rest%%/*}"
    if [ "$segment" = "$rest" ]; then
      rest=""
    else
      rest="${rest#*/}"
    fi
    case "$segment" in
      .|..) fail "$label must be a normalized relative path, got a '$segment' segment: $candidate" ;;
    esac
  done
}

# Resolve a relative path against the bundle root without following it out.
# Existing ancestors are resolved physically so a link farm cannot widen the
# root; the remainder is appended literally so a missing file still yields a
# decidable location.
resolve_within_bundle() {
  local label="$1"
  local bundle_root="$2"
  local relative="$3"
  local current="$bundle_root"
  local segment rest

  rest="$relative"
  while [ -n "$rest" ]; do
    segment="${rest%%/*}"
    if [ "$segment" = "$rest" ]; then
      rest=""
    else
      rest="${rest#*/}"
    fi
    if [ -d "$current/$segment" ] && [ ! -L "$current/$segment" ]; then
      current="$(cd "$current/$segment" && pwd -P)"
    else
      current="$current/$segment"
    fi
  done
  case "$current" in
    "$bundle_root"/*) ;;
    *) fail "$label must stay inside the bundle root: $relative" ;;
  esac
  printf '%s\n' "$current"
}

assert_sha256_value() {
  local label="$1"
  local value="$2"
  case "$value" in
    [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]) ;;
    *) fail "$label must be a lowercase 64-character SHA-256 value, got: ${value:-<missing>}" ;;
  esac
}

verify_bundle() {
  local bundle_root manifest allow_top_git="${2:-false}"
  [ -d "$1" ] || fail "bundle root must exist as a directory: $1"
  bundle_root="$(cd "$1" && pwd -P)"
  if [ "$allow_top_git" != true ] && { [ -e "$bundle_root/.git" ] || [ -L "$bundle_root/.git" ]; }; then
    fail 'ordinary bundle verification must not contain top-level Git metadata'
  fi
  manifest="$bundle_root/release-manifest.yaml"
  [ -f "$manifest" ] && [ ! -L "$manifest" ] \
    || fail "bundle is missing release-manifest.yaml: $bundle_root"

  # Structural gate first: no symbolic link may exist anywhere below the root.
  # This runs before any manifest-driven path is resolved, so path resolution
  # below cannot be redirected by a link.
  local found
  found="$(find_bundle_paths "$bundle_root" "$allow_top_git" -type l -print | head -n 1)"
  [ -z "$found" ] || fail "bundle must not contain a symlink: $found"

  # Structural gate on both manifests before a single value, path or hash is
  # read out of either. Both paths are fixed here, not taken from manifest
  # content, so this cannot be redirected.
  local workbuddy_manifest
  workbuddy_manifest="$bundle_root/$(expected_artifact_path workbuddy)/runtime-manifest.yaml"
  [ -f "$workbuddy_manifest" ] && [ ! -L "$workbuddy_manifest" ] \
    || fail 'WorkBuddy artifact must contain runtime-manifest.yaml'
  assert_manifest_grammar "$manifest" 'release manifest' release-manifest-2
  assert_manifest_grammar "$workbuddy_manifest" 'WorkBuddy runtime manifest' workbuddy-runtime-1
  assert_unique_keys "$manifest" 'release manifest'
  assert_unique_keys "$workbuddy_manifest" 'WorkBuddy runtime manifest'

  local schema_version version commit build_id license declared_payload fingerprint
  schema_version="$(manifest_scalar "$manifest" schema_version)"
  [ "$schema_version" = "2" ] || fail "unsupported release manifest schema_version: ${schema_version:-<missing>}"
  version="$(manifest_scalar "$manifest" zimaflow_version)"
  commit="$(manifest_scalar "$manifest" source_commit)"
  build_id="$(manifest_scalar "$manifest" build_id)"
  license="$(manifest_scalar "$manifest" license)"
  fingerprint="$(manifest_scalar "$manifest" host_capability_fingerprint)"
  declared_payload="$(manifest_scalar "$manifest" payload_sha256)"
  [ -n "$version" ] || fail 'release manifest is missing zimaflow_version'
  [ -n "$commit" ] || fail 'release manifest is missing source_commit'
  [ -n "$license" ] || fail 'release manifest is missing license'
  assert_source_commit_value "$commit"
  assert_sha256_value host_capability_fingerprint "$fingerprint"
  [ "$build_id" = "zimaflow-$version-$commit" ] \
    || fail "build_id does not match version and source commit: ${build_id:-<missing>}"
  assert_manifest_value 'release manifest reproducible_build' \
    "$(manifest_scalar "$manifest" reproducible_build)" "$EXPECTED_REPRODUCIBLE_BUILD"
  [ "$(manifest_scalar "$manifest" promotion)" = "immutable_tested_bundle" ] \
    || fail 'release manifest must declare an immutable tested bundle promotion'
  assert_manifest_value 'release manifest license' "$license" "$EXPECTED_LICENSE"
  assert_manifest_value 'release manifest ownership.source' \
    "$(manifest_nested_scalar "$manifest" ownership source)" "$EXPECTED_OWNERSHIP_SOURCE"
  assert_manifest_value 'release manifest ownership.release_bundle' \
    "$(manifest_nested_scalar "$manifest" ownership release_bundle)" "$EXPECTED_OWNERSHIP_RELEASE_BUNDLE"
  assert_manifest_value 'release manifest ownership.public_release' \
    "$(manifest_nested_scalar "$manifest" ownership public_release)" "$EXPECTED_OWNERSHIP_PUBLIC_RELEASE"
  assert_manifest_value 'release manifest constraints.symlinks' \
    "$(manifest_nested_scalar "$manifest" constraints symlinks)" "$EXPECTED_CONSTRAINT_SYMLINKS"
  assert_manifest_value 'release manifest constraints.development_machine_paths' \
    "$(manifest_nested_scalar "$manifest" constraints development_machine_paths)" "$EXPECTED_CONSTRAINT_DEVELOPMENT_PATHS"
  assert_manifest_value 'release manifest constraints.private_runtime_data' \
    "$(manifest_nested_scalar "$manifest" constraints private_runtime_data)" "$EXPECTED_CONSTRAINT_PRIVATE_RUNTIME_DATA"
  assert_sha256_value payload_sha256 "$declared_payload"

  # The release manifest cannot hash itself. A canonical identity copy inside
  # the payload makes a manifest-only edit observable without pretending this
  # unsigned bundle proves authenticity against an editor who rewrites both.
  local provenance expected_provenance_hash actual_provenance_hash version_cli capability_file
  provenance="$bundle_root/$PROVENANCE_FILE"
  [ -f "$provenance" ] && [ ! -L "$provenance" ] \
    || fail "bundle is missing payload-covered release identity: $PROVENANCE_FILE"
  expected_provenance_hash="$(
    printf 'zimaflow_version=%s\nsource_commit=%s\nhost_capability_fingerprint=%s\nlicense=%s\n' \
      "$version" "$commit" "$fingerprint" "$EXPECTED_LICENSE" | sha256_file /dev/stdin
  )"
  actual_provenance_hash="$(sha256_file "$provenance")"
  [ "$actual_provenance_hash" = "$expected_provenance_hash" ] \
    || fail 'release identity does not match the payload-covered provenance record'

  version_cli="$bundle_root/runtime/zimaflow/bin/zimaflow"
  [ -f "$version_cli" ] && [ ! -L "$version_cli" ] \
    || fail 'bundle is missing the payload-covered shared runtime CLI identity'
  grep -Fqx "VERSION=\"$version\"" "$version_cli" \
    || fail "release manifest zimaflow_version does not match the payload-covered shared runtime CLI: $version"

  capability_file="$bundle_root/runtime/zimaflow/references/host-capabilities.yaml"
  [ -f "$capability_file" ] && [ ! -L "$capability_file" ] \
    || fail 'bundle is missing the payload-covered host capability contract'
  [ "$(sha256_file "$capability_file")" = "$fingerprint" ] \
    || fail 'release manifest host_capability_fingerprint does not match the payload-covered capability contract'

  assert_manifest_value 'WorkBuddy runtime manifest schema_version' \
    "$(manifest_scalar "$workbuddy_manifest" schema_version)" "$EXPECTED_WORKBUDDY_SCHEMA"
  assert_manifest_value 'WorkBuddy runtime manifest doctor_contract_schema_version' \
    "$(manifest_scalar "$workbuddy_manifest" doctor_contract_schema_version)" "$EXPECTED_WORKBUDDY_DOCTOR_CONTRACT"
  assert_manifest_value 'WorkBuddy runtime manifest source_fingerprint' \
    "$(manifest_scalar "$workbuddy_manifest" source_fingerprint)" "$fingerprint"
  assert_manifest_value 'WorkBuddy runtime manifest host_id' \
    "$(manifest_scalar "$workbuddy_manifest" host_id)" "$EXPECTED_WORKBUDDY_HOST_ID"
  assert_manifest_value 'WorkBuddy runtime manifest packaging_mode' \
    "$(manifest_scalar "$workbuddy_manifest" packaging_mode)" "$EXPECTED_WORKBUDDY_PACKAGING_MODE"

  # Inventories are validated against the schema-2 contract fixed in this
  # script. A manifest cannot shorten this list to shorten the checks.
  local declared_licenses declared_executables declared_globs declared_artifacts
  manifest_has_section "$manifest" license_files \
    || fail 'release manifest is missing the license_files section'
  manifest_has_section "$manifest" required_executables \
    || fail 'release manifest is missing the required_executables section'
  manifest_has_section "$manifest" forbidden_path_globs \
    || fail 'release manifest is missing the forbidden_path_globs section'
  declared_licenses="$(manifest_list "$manifest" license_files)"
  declared_executables="$(manifest_list "$manifest" required_executables)"
  declared_globs="$(manifest_list "$manifest" forbidden_path_globs)"
  assert_declared_set 'license file' "$EXPECTED_LICENSE_FILES" "$declared_licenses"
  assert_declared_set 'required executable' "$EXPECTED_REQUIRED_EXECUTABLES" "$declared_executables"
  assert_declared_set 'forbidden path glob' "$EXPECTED_FORBIDDEN_PATH_GLOBS" "$declared_globs"

  grep -q '^artifacts:$' "$manifest" || fail 'release manifest is missing the artifacts section'
  declared_artifacts="$(manifest_artifact_names "$manifest")"
  assert_declared_set 'artifact' "$(printf '%s\n' $EXPECTED_ARTIFACT_NAMES)" "$declared_artifacts"

  # Validate and resolve every manifest-driven path before touching the
  # filesystem through it. Nothing below this block reads a path that has not
  # already been proven normalized, relative and contained.
  local relative resolved name artifact_path artifact_hash
  local resolved_licenses="" resolved_executables="" resolved_artifacts=""
  local shared_runtime_dir="" shared_runtime_artifact_hash=""
  while IFS= read -r relative; do
    [ -n "$relative" ] || continue
    assert_normalized_relative "declared license file" "$relative"
    resolved="$(resolve_within_bundle "declared license file" "$bundle_root" "$relative")"
    resolved_licenses="$resolved_licenses$relative	$resolved
"
  done <<EOF
$declared_licenses
EOF
  while IFS= read -r relative; do
    [ -n "$relative" ] || continue
    assert_normalized_relative "declared required executable" "$relative"
    resolved="$(resolve_within_bundle "declared required executable" "$bundle_root" "$relative")"
    resolved_executables="$resolved_executables$relative	$resolved
"
  done <<EOF
$declared_executables
EOF
  for name in $EXPECTED_ARTIFACT_NAMES; do
    artifact_path="$(manifest_artifact_field "$manifest" "$name" path)"
    artifact_hash="$(manifest_artifact_field "$manifest" "$name" sha256)"
    [ -n "$artifact_path" ] || fail "release manifest is missing the $name artifact path"
    assert_sha256_value "$name artifact sha256" "$artifact_hash"
    assert_normalized_relative "declared $name artifact path" "$artifact_path"
    [ "$artifact_path" = "$(expected_artifact_path "$name")" ] \
      || fail "$name artifact must be published at $(expected_artifact_path "$name"), manifest declares: $artifact_path"
    resolved="$(resolve_within_bundle "declared $name artifact path" "$bundle_root" "$artifact_path")"
    resolved_artifacts="$resolved_artifacts$name	$artifact_path	$artifact_hash	$resolved
"
    if [ "$name" = "shared_runtime" ]; then
      shared_runtime_dir="$resolved"
      shared_runtime_artifact_hash="$artifact_hash"
    fi
  done

  # Required host catalogs and the promoted verifier copy. These names are fixed
  # here, not taken from the manifest.
  local required
  for required in .claude-plugin/marketplace.json .agents/plugins/marketplace.json README.md "$BUNDLED_VERIFIER_NAME"; do
    [ -f "$bundle_root/$required" ] || fail "bundle is missing: $required"
  done
  [ -x "$bundle_root/$BUNDLED_VERIFIER_NAME" ] \
    || fail "the bundled verifier copy must stay executable: $BUNDLED_VERIFIER_NAME"
  grep -q '"owner"' "$bundle_root/.claude-plugin/marketplace.json" \
    || fail 'Claude catalog must declare an owner'
  grep -q '"owner"' "$bundle_root/.agents/plugins/marketplace.json" \
    || fail 'Codex catalog must declare an owner'

  while IFS="$(printf '\t')" read -r relative resolved; do
    [ -n "$relative" ] || continue
    [ -s "$resolved" ] || fail "declared license file is missing or empty: $relative"
  done <<EOF
$resolved_licenses
EOF

  while IFS="$(printf '\t')" read -r relative resolved; do
    [ -n "$relative" ] || continue
    [ -f "$resolved" ] || fail "declared required executable is missing: $relative"
    [ -x "$resolved" ] || fail "declared required executable is not executable: $relative"
  done <<EOF
$resolved_executables
EOF

  while IFS= read -r relative; do
    [ -n "$relative" ] || continue
    found="$(find_bundle_paths "$bundle_root" "$allow_top_git" -iname "*$relative*" -print | head -n 1)"
    [ -z "$found" ] || fail "bundle must not contain forbidden content: $found"
  done <<EOF
$declared_globs
EOF
  # The third needle is written as two concatenated string literals so that this
  # script, which now ships inside the bundle it scans, does not match its own
  # scanner text and report itself as a development path.
  if find_bundle_paths "$bundle_root" "$allow_top_git" -type f -print0 | xargs -0 -r grep -I -E "/Users/[A-Za-z0-9_]|/home/[a-z0-9_][a-z0-9_-]*/|knowledge""_base" >/dev/null 2>&1; then
    fail 'bundle must not contain a development-machine path'
  fi

  local computed
  while IFS="$(printf '\t')" read -r name artifact_path artifact_hash resolved; do
    [ -n "$name" ] || continue
    [ -d "$resolved" ] || fail "declared artifact directory is missing: $artifact_path"
    computed="$(tree_hash "$resolved")"
    [ "$computed" = "$artifact_hash" ] \
      || fail "artifact hash mismatch for $name ($artifact_path): expected $artifact_hash, computed $computed"
  done <<EOF
$resolved_artifacts
EOF

  # The WorkBuddy manifest reaches the portable shared runtime by one fixed
  # relative path. Unlike the release-manifest paths, this one legitimately
  # contains `..`, because the manifest sits two levels below the bundle root -
  # so it is pinned to its exact expected value and then required to resolve to
  # the very artifact the release manifest already pinned.
  local shared_relative shared_hash shared_resolved
  shared_relative="$(manifest_scalar "$workbuddy_manifest" shared_runtime_path)"
  shared_hash="$(manifest_scalar "$workbuddy_manifest" shared_runtime_sha256)"
  [ "$shared_relative" = "$EXPECTED_WORKBUDDY_SHARED_RUNTIME_PATH" ] \
    || fail "WorkBuddy shared runtime path must be exactly $EXPECTED_WORKBUDDY_SHARED_RUNTIME_PATH, manifest declares: ${shared_relative:-<missing>}"
  assert_sha256_value 'WorkBuddy shared runtime fingerprint' "$shared_hash"
  shared_resolved="$(cd "$(dirname "$workbuddy_manifest")/$shared_relative" 2>/dev/null && pwd -P)" \
    || fail "WorkBuddy shared runtime path does not resolve inside the bundle: $shared_relative"
  case "$shared_resolved" in
    "$bundle_root"/*) ;;
    *) fail "WorkBuddy shared runtime path must stay inside the bundle root: $shared_relative" ;;
  esac
  [ "$shared_resolved" = "$shared_runtime_dir" ] \
    || fail "WorkBuddy shared runtime path must resolve to the shared_runtime artifact the release manifest pins"
  [ "$shared_hash" = "$shared_runtime_artifact_hash" ] \
    || fail 'WorkBuddy shared runtime fingerprint must equal the shared_runtime artifact hash in the release manifest'
  computed="$(tree_hash "$shared_resolved")"
  [ "$computed" = "$shared_hash" ] \
    || fail "WorkBuddy shared runtime fingerprint mismatch: expected $shared_hash, computed $computed"

  computed="$(tree_hash "$bundle_root" release-manifest.yaml "$allow_top_git")"
  [ "$computed" = "$declared_payload" ] \
    || fail "payload hash mismatch: expected $declared_payload, computed $computed"

  echo "verify-release: OK $build_id ($license)"
  echo "verify-release: integrity model - detects drift from the recorded manifest; the manifest is unsigned, so this is not cryptographic proof of authenticity."
}

# Verify that a public distribution repository's root is the immutable bundle.
# Its only permitted transport addition is a real top-level Git directory/file.
verify_distribution() {
  local repo_root found path
  [ -d "$1" ] || fail "distribution root must exist as a directory: $1"
  repo_root="$(cd "$1" && pwd -P)"
  [ ! -L "$repo_root/.git" ] || fail 'distribution transport .git must not be a symlink'
  if [ -e "$repo_root/.git" ]; then
    git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
      || fail 'top-level .git is not valid Git transport metadata'
  fi
  # Recompute every payload hash while excluding only transport metadata. Any
  # nested .git, symlink, or payload addition remains part of the verification.
  verify_bundle "$repo_root" true
  found="$(find "$repo_root" \( -path "$repo_root/.git" -o -path "$repo_root/.git/*" \) -prune -o -type d -empty -print | head -n 1)"
  [ -z "$found" ] || fail "distribution root contains an unrecorded empty directory: $found"
  while IFS= read -r path; do
    [ "$path" = "$repo_root" ] && continue
    find "$path" -type f -print -quit | grep -q . \
      || fail "distribution root contains a non-payload directory: $path"
  done < <(find "$repo_root" \( -path "$repo_root/.git" -o -path "$repo_root/.git/*" \) -prune -o -type d -print)
  echo 'verify-release: distribution root is the verified bundle root'
}

main() {
  case "${1:-}" in
    --distribution)
      [ "$#" -eq 2 ] || { usage; return 2; }
      verify_distribution "$2"
      ;;
    -h|--help)
      usage
      return 0
      ;;
    "")
      usage
      return 2
      ;;
    -*)
      usage
      return 2
      ;;
    *)
      [ "$#" -eq 1 ] || { usage; return 2; }
      verify_bundle "$1"
      ;;
  esac
}

main "$@"
