#!/usr/bin/env python3
"""Deterministic behavior guard for the Reviewer–Executor Loop Contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


BRIEF_SECTIONS = ["执行上下文", "本轮目标", "任务范围", "权限", "硬约束", "阻断边界", "交付证据"]
REPORT_SECTIONS = ["完成结果", "根因与设计选择", "改动范围", "验证证据", "剩余风险", "待用户批准事项"]
HOST_NAMES = ("claude-code", "claude code", "codex", "workbuddy")
SOURCE_BODY_RE = re.compile(
    r"^#{1,6}\s+(Why|What Changes|Capabilities|Context|Decisions|ADDED Requirements|MODIFIED Requirements|Spec Compliance Report|Guardrail 承接|启动指引)\s*$",
    re.I | re.M,
)
COMMAND_RE = re.compile(r"`[^`]*(?:bash|pytest|python|npm|pnpm|yarn|go test|cargo test|mvn|gradle|openspec|zimaflow)[^`]*`", re.I)
STOP_RE = re.compile(r"停在\s*`?(review|archive|push|release|评审|归档|推送|发布)`?\s*前", re.I)
ATX_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$", re.M)
CHANGE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
ROUND_ID_RE = re.compile(r"^round-([0-9]+)$")
CAPABILITY_SEGMENT_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?$")
PROFILE = "reviewer_executor"
ACTIVE_PHASES = {"planned", "executing", "checkpoint", "review_ready", "changes_requested", "blocked"}
BLOCKER_ALLOWED_RE = re.compile(
    r"未裁决|产品决策|权限(?:扩大|不足)|目录(?:扩大|越界)|不可逆|覆盖用户改动|外部(?:凭据|credential)|"
    r"规范冲突|spec(?:ification)? conflict|unresolved product decision|permission expansion|directory expansion|"
    r"irreversible|overwrite user changes|external credential",
    re.I,
)
COLLABORATION_DEFAULTS = {
    "profile": "none",
    "objective_id": "",
    "round_id": "",
    "phase": "",
    "loop_events": "",
    "boundary_matrix": "",
    "latest_report": "",
    "latest_receipts": "[]",
    "termination": "",
    "event_head": "",
}
COLLABORATION_MANIFEST_KEYS = ("objective_plan", "subject_manifest")


def item(code: str, message: str, section: str | None = None) -> dict[str, str]:
    result = {"code": code, "message": message}
    if section:
        result["section"] = section
    return result


def parse_sections(text: str, expected: list[str]) -> tuple[dict[str, str], list[str], list[dict[str, str]]]:
    bodies: dict[str, list[str]] = {}
    order: list[str] = []
    current: str | None = None
    violations: list[dict[str, str]] = []
    unexpected_content_reported = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = ATX_HEADING_RE.match(line.strip())
        if match:
            level = len(match.group(1))
            name = match.group(2).strip().rstrip("#").rstrip()
            if name not in expected:
                violations.append(item("unexpected_section", f"契约外区块：{name}"))
                current = None
                continue
            if level != 2:
                violations.append(item("invalid_section_heading", f"区块必须使用二级标题：{name}", name))
                current = None
                continue
            if name in bodies:
                violations.append(item("duplicate_section", f"重复区块：{name}", name))
                current = None
            else:
                bodies[name] = []
                order.append(name)
                current = name
        elif current:
            bodies[current].append(line.rstrip())
        elif line.strip() and not unexpected_content_reported:
            violations.append(item("unexpected_content", f"第 {line_number} 行内容不属于契约区块"))
            unexpected_content_reported = True
    for name in expected:
        if name not in bodies:
            violations.append(item("missing_section", f"缺少区块：{name}", name))
    if len(bodies) == len(expected) and order != expected:
        violations.append(item("section_order", "区块顺序不符合契约"))
    return {name: "\n".join(lines).strip() for name, lines in bodies.items()}, order, violations


def cjk_count(text: str) -> int:
    return len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", text))


def labeled_value(body: str, label: str) -> str | None:
    pattern = re.compile(r"^\s*[-*+]\s*" + re.escape(label) + r"\s*[：:]\s*(.*?)\s*$")
    for line in body.splitlines():
        match = pattern.match(line)
        if match:
            value = match.group(1).strip()
            if len(value) >= 2 and value[0] == value[-1] == "`":
                value = value[1:-1]
            return value
    return None


def normalized_absolute_path(value: str) -> bool:
    return Path(value).is_absolute() and value != "/" and os.path.normpath(value) == value


def compact_text(value: str) -> str:
    value = re.sub(r"^\s*(?:#{1,6}|[-*+])\s*", "", value, flags=re.M)
    return re.sub(r"\s+", "", value)


def validate_source_boundaries(text: str, source_files: list[str]) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    compact_target = compact_text(text)
    for source_path in source_files:
        if not normalized_absolute_path(source_path):
            violations.append(item("source_file_not_absolute", f"--source-file 必须是规范化绝对路径：{source_path}"))
            continue
        source_text, read_violations = read_text(source_path)
        if read_violations:
            violations.append(item("source_input_unreadable", f"无法读取项目真源：{source_path}"))
            continue
        candidates = (source_text or "").splitlines()
        for candidate in candidates:
            compact_candidate = compact_text(candidate)
            if (cjk_count(compact_candidate) >= 24 or len(compact_candidate) >= 48) and compact_candidate in compact_target:
                violations.append(item("project_truth_body_copied", f"通信正文复制了项目真源内容：{source_path}"))
                break
    return violations


def read_text(path: str) -> tuple[str | None, list[dict[str, str]]]:
    try:
        return Path(path).read_text(encoding="utf-8"), []
    except OSError as exc:
        return None, [item("input_unreadable", str(exc))]


def clean_yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def yaml_top_value(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.*?)\s*$", text, re.M)
    return clean_yaml_scalar(match.group(1)) if match else ""


def yaml_nested_values(text: str, section: str) -> dict[str, str]:
    lines = text.splitlines()
    values: dict[str, str] = {}
    active = False
    for line in lines:
        if line == f"{section}:":
            active = True
            continue
        if active and line and not line[0].isspace():
            break
        if active:
            match = re.match(r"^  ([A-Za-z0-9_]+):\s*(.*?)\s*$", line)
            if match:
                values[match.group(1)] = clean_yaml_scalar(match.group(2))
    return values


def git_output(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return result.stdout.strip()


def git_paths(root: Path, *args: str) -> set[str]:
    output = git_output(root, *args)
    return {line for line in output.splitlines() if line}


def non_evidence_dirty_paths(root: Path, change: str) -> list[str]:
    dirty = (
        git_paths(root, "diff", "--name-only")
        | git_paths(root, "diff", "--cached", "--name-only")
        | git_paths(root, "ls-files", "--others", "--exclude-standard")
    )
    state = f"openspec/changes/{change}/.zimaflow-state.yaml"
    validation = f"openspec/changes/{change}/validation/reviewer-executor/"
    return sorted(path for path in dirty if path != state and not path.startswith(validation))


def stable_spec_id(value: str) -> str:
    normalized = unicodedata.normalize("NFC", unicodedata.normalize("NFC", value).lower())
    identity: list[str] = []
    separator_pending = False
    for character in normalized:
        if unicodedata.category(character)[:1] in {"L", "N"}:
            if separator_pending and identity:
                identity.append("-")
            identity.append(character)
            separator_pending = False
        elif identity:
            separator_pending = True
    return "".join(identity)


def canonical_delta_spec_candidates(root: Path, change: str) -> list[tuple[str, Path]]:
    specs_root = change_root(root, change) / "specs"
    if not specs_root.is_dir():
        raise ValueError("delta_specs_missing")
    if specs_root.is_symlink():
        raise ValueError("delta_spec_symlink_forbidden")
    resolved_root = specs_root.resolve()
    candidates: list[tuple[str, Path]] = []
    discovered: list[Path] = []
    for current, dirnames, filenames in os.walk(specs_root, followlinks=False):
        current_path = Path(current)
        if any((current_path / dirname).is_symlink() for dirname in dirnames):
            raise ValueError("delta_spec_symlink_forbidden")
        if "spec.md" in filenames:
            discovered.append(current_path / "spec.md")
    for path in discovered:
        relative = path.relative_to(specs_root)
        capability_parts = relative.parent.parts
        if not capability_parts:
            raise ValueError("delta_spec_path_invalid")
        if path.is_symlink() or any(
            specs_root.joinpath(*capability_parts[:index]).is_symlink()
            for index in range(1, len(capability_parts) + 1)
        ):
            raise ValueError("delta_spec_symlink_forbidden")
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            raise ValueError("delta_spec_path_invalid") from exc
        if resolved_root not in resolved.parents:
            raise ValueError("delta_spec_path_outside_root")
        if not path.is_file():
            raise ValueError("delta_spec_path_invalid")
        if any(
            unicodedata.normalize("NFC", segment) != segment
            or not segment.isascii()
            or not CAPABILITY_SEGMENT_RE.fullmatch(segment)
            or len(segment.encode("utf-8")) > 64
            for segment in capability_parts
        ):
            raise ValueError("delta_spec_capability_id_invalid")
        capability_id = "/".join(capability_parts)
        if len(capability_id.encode("utf-8")) > 255:
            raise ValueError("delta_spec_capability_id_invalid")
        candidates.append((capability_id, path))
    return sorted(
        candidates,
        key=lambda entry: (
            entry[0].encode("utf-8"),
            entry[1].relative_to(root).as_posix().encode("utf-8"),
        ),
    )


def required_spec_pairs(root: Path, change: str) -> dict[tuple[str, str, str], str]:
    pairs: dict[tuple[str, str, str], str] = {}
    for capability_id, path in canonical_delta_spec_candidates(root, change):
        requirement = ""
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = re.match(r"^### Requirement:\s*(.+?)\s*$", line)
            if match:
                requirement = stable_spec_id(match.group(1))
                if not requirement:
                    raise ValueError(
                        f"delta_spec_identity_invalid:{path.relative_to(root)}:{line_number}"
                    )
                continue
            match = re.match(r"^#### Scenario:\s*(.+?)\s*$", line)
            if not match:
                continue
            if not requirement:
                raise ValueError(f"delta_spec_invalid:{path.relative_to(root)}:{line_number}")
            scenario = stable_spec_id(match.group(1))
            if not scenario:
                raise ValueError(
                    f"delta_spec_identity_invalid:{path.relative_to(root)}:{line_number}"
                )
            pair = (capability_id, requirement, scenario)
            if pair in pairs:
                raise ValueError(f"delta_spec_id_collision:{pair[0]}:{pair[1]}:{pair[2]}")
            pairs[pair] = f"repo://{path.relative_to(root)}#{line_number}"
    if not pairs:
        raise ValueError("delta_specs_empty")
    return pairs


def has_namespaced_spec_pairs(pairs: object) -> bool:
    return any(
        isinstance(pair, tuple) and len(pair) == 3 and "/" in str(pair[0])
        for pair in pairs
    )


def boundary_matrix_version(top: dict[str, str]) -> int:
    raw = top.get("schema_version", "")
    if raw not in {"1", "2"}:
        raise ValueError("verification_subject_version_unsupported")
    normalization = top.get("normalization_version", "")
    if raw == "1" and normalization not in {"", "1"}:
        raise ValueError("verification_subject_version_unsupported")
    if raw == "2" and normalization != "2":
        raise ValueError("verification_subject_version_unsupported")
    return int(raw)


def matrix_schema_current_violations(
    root: Path, change: str, collaboration: dict[str, str]
) -> list[dict[str, str]]:
    try:
        required_pairs = required_spec_pairs(root, change)
        if not has_namespaced_spec_pairs(required_pairs):
            return []
        top, _ = parse_boundary_matrix(
            logical_repo_path(root, collaboration.get("boundary_matrix", ""), must_exist=True)
        )
        version = boundary_matrix_version(top)
    except (ValueError, FileNotFoundError, OSError) as exc:
        return [item(str(exc), "boundary matrix schema current-validity 无法重算")]
    if version == 1:
        return [item(
            "verification_subject_schema_upgrade_required",
            "namespaced/mixed Change 必须使用 boundary matrix schema/normalization v2",
        )]
    return []


def resolve_matrix_row_identity(
    version: int,
    row: dict[str, str],
    required_pairs: object,
) -> tuple[str, ...]:
    requirement_id = row.get("requirement_id", "")
    scenario_id = row.get("scenario_id", "")
    capability_id = row.get("capability_id", "")
    if requirement_id == "@composition":
        identity = (requirement_id, scenario_id)
        if capability_id:
            raise ValueError("boundary_matrix_invalid")
        if identity not in required_pairs:
            raise ValueError("spec_mapping_unknown")
        return identity
    candidates = sorted(
        pair
        for pair in required_pairs
        if isinstance(pair, tuple)
        and len(pair) == 3
        and pair[1:] == (requirement_id, scenario_id)
    )
    if version == 1:
        if capability_id:
            raise ValueError("boundary_matrix_invalid")
        if any("/" in pair[0] for pair in candidates):
            raise ValueError("verification_subject_schema_upgrade_required")
        if len(candidates) != 1:
            raise ValueError("spec_mapping_ambiguous" if len(candidates) > 1 else "spec_mapping_unknown")
        return candidates[0]
    if version != 2:
        raise ValueError("verification_subject_version_unsupported")
    if not capability_id:
        raise ValueError("spec_mapping_incomplete")
    identity = (capability_id, requirement_id, scenario_id)
    if identity not in required_pairs:
        raise ValueError("spec_mapping_unknown")
    return identity


def repo_links(text: str) -> set[str]:
    return set(re.findall(r"repo://[A-Za-z0-9._/@%+~:-]+", text))


def current_git_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return Path(result.stdout.strip()).resolve()


def change_root(root: Path, change: str) -> Path:
    if not CHANGE_ID_RE.fullmatch(change):
        raise ValueError("invalid_change_id")
    active = root / "openspec" / "changes" / change
    if active.is_dir():
        return active
    archive_root = root / "openspec" / "changes" / "archive"
    matches = sorted(
        candidate for candidate in archive_root.glob(f"*-{change}")
        if candidate.is_dir() and candidate.name.endswith("-" + change)
    ) if archive_root.is_dir() else []
    if len(matches) > 1:
        raise ValueError("archive_state_ambiguous")
    return matches[0] if matches else active


def state_path(root: Path, change: str) -> Path:
    return change_root(root, change) / ".zimaflow-state.yaml"


def validation_root_for(root: Path, change: str) -> Path:
    return (change_root(root, change) / "validation" / "reviewer-executor").resolve()


def logical_repo_path(root: Path, value: str, *, must_exist: bool = False) -> Path:
    if not value.startswith("repo://"):
        raise ValueError("artifact_path_not_logical")
    relative = value[len("repo://") :]
    if not relative or relative.startswith("/") or any(part in ("", ".", "..") for part in Path(relative).parts):
        raise ValueError("artifact_path_invalid")
    resolved = (root / relative).resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError("artifact_path_outside_repository")
    if not resolved.exists():
        parts = Path(relative).parts
        if len(parts) >= 4 and parts[:2] == ("openspec", "changes") and parts[2] != "archive":
            archived_root = change_root(root, parts[2])
            if archived_root != root / "openspec" / "changes" / parts[2]:
                archived_candidate = archived_root.joinpath(*parts[3:]).resolve()
                if archived_candidate == root or root in archived_candidate.parents:
                    resolved = archived_candidate
    if must_exist and not resolved.is_file():
        raise FileNotFoundError(value)
    return resolved


def load_loop_context(change: str) -> tuple[Path, Path, str, dict[str, str]]:
    root = current_git_root()
    path = state_path(root, change)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    text = path.read_text(encoding="utf-8")
    collaboration = dict(COLLABORATION_DEFAULTS)
    collaboration.update(yaml_nested_values(text, "collaboration"))
    return root, path, text, collaboration


def render_collaboration(values: dict[str, str]) -> str:
    def line(key: str) -> str:
        value = values.get(key, COLLABORATION_DEFAULTS.get(key, ""))
        return f"  {key}: {value}" if value else f"  {key}:"

    keys = list(COLLABORATION_DEFAULTS)
    keys.extend(key for key in COLLABORATION_MANIFEST_KEYS if values.get(key))
    return "\n".join(
        ["collaboration:"]
        + [line(key) for key in keys]
    )


def write_collaboration(path: Path, text: str, values: dict[str, str], *, updated_at: str | None = None) -> None:
    block = render_collaboration(values)
    pattern = re.compile(r"^collaboration:\n(?:^[ \t].*\n?)*", re.M)
    if pattern.search(text):
        updated = pattern.sub(block + "\n", text, count=1)
    else:
        marker = "\nartifact_hashes:\n"
        if marker in text:
            updated = text.replace(marker, f"\n{block}\n{marker}", 1)
        else:
            updated = text.rstrip() + f"\n\n{block}\n"
    updated = re.sub(
        r"^updated_at:\s*.*$",
        f"updated_at: {updated_at or now_iso()}",
        updated,
        count=1,
        flags=re.M,
    )
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(updated, encoding="utf-8")
    os.chmod(temp, 0o644)
    os.replace(temp, path)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_events(root: Path, collaboration: dict[str, str]) -> list[dict]:
    reference = collaboration.get("loop_events", "")
    if not reference:
        return []
    path = logical_repo_path(root, reference)
    if not path.exists():
        return []
    events: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"event_log_invalid:{line_number}:{exc.msg}") from exc
        if not isinstance(event, dict):
            raise ValueError(f"event_log_invalid:{line_number}:not_object")
        events.append(event)
    return events


def append_event(root: Path, collaboration: dict[str, str], event_type: str, **fields: object) -> dict:
    reference = collaboration.get("loop_events", "")
    path = logical_repo_path(root, reference)
    expected_parent = validation_root_for(root, str(fields["change_id"]))
    if path != expected_parent.resolve() and expected_parent.resolve() not in path.parents:
        raise ValueError("event_log_outside_validation_root")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("event_log_not_regular_file")
    existing = read_events(root, collaboration)
    event_timestamp = str(fields.pop("_event_timestamp", now_iso()))
    event = {
        "schema_version": 1,
        "event_id": f"{event_type}-{len(existing) + 1:04d}",
        "event_type": event_type,
        "timestamp": event_timestamp,
        **fields,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return event


def collaboration_event_state(collaboration: dict[str, str]) -> dict[str, str]:
    state = {
        key: collaboration.get(key, COLLABORATION_DEFAULTS[key])
        for key in COLLABORATION_DEFAULTS
        if key != "event_head"
    }
    state.update({key: collaboration[key] for key in COLLABORATION_MANIFEST_KEYS if collaboration.get(key)})
    return state


def commit_state_event(
    root: Path,
    path: Path,
    text: str,
    collaboration: dict[str, str],
    event_type: str,
    **fields: object,
) -> dict:
    event = append_event(
        root,
        collaboration,
        event_type,
        previous_event_id=collaboration.get("event_head", ""),
        state_after=collaboration_event_state(collaboration),
        **fields,
    )
    collaboration["event_head"] = str(event["event_id"])
    write_collaboration(path, text, collaboration, updated_at=str(event["timestamp"]))
    return event


EVENT_PHASES = {
    "objective_planned": "planned",
    "round_started": "executing",
    "checkpointed": "checkpoint",
    "blocked": "blocked",
    "objective_resumed": "executing",
    "review_ready_passed": "review_ready",
    "changes_requested": "executing",
    "accepted": "accepted",
}


def event_matches_summary(event: dict, collaboration: dict[str, str]) -> bool:
    if event.get("objective_id") != collaboration.get("objective_id"):
        return False
    if event.get("round_id") != collaboration.get("round_id"):
        return False
    state_after = event.get("state_after")
    if isinstance(state_after, dict):
        base_matches = all(
            str(state_after.get(key, "")) == collaboration.get(key, COLLABORATION_DEFAULTS[key])
            for key in COLLABORATION_DEFAULTS
            if key != "event_head"
        )
        manifest_matches = all(
            str(state_after.get(key, "")) == collaboration.get(key, "")
            for key in COLLABORATION_MANIFEST_KEYS
            if key in state_after or collaboration.get(key)
        )
        return base_matches and manifest_matches
    return EVENT_PHASES.get(str(event.get("event_type"))) == collaboration.get("phase")


def reconcile_history(
    root: Path, path: Path, text: str, collaboration: dict[str, str]
) -> tuple[str, dict[str, str], bool]:
    if collaboration.get("profile") != PROFILE:
        return text, collaboration, False
    events = read_events(root, collaboration)
    if not events:
        raise ValueError("lifecycle_history_missing")
    head = collaboration.get("event_head", "")
    if not head:
        tail = events[-1]
        if not event_matches_summary(tail, collaboration):
            raise ValueError("lifecycle_history_diverged")
        collaboration["event_head"] = str(tail.get("event_id", ""))
        if not collaboration["event_head"]:
            raise ValueError("lifecycle_history_diverged")
        write_collaboration(path, text, collaboration, updated_at=str(tail.get("timestamp") or now_iso()))
        return path.read_text(encoding="utf-8"), collaboration, True

    head_indexes = [index for index, event in enumerate(events) if event.get("event_id") == head]
    if len(head_indexes) != 1:
        raise ValueError("lifecycle_history_diverged")
    head_index = head_indexes[0]
    if head_index == len(events) - 1:
        if not event_matches_summary(events[-1], collaboration):
            raise ValueError("lifecycle_history_diverged")
        return text, collaboration, False
    if head_index != len(events) - 2:
        raise ValueError("lifecycle_history_diverged")
    pending = events[-1]
    state_after = pending.get("state_after")
    if pending.get("previous_event_id") != head or not isinstance(state_after, dict):
        raise ValueError("lifecycle_history_diverged")
    if pending.get("objective_id") != collaboration.get("objective_id"):
        raise ValueError("lifecycle_history_diverged")
    for key in COLLABORATION_DEFAULTS:
        if key != "event_head":
            collaboration[key] = str(state_after.get(key, COLLABORATION_DEFAULTS[key]))
    for key in COLLABORATION_MANIFEST_KEYS:
        if key in state_after:
            collaboration[key] = str(state_after[key])
    collaboration["event_head"] = str(pending.get("event_id", ""))
    if not collaboration["event_head"] or not event_matches_summary(pending, collaboration):
        raise ValueError("lifecycle_history_diverged")
    write_collaboration(path, text, collaboration, updated_at=str(pending.get("timestamp") or now_iso()))
    return path.read_text(encoding="utf-8"), collaboration, True


def violation_result(command: str, code: str, message: str, **extra: object) -> tuple[dict, int]:
    return build_result(command, None, [item(code, message)], **extra), 1


def context_or_error(
    command: str, change: str, *, recover_history: bool = False
) -> tuple[tuple[Path, Path, str, dict[str, str]] | None, tuple[dict, int] | None]:
    try:
        root, path, text, collaboration = load_loop_context(change)
        if "archive" in path.relative_to(root / "openspec" / "changes").parts and command not in {
            "subject-digest", "receipt-check", "coverage-check"
        }:
            return None, violation_result(command, "change_archived", "归档 Change 只允许执行只读 coverage 重算")
        recovered = False
        if recover_history:
            text, collaboration, recovered = reconcile_history(root, path, text, collaboration)
        collaboration["_history_recovered"] = "true" if recovered else "false"
        return (root, path, text, collaboration), None
    except ValueError as exc:
        return None, violation_result(command, str(exc), "Change 或状态路径无效")
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        return None, violation_result(command, "state_not_found", f"无法加载 Change state：{exc}")


def load_json_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("verification_subject_manifest_invalid") from exc
    if not isinstance(value, dict):
        raise ValueError("verification_subject_manifest_invalid")
    return value


def load_strict_json_object(path: Path, reason: str) -> dict:
    def reject_duplicate(pairs: list[tuple[str, object]]) -> dict:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(reason)
            result[key] = value
        return result

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(reason) from exc
    if not isinstance(value, dict):
        raise ValueError(reason)
    return value


def normalized_rfc3339_utc(value: object) -> tuple[datetime, str]:
    if not isinstance(value, str) or not value or re.search(r":60(?:[.,]|Z|[+-])", value):
        raise ValueError("resume_authorization_invalid")
    fraction = re.search(r"[.,]([0-9]+)(?=Z|[+-][0-9]{2}:[0-9]{2}$)", value)
    if fraction and len(fraction.group(1)) > 6:
        raise ValueError("resume_authorization_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("resume_authorization_invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("resume_authorization_invalid")
    normalized = parsed.astimezone(timezone.utc)
    return normalized, normalized.isoformat(timespec="microseconds").replace("+00:00", "Z")


def blocked_authorization_identity(blocked_event: dict) -> tuple[dict[str, object], str]:
    required_decision = str(blocked_event.get("required_decision") or blocked_event.get("blocker") or "")
    if not required_decision:
        raise ValueError("resume_authorization_invalid")
    required_hash = hashlib.sha256(required_decision.encode("utf-8")).hexdigest()
    if blocked_event.get("blocker_category") and blocked_event.get("blocker_code"):
        return {
            "blocker_category": blocked_event["blocker_category"],
            "blocker_code": blocked_event["blocker_code"],
            "required_decision_sha256": required_hash,
        }, required_hash
    blocker = str(blocked_event.get("blocker") or "")
    if not blocker:
        raise ValueError("resume_authorization_invalid")
    return {
        "blocker_text_sha256": hashlib.sha256(blocker.encode("utf-8")).hexdigest(),
        "required_decision_sha256": required_hash,
    }, required_hash


def validate_resume_authorization(
    root: Path,
    change: str,
    collaboration: dict[str, str],
    blocked_event: dict,
    authorization_reference: str,
    resume_timestamp: str,
) -> dict:
    validation_root = validation_root_for(root, change)
    try:
        envelope_path = logical_repo_path(root, authorization_reference, must_exist=True)
    except (ValueError, FileNotFoundError) as exc:
        raise ValueError("resume_authorization_missing") from exc
    if validation_root != envelope_path and validation_root not in envelope_path.parents:
        raise ValueError("resume_authorization_invalid")
    envelope = load_strict_json_object(envelope_path, "resume_authorization_invalid")
    identity, _ = blocked_authorization_identity(blocked_event)
    common_envelope = {
        "schema_version", "kind", "change_id", "objective_id", "round_id", "blocked_event_id",
        "approval_evidence", "approval_evidence_sha256", "created_at", *identity.keys(),
    }
    if set(envelope) != common_envelope:
        raise ValueError("resume_authorization_invalid")
    if envelope.get("schema_version") != 1 or envelope.get("kind") != "blocked_objective_resume_authorization":
        raise ValueError("resume_authorization_invalid")
    expected_common = {
        "change_id": change,
        "objective_id": collaboration.get("objective_id"),
        "round_id": collaboration.get("round_id"),
    }
    if any(envelope.get(key) != value for key, value in expected_common.items()):
        raise ValueError("resume_identity_mismatch")
    if envelope.get("blocked_event_id") != blocked_event.get("event_id"):
        raise ValueError("resume_blocked_event_stale")
    if any(envelope.get(key) != value for key, value in identity.items()):
        raise ValueError("resume_authorization_invalid")
    approval_reference = envelope.get("approval_evidence")
    if not isinstance(approval_reference, str):
        raise ValueError("resume_authorization_invalid")
    try:
        approval_path = logical_repo_path(root, approval_reference, must_exist=True)
    except (ValueError, FileNotFoundError) as exc:
        raise ValueError("resume_authorization_missing") from exc
    if validation_root != approval_path and validation_root not in approval_path.parents:
        raise ValueError("resume_authorization_invalid")
    approval_hash = sha256_file(approval_path)
    if envelope.get("approval_evidence_sha256") != approval_hash:
        raise ValueError("resume_authorization_invalid")
    approval = load_strict_json_object(approval_path, "resume_authorization_invalid")
    approval_keys = {
        "schema_version", "decision", "approved", "change_id", "objective_id", "round_id",
        "blocked_event_id", "approved_scope", "approval_authority", "approved_at", *identity.keys(),
    }
    if set(approval) != approval_keys:
        raise ValueError("resume_authorization_invalid")
    if approval.get("schema_version") != 1 or approval.get("decision") != "approve_blocked_objective_resume" or approval.get("approved") is not True:
        raise ValueError("resume_authorization_invalid")
    if any(approval.get(key) != value for key, value in expected_common.items()):
        raise ValueError("resume_identity_mismatch")
    if approval.get("blocked_event_id") != blocked_event.get("event_id"):
        raise ValueError("resume_blocked_event_stale")
    if any(approval.get(key) != value for key, value in identity.items()):
        raise ValueError("resume_authorization_invalid")
    scope = approval.get("approved_scope")
    authority = approval.get("approval_authority")
    if (
        not isinstance(scope, list)
        or not scope
        or not all(isinstance(entry, str) and entry.strip() for entry in scope)
        or not isinstance(authority, dict)
        or set(authority) != {"kind", "authority_id"}
        or authority.get("kind") not in {"user", "reviewer"}
        or not isinstance(authority.get("authority_id"), str)
        or not authority["authority_id"].strip()
        or authority.get("authority_id") == "executor"
    ):
        raise ValueError("resume_authorization_invalid")
    blocked_at, _ = normalized_rfc3339_utc(blocked_event.get("timestamp"))
    approved_at, approved_at_text = normalized_rfc3339_utc(approval.get("approved_at"))
    created_at, created_at_text = normalized_rfc3339_utc(envelope.get("created_at"))
    resume_at, resume_at_text = normalized_rfc3339_utc(resume_timestamp)
    if not blocked_at < approved_at <= created_at <= resume_at:
        raise ValueError("resume_authorization_invalid")
    return {
        "authorization": authorization_reference,
        "authorization_sha256": sha256_file(envelope_path),
        "approval_evidence": approval_reference,
        "approval_evidence_sha256": approval_hash,
        "approval_authority": authority,
        "approved_at": approved_at_text,
        "authorization_created_at": created_at_text,
        "resume_at": resume_at_text,
        "blocked_event_id": str(blocked_event["event_id"]),
        **identity,
    }


def authorization_obligations(events: list[dict], objective_id: str | None = None) -> list[dict]:
    keys = (
        "authorization", "authorization_sha256", "approval_evidence", "approval_evidence_sha256",
        "approval_authority", "approved_at", "authorization_created_at", "resume_at",
        "blocked_event_id", "blocker_category", "blocker_code", "blocker_text_sha256",
        "required_decision_sha256",
    )
    return [
        {key: event[key] for key in keys if key in event}
        for event in events
        if event.get("event_type") == "objective_resumed"
        and (objective_id is None or event.get("objective_id") == objective_id)
    ]


def authorization_current_violations(
    root: Path, events: list[dict], objective_id: str | None = None
) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    event_by_id = {str(event.get("event_id")): event for event in events}
    for resumed in (
        event for event in events
        if event.get("event_type") == "objective_resumed"
        and (objective_id is None or event.get("objective_id") == objective_id)
    ):
        references = (
            ("authorization", "authorization_sha256"),
            ("approval_evidence", "approval_evidence_sha256"),
        )
        paths: list[Path] = []
        missing = False
        changed = False
        for reference_key, hash_key in references:
            reference = resumed.get(reference_key)
            try:
                path = logical_repo_path(root, str(reference), must_exist=True)
            except (ValueError, FileNotFoundError):
                missing = True
                continue
            paths.append(path)
            if sha256_file(path) != resumed.get(hash_key):
                changed = True
        if missing:
            violations.append(item("resume_authorization_evidence_missing", "resume authorization artifact 不可解析"))
            continue
        if changed:
            violations.append(item("resume_authorization_evidence_changed", "resume authorization artifact bytes 已改变"))
            continue
        untracked = [
            path.relative_to(root).as_posix()
            for path in paths
            if subprocess.run(
                ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", path.relative_to(root).as_posix()],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode != 0
        ]
        if untracked:
            violations.append(item(
                "resume_authorization_evidence_untracked",
                "resume authorization artifact 未进入 Git truth：" + ", ".join(untracked),
            ))
            continue
        blocked = event_by_id.get(str(resumed.get("blocked_event_id")))
        if not blocked or blocked.get("event_type") != "blocked":
            violations.append(item("resume_authorization_identity_mismatch", "resume blocked event identity 不可重算"))
            continue
        collaboration = {
            "objective_id": str(resumed.get("objective_id", "")),
            "round_id": str(resumed.get("round_id", "")),
            "event_head": str(blocked.get("event_id", "")),
        }
        try:
            current = validate_resume_authorization(
                root,
                str(resumed.get("change_id", "")),
                collaboration,
                blocked,
                str(resumed.get("authorization", "")),
                str(resumed.get("resume_at", "")),
            )
        except ValueError:
            violations.append(item("resume_authorization_identity_mismatch", "resume authorization identity/timing 已改变"))
            continue
        frozen = authorization_obligations([resumed])[0]
        if any(current.get(key) != value for key, value in frozen.items()):
            violations.append(item("resume_authorization_identity_mismatch", "resume authorization frozen identity 不匹配"))
    return violations


def normalize_semantic_text(value: str) -> str:
    return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))


def canonical_content_hash(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError("verification_subject_manifest_invalid") from exc
    return hashlib.sha256(normalize_semantic_text(text).encode("utf-8")).hexdigest()


def normalized_repo_reference(root: Path, value: object, *, must_exist: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError("verification_subject_manifest_invalid")
    logical_repo_path(root, value, must_exist=must_exist)
    return "repo://" + Path(value[len("repo://") :]).as_posix()


def parse_required_tasks(root: Path, state_text: str) -> dict[str, dict[str, object]]:
    tasks_reference = yaml_nested_values(state_text, "openspec").get("tasks_path", "")
    try:
        tasks_path = (
            logical_repo_path(root, tasks_reference, must_exist=True)
            if tasks_reference.startswith("repo://")
            else logical_repo_path(root, "repo://" + tasks_reference, must_exist=True)
        )
        text = normalize_semantic_text(tasks_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, FileNotFoundError) as exc:
        raise ValueError("verification_subject_mapping_mismatch") from exc
    tasks: dict[str, dict[str, object]] = {}
    current_id = ""
    current_lines: list[str] = []

    def finish_current() -> None:
        nonlocal current_id, current_lines
        if current_id:
            tasks[current_id]["content"] = normalize_semantic_text("\n".join(current_lines).rstrip())
        current_id = ""
        current_lines = []

    for line in text.splitlines():
        match = re.match(r"^[ \t]*- \[([ xX])\][ \t]+([0-9]+(?:\.[0-9]+)*)[ \t]+(.+?)[ \t]*$", line)
        if match:
            finish_current()
            task_id = match.group(2)
            if task_id in tasks:
                raise ValueError("objective_task_mapping_duplicate")
            tasks[task_id] = {
                "task_id": task_id,
                "content": "",
                "completed": match.group(1).lower() == "x",
            }
            current_id = task_id
            current_lines = [match.group(3)]
        elif current_id and re.match(r"^[ \t]*#{1,6}[ \t]+", line):
            finish_current()
        elif current_id:
            current_lines.append(line)
    finish_current()
    return tasks


def required_task_semantics(root: Path, state_text: str, required_task_ids: list[str]) -> list[dict[str, str]]:
    tasks = parse_required_tasks(root, state_text)
    normalized_ids = sorted({normalize_semantic_text(value) for value in required_task_ids})
    if len(normalized_ids) != len(required_task_ids) or any(task_id not in tasks for task_id in normalized_ids):
        raise ValueError("verification_subject_mapping_mismatch")
    return [{"task_id": task_id, "content": str(tasks[task_id]["content"])} for task_id in normalized_ids]


def validate_objective_plan(root: Path, state_text: str, change: str, plan: dict) -> tuple[list[dict], dict[str, dict[str, object]]]:
    objectives = plan.get("required_objectives")
    if plan.get("schema_version") != 1 or plan.get("change_id") != change or not isinstance(objectives, list) or not objectives:
        raise ValueError("verification_subject_manifest_invalid")
    allowed_plan_keys = {"schema_version", "change_id", "required_objectives", "metadata"}
    allowed_objective_keys = {
        "objective_id", "order", "purpose", "required", "required_task_ids", "manifest", "remediates", "metadata"
    }
    if set(plan) - allowed_plan_keys:
        raise ValueError("verification_subject_manifest_invalid")
    tasks = parse_required_tasks(root, state_text)
    objective_ids: set[str] = set()
    orders: set[int] = set()
    owners: dict[str, list[str]] = {}
    normalized: list[dict] = []
    for objective in objectives:
        if not isinstance(objective, dict) or set(objective) - allowed_objective_keys:
            raise ValueError("verification_subject_manifest_invalid")
        objective_id = objective.get("objective_id")
        order = objective.get("order")
        task_ids = objective.get("required_task_ids")
        if (
            not isinstance(objective_id, str) or not objective_id or objective_id in objective_ids
            or not isinstance(order, int) or order < 1 or order in orders
            or objective.get("required") is not True
            or not isinstance(objective.get("purpose"), str) or not objective.get("purpose")
            or not isinstance(objective.get("manifest"), str)
            or not isinstance(task_ids, list) or not task_ids
            or not all(isinstance(task_id, str) and task_id for task_id in task_ids)
        ):
            raise ValueError("verification_subject_manifest_invalid")
        objective_ids.add(objective_id)
        orders.add(order)
        if len(set(task_ids)) != len(task_ids):
            raise ValueError("objective_task_mapping_duplicate")
        for task_id in task_ids:
            if task_id not in tasks:
                raise ValueError("objective_task_mapping_unknown")
            owners.setdefault(task_id, []).append(objective_id)
        remediates = objective.get("remediates", [])
        if not isinstance(remediates, list) or not all(isinstance(value, str) and value for value in remediates):
            raise ValueError("verification_subject_manifest_invalid")
        normalized.append(objective)
    if orders != set(range(1, len(normalized) + 1)):
        raise ValueError("verification_subject_manifest_invalid")
    if any(len(values) > 1 for values in owners.values()):
        raise ValueError("objective_task_mapping_duplicate")
    if set(owners) != set(tasks):
        raise ValueError("objective_task_mapping_incomplete")
    return sorted(normalized, key=lambda entry: entry["order"]), tasks


SET_ARRAY_KEYS = {
    "allowed_hosts",
    "allowed_isolation",
    "refs",
    "required_evidence",
    "required_task_ids",
    "requirement_ids",
    "scenario_ids",
    "spec_pairs",
    "subject_ids",
}


def projection_obligation_pairs(projection: dict) -> set[tuple[str, ...]]:
    version = (projection.get("schema_version"), projection.get("normalization_version"))
    if version not in {(1, 1), (2, 2)}:
        raise ValueError("verification_subject_version_unsupported")
    pairs: set[tuple[str, ...]] = set()
    for subject in projection.get("subjects", []):
        raw_pairs = subject.get("spec_pairs", [])
        if not isinstance(raw_pairs, list):
            raise ValueError("verification_subject_manifest_invalid")
        for pair in raw_pairs:
            expected_keys = (
                {"requirement_id", "scenario_id"}
                if version == (1, 1)
                else {"capability_id", "requirement_id", "scenario_id"}
            )
            if not isinstance(pair, dict) or set(pair) != expected_keys:
                raise ValueError("verification_subject_manifest_invalid")
            if version == (1, 1):
                pairs.add((str(pair["requirement_id"]), str(pair["scenario_id"])))
            else:
                pairs.add((
                    str(pair["capability_id"]),
                    str(pair["requirement_id"]),
                    str(pair["scenario_id"]),
                ))
        if subject.get("kind") == "composition_invariant":
            pairs.add(("@composition", str(subject["subject_id"])))
    return pairs


def resolved_projection_obligation_pairs(
    projection: dict, required_pairs: object
) -> set[tuple[str, ...]]:
    declared = projection_obligation_pairs(projection)
    version = (projection.get("schema_version"), projection.get("normalization_version"))
    if version == (2, 2):
        return declared
    resolved: set[tuple[str, ...]] = set()
    for pair in declared:
        if pair[0] == "@composition":
            resolved.add(pair)
            continue
        candidates = sorted(
            required
            for required in required_pairs
            if len(required) == 3 and required[1:] == pair
        )
        if any("/" in candidate[0] for candidate in candidates):
            raise ValueError("verification_subject_schema_upgrade_required")
        if len(candidates) != 1:
            raise ValueError("spec_mapping_ambiguous" if len(candidates) > 1 else "spec_mapping_unknown")
        resolved.add(candidates[0])
    return resolved
VERIFICATION_TIER_GATES = {
    "checkpoint_targeted": "checkpoint",
    "objective_scope": "review-ready",
    "whole_change": "whole-change",
    "release": "release",
}
STRUCTURED_BLOCKER_CATEGORIES = {
    "product_decision",
    "permission_expansion",
    "directory_expansion",
    "irreversible_operation",
    "overwrite_user_changes",
    "external_credentials",
    "external_system",
    "specification_conflict",
}


def normalize_contract_value(value: object, key: str = "") -> object:
    if isinstance(value, str):
        return normalize_semantic_text(value)
    if isinstance(value, list):
        normalized = [normalize_contract_value(entry) for entry in value]
        if key == "allowed_isolation":
            normalized = [str(Path(entry).resolve()) if isinstance(entry, str) and Path(entry).is_absolute() else entry for entry in normalized]
        if key in SET_ARRAY_KEYS:
            return sorted(normalized, key=lambda entry: json.dumps(entry, ensure_ascii=False, sort_keys=True))
        return normalized
    if isinstance(value, dict):
        return {name: normalize_contract_value(entry, name) for name, entry in value.items()}
    if value is None or isinstance(value, (bool, int)):
        return value
    raise ValueError("verification_subject_manifest_invalid")


def structured_repo_references(value: object) -> set[str]:
    references: set[str] = set()
    if isinstance(value, str) and value.startswith("repo://"):
        references.add(value)
    elif isinstance(value, list):
        for entry in value:
            references.update(structured_repo_references(entry))
    elif isinstance(value, dict):
        for entry in value.values():
            references.update(structured_repo_references(entry))
    return references


def structured_artifact(path: Path) -> tuple[object | None, set[str], str | None]:
    """Return structured content, its repo refs, and any downstream evidence role.

    Evidence identity is content-owned.  A legal filename or extension must not
    be able to turn a receipt/matrix/Report into an upstream manifest input.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None, set(), None
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = None
    if isinstance(value, (dict, list)):
        keys = set(value) if isinstance(value, dict) else set()
        role = None
        if {
            "command", "cwd", "git_commit", "source_tree", "batch_id",
            "sequence", "result", "evidence_type", "artifacts",
        }.issubset(keys):
            role = "receipt"
        elif {"change_id", "objective_id", "round_id", "rows", "diff_artifact"}.issubset(keys):
            role = "boundary_matrix"
        elif "event_type" in keys and "event_hash" in keys:
            role = "event_log"
        return value, structured_repo_references(value), role

    headings = {
        match.group(2).strip().rstrip("#").rstrip()
        for match in ATX_HEADING_RE.finditer(text)
        if len(match.group(1)) == 2
    }
    if set(REPORT_SECTIONS).issubset(headings):
        return None, repo_links(text), "execution_report"
    if text.startswith("diff --git ") or text.startswith("GIT binary patch"):
        return None, set(), "diff"

    yaml_keys = {
        match.group(1)
        for match in re.finditer(r"(?m)^\s*(?:-\s+)?([A-Za-z_][A-Za-z0-9_-]*)\s*:", text)
    }
    first_content = next((line.strip() for line in text.splitlines() if line.strip()), "")
    yaml_like = (
        first_content == "---"
        or bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*\s*:.*", first_content))
    )
    if yaml_like and len(yaml_keys) >= 2:
        role = None
        if {"change_id", "objective_id", "round_id", "rows", "diff_artifact"}.issubset(yaml_keys):
            role = "boundary_matrix"
        return {"yaml_keys": sorted(yaml_keys)}, repo_links(text), role
    return None, set(), None


def validate_manifest_dag(root: Path, manifest_path: Path, manifest: dict, validation_root: Path) -> None:
    visited: set[Path] = set()
    active: set[Path] = {manifest_path}

    def visit_structured(path: Path) -> None:
        if path in active:
            raise ValueError("verification_subject_cycle_detected")
        if path in visited:
            return
        visited.add(path)
        value, references, downstream_role = structured_artifact(path)
        if downstream_role is not None:
            raise ValueError("verification_subject_cycle_detected")
        if value is None:
            if path.suffix.lower() == ".json":
                raise ValueError("verification_subject_manifest_invalid")
            return
        active.add(path)
        for reference in references:
            try:
                target = logical_repo_path(root, reference, must_exist=True)
            except (ValueError, FileNotFoundError) as exc:
                raise ValueError("verification_subject_manifest_invalid") from exc
            if target == manifest_path:
                raise ValueError("verification_subject_cycle_detected")
            visit_structured(target)
        active.remove(path)

    for reference in structured_repo_references(manifest):
        try:
            target = logical_repo_path(root, reference, must_exist=False)
        except ValueError as exc:
            raise ValueError("verification_subject_manifest_invalid") from exc
        if target == manifest_path:
            raise ValueError("verification_subject_cycle_detected")
        if target.is_file():
            visit_structured(target)


def build_subject_projection(
    root: Path, state_text: str, change: str, objective_id: str, objective: dict, manifest: dict
) -> dict:
    allowed_manifest_keys = {
        "schema_version", "normalization_version", "change_id", "objective_id",
        "required_task_ids", "subjects", "metadata",
    }
    allowed_subject_keys = {
        "subject_id", "kind", "refs", "semantic_inputs", "requirement_ids", "scenario_ids",
        "spec_pairs", "boundary_id", "owner", "invariant", "required_evidence",
        "verification_contract", "metadata",
    }
    version = (manifest.get("schema_version"), manifest.get("normalization_version"))
    if version not in {(1, 1), (2, 2)}:
        raise ValueError("verification_subject_version_unsupported")
    if version == (1, 1) and has_namespaced_spec_pairs(required_spec_pairs(root, change)):
        raise ValueError("verification_subject_schema_upgrade_required")
    if set(manifest) - allowed_manifest_keys:
        raise ValueError("verification_subject_manifest_invalid")
    required_task_ids = objective.get("required_task_ids")
    if not isinstance(required_task_ids, list) or not required_task_ids or not all(
        isinstance(value, str) and value for value in required_task_ids
    ):
        raise ValueError("verification_subject_mapping_mismatch")
    manifest_task_ids = manifest.get("required_task_ids")
    if (
        not isinstance(manifest_task_ids, list)
        or len(manifest_task_ids) != len(required_task_ids)
        or sorted(manifest_task_ids) != sorted(required_task_ids)
    ):
        raise ValueError("verification_subject_mapping_mismatch")
    subjects = manifest.get("subjects")
    if not isinstance(subjects, list) or not subjects:
        raise ValueError("verification_subject_manifest_invalid")
    normalized_subjects: list[dict] = []
    subject_ids: set[str] = set()
    for raw_subject in subjects:
        if not isinstance(raw_subject, dict) or set(raw_subject) - allowed_subject_keys:
            raise ValueError("verification_subject_manifest_invalid")
        subject_id = raw_subject.get("subject_id")
        kind = raw_subject.get("kind")
        refs = raw_subject.get("refs")
        inputs = raw_subject.get("semantic_inputs")
        evidence = raw_subject.get("required_evidence")
        contract = raw_subject.get("verification_contract")
        raw_spec_pairs = raw_subject.get("spec_pairs", [])
        pair_keys = (
            {"requirement_id", "scenario_id"}
            if version == (1, 1)
            else {"capability_id", "requirement_id", "scenario_id"}
        )
        if (
            not isinstance(subject_id, str)
            or not subject_id
            or subject_id in subject_ids
            or not isinstance(kind, str)
            or not kind
            or not isinstance(refs, list)
            or not refs
            or not all(isinstance(reference, str) and reference.startswith("repo://") for reference in refs)
            or not isinstance(inputs, list)
            or not inputs
            or not isinstance(evidence, list)
            or not evidence
            or not all(isinstance(value, str) and value for value in evidence)
            or not isinstance(contract, dict)
            or not contract
            or not isinstance(raw_spec_pairs, list)
            or any(not isinstance(pair, dict) or set(pair) != pair_keys for pair in raw_spec_pairs)
        ):
            raise ValueError("verification_subject_manifest_invalid")
        subject_ids.add(subject_id)
        normalized_inputs: list[dict[str, str]] = []
        for raw_input in inputs:
            if not isinstance(raw_input, dict) or set(raw_input) - {"path", "sha256"}:
                raise ValueError("verification_subject_manifest_invalid")
            reference = normalized_repo_reference(root, raw_input.get("path"), must_exist=True)
            content_hash = canonical_content_hash(logical_repo_path(root, reference, must_exist=True))
            declared_hash = raw_input.get("sha256")
            if declared_hash is not None and declared_hash != content_hash:
                raise ValueError("verification_subject_mapping_mismatch")
            normalized_inputs.append({"path": reference, "sha256": content_hash})
        semantic_subject = {
            key: value
            for key, value in raw_subject.items()
            if key not in {"refs", "semantic_inputs", "metadata"}
        }
        semantic_subject["subject_id"] = normalize_semantic_text(subject_id)
        semantic_subject["kind"] = normalize_semantic_text(kind)
        semantic_subject["refs"] = sorted(
            {normalized_repo_reference(root, reference) for reference in refs}
        )
        semantic_subject["semantic_inputs"] = sorted(normalized_inputs, key=lambda entry: entry["path"])
        semantic_subject["required_evidence"] = sorted(
            {normalize_semantic_text(str(value)) for value in evidence}
        )
        semantic_subject["verification_contract"] = normalize_contract_value(contract)
        normalized_subjects.append(normalize_contract_value(semantic_subject))
    return {
        "schema_version": version[0],
        "normalization_version": version[1],
        "change_id": normalize_semantic_text(change),
        "objective_id": normalize_semantic_text(objective_id),
        "objective_order": int(objective["order"]),
        "objective_purpose": normalize_semantic_text(str(objective["purpose"])),
        "remediates": sorted(normalize_semantic_text(str(value)) for value in objective.get("remediates", [])),
        "required_tasks": required_task_semantics(root, state_text, required_task_ids),
        "subjects": sorted(normalized_subjects, key=lambda entry: str(entry["subject_id"])),
    }


def load_manifest_opt_in(
    root: Path, change: str, objective_id: str, plan_reference: str, validation_root: Path
) -> tuple[str, str, dict]:
    try:
        plan_path = logical_repo_path(root, plan_reference, must_exist=True)
    except (ValueError, FileNotFoundError) as exc:
        raise ValueError("verification_subject_manifest_missing") from exc
    if validation_root not in plan_path.parents:
        raise ValueError("verification_subject_manifest_invalid")
    plan = load_json_object(plan_path)
    state_text = state_path(root, change).read_text(encoding="utf-8")
    objectives, _ = validate_objective_plan(root, state_text, change, plan)
    matches = [entry for entry in objectives if isinstance(entry, dict) and entry.get("objective_id") == objective_id]
    if len(matches) != 1:
        raise ValueError("verification_subject_mapping_mismatch")
    objective = matches[0]
    manifest_reference = objective.get("manifest")
    if not isinstance(manifest_reference, str):
        raise ValueError("verification_subject_manifest_missing")
    try:
        manifest_path = logical_repo_path(root, manifest_reference, must_exist=True)
    except (ValueError, FileNotFoundError) as exc:
        raise ValueError("verification_subject_manifest_missing") from exc
    if validation_root not in manifest_path.parents:
        raise ValueError("verification_subject_manifest_invalid")
    manifest = load_json_object(manifest_path)
    if (
        manifest.get("change_id") != change
        or manifest.get("objective_id") != objective_id
    ):
        raise ValueError("verification_subject_mapping_mismatch")
    if (manifest.get("schema_version"), manifest.get("normalization_version")) not in {(1, 1), (2, 2)}:
        raise ValueError("verification_subject_version_unsupported")
    validate_manifest_dag(root, manifest_path, manifest, validation_root)
    projection = build_subject_projection(root, state_text, change, objective_id, objective, manifest)
    digest = hashlib.sha256(
        json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return manifest_reference, digest, projection


def subject_digest(args: argparse.Namespace) -> tuple[dict, int]:
    context, error = context_or_error("subject-digest", args.change)
    if error:
        return error
    assert context is not None
    root, _, _, _ = context
    validation_root = validation_root_for(root, args.change)
    try:
        manifest_reference, digest, projection = load_manifest_opt_in(
            root, args.change, args.objective, args.objective_plan, validation_root
        )
    except ValueError as exc:
        return violation_result("subject-digest", str(exc), "objective plan 或 subject manifest 无效")
    return build_result(
        "subject-digest", None, [], manifest_enabled=True, manifest=manifest_reference,
        subject_digest=digest, subject_ids=[entry["subject_id"] for entry in projection["subjects"]],
        schema_version=projection["schema_version"],
        normalization_version=projection["normalization_version"],
    ), 0


def current_subject_context(root: Path, change: str, collaboration: dict[str, str]) -> tuple[str, str, dict]:
    plan_reference = collaboration.get("objective_plan", "")
    if not plan_reference:
        raise ValueError("verification_subject_manifest_missing")
    validation_root = validation_root_for(root, change)
    return load_manifest_opt_in(root, change, collaboration["objective_id"], plan_reference, validation_root)


def verification_subject_context(
    root: Path, change: str, collaboration: dict[str, str], gate: str | None
) -> tuple[str, str, dict]:
    if gate not in {"whole-change", "release"}:
        return current_subject_context(root, change, collaboration)
    plan_reference = collaboration.get("objective_plan", "")
    if not plan_reference:
        raise ValueError("verification_subject_manifest_missing")
    state_text = state_path(root, change).read_text(encoding="utf-8")
    objectives, _ = validate_objective_plan(
        root, state_text, change, load_json_object(logical_repo_path(root, plan_reference, must_exist=True))
    )
    validation_root = validation_root_for(root, change)
    objective_digests: list[dict[str, object]] = []
    subjects: dict[str, dict] = {}
    subject_owners: dict[str, str] = {}
    for objective in objectives:
        objective_id = str(objective["objective_id"])
        _, digest, projection = load_manifest_opt_in(
            root, change, objective_id, plan_reference, validation_root
        )
        objective_digests.append({
            "objective_id": objective_id,
            "schema_version": projection["schema_version"],
            "normalization_version": projection["normalization_version"],
            "subject_digest": digest,
        })
        for subject in projection.get("subjects", []):
            subject_id = str(subject["subject_id"])
            previous = subjects.get(subject_id)
            if previous is not None and previous != subject:
                previous_owner = subject_owners[subject_id]
                if previous_owner not in objective.get("remediates", []):
                    raise ValueError("verification_subject_mapping_mismatch")
            subjects[subject_id] = subject
            subject_owners[subject_id] = objective_id
    aggregate_version = 2 if any(entry["schema_version"] == 2 for entry in objective_digests) else 1
    rendered_objective_digests = (
        objective_digests
        if aggregate_version == 2
        else [
            {"objective_id": entry["objective_id"], "subject_digest": entry["subject_digest"]}
            for entry in objective_digests
        ]
    )
    aggregate = {
        "schema_version": aggregate_version,
        "normalization_version": aggregate_version,
        "change_id": change,
        "objective_digests": rendered_objective_digests,
        "subjects": [subjects[key] for key in sorted(subjects)],
    }
    digest = hashlib.sha256(
        json.dumps(aggregate, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return plan_reference, digest, aggregate


def current_plan_context(
    root: Path, state_text: str, change: str, collaboration: dict[str, str]
) -> tuple[list[dict], dict[str, dict[str, object]], dict]:
    reference = collaboration.get("objective_plan", "")
    if not reference:
        raise ValueError("verification_subject_manifest_missing")
    try:
        plan_path = logical_repo_path(root, reference, must_exist=True)
    except (ValueError, FileNotFoundError) as exc:
        raise ValueError("verification_subject_manifest_missing") from exc
    plan = load_json_object(plan_path)
    objectives, tasks = validate_objective_plan(root, state_text, change, plan)
    matches = [entry for entry in objectives if entry["objective_id"] == collaboration["objective_id"]]
    if len(matches) != 1:
        raise ValueError("verification_subject_mapping_mismatch")
    return objectives, tasks, matches[0]


def objective_task_gate_violations(
    root: Path, state_text: str, change: str, collaboration: dict[str, str], *, whole_change: bool = False
) -> list[dict[str, str]]:
    try:
        objectives, tasks, current = current_plan_context(root, state_text, change, collaboration)
    except ValueError as exc:
        return [item(str(exc), "objective plan task ownership 无法验证")]
    assignment_violations = objective_assignment_violations(root, collaboration, objectives)
    if assignment_violations:
        return assignment_violations
    task_ids = sorted(tasks) if whole_change else sorted(current["required_task_ids"])
    incomplete = [task_id for task_id in task_ids if not tasks[task_id]["completed"]]
    if incomplete:
        return [item("task_completion_incomplete", "required tasks 未完成：" + ", ".join(incomplete))]
    return []


def objective_assignment_violations(
    root: Path, collaboration: dict[str, str], objectives: list[dict]
) -> list[dict[str, str]]:
    try:
        events = read_events(root, collaboration)
    except ValueError as exc:
        return [item("event_log_invalid", str(exc))]
    assignments = {entry["objective_id"]: sorted(entry["required_task_ids"]) for entry in objectives}
    for event in events:
        if event.get("event_type") != "objective_planned" or not isinstance(event.get("required_task_ids"), list):
            continue
        objective_id = str(event.get("objective_id", ""))
        if objective_id in assignments and sorted(event["required_task_ids"]) != assignments[objective_id]:
            return [item("objective_task_assignment_changed", f"objective task 归属已静默改变：{objective_id}")]
    return []


def receipt_provenance_authorized(root: Path, receipt: dict, projection: dict) -> bool:
    if receipt.get("cwd") != str(root):
        return False
    host = receipt.get("host")
    isolation = receipt.get("isolation_id")
    subject_ids = set(receipt.get("subject_ids", []))
    for subject in projection.get("subjects", []):
        if subject.get("subject_id") not in subject_ids:
            continue
        contract = subject.get("verification_contract", {})
        allowed_hosts = contract.get("allowed_hosts", [])
        allowed_isolation = contract.get("allowed_isolation", [])
        if host not in allowed_hosts or isolation not in allowed_isolation:
            return False
    return True


def subject_fingerprints(projection: dict) -> dict[str, str]:
    return {
        str(subject["subject_id"]): hashlib.sha256(
            json.dumps(subject, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        for subject in projection.get("subjects", [])
    }


def subject_obligations(projection: dict) -> dict[str, dict]:
    """Freeze the reviewer-owned obligation contract, excluding implementation bytes."""
    obligations: dict[str, dict] = {}
    for subject in projection.get("subjects", []):
        subject_id = str(subject["subject_id"])
        obligations[subject_id] = normalize_contract_value(
            {
                "subject_id": subject_id,
                "kind": subject.get("kind", ""),
                "refs": subject.get("refs", []),
                "spec_pairs": subject.get("spec_pairs", []),
                "requirement_ids": subject.get("requirement_ids", []),
                "scenario_ids": subject.get("scenario_ids", []),
                "boundary_id": subject.get("boundary_id", ""),
                "invariant": subject.get("invariant", ""),
                "owner": subject.get("owner", ""),
                "required_evidence": subject.get("required_evidence", []),
                "verification_contract": subject.get("verification_contract", {}),
            }
        )
    return obligations


def obligations_cover(frozen: object, candidate_projection: dict) -> bool:
    if not isinstance(frozen, dict) or not frozen:
        return False
    candidate = subject_obligations(candidate_projection)
    set_fields = {"refs", "spec_pairs", "requirement_ids", "scenario_ids", "required_evidence"}
    exact_fields = {"kind", "boundary_id", "invariant", "owner", "verification_contract"}
    for subject_id, accepted in frozen.items():
        current = candidate.get(str(subject_id))
        if not isinstance(accepted, dict) or not isinstance(current, dict):
            return False
        for field in exact_fields:
            if current.get(field) != accepted.get(field):
                return False
        for field in set_fields:
            accepted_values = {
                json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                for value in accepted.get(field, [])
            }
            current_values = {
                json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                for value in current.get(field, [])
            }
            if not accepted_values.issubset(current_values):
                return False
    return True


def accepted_current_evaluation(
    root: Path, state_text: str, change: str, collaboration: dict[str, str], *, include_current: bool
) -> tuple[list[dict], list[dict]]:
    objectives, _, current = current_plan_context(root, state_text, change, collaboration)
    events = read_events(root, collaboration)
    current_order = int(current["order"])
    candidates = [
        objective for objective in objectives
        if include_current or int(objective["order"]) < current_order
    ]
    evaluations: list[dict] = []
    accepted_events: dict[str, dict] = {}
    for event in events:
        if event.get("event_type") == "accepted" and isinstance(event.get("accepted_subject_digest"), str):
            accepted_events[str(event.get("objective_id"))] = event
    for objective in candidates:
        objective_id = str(objective["objective_id"])
        accepted = accepted_events.get(objective_id)
        if not accepted:
            evaluations.append({"objective_id": objective_id, "accepted_current": False, "reason": "objective_not_accepted"})
            continue
        expected_authorizations = authorization_obligations(events, objective_id)
        if accepted.get("authorization_obligations", []) != expected_authorizations:
            evaluations.append({
                "objective_id": objective_id,
                "accepted_current": False,
                "reason": "resume_authorization_identity_mismatch",
            })
            continue
        current_authorization_violations = authorization_current_violations(root, events, objective_id)
        if current_authorization_violations:
            evaluations.append({
                "objective_id": objective_id,
                "accepted_current": False,
                "reason": current_authorization_violations[0]["code"],
            })
            continue
        try:
            manifest_reference, digest, projection = load_manifest_opt_in(
                root,
                change,
                objective_id,
                collaboration["objective_plan"],
                validation_root_for(root, change),
            )
        except ValueError as exc:
            evaluations.append({"objective_id": objective_id, "accepted_current": False, "reason": str(exc)})
            continue
        current_fingerprints = subject_fingerprints(projection)
        current_version = (projection.get("schema_version"), projection.get("normalization_version"))
        accepted_version = (
            accepted.get("subject_schema_version", 1),
            accepted.get("subject_normalization_version", 1),
        )
        if accepted_version != current_version:
            evaluations.append({
                "objective_id": objective_id,
                "accepted_current": False,
                "reason": "verification_subject_version_mismatch",
                "accepted_digest": accepted.get("accepted_subject_digest"),
                "current_digest": digest,
                "changed_subject_ids": [],
                "manifest": manifest_reference,
                "accepted_obligations": accepted.get("accepted_obligations", {}),
            })
            continue
        accepted_fingerprints = accepted.get("accepted_subject_fingerprints", {})
        changed_subject_ids = sorted(
            subject_id
            for subject_id in set(current_fingerprints) | set(accepted_fingerprints)
            if current_fingerprints.get(subject_id) != accepted_fingerprints.get(subject_id)
        )
        if accepted.get("accepted_subject_digest") != digest:
            if not changed_subject_ids:
                changed_subject_ids = sorted(
                    set(current_fingerprints) | set(str(value) for value in accepted.get("accepted_subject_ids", []))
                )
            evaluations.append(
                {
                    "objective_id": objective_id,
                    "accepted_current": False,
                    "reason": "accepted_objective_subject_stale",
                    "accepted_digest": accepted.get("accepted_subject_digest"),
                    "current_digest": digest,
                    "changed_subject_ids": changed_subject_ids,
                    "manifest": manifest_reference,
                    "accepted_obligations": accepted.get("accepted_obligations", {}),
                }
            )
        else:
            evaluations.append(
                {
                    "objective_id": objective_id,
                    "accepted_current": True,
                    "accepted_digest": digest,
                    "current_digest": digest,
                    "changed_subject_ids": [],
                    "manifest": manifest_reference,
                    "accepted_obligations": accepted.get("accepted_obligations", {}),
                }
            )
    by_id = {entry["objective_id"]: entry for entry in objectives}
    current_by_id = {entry["objective_id"]: entry for entry in evaluations}
    for stale in evaluations:
        if stale.get("reason") != "accepted_objective_subject_stale":
            continue
        stale_id = str(stale["objective_id"])
        replacements: list[str] = []
        for remediation_id, remediation_eval in current_by_id.items():
            remediation = by_id.get(remediation_id, {})
            if not remediation_eval.get("accepted_current") or stale_id not in remediation.get("remediates", []):
                continue
            try:
                _, _, remediation_projection = load_manifest_opt_in(
                    root,
                    change,
                    remediation_id,
                    collaboration["objective_plan"],
                    validation_root_for(root, change),
                )
            except ValueError:
                continue
            if obligations_cover(stale.get("accepted_obligations"), remediation_projection):
                replacements.append(remediation_id)
        if replacements:
            stale["coverage_satisfied"] = True
            stale["replacement_objective_ids"] = sorted(replacements)
    return objectives, evaluations


def accepted_current_violations(evaluations: list[dict], gate: str) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    for evaluation in evaluations:
        if evaluation.get("accepted_current") or evaluation.get("coverage_satisfied"):
            continue
        reason = str(evaluation.get("reason", "objective_not_accepted"))
        if reason == "accepted_objective_subject_stale":
            violations.append(
                item(reason, f"accepted objective 当前证明已失效：{evaluation['objective_id']}（gate={gate}）")
            )
        else:
            violations.append(item(reason, f"required objective 尚无当前有效 acceptance：{evaluation['objective_id']}"))
    return violations


def current_remediation_covers(
    root: Path, change: str, collaboration: dict[str, str], evaluations: list[dict]
) -> bool:
    stale = [entry for entry in evaluations if entry.get("reason") == "accepted_objective_subject_stale"]
    non_stale = [
        entry for entry in evaluations
        if not entry.get("accepted_current") and entry.get("reason") != "accepted_objective_subject_stale"
    ]
    if non_stale or not stale:
        return False
    try:
        _, _, current = current_plan_context(
            root, state_path(root, change).read_text(encoding="utf-8"), change, collaboration
        )
        _, _, current_projection = current_subject_context(root, change, collaboration)
    except ValueError:
        return False
    stale_ids = {str(entry["objective_id"]) for entry in stale}
    if not stale_ids.issubset(set(current.get("remediates", []))):
        return False
    for evaluation in stale:
        if not obligations_cover(evaluation.get("accepted_obligations"), current_projection):
            evaluation["remediation_reason"] = "remediation_obligation_incomplete"
            return False
    for evaluation in stale:
        evaluation["candidate_covering_objective_ids"] = [collaboration["objective_id"]]
        evaluation["coverage_pending_acceptance"] = True
    return True


def whole_change_matrix_violations(
    root: Path, change: str, collaboration: dict[str, str], evaluations: list[dict]
) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    try:
        objectives, _, _ = current_plan_context(
            root, state_path(root, change).read_text(encoding="utf-8"), change, collaboration
        )
        events = read_events(root, collaboration)
        required_pairs = set(required_spec_pairs(root, change))
    except ValueError as exc:
        return [item(str(exc), "whole-change mapping 无法重算")]
    evaluation_by_id = {entry["objective_id"]: entry for entry in evaluations}
    pair_owners: dict[tuple[str, str], list[tuple[str, str]]] = {}
    subject_ids_by_objective: dict[str, set[str]] = {}
    evidence_by_subject: dict[str, dict[str, set[str]]] = {}
    manifest_by_objective: dict[str, str] = {}
    version_by_objective: dict[str, int] = {}
    for objective in objectives:
        objective_id = str(objective["objective_id"])
        try:
            manifest_reference, _, projection = load_manifest_opt_in(
                root,
                change,
                objective_id,
                collaboration["objective_plan"],
                validation_root_for(root, change),
            )
        except ValueError as exc:
            violations.append(item(str(exc), f"objective manifest 无法重算：{objective_id}"))
            continue
        manifest_by_objective[objective_id] = manifest_reference
        version_by_objective[objective_id] = int(projection["schema_version"])
        subject_ids_by_objective[objective_id] = {entry["subject_id"] for entry in projection["subjects"]}
        evidence_by_subject[objective_id] = {
            str(entry["subject_id"]): set(str(value) for value in entry.get("required_evidence", []))
            for entry in projection["subjects"]
        }
        try:
            obligation_pairs = resolved_projection_obligation_pairs(projection, required_pairs)
        except ValueError as exc:
            violations.append(item(str(exc), f"subject obligations 无效：{objective_id}"))
            continue
        for pair in obligation_pairs:
            owner_subjects = [
                str(subject["subject_id"])
                for subject in projection["subjects"]
                if pair in resolved_projection_obligation_pairs(
                    {
                        "schema_version": projection["schema_version"],
                        "normalization_version": projection["normalization_version"],
                        "subjects": [subject],
                    },
                    required_pairs,
                )
            ]
            for subject_id in owner_subjects:
                pair_owners.setdefault(pair, []).append((objective_id, subject_id))
        required_pairs.update(
            pair for pair in obligation_pairs if pair[0] == "@composition"
        )

    accepted_events = {
        str(event.get("objective_id")): event
        for event in events
        if event.get("event_type") == "accepted"
    }
    valid_receipts_by_objective: dict[str, dict[str, dict]] = {}
    for objective in objectives:
        objective_id = str(objective["objective_id"])
        evaluation = evaluation_by_id.get(objective_id, {})
        if evaluation.get("coverage_satisfied"):
            continue
        if not evaluation.get("accepted_current"):
            continue
        event = accepted_events.get(objective_id, {})
        references = event.get("evidence_refs", [])
        if not isinstance(references, list) or not references:
            violations.append(item("objective_scope_receipt_missing", f"accepted objective 缺少 scope receipts：{objective_id}"))
            continue
        objective_collaboration = dict(collaboration)
        objective_collaboration["objective_id"] = objective_id
        objective_collaboration["subject_manifest"] = manifest_by_objective.get(objective_id, "")
        valid_by_ref: dict[str, dict] = {}
        for reference in references:
            try:
                receipt_path = logical_repo_path(root, str(reference), must_exist=True)
            except (ValueError, FileNotFoundError):
                violations.append(item("boundary_evidence_missing", f"accepted receipt 不可解析：{reference}"))
                continue
            receipt, receipt_violations = validate_receipt(
                root,
                receipt_path,
                objective_collaboration,
                git_output(root, "rev-parse", "HEAD"),
                git_output(root, "rev-parse", "HEAD^{tree}"),
                change=change,
                expected_gate="review-ready",
            )
            violations.extend(receipt_violations)
            if receipt and not receipt_violations:
                valid_by_ref[str(reference)] = receipt
        if not any(receipt.get("verification_tier") == "objective_scope" for receipt in valid_by_ref.values()):
            violations.append(item("objective_scope_receipt_missing", f"accepted objective 无有效 scope receipt：{objective_id}"))
        valid_receipts_by_objective[objective_id] = valid_by_ref
    effective_owners: dict[tuple[str, str], tuple[str, str]] = {}
    for pair, owners in pair_owners.items():
        active = []
        for objective_id, subject_id in owners:
            evaluation = evaluation_by_id.get(objective_id, {})
            if evaluation.get("reason") == "accepted_objective_subject_stale" and evaluation.get("coverage_satisfied"):
                continue
            active.append((objective_id, subject_id))
        if len(active) > 1:
            violations.append(item("spec_mapping_duplicate", f"whole-change spec pair 重复：{pair[0]}/{pair[1]}"))
        elif len(active) == 1:
            effective_owners[pair] = active[0]
    for pair in sorted(required_pairs - set(effective_owners)):
        violations.append(item("spec_mapping_incomplete", f"whole-change 缺少 delta spec scenario：{pair[0]}/{pair[1]}"))
    for pair in sorted(set(effective_owners) - required_pairs):
        violations.append(item("spec_mapping_unknown", f"whole-change 引用了未知 delta spec scenario：{pair[0]}/{pair[1]}"))

    matrix_by_objective: dict[str, str] = {}
    for event in events:
        if event.get("event_type") == "objective_planned" and isinstance(event.get("boundary_matrix"), str):
            matrix_by_objective[str(event.get("objective_id"))] = str(event["boundary_matrix"])
    rows_by_boundary: dict[str, list[dict[str, str]]] = {}
    expected_by_objective: dict[str, set[tuple[str, ...]]] = {}
    for pair, (objective_id, _) in effective_owners.items():
        expected_by_objective.setdefault(objective_id, set()).add(pair)
    for objective_id, expected in expected_by_objective.items():
        reference = matrix_by_objective.get(objective_id, "")
        try:
            matrix_path = logical_repo_path(root, reference, must_exist=True)
            top, rows = parse_boundary_matrix(matrix_path)
        except (ValueError, FileNotFoundError, OSError) as exc:
            violations.append(item("boundary_matrix_open", f"objective matrix 不可用：{objective_id}: {exc}"))
            continue
        if top.get("change_id") != change or top.get("objective_id") != objective_id:
            violations.append(item("boundary_matrix_invalid", f"objective matrix identity 不匹配：{objective_id}"))
        try:
            matrix_version = boundary_matrix_version(top)
        except ValueError as exc:
            violations.append(item(str(exc), f"objective matrix version 无效：{objective_id}"))
            matrix_version = 0
        if matrix_version != version_by_objective.get(objective_id):
            violations.append(item("verification_subject_version_mismatch", f"objective matrix/manifest version 不一致：{objective_id}"))
        actual: dict[tuple[str, ...], int] = {}
        for row in rows:
            try:
                pair = resolve_matrix_row_identity(matrix_version, row, required_pairs)
            except ValueError as exc:
                violations.append(item(str(exc), f"whole-change row spec identity 无效：{row.get('row_id', '?')}"))
            else:
                actual[pair] = actual.get(pair, 0) + 1
            if row.get("status") != "covered":
                violations.append(item("boundary_matrix_open", f"whole-change matrix row 未闭合：{row.get('row_id', '?')}"))
            row_subject_ids = set(split_csv(row.get("subject_ids", "")))
            if not row_subject_ids or not row_subject_ids.issubset(subject_ids_by_objective.get(objective_id, set())):
                violations.append(item("verification_subject_mapping_mismatch", f"whole-change row subject mapping 无效：{row.get('row_id', '?')}"))
            required_types = set(split_csv(row.get("required_evidence", "")))
            manifest_types = set().union(
                *(evidence_by_subject.get(objective_id, {}).get(subject_id, set()) for subject_id in row_subject_ids)
            ) if row_subject_ids else set()
            if not manifest_types.issubset(required_types):
                violations.append(item("boundary_evidence_missing", f"whole-change row 未声明 manifest required evidence：{row.get('row_id', '?')}"))
            refs = split_csv(row.get("evidence_refs", ""))
            valid_by_ref = valid_receipts_by_objective.get(objective_id, {})
            present_types = {
                str(valid_by_ref[reference].get("evidence_type"))
                for reference in refs
                if reference in valid_by_ref
            }
            if not required_types.issubset(present_types):
                violations.append(item("boundary_evidence_missing", f"whole-change row 缺少 current evidence：{row.get('row_id', '?')}"))
            rows_by_boundary.setdefault(row.get("boundary_id", ""), []).append(row)
        if set(actual) != expected:
            code = "spec_mapping_incomplete" if expected - set(actual) else "spec_mapping_unknown"
            violations.append(item(code, f"objective matrix spec mapping 不完整：{objective_id}"))
        if any(count > 1 for count in actual.values()):
            violations.append(item("spec_mapping_duplicate", f"objective matrix 重复 spec pair：{objective_id}"))
    for boundary in systemic_boundaries(events):
        rows = rows_by_boundary.get(boundary, [])
        if not rows or any(row.get("status") != "covered" for row in rows):
            violations.append(item("recurrence_upgrade_unresolved", f"whole-change recurrence 未闭合：{boundary}"))
    return violations


def coverage_check(args: argparse.Namespace) -> tuple[dict, int]:
    context, error = context_or_error("coverage-check", args.change)
    if error:
        return error
    assert context is not None
    root, _, state_text, collaboration = context
    try:
        authorization_violations = authorization_current_violations(
            root, read_events(root, collaboration)
        )
    except ValueError as exc:
        authorization_violations = [item(str(exc), "resume authorization history 无法重算")]
    if authorization_violations:
        return build_result(
            "coverage-check", None, authorization_violations, applicable=True, gate=args.gate,
            blocking_reasons=[entry["code"] for entry in authorization_violations],
        ), 1
    schema_violations = matrix_schema_current_violations(root, args.change, collaboration)
    if schema_violations:
        return build_result(
            "coverage-check", None, schema_violations, applicable=True, gate=args.gate,
            blocking_reasons=[entry["code"] for entry in schema_violations],
        ), 1
    if not collaboration.get("objective_plan"):
        return build_result("coverage-check", None, [], applicable=False, gate=args.gate), 0
    violations = objective_task_gate_violations(
        root, state_text, args.change, collaboration, whole_change=args.gate in {"whole-change", "release"}
    )
    evaluations: list[dict] = []
    try:
        _, evaluations = accepted_current_evaluation(
            root,
            state_text,
            args.change,
            collaboration,
            include_current=args.gate in {"whole-change", "release"},
        )
        accepted_violations = accepted_current_violations(evaluations, args.gate)
        if args.gate == "review-ready":
            if current_remediation_covers(root, args.change, collaboration, evaluations):
                accepted_violations = [entry for entry in accepted_violations if entry["code"] != "accepted_objective_subject_stale"]
            elif any(entry.get("remediation_reason") == "remediation_obligation_incomplete" for entry in evaluations):
                accepted_violations.append(
                    item("remediation_obligation_incomplete", "当前 remediation objective 未覆盖 predecessor 冻结的完整 obligations")
                )
        violations.extend(accepted_violations)
        if args.gate in {"whole-change", "release"}:
            violations.extend(whole_change_matrix_violations(root, args.change, collaboration, evaluations))
    except ValueError as exc:
        violations.append(item(str(exc), "accepted-current 无法重算"))
    receipt_results: list[dict] = []
    if args.gate in {"whole-change", "release"}:
        receipt_references = list(args.receipt)
        explicit_receipts = bool(receipt_references)
        if not receipt_references:
            expected_tier = "whole_change" if args.gate == "whole-change" else "release"
            receipts_root = validation_root_for(root, args.change) / "receipts"
            if receipts_root.is_dir():
                for candidate in sorted(receipts_root.rglob("*.json")):
                    try:
                        payload = load_json_object(candidate)
                    except ValueError:
                        continue
                    if payload.get("verification_tier") == expected_tier and payload.get("change_id") == args.change:
                        receipt_references.append("repo://" + candidate.relative_to(root).as_posix())
        if not receipt_references:
            code = "whole_change_receipt_missing" if args.gate == "whole-change" else "release_receipt_missing"
            violations.append(item(code, f"{args.gate} gate 缺少对应 tier receipt"))
        candidate_violations: list[dict[str, str]] = []
        has_valid_candidate = False
        for reference in receipt_references:
            try:
                receipt_path = logical_repo_path(root, reference, must_exist=True)
            except (ValueError, FileNotFoundError):
                current_violations = [item("boundary_evidence_missing", f"gate receipt 不可解析：{reference}")]
                candidate_violations.extend(current_violations)
                receipt_results.append(
                    {"reference": reference, "verification_tier": None, "valid": False,
                     "blocking_reasons": [entry["code"] for entry in current_violations]}
                )
                continue
            receipt, receipt_violations = validate_receipt(
                root,
                receipt_path,
                collaboration,
                git_output(root, "rev-parse", "HEAD"),
                git_output(root, "rev-parse", "HEAD^{tree}"),
                change=args.change,
                expected_gate=args.gate,
            )
            candidate_violations.extend(receipt_violations)
            has_valid_candidate = has_valid_candidate or bool(receipt and not receipt_violations)
            if receipt:
                receipt_results.append(
                    {"reference": reference, "verification_tier": receipt.get("verification_tier"),
                     "valid": not receipt_violations,
                     "blocking_reasons": [entry["code"] for entry in receipt_violations]}
                )
        if explicit_receipts or not has_valid_candidate:
            violations.extend(candidate_violations)
    task_codes = {entry["code"] for entry in objective_task_gate_violations(
        root, state_text, args.change, collaboration, whole_change=args.gate in {"whole-change", "release"}
    )}
    implemented = "task_completion_incomplete" not in task_codes
    return build_result(
        "coverage-check", None, violations, applicable=True, gate=args.gate,
        accepted_current=evaluations, receipts=receipt_results,
        implemented=implemented,
        closure_pending=implemented and bool(violations),
        review_ready=collaboration.get("phase") == "review_ready",
        accepted=collaboration.get("phase") == "accepted",
        release_ready=args.gate == "release" and not violations,
        blocking_reasons=[entry["code"] for entry in violations],
    ), 0 if not violations else 1


def mark_implemented(args: argparse.Namespace) -> tuple[dict, int]:
    context, error = context_or_error("mark-implemented", args.change, recover_history=True)
    if error:
        return error
    assert context is not None
    root, path, state_text, collaboration = context
    if not collaboration.get("objective_plan"):
        return violation_result("mark-implemented", "verification_subject_manifest_missing", "implemented fact 仅用于 manifest path")
    if collaboration["phase"] not in {"planned", "executing", "checkpoint"}:
        return violation_result("mark-implemented", "illegal_transition", "当前 lifecycle 不能记录 implemented fact")
    violations = objective_task_gate_violations(root, state_text, args.change, collaboration)
    if violations:
        return build_result(
            "mark-implemented", None, violations, implemented=False,
            blocking_reasons=[entry["code"] for entry in violations],
        ), 1
    try:
        manifest_reference, digest, projection = current_subject_context(root, args.change, collaboration)
        events = read_events(root, collaboration)
    except ValueError as exc:
        return violation_result("mark-implemented", str(exc), "implemented subject 无法重算")
    for event in reversed(events):
        if event.get("event_type") == "implemented" and event.get("objective_id") == collaboration["objective_id"]:
            if event.get("subject_digest") == digest:
                return build_result("mark-implemented", None, [], changed=False, implemented=True, subject_digest=digest), 0
            break
    commit_state_event(
        root,
        path,
        state_text,
        collaboration,
        "implemented",
        change_id=args.change,
        objective_id=collaboration["objective_id"],
        round_id=collaboration["round_id"],
        actor="executor",
        subject_manifest=manifest_reference,
        subject_digest=digest,
        subject_ids=sorted(entry["subject_id"] for entry in projection["subjects"]),
        required_task_ids=sorted(entry["task_id"] for entry in projection["required_tasks"]),
    )
    return build_result("mark-implemented", None, [], changed=True, implemented=True, subject_digest=digest), 0


def validate_brief(args: argparse.Namespace) -> tuple[dict, int]:
    text, violations = read_text(args.file)
    if text is None:
        return build_result("validate-brief", args.file, violations), 2
    sections, order, parsed = parse_sections(text, BRIEF_SECTIONS)
    violations.extend(parsed)
    count = cjk_count(text)
    if count < 200 or count > 500:
        violations.append(item("brief_length_out_of_range", f"中文字符数 {count}，要求 200–500"))
    if SOURCE_BODY_RE.search(text):
        violations.append(item("project_truth_body_copied", "Brief 复制了项目真源或 Handover 正文结构"))
    violations.extend(validate_source_boundaries(text, args.source_file))
    for name in BRIEF_SECTIONS:
        if name in sections and not sections[name].strip():
            violations.append(item("empty_section", f"空区块：{name}", name))

    context = sections.get("执行上下文", "")
    context_labels = ("目标宿主", "代码仓", "项目知识库", "当前分支 / OpenSpec Change", "项目真源入口")
    context_values = {label: labeled_value(context, label) for label in context_labels}
    for label, value in context_values.items():
        if not value:
            violations.append(item("context_field_missing", f"执行上下文缺少：{label}", "执行上下文"))

    if not normalized_absolute_path(args.code_root):
        violations.append(item("code_root_not_absolute", "--code-root 必须是规范化绝对路径", "执行上下文"))
    if not normalized_absolute_path(args.docs_root):
        violations.append(item("docs_root_not_absolute", "--docs-root 必须是规范化绝对路径", "执行上下文"))
    for forbidden_root in args.forbidden_root:
        if not normalized_absolute_path(forbidden_root):
            violations.append(item("forbidden_root_not_absolute", f"--forbidden-root 必须是规范化绝对路径：{forbidden_root}", "权限"))

    declared_host = context_values["目标宿主"]
    if declared_host and declared_host.lower() != args.host:
        violations.append(item("host_mismatch", "目标宿主与 --host 不一致", "执行上下文"))
    declared_code_root = context_values["代码仓"]
    if declared_code_root:
        if not normalized_absolute_path(declared_code_root):
            violations.append(item("declared_code_root_not_absolute", "代码仓必须是规范化绝对路径", "执行上下文"))
        elif declared_code_root != args.code_root:
            violations.append(item("code_root_mismatch", "代码仓与 --code-root 不一致", "执行上下文"))
    declared_docs_root = context_values["项目知识库"]
    if declared_docs_root:
        if not normalized_absolute_path(declared_docs_root):
            violations.append(item("declared_docs_root_not_absolute", "项目知识库必须是规范化绝对路径", "执行上下文"))
        elif declared_docs_root != args.docs_root:
            violations.append(item("docs_root_mismatch", "项目知识库与 --docs-root 不一致", "执行上下文"))
    project_truth_entry = context_values["项目真源入口"]
    if not project_truth_entry:
        violations.append(item("project_truth_entry_missing", "执行上下文缺少项目真源入口", "执行上下文"))
    elif not re.search(r"repo://|docs://|(?:^|\s)/[^\s`]+", project_truth_entry):
        violations.append(item("project_truth_entry_missing", "项目真源入口缺少 repo://、docs:// 或绝对路径", "执行上下文"))

    permissions = sections.get("权限", "")
    autonomous = labeled_value(permissions, "可自主执行") or ""
    for label in ("可自主执行", "禁止执行", "需用户批准"):
        if not labeled_value(permissions, label):
            violations.append(item("permission_category_missing", f"权限缺少：{label}", "权限"))
    unsafe = re.search(r"\bpush\b|发布|上线|不可逆|删除(?:历史|用户|生产|真实)?数据|真实数据迁移|生产数据迁移|外部凭据", autonomous, re.I)
    if unsafe:
        violations.append(item("unauthorized_operation", f"可自主执行包含高风险动作：{unsafe.group(0)}", "权限"))

    forbidden_line = labeled_value(permissions, "禁止执行") or ""
    for root in args.forbidden_root:
        if root not in forbidden_line:
            violations.append(item("forbidden_root_not_guarded", f"禁止目录未被明确保护：{root}", "权限"))

    scope = sections.get("任务范围", "")
    bullets = [line for line in scope.splitlines() if re.match(r"^\s*[-*+]\s+", line)]
    code_detail = re.search(r"```|\b(?:def|class|function)\s+|[A-Za-z_$][\w$]*\s*\([^\n)]*\)|(?:^|\s)[\w./-]+:\d+", scope, re.M)
    if len(bullets) > 6 or code_detail:
        violations.append(item("implementation_too_detailed", "任务范围展开了过多条目或函数/行号级实现", "任务范围"))

    if args.recurrence_count is not None:
        violations.append(item("manual_recurrence_forbidden", "复发次数必须从 append-only finding events 派生"))

    recurrence_upgrade = False
    if getattr(args, "change", None):
        context, error = context_or_error("validate-brief", args.change)
        if error:
            return error
        assert context is not None
        root, _, _, collaboration = context
        if collaboration["profile"] == PROFILE:
            try:
                events = read_events(root, collaboration)
            except ValueError as exc:
                violations.append(item("event_log_invalid", str(exc)))
                events = []
            recurrence_upgrade = any(
                event.get("event_type") == "finding_recorded" and event.get("systemic_upgrade_required") is True
                for event in events
            )
            goal = sections.get("本轮目标", "")
            scope = sections.get("任务范围", "")
            evidence = sections.get("交付证据", "")
            if collaboration.get("objective_id") not in goal or not re.search(r"Definition of Done|DoD|完成门", goal, re.I):
                violations.append(item("objective_definition_of_done_missing", "本轮目标必须标识 objective 与 Definition of Done", "本轮目标"))
            if not re.search(r"任务级|required task|完成门", scope, re.I):
                violations.append(item("task_level_gate_missing", "任务范围必须声明任务级完成门", "任务范围"))
            if not re.search(r"checkpoint.*(?:不|内部)|(?:不|内部).*checkpoint", evidence, re.I):
                violations.append(item("checkpoint_internal_policy_missing", "交付证据必须声明 checkpoint 只供内部使用", "交付证据"))
            if not re.search(r"review_ready|blocked", evidence):
                violations.append(item("report_stopping_policy_missing", "交付证据必须把 Report 限定为 review_ready 或 blocked", "交付证据"))

    if recurrence_upgrade or args.assumption_invalid:
        goal = sections.get("本轮目标", "")
        constraints = sections.get("硬约束", "")
        if not re.search(r"根因|系统性|结构性|完整边界审计|边界治理", goal):
            violations.append(item("root_cause_escalation_missing", "复发或假设失效时目标未升级为系统治理", "本轮目标"))
        if not re.search(r"禁止.*(?:逐函数|逐问题|逐点|局部|兼容|补丁)", constraints):
            violations.append(item("point_patch_prohibition_missing", "复发或假设失效时未禁止点补丁", "硬约束"))

    blockers = sections.get("阻断边界", "")
    if re.search(r"普通测试失败|测试失败|构建失败|编译失败|实现困难", blockers):
        violations.append(item("ordinary_failure_marked_blocker", "普通失败或实现困难被列为阻断", "阻断边界"))
    allowed = re.compile(r"用户.{0,8}(?:决策|确认|批准|选择|裁决)|产品决策|架构决策|权限|目录|不可逆|覆盖用户改动|外部凭据|规范")
    blocker_bullets = [line for line in blockers.splitlines() if re.match(r"^\s*[-*+]\s+", line)]
    blocker_clauses = [
        clause.strip()
        for line in blocker_bullets
        for clause in re.split(r"[、，,；;]|\b(?:or|and)\b|或|以及|和|与", re.sub(r"^\s*[-*+]\s+", "", line), flags=re.I)
        if clause.strip()
    ]
    if any(not allowed.search(clause) for clause in blocker_clauses):
        violations.append(item("blocker_out_of_scope", "阻断边界包含契约外条件", "阻断边界"))

    evidence = sections.get("交付证据", "")
    if "Execution Report" not in evidence:
        violations.append(item("execution_report_required", "交付证据未要求 Execution Report", "交付证据"))
    if not COMMAND_RE.search(evidence):
        violations.append(item("machine_verification_missing", "交付证据缺少可运行命令", "交付证据"))
    if not STOP_RE.search(evidence):
        violations.append(item("completion_boundary_missing", "交付证据未声明停止边界", "交付证据"))

    result = build_result("validate-brief", args.file, violations, sections=order, content_character_count=count, host=args.host)
    return result, 0 if not violations else 1


def validate_report(args: argparse.Namespace) -> tuple[dict, int]:
    text, violations = read_text(args.file)
    if text is None:
        return build_result("validate-report", args.file, violations), 2
    sections, order, parsed = parse_sections(text, REPORT_SECTIONS)
    violations.extend(parsed)
    count = cjk_count(text)
    if count < 80 or count > 500:
        violations.append(item("report_length_out_of_range", f"中文字符数 {count}，要求 80–500"))
    if SOURCE_BODY_RE.search(text):
        violations.append(item("project_truth_body_copied", "Report 复制了项目真源或 Handover 正文结构"))
    violations.extend(validate_source_boundaries(text, args.source_file))
    for name in REPORT_SECTIONS:
        if name in sections and not sections[name].strip():
            violations.append(item("empty_section", f"空区块：{name}", name))
    evidence = sections.get("验证证据", "")
    if not COMMAND_RE.search(evidence):
        violations.append(item("machine_verification_missing", "验证证据缺少可复跑命令", "验证证据"))
    if not re.search(r"repo://|docs://|https?://|(?:^|[\s`(])/(?!/)[^\s`]+", evidence):
        violations.append(item("evidence_path_missing", "验证证据缺少可审计路径或 URL", "验证证据"))
    report_status = ""
    if getattr(args, "change", None):
        context, error = context_or_error("validate-report", args.change)
        if error:
            return error
        assert context is not None
        _, _, _, collaboration = context
        if collaboration["profile"] == PROFILE:
            completion = sections.get("完成结果", "")
            match = re.search(r"(?:^|\n)\s*(?:status\s*[:：]\s*)?(review_ready|blocked)\b", completion, re.I)
            if not match:
                violations.append(item("report_status_invalid", "opt-in Report 的完成结果必须声明 review_ready 或 blocked", "完成结果"))
            else:
                report_status = match.group(1).lower()
            if report_status == "review_ready":
                required_links = {
                    "diff_evidence_missing": r"diff|差异|改动",
                    "matrix_evidence_missing": r"matrix|矩阵",
                    "receipt_evidence_missing": r"receipt|回执",
                    "task_state_evidence_missing": r"task|任务",
                }
                for code, pattern in required_links.items():
                    if not re.search(pattern, evidence, re.I):
                        violations.append(item(code, "review_ready Report 缺少必需的结构化证据索引", "验证证据"))
            elif report_status == "blocked" and not BLOCKER_ALLOWED_RE.search(completion):
                violations.append(item("blocker_out_of_scope", "blocked 仅允许未裁决决策、权限/目录扩大、不可逆操作、用户改动、外部凭据或规范冲突", "完成结果"))
    result = build_result("validate-report", args.file, violations, sections=order, content_character_count=count)
    if report_status:
        result["report_status"] = report_status
    return result, 0 if not violations else 1


def normalized_brief(text: str) -> dict[str, str]:
    sections, _, violations = parse_sections(text, BRIEF_SECTIONS)
    if violations:
        raise ValueError("brief structure is invalid")
    result: dict[str, str] = {}
    for name in BRIEF_SECTIONS:
        body = sections[name].lower()
        for host in HOST_NAMES:
            body = body.replace(host, "<host>")
        body = re.sub(r"[`*_#]", "", body)
        body = re.sub(r"^\s*[-+]\s*", "", body, flags=re.M)
        result[name] = re.sub(r"\s+", "", body)
    return result


def parity(args: argparse.Namespace) -> tuple[dict, int]:
    files = {"claude-code": args.claude_code, "codex": args.codex, "workbuddy": args.workbuddy}
    semantics: dict[str, dict[str, str]] = {}
    violations: list[dict[str, str]] = []
    for host, path in files.items():
        text, read_violations = read_text(path)
        if read_violations:
            violations.extend(read_violations)
            continue
        try:
            semantics[host] = normalized_brief(text or "")
        except ValueError as exc:
            violations.append(item("parity_input_invalid", f"{host}: {exc}"))
    mismatched: list[str] = []
    if not violations:
        baseline = semantics["claude-code"]
        mismatched = [name for name in BRIEF_SECTIONS if any(semantics[host][name] != baseline[name] for host in ("codex", "workbuddy"))]
        if mismatched:
            violations.append(item("parity_mismatch", "三宿主 Brief 语义不一致：" + ", ".join(mismatched)))
    result = build_result("parity", None, violations, files=files, mismatched_sections=mismatched)
    return result, 0 if not violations else 1


def handover_decision(args: argparse.Namespace) -> tuple[dict, int]:
    if args.reason in ("interrupted", "long-pause", "explicit-request"):
        action = "generate"
    elif args.reason == "executor-change" and not args.project_source_sufficient:
        action = "generate"
    else:
        action = "none"
    return {
        "command": "handover-decision",
        "valid": True,
        "reason": args.reason,
        "project_source_sufficient": args.project_source_sufficient,
        "handover_action": action,
        "violations": [],
    }, 0


def start_objective(args: argparse.Namespace) -> tuple[dict, int]:
    context, error = context_or_error("start", args.change)
    if error:
        return error
    assert context is not None
    root, path, text, collaboration = context
    if collaboration.get("profile") == PROFILE:
        try:
            current_authorization_violations = authorization_current_violations(
                root, read_events(root, collaboration)
            )
        except ValueError as exc:
            current_authorization_violations = [item(str(exc), "resume authorization history 无法重算")]
        if current_authorization_violations:
            return build_result(
                "start", None, current_authorization_violations, changed=False,
                blocking_reasons=[entry["code"] for entry in current_authorization_violations],
            ), 1
        schema_violations = matrix_schema_current_violations(root, args.change, collaboration)
        if schema_violations:
            return build_result(
                "start", None, schema_violations, changed=False,
                blocking_reasons=[entry["code"] for entry in schema_violations],
            ), 1
    if yaml_nested_values(text, "openspec").get("spec_review_confirmed") != "true":
        return violation_result("start", "spec_review_not_confirmed", "用户尚未确认 OpenSpec review")
    implementation = yaml_nested_values(text, "implementation")
    expected_isolation = implementation.get("worktree_path", "")
    if implementation.get("isolation") == "worktree" and Path(expected_isolation).resolve() != root:
        return violation_result("start", "isolation_mismatch", "state worktree 与当前已核实代码根不一致")
    try:
        events_path = logical_repo_path(root, args.events)
        matrix_path = logical_repo_path(root, args.matrix)
    except ValueError as exc:
        return violation_result("start", str(exc), "events/matrix 必须使用安全 repo:// 路径")
    validation_root = validation_root_for(root, args.change)
    if validation_root not in events_path.parents or validation_root not in matrix_path.parents:
        return violation_result("start", "artifact_path_outside_validation_root", "loop artifacts 必须位于 Change validation/reviewer-executor 下")
    manifest_reference = ""
    subject_digest = ""
    manifest_projection: dict = {}
    if args.objective_plan:
        try:
            manifest_reference, subject_digest, manifest_projection = load_manifest_opt_in(
                root, args.change, args.objective, args.objective_plan, validation_root
            )
        except ValueError as exc:
            return violation_result("start", str(exc), "objective plan 或 subject manifest 无效")
    if not ROUND_ID_RE.fullmatch(args.round):
        return violation_result("start", "round_id_invalid", "round id 必须使用 round-NN")
    if (
        args.objective_plan
        and collaboration["profile"] != PROFILE
        and int(manifest_projection.get("objective_order", 0)) != 1
    ):
        return violation_result("start", "objective_sequence_invalid", "ordered plan 必须从首个 objective 启动")
    if collaboration["profile"] == PROFILE:
        same = (
            collaboration["objective_id"] == args.objective
            and collaboration["round_id"] == args.round
            and collaboration["loop_events"] == args.events
            and collaboration["boundary_matrix"] == args.matrix
            and collaboration.get("objective_plan", "") == (args.objective_plan or "")
            and collaboration.get("subject_manifest", "") == manifest_reference
        )
        if not same:
            if (
                not args.objective_plan
                or collaboration.get("objective_plan") != args.objective_plan
                or collaboration["phase"] != "accepted"
                or collaboration["objective_id"] == args.objective
                or args.round != "round-01"
            ):
                return violation_result("start", "objective_conflict", "已有 Reviewer–Executor objective 与请求不一致")
            requested = dict(collaboration)
            requested["objective_id"] = args.objective
            requested["round_id"] = args.round
            requested["subject_manifest"] = manifest_reference
            try:
                objectives, _, candidate = current_plan_context(root, text, args.change, requested)
                current = next(entry for entry in objectives if entry["objective_id"] == collaboration["objective_id"])
                assignment_violations = objective_assignment_violations(root, collaboration, objectives)
                if assignment_violations:
                    return build_result("start", None, assignment_violations, changed=False), 1
                if int(candidate["order"]) != int(current["order"]) + 1:
                    return violation_result("start", "objective_sequence_invalid", "只能启动 ordered plan 的下一个 objective")
                _, predecessor_evaluations = accepted_current_evaluation(
                    root, text, args.change, requested, include_current=False
                )
            except (ValueError, StopIteration) as exc:
                return violation_result("start", str(exc), "后续 objective 无法验证")
            invalid_predecessors = [
                entry for entry in predecessor_evaluations
                if not entry.get("accepted_current") and not entry.get("coverage_satisfied")
            ]
            stale_ids = {
                str(entry["objective_id"])
                for entry in invalid_predecessors
                if entry.get("reason") == "accepted_objective_subject_stale"
            }
            non_stale_invalid = [
                entry for entry in invalid_predecessors if entry.get("reason") != "accepted_objective_subject_stale"
            ]
            remediates = set(candidate.get("remediates", []))
            if non_stale_invalid or (stale_ids and not stale_ids.issubset(remediates)):
                violations = accepted_current_violations(invalid_predecessors, "start-subsequent")
                return build_result(
                    "start", None, violations, changed=False,
                    blocking_reasons=[entry["code"] for entry in violations],
                    accepted_current=predecessor_evaluations,
                ), 1
            candidate_subject_ids = {entry["subject_id"] for entry in manifest_projection.get("subjects", [])}
            for stale_id in stale_ids:
                try:
                    _, _, stale_projection = load_manifest_opt_in(
                        root, args.change, stale_id, args.objective_plan, validation_root
                    )
                except ValueError as exc:
                    return violation_result("start", str(exc), "remediation predecessor subject 无法重算")
                stale_subject_ids = {entry["subject_id"] for entry in stale_projection.get("subjects", [])}
                if not stale_subject_ids.issubset(candidate_subject_ids):
                    return violation_result(
                        "start", "accepted_objective_subject_stale", "remediation objective 未完整覆盖 stale predecessor subjects"
                    )
            collaboration.update(
                {
                    "objective_id": args.objective,
                    "round_id": args.round,
                    "phase": "planned",
                    "boundary_matrix": args.matrix,
                    "latest_report": "",
                    "latest_receipts": "[]",
                    "termination": "",
                    "subject_manifest": manifest_reference,
                }
            )
            commit_state_event(
                root,
                path,
                text,
                collaboration,
                "objective_planned",
                change_id=args.change,
                objective_id=args.objective,
                round_id=args.round,
                actor="reviewer",
                objective_order=manifest_projection.get("objective_order"),
                objective_purpose=manifest_projection.get("objective_purpose"),
                required_task_ids=[entry["task_id"] for entry in manifest_projection.get("required_tasks", [])],
                subject_digest=subject_digest,
                subject_ids=sorted(candidate_subject_ids),
                remediates=sorted(remediates),
                boundary_matrix=args.matrix,
                **({
                    "subject_schema_version": 2,
                    "subject_normalization_version": 2,
                } if manifest_projection.get("schema_version") == 2 else {}),
            )
            return build_result(
                "start", None, [], applicable=True, changed=True, phase="planned",
                manifest_enabled=True, subject_digest=subject_digest,
                stale_predecessors=sorted(stale_ids), remediation=bool(stale_ids),
            ), 0
        if args.objective_plan:
            return build_result(
                "start", None, [], applicable=True, changed=False, phase=collaboration["phase"],
                manifest_enabled=True, subject_digest=subject_digest,
            ), 0
        return build_result("start", None, [], applicable=True, changed=False, phase=collaboration["phase"]), 0

    collaboration.update(
        {
            "profile": PROFILE,
            "objective_id": args.objective,
            "round_id": args.round,
            "phase": "planned",
            "loop_events": args.events,
            "boundary_matrix": args.matrix,
            "latest_report": "",
            "latest_receipts": "[]",
            "termination": "",
        }
    )
    if args.objective_plan:
        collaboration.update(
            {
                "objective_plan": args.objective_plan,
                "subject_manifest": manifest_reference,
            }
        )
    events_path.parent.mkdir(parents=True, exist_ok=True)
    event_fields: dict[str, object] = {}
    if args.objective_plan:
        event_fields = {
            "objective_order": manifest_projection.get("objective_order"),
            "objective_purpose": manifest_projection.get("objective_purpose"),
            "required_task_ids": [entry["task_id"] for entry in manifest_projection.get("required_tasks", [])],
            "subject_digest": subject_digest,
            "subject_ids": [entry["subject_id"] for entry in manifest_projection.get("subjects", [])],
            "boundary_matrix": args.matrix,
        }
        if manifest_projection.get("schema_version") == 2:
            event_fields.update({
                "subject_schema_version": 2,
                "subject_normalization_version": 2,
            })
    commit_state_event(
        root,
        path,
        text,
        collaboration,
        "objective_planned",
        change_id=args.change,
        objective_id=args.objective,
        round_id=args.round,
        actor="reviewer",
        **event_fields,
    )
    if args.objective_plan:
        return build_result(
            "start", None, [], applicable=True, changed=True, phase="planned",
            manifest_enabled=True, subject_digest=subject_digest,
        ), 0
    return build_result("start", None, [], applicable=True, changed=True, phase="planned"), 0


LEGAL_TRANSITIONS = {
    "planned": {"executing"},
    "executing": {"checkpoint", "blocked"},
    "checkpoint": {"executing", "blocked"},
}


def resume_objective(args: argparse.Namespace) -> tuple[dict, int]:
    context, error = context_or_error("resume", args.change, recover_history=True)
    if error:
        return error
    assert context is not None
    root, path, text, collaboration = context
    if collaboration["profile"] != PROFILE:
        return violation_result("resume", "profile_not_active", "Reviewer–Executor profile 未启用")
    events = read_events(root, collaboration)
    head = events[-1] if events and events[-1].get("event_id") == collaboration.get("event_head") else {}
    if collaboration.get("phase") == "executing" and head.get("event_type") == "objective_resumed":
        if head.get("authorization") != args.authorization:
            return violation_result("resume", "objective_not_blocked", "当前 objective 已不处于 blocked")
        try:
            current_authorization = sha256_file(logical_repo_path(root, str(head["authorization"]), must_exist=True))
            current_approval = sha256_file(logical_repo_path(root, str(head["approval_evidence"]), must_exist=True))
        except (KeyError, ValueError, FileNotFoundError, OSError):
            return violation_result("resume", "resume_authorization_evidence_changed", "resume evidence 已不再匹配")
        if (
            current_authorization != head.get("authorization_sha256")
            or current_approval != head.get("approval_evidence_sha256")
        ):
            return violation_result("resume", "resume_authorization_evidence_changed", "resume evidence 已不再匹配")
        return build_result(
            "resume", None, [], valid=True, changed=False, phase="executing",
            history_recovered=collaboration.get("_history_recovered") == "true",
        ), 0
    if collaboration.get("phase") != "blocked" or collaboration.get("termination") == "explicit":
        return violation_result("resume", "objective_not_blocked", "只有当前 blocked objective 可以恢复")
    if head.get("event_type") != "blocked":
        return violation_result("resume", "resume_blocked_event_stale", "当前 event head 不是 blocked event")
    resume_timestamp = now_iso()
    try:
        authorization = validate_resume_authorization(
            root, args.change, collaboration, head, args.authorization, resume_timestamp
        )
    except ValueError as exc:
        reason = str(exc)
        if reason == "resume_blocked_event_stale":
            try:
                envelope = load_strict_json_object(
                    logical_repo_path(root, args.authorization, must_exist=True),
                    "resume_authorization_invalid",
                )
                bound_event = envelope.get("blocked_event_id")
                if any(
                    event.get("event_type") == "objective_resumed"
                    and event.get("blocked_event_id") == bound_event
                    for event in events
                ):
                    reason = "resume_authorization_stale"
            except (ValueError, FileNotFoundError):
                pass
        return violation_result("resume", reason, "blocked objective authorization 无效")
    collaboration["phase"] = "executing"
    commit_state_event(
        root,
        path,
        text,
        collaboration,
        "objective_resumed",
        change_id=args.change,
        objective_id=collaboration["objective_id"],
        round_id=collaboration["round_id"],
        actor="executor",
        from_phase="blocked",
        to_phase="executing",
        _event_timestamp=resume_timestamp,
        **authorization,
    )
    return build_result(
        "resume", None, [], changed=True, phase="executing",
        blocked_event_id=authorization["blocked_event_id"],
        approval_authority=authorization["approval_authority"],
        history_recovered=collaboration.get("_history_recovered") == "true",
    ), 0


def transition_objective(args: argparse.Namespace) -> tuple[dict, int]:
    context, error = context_or_error("transition", args.change, recover_history=True)
    if error:
        return error
    assert context is not None
    root, path, text, collaboration = context
    if collaboration["profile"] != PROFILE:
        return violation_result("transition", "profile_not_active", "Reviewer–Executor profile 未启用")
    current = collaboration["phase"]
    if args.to == current:
        return build_result(
            "transition", None, [], valid=True, changed=False, phase=current,
            history_recovered=collaboration.get("_history_recovered") == "true"
        ), 0
    if args.to not in LEGAL_TRANSITIONS.get(current, set()):
        return violation_result("transition", "illegal_transition", f"非法 round transition：{current} -> {args.to}", phase=current)
    blocker_fields: dict[str, object] = {}
    if args.to == "blocked":
        if collaboration.get("objective_plan"):
            if (
                args.blocker_category not in STRUCTURED_BLOCKER_CATEGORIES
                or not args.blocker_code
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.blocker_code)
                or not args.required_decision
            ):
                return violation_result("transition", "blocker_out_of_scope", "manifest path blocked 必须使用允许的 structured blocker")
            try:
                _, _, projection = current_subject_context(root, args.change, collaboration)
                current_subject_ids = {entry["subject_id"] for entry in projection["subjects"]}
            except ValueError as exc:
                return violation_result("transition", str(exc), "structured blocker subject 无法验证")
            affected_subjects = sorted(set(args.affected_subject))
            if not affected_subjects or not set(affected_subjects).issubset(current_subject_ids):
                return violation_result("transition", "verification_subject_mapping_mismatch", "blocker affected subjects 不属于当前 objective")
            for reference in args.evidence_ref:
                try:
                    logical_repo_path(root, reference, must_exist=True)
                except (ValueError, FileNotFoundError):
                    return violation_result("transition", "blocker_evidence_missing", "structured blocker evidence 不可解析")
            blocker_fields = {
                "blocker_category": args.blocker_category,
                "blocker_code": args.blocker_code,
                "affected_subjects": affected_subjects,
                "evidence_refs": args.evidence_ref,
                "required_decision": args.required_decision,
            }
        else:
            if not args.blocker:
                return violation_result("transition", "blocker_evidence_missing", "blocked transition 必须说明真实 blocker", phase=current)
            if not BLOCKER_ALLOWED_RE.search(args.blocker):
                return violation_result("transition", "blocker_out_of_scope", "普通测试失败或实现困难不是 blocker", phase=current)
    collaboration["phase"] = args.to
    commit_state_event(
        root,
        path,
        text,
        collaboration,
        "checkpointed" if args.to == "checkpoint" else ("blocked" if args.to == "blocked" else "round_started"),
        change_id=args.change,
        objective_id=collaboration["objective_id"],
        round_id=collaboration["round_id"],
        actor="executor",
        blocker=args.blocker or "",
        **blocker_fields,
        from_phase=current,
        to_phase=args.to,
    )
    return build_result(
        "transition", None, [], changed=True, phase=args.to,
        history_recovered=collaboration.get("_history_recovered") == "true"
    ), 0


def record_finding(args: argparse.Namespace) -> tuple[dict, int]:
    context, error = context_or_error("record-finding", args.change, recover_history=True)
    if error:
        return error
    assert context is not None
    root, path, text, collaboration = context
    if collaboration["profile"] != PROFILE:
        return violation_result("record-finding", "profile_not_active", "Reviewer–Executor profile 未启用")
    if args.recurrence_count is not None:
        return violation_result("record-finding", "manual_recurrence_forbidden", "复发次数必须从 durable finding history 派生")
    if not all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value) for value in (args.defect_class, args.boundary, args.requirement)):
        return violation_result("record-finding", "finding_id_invalid", "defect class、boundary 与 requirement 必须使用稳定 ID")
    try:
        events = read_events(root, collaboration)
    except ValueError as exc:
        return violation_result("record-finding", "event_log_invalid", str(exc))
    matching = [
        event
        for event in events
        if event.get("event_type") == "finding_recorded"
        and event.get("objective_id") == collaboration["objective_id"]
        and event.get("defect_class") == args.defect_class
        and event.get("boundary_id") == args.boundary
    ]
    occurrence = len(matching) + 1
    previous_round_requirement = any(
        event.get("event_type") == "finding_recorded"
        and event.get("objective_id") == collaboration["objective_id"]
        and event.get("requirement_id") == args.requirement
        and event.get("round_id") != collaboration["round_id"]
        for event in events
    )
    upgrade = occurrence >= 2 or args.composition_failure or args.assumption_invalid or previous_round_requirement
    commit_state_event(
        root,
        path,
        text,
        collaboration,
        "finding_recorded",
        change_id=args.change,
        objective_id=collaboration["objective_id"],
        round_id=collaboration["round_id"],
        actor="reviewer",
        defect_class=args.defect_class,
        boundary_id=args.boundary,
        requirement_id=args.requirement,
        occurrence_count=occurrence,
        composition_failure=args.composition_failure,
        assumption_invalid=args.assumption_invalid,
        systemic_upgrade_required=upgrade,
    )
    return build_result(
        "record-finding",
        None,
        [],
        occurrence_count=occurrence,
        systemic_upgrade_required=upgrade,
        derived_from=collaboration["loop_events"],
    ), 0


def parse_boundary_matrix(path: Path) -> tuple[dict[str, str], list[dict[str, str]]]:
    top: dict[str, str] = {}
    rows: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_]+):\s*(.*?)\s*$", raw)
        if match:
            top[match.group(1)] = clean_yaml_scalar(match.group(2))
            continue
        match = re.match(r"^  - ([A-Za-z0-9_]+):\s*(.*?)\s*$", raw)
        if match:
            current = {match.group(1): clean_yaml_scalar(match.group(2)), "_line": str(line_number)}
            rows.append(current)
            continue
        match = re.match(r"^    ([A-Za-z0-9_]+):\s*(.*?)\s*$", raw)
        if match and current is not None:
            current[match.group(1)] = clean_yaml_scalar(match.group(2))
            continue
        raise ValueError(f"boundary_matrix_invalid:{line_number}")
    return top, rows


def split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.strip("[]").split(",") if part.strip()]


def boundary_matrix_has_unknown_fields(
    version: int, top: dict[str, str], rows: list[dict[str, str]]
) -> bool:
    allowed_top = {
        "schema_version", "normalization_version", "change_id", "objective_id", "round_id",
        "diff_base", "diff_artifact", "subject_manifest", "subject_digest", "rows",
    }
    allowed_row = {
        "_line", "row_id", "requirement_id", "scenario_id", "boundary_id",
        "owner", "invariant", "required_evidence", "evidence_refs", "status", "waiver_evidence",
        "subject_ids", "systemic_closure",
    }
    if version == 2:
        allowed_row.add("capability_id")
    return bool(set(top) - allowed_top or any(set(row) - allowed_row for row in rows))


def receipt_allowed_keys(required: tuple[str, ...], manifest_enabled: bool, subject_version: int) -> set[str]:
    allowed = set(required) | {
        "change_id", "objective_id", "round_id", "stdout_sha256", "stderr_sha256",
    }
    if manifest_enabled:
        allowed |= {"manifest", "subject_digest", "subject_ids", "verification_tier", "host"}
    if subject_version == 2:
        allowed |= {"subject_schema_version", "subject_normalization_version"}
    return allowed


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_receipt(
    root: Path, receipt_path: Path, collaboration: dict[str, str], expected_commit: str, expected_tree: str,
    *, change: str = "", expected_gate: str | None = None,
) -> tuple[dict | None, list[dict[str, str]]]:
    violations: list[dict[str, str]] = []
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, [item("boundary_evidence_missing", f"receipt 不可读：{receipt_path}")]
    required = (
        "schema_version",
        "command",
        "cwd",
        "git_commit",
        "source_tree",
        "isolation_id",
        "batch_id",
        "sequence",
        "started_at",
        "finished_at",
        "exit_code",
        "result",
        "evidence_type",
        "artifacts",
    )
    if not isinstance(receipt, dict) or any(key not in receipt for key in required):
        return None, [item("receipt_schema_invalid", f"receipt 字段不完整：{receipt_path}")]
    manifest_enabled = bool(collaboration.get("objective_plan") and collaboration.get("subject_manifest"))
    base_allowed_receipt_keys = receipt_allowed_keys(required, False, 1)
    if receipt.get("schema_version") != 1:
        violations.append(item("receipt_schema_invalid", f"receipt schema version 不受支持：{receipt_path}"))
    if not manifest_enabled and set(receipt) - base_allowed_receipt_keys:
        violations.append(item("receipt_schema_invalid", f"v1 receipt 含未知字段：{receipt_path}"))
    projection: dict = {}
    if manifest_enabled:
        extra_required = ("change_id", "objective_id", "manifest", "subject_digest", "subject_ids", "verification_tier", "host")
        if any(key not in receipt for key in extra_required):
            violations.append(item("receipt_schema_invalid", f"manifest receipt 字段不完整：{receipt_path}"))
        else:
            try:
                manifest_reference, current_digest, projection = verification_subject_context(
                    root, change, collaboration, expected_gate
                )
            except ValueError as exc:
                violations.append(item(str(exc), "当前 verification subject 无法重算"))
            else:
                allowed_receipt_keys = receipt_allowed_keys(
                    required, True, int(projection.get("schema_version", 0))
                )
                if set(receipt) - allowed_receipt_keys:
                    violations.append(item(
                        "receipt_schema_invalid",
                        f"v{projection.get('schema_version')} receipt 含未知字段：{receipt_path}",
                    ))
                if receipt.get("change_id") != change or receipt.get("objective_id") != collaboration["objective_id"]:
                    violations.append(item("receipt_objective_mismatch", f"receipt change/objective 不匹配：{receipt_path}"))
                if receipt.get("manifest") != manifest_reference:
                    violations.append(item("verification_subject_mapping_mismatch", f"receipt manifest pointer 不匹配：{receipt_path}"))
                if receipt.get("subject_digest") != current_digest:
                    violations.append(item("verification_subject_digest_mismatch", f"receipt subject digest 已失效：{receipt_path}"))
                projection_version = (projection.get("schema_version"), projection.get("normalization_version"))
                receipt_version = (
                    receipt.get("subject_schema_version", 1),
                    receipt.get("subject_normalization_version", 1),
                )
                if receipt_version != projection_version:
                    violations.append(item("verification_subject_version_mismatch", f"receipt subject version 不匹配：{receipt_path}"))
                if projection_version == (1, 1) and (
                    "subject_schema_version" in receipt or "subject_normalization_version" in receipt
                ):
                    violations.append(item("receipt_schema_invalid", f"v1 receipt 不得伪装 versioned subject：{receipt_path}"))
                expected_subject_ids = sorted(entry["subject_id"] for entry in projection["subjects"])
                if sorted(receipt.get("subject_ids", [])) != expected_subject_ids:
                    violations.append(item("verification_subject_mapping_mismatch", f"receipt subject IDs 不完整：{receipt_path}"))
                expected_tier = next(
                    (tier for tier, gate in VERIFICATION_TIER_GATES.items() if gate == expected_gate), None
                )
                if expected_tier and receipt.get("verification_tier") != expected_tier:
                    violations.append(item("verification_tier_not_eligible", f"receipt tier 不适用于 {expected_gate}：{receipt_path}"))
                if not receipt_provenance_authorized(root, receipt, projection):
                    violations.append(item("receipt_provenance_unauthorized", f"receipt provenance 未获 verification contract 授权：{receipt_path}"))
    else:
        if receipt["git_commit"] != expected_commit:
            violations.append(item("receipt_commit_stale", f"receipt commit 与当前 commit 不一致：{receipt_path}"))
        if receipt.get("source_tree") != expected_tree:
            violations.append(item("receipt_source_tree_stale", f"receipt source tree 与当前源码不一致：{receipt_path}"))
        if receipt["cwd"] != str(root):
            violations.append(item("receipt_cwd_mismatch", f"receipt cwd 与当前代码根不一致：{receipt_path}"))
        if receipt["isolation_id"] != str(root):
            violations.append(item("receipt_isolation_mismatch", f"receipt isolation 与当前 worktree 不一致：{receipt_path}"))
    if receipt["exit_code"] != 0 or receipt["result"] != "passed":
        violations.append(item("receipt_result_failed", f"receipt 未通过：{receipt_path}"))
    if not manifest_enabled and (
        receipt.get("objective_id") != collaboration["objective_id"] or receipt.get("round_id") != collaboration["round_id"]
    ):
        violations.append(item("receipt_round_mismatch", f"receipt objective/round 与当前状态不一致：{receipt_path}"))
    if not isinstance(receipt["command"], list) or not receipt["command"]:
        violations.append(item("receipt_schema_invalid", f"receipt command 必须是 argv：{receipt_path}"))
    if not isinstance(receipt["sequence"], int) or receipt["sequence"] < 1:
        violations.append(item("receipt_order_invalid", f"receipt sequence 无效：{receipt_path}"))
    if not isinstance(receipt["artifacts"], list):
        violations.append(item("receipt_schema_invalid", f"receipt artifacts 必须是列表：{receipt_path}"))
    else:
        for artifact in receipt["artifacts"]:
            try:
                artifact_path = logical_repo_path(root, artifact["path"], must_exist=True)
                if sha256_file(artifact_path) != artifact["sha256"]:
                    code = "receipt_artifact_integrity_invalid" if manifest_enabled else "receipt_artifact_hash_mismatch"
                    violations.append(item(code, f"artifact hash 不一致：{artifact['path']}"))
            except (KeyError, TypeError, ValueError, FileNotFoundError):
                code = "receipt_artifact_integrity_invalid" if manifest_enabled else "boundary_evidence_missing"
                violations.append(item(code, f"receipt artifact 不可解析：{artifact}"))
    return receipt, violations


def run_receipt(args: argparse.Namespace) -> tuple[dict, int]:
    context, error = context_or_error("run-receipt", args.change, recover_history=True)
    if error:
        return error
    assert context is not None
    root, _, text, collaboration = context
    if collaboration["profile"] != PROFILE:
        return violation_result("run-receipt", "profile_not_active", "Reviewer–Executor profile 未启用")
    try:
        authorization_violations = authorization_current_violations(root, read_events(root, collaboration))
    except ValueError as exc:
        authorization_violations = [item(str(exc), "resume authorization history 无法重算")]
    if authorization_violations:
        return build_result(
            "run-receipt", None, authorization_violations, changed=False,
            blocking_reasons=[entry["code"] for entry in authorization_violations],
        ), 1
    schema_violations = matrix_schema_current_violations(root, args.change, collaboration)
    if schema_violations:
        return build_result(
            "run-receipt", None, schema_violations, changed=False,
            blocking_reasons=[entry["code"] for entry in schema_violations],
        ), 1
    manifest_enabled = bool(collaboration.get("objective_plan") and collaboration.get("subject_manifest"))
    dirty_source = non_evidence_dirty_paths(root, args.change)
    if dirty_source and not manifest_enabled:
        return violation_result(
            "run-receipt", "source_worktree_dirty", "存在 receipts 无法覆盖的源码漂移", dirty_paths=dirty_source
        )
    implementation = yaml_nested_values(text, "implementation")
    if not manifest_enabled and (
        implementation.get("isolation") != "worktree" or Path(implementation.get("worktree_path", "")).resolve() != root
    ):
        return violation_result("run-receipt", "receipt_isolation_mismatch", "当前 worktree 与 state isolation 不一致")
    manifest_reference = ""
    current_digest = ""
    subject_ids: list[str] = []
    projection: dict = {}
    if manifest_enabled:
        if not args.verification_tier or not args.gate or not args.host:
            return violation_result("run-receipt", "verification_tier_not_eligible", "manifest receipt 必须声明 tier、gate 与 host")
        if VERIFICATION_TIER_GATES.get(args.verification_tier) != args.gate:
            return violation_result("run-receipt", "verification_tier_not_eligible", "verification tier 与 gate owner 不匹配")
        if args.verification_tier == "checkpoint_targeted" and collaboration["phase"] != "checkpoint":
            return violation_result("run-receipt", "verification_tier_not_eligible", "checkpoint receipt 只能在 checkpoint phase 生成")
        if args.verification_tier == "objective_scope" and collaboration["phase"] not in {"executing", "checkpoint"}:
            return violation_result("run-receipt", "verification_tier_not_eligible", "objective scope receipt 只能在 review-ready 申请时生成")
        if args.verification_tier in {"whole_change", "release"}:
            if collaboration["phase"] != "accepted":
                return violation_result(
                    "run-receipt", "verification_tier_not_eligible",
                    "whole-change/release receipt 只能在最后一个 objective accepted 后的对应 Change gate 生成",
                )
            preflight = objective_task_gate_violations(
                root, text, args.change, collaboration, whole_change=True
            )
            try:
                _, evaluations = accepted_current_evaluation(
                    root, text, args.change, collaboration, include_current=True
                )
                preflight.extend(accepted_current_violations(evaluations, args.gate))
            except ValueError as exc:
                preflight.append(item(str(exc), "Change gate verification subject 无法重算"))
            if preflight:
                return build_result(
                    "run-receipt", None, preflight, changed=False,
                    blocking_reasons=[entry["code"] for entry in preflight],
                ), 1
        try:
            manifest_reference, current_digest, projection = verification_subject_context(
                root, args.change, collaboration, args.gate
            )
        except ValueError as exc:
            return violation_result("run-receipt", str(exc), "当前 verification subject 无法重算")
        subject_ids = sorted(entry["subject_id"] for entry in projection["subjects"])
        provisional = {
            "cwd": str(root),
            "host": args.host,
            "isolation_id": str(root),
            "subject_ids": subject_ids,
        }
        if not receipt_provenance_authorized(root, provisional, projection):
            return violation_result("run-receipt", "receipt_provenance_unauthorized", "当前 provenance 未获 verification contract 授权")
    command = list(args.argv)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        return violation_result("run-receipt", "receipt_command_missing", "-- 后必须提供命令 argv")
    try:
        output = logical_repo_path(root, args.output)
        validation_root = validation_root_for(root, args.change)
        if validation_root not in output.parents:
            raise ValueError("receipt_path_outside_validation_root")
        artifacts = [
            {"path": reference, "sha256": sha256_file(logical_repo_path(root, reference, must_exist=True))}
            for reference in args.artifact
        ]
    except (ValueError, FileNotFoundError) as exc:
        return violation_result("run-receipt", str(exc), "receipt output/artifact 路径无效")
    commit = git_output(root, "rev-parse", "HEAD")
    source_tree = git_output(root, "rev-parse", "HEAD^{tree}")
    started = now_iso()
    completed = subprocess.run(command, cwd=root, text=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    finished = now_iso()
    receipt = {
        "schema_version": 1,
        "command": command,
        "cwd": str(root),
        "git_commit": commit,
        "source_tree": source_tree,
        "isolation_id": str(root),
        "change_id": args.change,
        "objective_id": collaboration["objective_id"],
        "round_id": collaboration["round_id"],
        "batch_id": args.batch,
        "sequence": args.sequence,
        "started_at": started,
        "finished_at": finished,
        "exit_code": completed.returncode,
        "result": "passed" if completed.returncode == 0 else "failed",
        "evidence_type": args.evidence_type,
        "artifacts": artifacts,
        "stdout_sha256": hashlib.sha256(completed.stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(completed.stderr).hexdigest(),
    }
    if manifest_enabled:
        subject_fields = {
            "manifest": manifest_reference,
            "subject_digest": current_digest,
            "subject_ids": subject_ids,
            "verification_tier": args.verification_tier,
            "host": args.host,
        }
        if projection.get("schema_version") == 2:
            subject_fields.update({
                "subject_schema_version": 2,
                "subject_normalization_version": 2,
            })
        receipt.update(subject_fields)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, output)
    result = build_result("run-receipt", str(output), [], receipt=receipt)
    return result, completed.returncode


def receipt_check(args: argparse.Namespace) -> tuple[dict, int]:
    context, error = context_or_error("receipt-check", args.change)
    if error:
        return error
    assert context is not None
    root, _, _, collaboration = context
    try:
        receipt_path = logical_repo_path(root, args.receipt, must_exist=True)
    except (ValueError, FileNotFoundError):
        return violation_result("receipt-check", "boundary_evidence_missing", "receipt 不可解析")
    receipt, violations = validate_receipt(
        root,
        receipt_path,
        collaboration,
        git_output(root, "rev-parse", "HEAD"),
        git_output(root, "rev-parse", "HEAD^{tree}"),
        change=args.change,
        expected_gate=args.gate,
    )
    return build_result(
        "receipt-check", str(receipt_path), violations, reusable=not violations,
        receipt_round=receipt.get("round_id") if receipt else None,
        blocking_reasons=[entry["code"] for entry in violations],
    ), 0 if not violations else 1


def systemic_boundaries(events: list[dict]) -> set[str]:
    return {
        str(event.get("boundary_id"))
        for event in events
        if event.get("event_type") == "finding_recorded" and event.get("systemic_upgrade_required") is True
    }


def review_ready(args: argparse.Namespace) -> tuple[dict, int]:
    context, error = context_or_error("review-ready", args.change, recover_history=True)
    if error:
        return error
    assert context is not None
    root, path, text, collaboration = context
    if collaboration["profile"] != PROFILE:
        return build_result("review-ready", None, [], applicable=False, changed=False, phase="none"), 0
    if collaboration["termination"] == "explicit":
        return violation_result("review-ready", "objective_terminated", "objective 已显式终止")
    already_ready = collaboration["phase"] == "review_ready"
    if collaboration["phase"] not in {"executing", "checkpoint", "review_ready"}:
        return violation_result("review-ready", "illegal_transition", f"当前 phase 不能申请 review_ready：{collaboration['phase']}")

    violations: list[dict[str, str]] = []
    dirty_source = non_evidence_dirty_paths(root, args.change)
    manifest_enabled = bool(collaboration.get("objective_plan") and collaboration.get("subject_manifest"))
    if dirty_source and not manifest_enabled:
        violations.append(item("source_worktree_dirty", "存在 receipts 之后的非证据源码漂移"))
    tasks_reference = yaml_nested_values(text, "openspec").get("tasks_path", "")
    tasks_repo_reference = tasks_reference if tasks_reference.startswith("repo://") else f"repo://{tasks_reference}"
    if manifest_enabled:
        violations.extend(objective_task_gate_violations(root, text, args.change, collaboration))
        try:
            _, predecessor_evaluations = accepted_current_evaluation(
                root, text, args.change, collaboration, include_current=False
            )
            predecessor_violations = accepted_current_violations(predecessor_evaluations, "review-ready")
            if current_remediation_covers(root, args.change, collaboration, predecessor_evaluations):
                predecessor_violations = [
                    entry for entry in predecessor_violations if entry["code"] != "accepted_objective_subject_stale"
                ]
            violations.extend(predecessor_violations)
        except ValueError as exc:
            violations.append(item(str(exc), "accepted predecessors 无法重算"))
    else:
        try:
            tasks_path = logical_repo_path(root, tasks_reference) if tasks_reference.startswith("repo://") else (root / tasks_reference).resolve()
            tasks_text = tasks_path.read_text(encoding="utf-8")
            if re.search(r"^[ \t]*- \[ \]", tasks_text, re.M):
                violations.append(item("task_completion_incomplete", "OpenSpec required tasks 仍有未完成项"))
        except OSError:
            violations.append(item("task_completion_incomplete", "OpenSpec tasks 文件不可读"))

    report_text = ""
    report_links: set[str] = set()
    if not args.report:
        violations.append(item("report_missing", "review-ready 必须提供 Execution Report"))
    else:
        source_files = []
        openspec = yaml_nested_values(text, "openspec")
        for key in ("proposal_path", "design_path", "tasks_path"):
            value = openspec.get(key, "")
            try:
                if not value:
                    raise ValueError("empty path")
                candidate = (root / value).resolve() if not value.startswith("repo://") else logical_repo_path(root, value)
                if candidate.is_file():
                    source_files.append(str(candidate))
                else:
                    violations.append(item("project_source_invalid", f"OpenSpec source 不可读：{key}"))
            except ValueError:
                violations.append(item("project_source_invalid", f"OpenSpec source 路径无效：{key}"))
        report_result, _ = validate_report(
            argparse.Namespace(file=args.report, source_file=source_files, change=args.change, json=True)
        )
        violations.extend(report_result["violations"])
        try:
            report_path = Path(args.report).resolve()
            report_path.relative_to(root)
            report_text = report_path.read_text(encoding="utf-8")
            report_links = repo_links(report_text)
            for reference in report_links:
                logical_repo_path(root, reference, must_exist=True)
        except ValueError:
            violations.append(item("report_path_outside_repository", "Execution Report 必须位于当前代码仓"))
        except (FileNotFoundError, OSError):
            violations.append(item("report_evidence_link_unresolved", "Execution Report 存在不可解析的 repo:// 证据链接"))

    receipt_refs: list[str] = []
    rows: list[dict[str, str]] = []
    matrix_reference = collaboration["boundary_matrix"]
    try:
        matrix_path = logical_repo_path(root, collaboration["boundary_matrix"], must_exist=True)
        top, rows = parse_boundary_matrix(matrix_path)
        try:
            matrix_version = boundary_matrix_version(top)
        except ValueError as exc:
            matrix_version = 0
            violations.append(item(str(exc), "matrix schema version 不受支持"))
        if boundary_matrix_has_unknown_fields(matrix_version, top, rows):
            violations.append(item("boundary_matrix_invalid", f"matrix schema v{matrix_version} 含未知字段"))
        if top.get("change_id") != args.change:
            violations.append(item("boundary_matrix_invalid", "matrix schema/change 不匹配"))
        if top.get("objective_id") != collaboration["objective_id"] or top.get("round_id") != collaboration["round_id"]:
            violations.append(item("boundary_matrix_invalid", "matrix objective/round 不匹配"))
        expected_subject_ids: set[str] = set()
        expected_evidence_by_subject: dict[str, set[str]] = {}
        matrix_subject_ids: set[str] = set()
        if manifest_enabled:
            try:
                manifest_reference, current_digest, projection = current_subject_context(root, args.change, collaboration)
                expected_subject_ids = {entry["subject_id"] for entry in projection["subjects"]}
                expected_evidence_by_subject = {
                    str(entry["subject_id"]): set(str(value) for value in entry.get("required_evidence", []))
                    for entry in projection["subjects"]
                }
                if matrix_version != projection.get("schema_version"):
                    violations.append(item(
                        "verification_subject_version_mismatch",
                        "matrix schema version 与当前 manifest 不一致",
                    ))
                if top.get("subject_manifest") != manifest_reference or top.get("subject_digest") != current_digest:
                    violations.append(item("verification_subject_mapping_mismatch", "matrix manifest pointer/digest 与当前 objective 不一致"))
            except ValueError as exc:
                violations.append(item(str(exc), "当前 verification subject 无法重算"))
        if not rows:
            violations.append(item("boundary_matrix_open", "matrix 没有 required rows"))
        all_spec_pairs = required_spec_pairs(root, args.change)
        if matrix_version == 1 and has_namespaced_spec_pairs(all_spec_pairs):
            violations.append(item(
                "verification_subject_schema_upgrade_required",
                "namespaced/mixed Change 必须在 review-ready 前使用 matrix schema v2",
            ))
        required_pairs = all_spec_pairs
        if manifest_enabled and "projection" in locals():
            try:
                declared_pairs = resolved_projection_obligation_pairs(projection, all_spec_pairs)
            except ValueError as exc:
                violations.append(item(str(exc), "current objective obligations 无法解析"))
                declared_pairs = set()
            unknown_declared = {
                pair for pair in declared_pairs
                if pair[0] != "@composition" and pair not in all_spec_pairs
            }
            for pair in sorted(unknown_declared):
                violations.append(item("spec_mapping_unknown", f"manifest 引用了未知 delta spec scenario：{pair[0]}/{pair[1]}"))
            required_pairs = {
                pair: all_spec_pairs.get(pair, "manifest-composition")
                for pair in declared_pairs
                if pair[0] == "@composition" or pair in all_spec_pairs
            }
        row_pairs: dict[tuple[str, ...], list[str]] = {}
        for row in rows:
            required_keys = ("row_id", "requirement_id", "scenario_id", "boundary_id", "owner", "invariant", "required_evidence", "evidence_refs", "status")
            if any(not row.get(key) for key in required_keys):
                violations.append(item("boundary_matrix_invalid", f"matrix row 字段不完整：{row.get('row_id', row.get('_line', '?'))}"))
                continue
            if manifest_enabled:
                row_subject_ids = set(split_csv(row.get("subject_ids", "")))
                if not row_subject_ids:
                    violations.append(item("verification_subject_mapping_mismatch", f"matrix row 缺少 subject IDs：{row.get('row_id', '?')}"))
                matrix_subject_ids.update(row_subject_ids)
                declared_types = set(split_csv(row.get("required_evidence", "")))
                manifest_types = set().union(
                    *(expected_evidence_by_subject.get(subject_id, set()) for subject_id in row_subject_ids)
                ) if row_subject_ids else set()
                if not manifest_types.issubset(declared_types):
                    violations.append(item("boundary_evidence_missing", f"matrix row 未声明 manifest required evidence：{row.get('row_id', '?')}"))
            try:
                pair = resolve_matrix_row_identity(matrix_version, row, required_pairs)
            except ValueError as exc:
                violations.append(item(str(exc), f"matrix row spec identity 无效：{row.get('row_id', '?')}"))
            else:
                row_pairs.setdefault(pair, []).append(row.get("row_id", row.get("_line", "?")))
            if row["status"] in {"open", "failed"}:
                violations.append(item("boundary_matrix_open", f"matrix row 未闭合：{row['row_id']}"))
            if row["status"] == "waived":
                waiver = row.get("waiver_evidence", "")
                try:
                    logical_repo_path(root, waiver, must_exist=True)
                except (ValueError, FileNotFoundError):
                    violations.append(item("boundary_waiver_evidence_missing", f"waiver 缺少用户证据：{row['row_id']}"))
            else:
                receipt_refs.extend(split_csv(row.get("evidence_refs", "")))
        missing_pairs = sorted(set(required_pairs) - set(row_pairs))
        unknown_pairs = sorted(set(row_pairs) - set(required_pairs))
        duplicate_pairs = sorted(pair for pair, row_ids in row_pairs.items() if len(row_ids) > 1)
        for pair in missing_pairs:
            violations.append(item("spec_mapping_incomplete", f"matrix 缺少 delta spec scenario：{'/'.join(pair)}"))
        for pair in unknown_pairs:
            violations.append(item("spec_mapping_unknown", f"matrix 引用了未知 delta spec scenario：{'/'.join(pair)}"))
        for pair in duplicate_pairs:
            violations.append(item("spec_mapping_duplicate", f"matrix 重复映射 delta spec scenario：{'/'.join(pair)}"))
        if manifest_enabled and matrix_subject_ids != expected_subject_ids:
            violations.append(item("verification_subject_mapping_mismatch", "matrix subject IDs 未完整且唯一映射当前 manifest"))

        diff_base = top.get("diff_base", "")
        diff_reference = top.get("diff_artifact", "")
        try:
            if not re.fullmatch(r"[0-9a-f]{40}", diff_base):
                raise ValueError("diff_base_invalid")
            resolved_base = git_output(root, "rev-parse", "--verify", f"{diff_base}^{{commit}}")
            if resolved_base != diff_base:
                raise ValueError("diff_base_invalid")
            diff_path = logical_repo_path(root, diff_reference, must_exist=True)
            # Review identity is the complete tracked workspace projection from
            # the approved base, not only committed HEAD.  This includes index
            # and working-tree bytes that formal verification may have read.
            diff_identity = diff_base if manifest_enabled else f"{diff_base}..HEAD"
            expected_diff = subprocess.run(
                ["git", "-C", str(root), "diff", "--binary", diff_identity],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout
            if diff_path.read_bytes() != expected_diff:
                expected_scope = "当前 tracked workspace" if manifest_enabled else "当前 HEAD"
                violations.append(item("diff_evidence_invalid", f"matrix diff artifact 不是 diff_base 到{expected_scope}的精确差异"))
            if manifest_enabled and "projection" in locals():
                review_sources = {
                    logical_repo_path(root, manifest_reference, must_exist=True),
                    logical_repo_path(root, collaboration["objective_plan"], must_exist=True),
                    logical_repo_path(root, tasks_repo_reference, must_exist=True),
                }
                for subject in projection.get("subjects", []):
                    for source in subject.get("semantic_inputs", []):
                        review_sources.add(logical_repo_path(root, source["path"], must_exist=True))
                    for reference in subject.get("refs", []):
                        target = logical_repo_path(root, reference, must_exist=False)
                        if target.is_file():
                            review_sources.add(target)
                untracked_sources = []
                for source in sorted(review_sources):
                    relative = source.relative_to(root).as_posix()
                    tracked = subprocess.run(
                        ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", relative],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    if tracked.returncode != 0:
                        untracked_sources.append(relative)
                if untracked_sources:
                    violations.append(item(
                        "verification_subject_diff_incomplete",
                        "canonical subject 含未进入 tracked review diff 的文件：" + ", ".join(untracked_sources),
                    ))
        except (ValueError, FileNotFoundError, OSError, subprocess.CalledProcessError):
            violations.append(item("diff_evidence_invalid", "matrix diff_base/diff_artifact 不可解析"))
    except (ValueError, FileNotFoundError, OSError) as exc:
        violations.append(item("boundary_matrix_open", f"matrix 不可用：{exc}"))

    required_report_links = {tasks_repo_reference, matrix_reference}
    if manifest_enabled and 'manifest_reference' in locals():
        required_report_links.add(manifest_reference)
    if 'diff_reference' in locals() and diff_reference:
        required_report_links.add(diff_reference)
    required_report_links.update(receipt_refs)
    for reference in sorted(required_report_links - report_links):
        violations.append(item("report_evidence_link_missing", f"Execution Report 缺少精确证据链接：{reference}"))

    receipts: list[dict] = []
    valid_receipts: list[dict] = []
    receipts_by_ref: dict[str, dict] = {}
    expected_commit = git_output(root, "rev-parse", "HEAD")
    expected_tree = git_output(root, "rev-parse", "HEAD^{tree}")
    for reference in dict.fromkeys(receipt_refs):
        try:
            receipt_path = logical_repo_path(root, reference, must_exist=True)
        except (ValueError, FileNotFoundError):
            violations.append(item("boundary_evidence_missing", f"matrix evidence 不存在：{reference}"))
            continue
        receipt, receipt_violations = validate_receipt(
            root, receipt_path, collaboration, expected_commit, expected_tree,
            change=args.change, expected_gate="review-ready",
        )
        violations.extend(receipt_violations)
        if receipt:
            receipts.append(receipt)
            receipts_by_ref[reference] = receipt
            if not receipt_violations:
                valid_receipts.append(receipt)
    if manifest_enabled and not any(receipt.get("verification_tier") == "objective_scope" for receipt in valid_receipts):
        violations.append(item("objective_scope_receipt_missing", "当前 objective 缺少有效 objective_scope receipt"))

    batches: dict[str, list[int]] = {}
    for receipt in receipts:
        if isinstance(receipt.get("sequence"), int):
            batches.setdefault(str(receipt.get("batch_id")), []).append(receipt["sequence"])
    for batch, sequences in batches.items():
        if sorted(sequences) != list(range(1, len(sequences) + 1)):
            violations.append(item("receipt_order_invalid", f"receipt batch 顺序无效：{batch}"))

    receipt_types_by_ref = {reference: receipt.get("evidence_type") for reference, receipt in receipts_by_ref.items()}
    for row in rows:
        if row.get("status") == "waived":
            continue
        required_types = set(split_csv(row.get("required_evidence", "")))
        present_types = {
            receipt_types_by_ref.get(reference)
            for reference in split_csv(row.get("evidence_refs", ""))
            if receipt_types_by_ref.get(reference)
        }
        if not required_types.issubset(present_types):
            violations.append(item("boundary_evidence_missing", f"matrix row 缺少 evidence type：{row.get('row_id', '?')}"))

    try:
        events = read_events(root, collaboration)
    except ValueError as exc:
        violations.append(item("event_log_invalid", str(exc)))
        events = []
    violations.extend(authorization_current_violations(root, events, collaboration["objective_id"]))
    for boundary in systemic_boundaries(events):
        boundary_rows = [row for row in rows if row.get("boundary_id") == boundary]
        if not boundary_rows or any(row.get("status") != "covered" for row in boundary_rows):
            violations.append(item("recurrence_upgrade_unresolved", f"复发边界尚未证明系统性闭合：{boundary}"))

    if violations:
        return build_result("review-ready", None, violations, applicable=True, changed=False, phase=collaboration["phase"], blocking_reasons=[entry["code"] for entry in violations]), 1

    try:
        report_reference = "repo://" + str(Path(args.report).resolve().relative_to(root))
    except ValueError:
        return violation_result("review-ready", "report_path_outside_repository", "Execution Report 必须位于当前代码仓", phase=collaboration["phase"])

    if not already_ready:
        collaboration["phase"] = "review_ready"
        collaboration["latest_report"] = report_reference
        collaboration["latest_receipts"] = "[" + ",".join(dict.fromkeys(receipt_refs)) + "]"
        ready_subject_fields: dict[str, object] = {}
        if manifest_enabled:
            ready_subject_fields = {
                "subject_manifest": manifest_reference,
                "subject_digest": current_digest,
                "subject_ids": sorted(expected_subject_ids),
                "subject_fingerprints": subject_fingerprints(projection),
                "subject_obligations": subject_obligations(projection),
            }
            if projection.get("schema_version") == 2:
                ready_subject_fields.update({
                    "subject_schema_version": 2,
                    "subject_normalization_version": 2,
                })
        review_artifact_hashes = {
            report_reference: sha256_file(report_path),
            matrix_reference: sha256_file(matrix_path),
            diff_reference: sha256_file(diff_path),
        }
        commit_state_event(
            root,
            path,
            text,
            collaboration,
            "review_ready_passed",
            change_id=args.change,
            objective_id=collaboration["objective_id"],
            round_id=collaboration["round_id"],
            actor="executor",
            report=collaboration["latest_report"],
            receipts=list(dict.fromkeys(receipt_refs)),
            review_artifact_hashes=review_artifact_hashes,
            authorization_obligations=authorization_obligations(events, collaboration["objective_id"]),
            **ready_subject_fields,
        )
    return build_result(
        "review-ready", None, [], applicable=True, changed=not already_ready, phase="review_ready",
        history_recovered=collaboration.get("_history_recovered") == "true", blocking_reasons=[]
    ), 0


def validate_feedback(path: str, collaboration: dict[str, str]) -> list[dict[str, str]]:
    text, violations = read_text(path)
    if text is None:
        return violations
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\s*[-*+]\s*([A-Za-z_]+)\s*[:：]\s*(.*?)\s*$", line)
        if match:
            values[match.group(1)] = match.group(2)
    for key in ("objective_id", "requirement_id", "boundary_id", "invariant", "evidence_gap"):
        if not values.get(key):
            violations.append(item("feedback_field_missing", f"review feedback 缺少：{key}"))
    if values.get("objective_id") and values["objective_id"] != collaboration["objective_id"]:
        violations.append(item("feedback_objective_mismatch", "review feedback objective 与当前状态不一致"))
    point_patch = re.search(
        r"(?:修改|编辑|删除|新增|替换|先.*再).{0,30}(?:[/\\][\w.-]+|\.(?:py|sh|js|ts|md)|\w+\s*\([^)]*\)|第\s*\d+\s*行)|逐(?:文件|函数|finding|问题)",
        text,
        re.I,
    )
    if point_patch:
        violations.append(item("point_patch_instruction", "review feedback 必须描述 objective/requirement/boundary/evidence gap，不能给 patch sequence"))
    return violations


def next_round_id(current: str) -> str:
    match = ROUND_ID_RE.fullmatch(current)
    if not match:
        raise ValueError("round_id_invalid")
    width = len(match.group(1))
    return f"round-{int(match.group(1)) + 1:0{width}d}"


def review_decision(args: argparse.Namespace) -> tuple[dict, int]:
    context, error = context_or_error("review-decision", args.change, recover_history=True)
    if error:
        return error
    assert context is not None
    root, path, text, collaboration = context
    if collaboration["profile"] != PROFILE:
        return violation_result("review-decision", "profile_not_active", "Reviewer–Executor profile 未启用")
    try:
        current_events = read_events(root, collaboration)
        current_authorization_violations = authorization_current_violations(
            root, current_events, collaboration["objective_id"]
        )
    except ValueError as exc:
        current_authorization_violations = [item(str(exc), "resume authorization history 无法重算")]
    if current_authorization_violations:
        return build_result(
            "review-decision", None, current_authorization_violations, changed=False,
            phase=collaboration["phase"],
            blocking_reasons=[entry["code"] for entry in current_authorization_violations],
        ), 1
    if collaboration.get("objective_plan") and collaboration.get("subject_manifest"):
        try:
            _, predecessor_evaluations = accepted_current_evaluation(
                root, text, args.change, collaboration, include_current=False
            )
            predecessor_violations = accepted_current_violations(predecessor_evaluations, "review-decision")
            if current_remediation_covers(root, args.change, collaboration, predecessor_evaluations):
                predecessor_violations = [
                    entry for entry in predecessor_violations
                    if entry["code"] != "accepted_objective_subject_stale"
                ]
        except ValueError as exc:
            predecessor_violations = [item(str(exc), "accepted predecessors 无法重算")]
        if predecessor_violations:
            return build_result(
                "review-decision", None, predecessor_violations, changed=False,
                phase=collaboration["phase"],
                blocking_reasons=[entry["code"] for entry in predecessor_violations],
            ), 1
    schema_violations = matrix_schema_current_violations(root, args.change, collaboration)
    if schema_violations:
        return build_result(
            "review-decision", None, schema_violations, changed=False,
            phase=collaboration["phase"],
            blocking_reasons=[entry["code"] for entry in schema_violations],
        ), 1
    if collaboration["phase"] == "accepted" and args.decision == "accepted":
        return build_result(
            "review-decision", None, [], changed=False, phase="accepted",
            round_id=collaboration["round_id"], termination=collaboration["termination"]
        ), 0
    if collaboration["termination"] == "explicit" and args.decision == "terminated":
        return build_result(
            "review-decision", None, [], changed=False, phase=collaboration["phase"],
            round_id=collaboration["round_id"], termination="explicit"
        ), 0
    if collaboration["phase"] != "review_ready":
        return violation_result("review-decision", "review_not_ready", "reviewer decision 只能发生在 review_ready")
    if args.decision == "changes-requested":
        if not args.feedback:
            return violation_result("review-decision", "feedback_missing", "changes-requested 必须提供 boundary-owned feedback")
        violations = validate_feedback(args.feedback, collaboration)
        try:
            feedback_reference = "repo://" + str(Path(args.feedback).resolve().relative_to(root))
        except ValueError:
            violations.append(item("feedback_path_outside_repository", "review feedback 必须位于当前代码仓"))
        if violations:
            return build_result("review-decision", None, violations, changed=False, phase="review_ready"), 1
        current_round = collaboration["round_id"]
        new_round = next_round_id(current_round)
        collaboration["round_id"] = new_round
        collaboration["phase"] = "executing"
        collaboration["latest_report"] = ""
        collaboration["latest_receipts"] = "[]"
        commit_state_event(
            root,
            path,
            text,
            collaboration,
            "changes_requested",
            change_id=args.change,
            objective_id=collaboration["objective_id"],
            round_id=new_round,
            actor="reviewer",
            reviewed_round=current_round,
            feedback=feedback_reference,
        )
    elif args.decision == "accepted":
        acceptance_fields: dict[str, object] = {}
        if collaboration.get("objective_plan"):
            try:
                manifest_reference, digest, projection = current_subject_context(root, args.change, collaboration)
                events = read_events(root, collaboration)
            except ValueError as exc:
                return violation_result("review-decision", str(exc), "accepted subject 无法冻结")
            ready_event = next(
                (
                    event for event in reversed(events)
                    if event.get("event_type") == "review_ready_passed"
                    and event.get("objective_id") == collaboration["objective_id"]
                    and event.get("round_id") == collaboration["round_id"]
                ),
                None,
            )
            current_subject_ids = sorted(entry["subject_id"] for entry in projection["subjects"])
            if (
                not ready_event
                or ready_event.get("subject_manifest") != manifest_reference
                or ready_event.get("subject_digest") != digest
                or ready_event.get("subject_ids") != current_subject_ids
            ):
                return violation_result(
                    "review-decision",
                    "verification_subject_digest_mismatch",
                    "当前 subject 与通过 review-ready 的冻结对象不一致",
                    changed=False,
                    phase="review_ready",
                )
            projection_version = (projection.get("schema_version"), projection.get("normalization_version"))
            ready_version = (
                ready_event.get("subject_schema_version", 1),
                ready_event.get("subject_normalization_version", 1),
            )
            if ready_version != projection_version:
                return violation_result(
                    "review-decision",
                    "verification_subject_version_mismatch",
                    "review-ready subject version 与当前 manifest 不一致",
                    changed=False,
                    phase="review_ready",
                )
            current_authorizations = authorization_obligations(events, collaboration["objective_id"])
            if ready_event.get("authorization_obligations", []) != current_authorizations:
                return violation_result(
                    "review-decision",
                    "resume_authorization_identity_mismatch",
                    "review-ready authorization obligations 与当前 history 不一致",
                    changed=False,
                    phase="review_ready",
                )
            frozen_artifacts = ready_event.get("review_artifact_hashes")
            if (
                ready_event.get("report") != collaboration.get("latest_report")
                or not isinstance(frozen_artifacts, dict)
                or not frozen_artifacts
            ):
                return violation_result(
                    "review-decision",
                    "review_ready_evidence_changed",
                    "review-ready 下游证据快照缺失或 identity 已改变",
                    changed=False,
                    phase="review_ready",
                )
            try:
                artifact_changed = any(
                    not isinstance(reference, str)
                    or not isinstance(expected_hash, str)
                    or sha256_file(logical_repo_path(root, reference, must_exist=True)) != expected_hash
                    for reference, expected_hash in frozen_artifacts.items()
                )
            except (ValueError, FileNotFoundError, OSError):
                artifact_changed = True
            if artifact_changed:
                return violation_result(
                    "review-decision",
                    "review_ready_evidence_changed",
                    "Report、boundary matrix 或 diff 已不再等于通过 review-ready 的证据",
                    changed=False,
                    phase="review_ready",
                )
            ready_receipts = ready_event.get("receipts", [])
            if (
                not isinstance(ready_receipts, list)
                or ready_receipts != split_csv(collaboration.get("latest_receipts", ""))
            ):
                return violation_result(
                    "review-decision",
                    "objective_scope_receipt_missing",
                    "当前 receipt 集合与通过 review-ready 的冻结集合不一致",
                    changed=False,
                    phase="review_ready",
                )
            receipt_violations: list[dict[str, str]] = []
            valid_receipts: list[dict] = []
            for reference in ready_receipts:
                try:
                    receipt_path = logical_repo_path(root, str(reference), must_exist=True)
                except (ValueError, FileNotFoundError):
                    receipt_violations.append(item("boundary_evidence_missing", f"review-ready receipt 不可解析：{reference}"))
                    continue
                receipt, current_violations = validate_receipt(
                    root,
                    receipt_path,
                    collaboration,
                    git_output(root, "rev-parse", "HEAD"),
                    git_output(root, "rev-parse", "HEAD^{tree}"),
                    change=args.change,
                    expected_gate="review-ready",
                )
                receipt_violations.extend(current_violations)
                if receipt and not current_violations:
                    valid_receipts.append(receipt)
            if not any(receipt.get("verification_tier") == "objective_scope" for receipt in valid_receipts):
                receipt_violations.append(item("objective_scope_receipt_missing", "冻结的 review-ready receipt 集合无有效 objective_scope 证据"))
            if receipt_violations:
                return build_result(
                    "review-decision",
                    None,
                    receipt_violations,
                    changed=False,
                    phase="review_ready",
                    blocking_reasons=[entry["code"] for entry in receipt_violations],
                ), 1
            acceptance_fields = {
                "subject_manifest": ready_event["subject_manifest"],
                "accepted_subject_digest": ready_event["subject_digest"],
                "accepted_subject_ids": ready_event["subject_ids"],
                "accepted_subject_fingerprints": ready_event.get("subject_fingerprints", {}),
                "accepted_obligations": ready_event.get("subject_obligations", {}),
                "evidence_refs": ready_receipts,
            }
            if projection.get("schema_version") == 2:
                acceptance_fields.update({
                    "subject_schema_version": 2,
                    "subject_normalization_version": 2,
                })
        acceptance_fields["authorization_obligations"] = authorization_obligations(
            current_events, collaboration["objective_id"]
        )
        collaboration["phase"] = "accepted"
        commit_state_event(
            root,
            path,
            text,
            collaboration,
            "accepted",
            change_id=args.change,
            objective_id=collaboration["objective_id"],
            round_id=collaboration["round_id"],
            actor="reviewer",
            **acceptance_fields,
        )
    else:
        if not args.user_evidence:
            return violation_result("review-decision", "termination_evidence_missing", "显式终止必须提供用户证据")
        try:
            logical_repo_path(root, args.user_evidence, must_exist=True)
        except (ValueError, FileNotFoundError):
            return violation_result("review-decision", "termination_evidence_missing", "终止证据不可解析")
        collaboration["termination"] = "explicit"
        commit_state_event(
            root,
            path,
            text,
            collaboration,
            "terminated",
            change_id=args.change,
            objective_id=collaboration["objective_id"],
            round_id=collaboration["round_id"],
            actor="reviewer",
            user_evidence=args.user_evidence,
        )
    return build_result(
        "review-decision",
        None,
        [],
        changed=True,
        phase=collaboration["phase"],
        round_id=collaboration["round_id"],
        termination=collaboration["termination"],
        history_recovered=collaboration.get("_history_recovered") == "true",
    ), 0


def build_result(command: str, path: str | None, violations: list[dict[str, str]], **extra: object) -> dict:
    result = {"command": command, "valid": not violations}
    if path is not None:
        result["file"] = path
    result.update(extra)
    result["violations"] = violations
    return result


def make_parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(prog="zimaflow reviewer-executor", allow_abbrev=False)
    sub = top.add_subparsers(dest="action", required=True)
    brief = sub.add_parser("validate-brief", allow_abbrev=False)
    brief.add_argument("--file", required=True)
    brief.add_argument("--host", required=True, choices=("claude-code", "codex", "workbuddy"))
    brief.add_argument("--code-root", required=True)
    brief.add_argument("--docs-root", required=True)
    brief.add_argument("--change")
    brief.add_argument("--recurrence-count", type=int)
    brief.add_argument("--assumption-invalid", action="store_true")
    brief.add_argument("--forbidden-root", action="append", default=[])
    brief.add_argument("--source-file", action="append", required=True)
    brief.add_argument("--json", action="store_true")
    report = sub.add_parser("validate-report", allow_abbrev=False)
    report.add_argument("--file", required=True)
    report.add_argument("--source-file", action="append", required=True)
    report.add_argument("--change")
    report.add_argument("--json", action="store_true")
    compare = sub.add_parser("parity", allow_abbrev=False)
    compare.add_argument("--claude-code", required=True)
    compare.add_argument("--codex", required=True)
    compare.add_argument("--workbuddy", required=True)
    compare.add_argument("--json", action="store_true")
    decision = sub.add_parser("handover-decision", allow_abbrev=False)
    decision.add_argument("--reason", required=True, choices=("normal-review", "executor-change", "interrupted", "long-pause", "explicit-request"))
    decision.add_argument("--project-source-sufficient", action="store_true")
    decision.add_argument("--json", action="store_true")
    digest = sub.add_parser("subject-digest", allow_abbrev=False)
    digest.add_argument("--change", required=True)
    digest.add_argument("--objective", required=True)
    digest.add_argument("--objective-plan", required=True)
    digest.add_argument("--json", action="store_true")
    start = sub.add_parser("start", allow_abbrev=False)
    start.add_argument("--change", required=True)
    start.add_argument("--objective", required=True)
    start.add_argument("--round", required=True)
    start.add_argument("--events", required=True)
    start.add_argument("--matrix", required=True)
    start.add_argument("--objective-plan")
    start.add_argument("--json", action="store_true")
    transition = sub.add_parser("transition", allow_abbrev=False)
    transition.add_argument("--change", required=True)
    transition.add_argument("--to", required=True, choices=("executing", "checkpoint", "blocked"))
    transition.add_argument("--blocker")
    transition.add_argument("--blocker-category")
    transition.add_argument("--blocker-code")
    transition.add_argument("--affected-subject", action="append", default=[])
    transition.add_argument("--evidence-ref", action="append", default=[])
    transition.add_argument("--required-decision")
    transition.add_argument("--json", action="store_true")
    resume = sub.add_parser("resume", allow_abbrev=False)
    resume.add_argument("--change", required=True)
    resume.add_argument("--authorization", required=True)
    resume.add_argument("--json", action="store_true")
    finding = sub.add_parser("record-finding", allow_abbrev=False)
    finding.add_argument("--change", required=True)
    finding.add_argument("--defect-class", required=True)
    finding.add_argument("--boundary", required=True)
    finding.add_argument("--requirement", required=True)
    finding.add_argument("--composition-failure", action="store_true")
    finding.add_argument("--assumption-invalid", action="store_true")
    finding.add_argument("--recurrence-count", type=int)
    finding.add_argument("--json", action="store_true")
    receipt = sub.add_parser("run-receipt", allow_abbrev=False)
    receipt.add_argument("--change", required=True)
    receipt.add_argument("--output", required=True)
    receipt.add_argument("--batch", required=True)
    receipt.add_argument("--sequence", required=True, type=int)
    receipt.add_argument("--evidence-type", required=True, choices=("positive", "negative", "composition", "distribution", "sensitivity", "spec"))
    receipt.add_argument("--artifact", action="append", default=[])
    receipt.add_argument("--verification-tier", choices=tuple(VERIFICATION_TIER_GATES))
    receipt.add_argument("--gate", choices=tuple(VERIFICATION_TIER_GATES.values()))
    receipt.add_argument("--host", choices=("claude-code", "codex", "workbuddy"))
    receipt.add_argument("argv", nargs=argparse.REMAINDER)
    receipt.add_argument("--json", action="store_true")
    check = sub.add_parser("receipt-check", allow_abbrev=False)
    check.add_argument("--change", required=True)
    check.add_argument("--receipt", required=True)
    check.add_argument("--gate", required=True, choices=tuple(VERIFICATION_TIER_GATES.values()))
    check.add_argument("--json", action="store_true")
    coverage = sub.add_parser("coverage-check", allow_abbrev=False)
    coverage.add_argument("--change", required=True)
    coverage.add_argument("--gate", required=True, choices=("start-subsequent", "review-ready", "whole-change", "release"))
    coverage.add_argument("--receipt", action="append", default=[])
    coverage.add_argument("--json", action="store_true")
    implemented = sub.add_parser("mark-implemented", allow_abbrev=False)
    implemented.add_argument("--change", required=True)
    implemented.add_argument("--json", action="store_true")
    ready = sub.add_parser("review-ready", allow_abbrev=False)
    ready.add_argument("--change", required=True)
    ready.add_argument("--report")
    ready.add_argument("--json", action="store_true")
    review = sub.add_parser("review-decision", allow_abbrev=False)
    review.add_argument("--change", required=True)
    review.add_argument("--decision", required=True, choices=("accepted", "changes-requested", "terminated"))
    review.add_argument("--feedback")
    review.add_argument("--user-evidence")
    review.add_argument("--json", action="store_true")
    return top


def main() -> int:
    args = make_parser().parse_args()
    handlers = {
        "validate-brief": validate_brief,
        "validate-report": validate_report,
        "parity": parity,
        "handover-decision": handover_decision,
        "subject-digest": subject_digest,
        "start": start_objective,
        "transition": transition_objective,
        "resume": resume_objective,
        "record-finding": record_finding,
        "run-receipt": run_receipt,
        "receipt-check": receipt_check,
        "coverage-check": coverage_check,
        "mark-implemented": mark_implemented,
        "review-ready": review_ready,
        "review-decision": review_decision,
    }
    result, status = handlers[args.action](args)
    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    elif result["valid"]:
        print(f"Reviewer–Executor {args.action}: PASS")
    else:
        for violation in result["violations"]:
            print(f"FAIL [{violation['code']}]: {violation['message']}", file=sys.stderr)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
