#!/usr/bin/env python3
"""Audit and migrate legacy company Specflow state without destroying evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import sys
import tempfile
from typing import Any


KNOWN_FIELDS = {
    "schema_version",
    "change_id",
    "change",
    "phase",
    "mode",
    "updated_at",
    "updated_by",
    "requirement_contract.path",
    "requirement_contract.status",
    "requirement_contract.confirmed_at",
    "requirement_contract.intent_lock",
    "decision.path",
    "decision.status",
    "prototype.enabled",
    "prototype.prototype_path",
    "prototype.review_notes_path",
    "prototype.status",
    "openspec.change_path",
    "openspec.proposal_path",
    "openspec.design_path",
    "openspec.tasks_path",
    "openspec.spec_review_confirmed",
    "openspec.spec_review_confirmed_at",
    "implementation.isolation",
    "implementation.branch",
    "implementation.worktree_path",
    "implementation.started_at",
    "implementation.completed_at",
    "verification.opsx_verify",
    "verification.full_tests",
    "verification.last_command",
    "verification.last_result",
    "verification.evidence_path",
    "verification.blocked_reason",
    "verification.verified_at",
    "archive.status",
    "archive.archived_at",
    "archive.docs_synced",
    "handover.latest_path",
    "handover.updated_at",
}

MATERIAL_FIELDS = (
    "change_id",
    "change",
    "phase",
    "mode",
    "verification.opsx_verify",
    "verification.full_tests",
    "archive.status",
    "archive.docs_synced",
    "handover.latest_path",
)

PHASES = {
    "contract_confirmed": 10,
    "route_decided": 20,
    "prototype_reviewed": 30,
    "spec_proposed": 40,
    "spec_reviewed": 50,
    "build_started": 60,
    "build_completed": 70,
    "verified": 80,
    "archived": 90,
    "closed": 100,
    "blocked": 0,
}


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def strip_comment(value: str) -> str:
    single = double = False
    for index, char in enumerate(value):
        if char == "'" and not double:
            single = not single
        elif char == '"' and not single:
            double = not double
        elif char == "#" and not single and not double and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value.rstrip()


def scalar(value: str) -> Any:
    value = strip_comment(value.strip())
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    if value in ("true", "false"):
        return value == "true"
    if value in ("null", "~"):
        return None
    if re.fullmatch(r"-?[0-9]+", value):
        return int(value)
    return value


def parse_simple_yaml(path: pathlib.Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    section = ""
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if "\t" in raw:
            raise ValueError(f"unsupported_tab_indent:{number}")
        indent = len(raw) - len(raw.lstrip(" "))
        match = re.match(r"^([A-Za-z0-9_.-]+):(?:\s*(.*))?$", raw.strip())
        if not match:
            raise ValueError(f"unsupported_yaml:{number}")
        key, value = match.group(1), match.group(2) or ""
        if indent == 0:
            if value == "":
                section = key
                continue
            section = ""
            result[key] = scalar(value)
        elif indent == 2 and section:
            result[f"{section}.{key}"] = scalar(value)
        else:
            raise ValueError(f"unsupported_yaml_depth:{number}")
    return result


def family(path: pathlib.Path) -> str:
    return "spec-superflow" if path.name == ".spec-superflow.yaml" else "specflow-state-v1"


def discover(project: pathlib.Path) -> dict[str, list[pathlib.Path]]:
    changes = project / "openspec" / "changes"
    grouped: dict[str, list[pathlib.Path]] = {}
    if not changes.is_dir():
        return grouped
    for change_dir in sorted(path for path in changes.iterdir() if path.is_dir()):
        files = [change_dir / name for name in (".specflow-state.yaml", ".spec-superflow.yaml")]
        existing = [path for path in files if path.is_file() and not path.is_symlink()]
        if existing:
            grouped[change_dir.name] = existing
    return grouped


def canonical_change_id(data: dict[str, Any], fallback: str) -> str:
    return str(data.get("change_id") or data.get("change") or fallback)


def conflict_reason(records: list[dict[str, Any]]) -> str:
    if len(records) < 2:
        return "none"
    for key in MATERIAL_FIELDS:
        values = {json.dumps(record[key], sort_keys=True) for record in records if key in record and record[key] not in (None, "")}
        if len(values) > 1:
            return f"material_field_conflict:{key}"
    return "none"


def source_fingerprint(project: pathlib.Path, paths: list[pathlib.Path]) -> tuple[str, list[str], list[str]]:
    relative = [path.relative_to(project).as_posix() for path in paths]
    hashes = [sha256(path) for path in paths]
    joined = "\n".join(f"{name}:{digest}" for name, digest in zip(relative, hashes))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest(), relative, hashes


def read_receipt(path: pathlib.Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        return {}
    try:
        return parse_simple_yaml(path)
    except ValueError:
        return {"invalid": True}


def receipt_status(project: pathlib.Path, change_dir: pathlib.Path, paths: list[pathlib.Path]) -> str:
    target = change_dir / ".specflow" / "change-state.yaml"
    receipt_path = change_dir / ".specflow" / "migration-receipt.yaml"
    receipt = read_receipt(receipt_path)
    if not receipt and not target.exists():
        return "not_migrated"
    if not receipt or not target.is_file() or target.is_symlink():
        return "invalid_receipt"
    fingerprint, _, _ = source_fingerprint(project, paths)
    if receipt.get("source_fingerprint") != fingerprint:
        return "stale_source"
    if receipt.get("target_sha256") != sha256(target):
        return "stale_target"
    return "current"


def audit(project: pathlib.Path) -> dict[str, Any]:
    changes = []
    overall = "clean"
    for directory_name, paths in discover(project).items():
        records = []
        sources = []
        parse_error = ""
        for path in paths:
            try:
                record = parse_simple_yaml(path)
            except ValueError as exc:
                record = {}
                parse_error = str(exc)
            records.append(record)
            sources.append(
                {
                    "path": path.relative_to(project).as_posix(),
                    "schema_family": family(path),
                    "mapped_fields": sorted(key for key in record if key in KNOWN_FIELDS),
                    "unmapped_fields": sorted(key for key in record if key not in KNOWN_FIELDS),
                    "sha256": sha256(path),
                }
            )
        ambiguity = f"parse_error:{parse_error}" if parse_error else conflict_reason(records)
        status = receipt_status(project, paths[0].parent, paths)
        if ambiguity != "none":
            overall = "ambiguous"
        elif status.startswith("stale") and overall == "clean":
            overall = "stale"
        merged = merge_records(records)
        changes.append(
            {
                "change_id": canonical_change_id(merged, directory_name),
                "change_dir": paths[0].parent.relative_to(project).as_posix(),
                "ambiguity": ambiguity,
                "receipt_status": status,
                "next_action": next_action(ambiguity, status),
                "sources": sources,
            }
        )
    return {"schema_version": 1, "status": overall, "project": ".", "changes": changes}


def next_action(ambiguity: str, status: str) -> str:
    if ambiguity != "none":
        return "resolve_legacy_conflict"
    if status == "not_migrated":
        return "review_then_migrate"
    if status == "current":
        return "none"
    return "review_stale_migration_evidence"


def merge_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for record in records:
        for key, value in record.items():
            if key not in merged or merged[key] in (None, ""):
                merged[key] = value
    return merged


def evidence_conflict(change_dir: pathlib.Path, record: dict[str, Any]) -> str:
    phase = str(record.get("phase") or "")
    rank = PHASES.get(phase, -1)
    if rank < 0:
        return "unknown_phase"
    if rank >= PHASES["verified"]:
        tasks = change_dir / "tasks.md"
        if not tasks.is_file() or re.search(r"(?m)^\s*- \[ \]", tasks.read_text(encoding="utf-8")):
            return "incomplete_tasks"
        if record.get("verification.opsx_verify") != "passed":
            return "opsx_verify_not_passed"
        if record.get("verification.full_tests") != "passed":
            return "full_tests_not_passed"
    if rank >= PHASES["archived"] and record.get("archive.status") != "archived":
        return "archive_not_confirmed"
    if rank >= PHASES["closed"]:
        if record.get("archive.docs_synced") is not True:
            return "docs_not_synced"
        handover = record.get("handover.latest_path")
        if not handover:
            return "handover_missing"
    return ""


def yaml_value(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return '""'
    text = str(value)
    if re.fullmatch(r"[A-Za-z0-9_./+-]+", text):
        return text
    return json.dumps(text, ensure_ascii=False)


def render_target(change_id: str, record: dict[str, Any], families: list[str]) -> str:
    lines = [
        "schema_version: 2",
        f"change_id: {yaml_value(change_id)}",
        f"phase: {yaml_value(record.get('phase', ''))}",
        f"mode: {yaml_value(record.get('mode', 'full'))}",
        f"legacy_schema_families: {yaml_value(','.join(families))}",
    ]
    sections = ("requirement_contract", "decision", "prototype", "openspec", "implementation", "verification", "archive", "handover")
    for section in sections:
        fields = sorted((key.split(".", 1)[1], value) for key, value in record.items() if key.startswith(f"{section}.") and key in KNOWN_FIELDS)
        if not fields:
            continue
        lines.append(f"{section}:")
        lines.extend(f"  {key}: {yaml_value(value)}" for key, value in fields)
    lines.append("")
    return "\n".join(lines)


def atomic_write(path: pathlib.Path, content: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def migrate(project: pathlib.Path, change: str) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", change):
        raise MigrationBlocked("invalid_change_id")
    grouped = discover(project)
    paths = grouped.get(change, [])
    if not paths:
        raise MigrationBlocked("legacy_state_not_found")
    change_dir = project / "openspec" / "changes" / change
    target = change_dir / ".specflow" / "change-state.yaml"
    receipt_path = change_dir / ".specflow" / "migration-receipt.yaml"
    status = receipt_status(project, change_dir, paths)
    if status == "current":
        return {"schema_version": 1, "status": "already_migrated", "change_id": change, "target": target.relative_to(project).as_posix()}
    if status != "not_migrated":
        raise MigrationBlocked("stale_receipt")

    records = []
    for path in paths:
        try:
            records.append(parse_simple_yaml(path))
        except ValueError as exc:
            raise MigrationBlocked(f"legacy_parse_error:{exc}") from exc
    ambiguity = conflict_reason(records)
    if ambiguity != "none":
        raise MigrationBlocked(f"ambiguous_legacy_state:{ambiguity}")
    record = merge_records(records)
    unknown = sorted({key for item in records for key in item if key not in KNOWN_FIELDS})
    risky_unknown = [key for key in unknown if re.search(r"phase|status|verif|archive|complete|closed", key, re.I)]
    if risky_unknown:
        raise MigrationBlocked(f"ambiguous_legacy_state:unknown_lifecycle_field:{risky_unknown[0]}")
    change_id = canonical_change_id(record, change)
    if change_id != change:
        raise MigrationBlocked("ambiguous_legacy_state:change_id_mismatch")
    conflict = evidence_conflict(change_dir, record)
    if conflict:
        raise MigrationBlocked(f"completion_evidence_conflict:{conflict}")

    target_content = render_target(change_id, record, [family(path) for path in paths])
    atomic_write(target, target_content)
    target_hash = sha256(target)
    fingerprint, relative, hashes = source_fingerprint(project, paths)
    timestamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    receipt = "\n".join(
        [
            "schema_version: 1",
            "mapping_version: 1",
            f"change_id: {yaml_value(change_id)}",
            f"source_paths: {yaml_value(','.join(relative))}",
            f"source_hashes: {yaml_value(','.join(hashes))}",
            f"source_fingerprint: {fingerprint}",
            f"target_path: {target.relative_to(project).as_posix()}",
            f"target_sha256: {target_hash}",
            f"unmapped_fields: {yaml_value(','.join(unknown))}",
            f"executed_at: {yaml_value(timestamp)}",
            "",
        ]
    )
    atomic_write(receipt_path, receipt)
    return {
        "schema_version": 1,
        "status": "migrated",
        "change_id": change_id,
        "target": target.relative_to(project).as_posix(),
        "receipt": receipt_path.relative_to(project).as_posix(),
        "legacy_preserved": True,
        "unmapped_fields": unknown,
    }


class MigrationBlocked(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="legacy-state")
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("audit", "migrate"):
        command = subparsers.add_parser(action)
        command.add_argument("--project", default=".")
        command.add_argument("--json", action="store_true")
        if action == "migrate":
            command.add_argument("--change", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project = pathlib.Path(args.project).expanduser().resolve()
    if not project.is_dir():
        print("Project path must be an existing directory.", file=sys.stderr)
        return 2
    try:
        result = audit(project) if args.action == "audit" else migrate(project, args.change)
    except MigrationBlocked as exc:
        payload = {"schema_version": 1, "status": "blocked", "reason": str(exc)}
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    else:
        print(f"Legacy state {args.action}: {result['status']}")
        if args.action == "audit":
            for item in result["changes"]:
                print(f"- {item['change_id']}: {item['ambiguity']}, receipt={item['receipt_status']}, next={item['next_action']}")
        else:
            print(f"Change: {result['change_id']}")
            print(f"Target: {result['target']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
