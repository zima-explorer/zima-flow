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
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def required_spec_pairs(root: Path, change: str) -> dict[tuple[str, str], str]:
    specs_root = root / "openspec" / "changes" / change / "specs"
    if not specs_root.is_dir():
        raise ValueError("delta_specs_missing")
    pairs: dict[tuple[str, str], str] = {}
    for path in sorted(specs_root.glob("*/spec.md")):
        requirement = ""
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = re.match(r"^### Requirement:\s*(.+?)\s*$", line)
            if match:
                requirement = stable_spec_id(match.group(1))
                continue
            match = re.match(r"^#### Scenario:\s*(.+?)\s*$", line)
            if not match:
                continue
            if not requirement:
                raise ValueError(f"delta_spec_invalid:{path.relative_to(root)}:{line_number}")
            pair = (requirement, stable_spec_id(match.group(1)))
            if not all(pair) or pair in pairs:
                raise ValueError(f"delta_spec_id_collision:{pair[0]}:{pair[1]}")
            pairs[pair] = f"repo://{path.relative_to(root)}#{line_number}"
    if not pairs:
        raise ValueError("delta_specs_empty")
    return pairs


def repo_links(text: str) -> set[str]:
    return set(re.findall(r"repo://[A-Za-z0-9._/@%+~:-]+", text))


def current_git_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return Path(result.stdout.strip()).resolve()


def state_path(root: Path, change: str) -> Path:
    if not CHANGE_ID_RE.fullmatch(change):
        raise ValueError("invalid_change_id")
    return root / "openspec" / "changes" / change / ".zimaflow-state.yaml"


def logical_repo_path(root: Path, value: str, *, must_exist: bool = False) -> Path:
    if not value.startswith("repo://"):
        raise ValueError("artifact_path_not_logical")
    relative = value[len("repo://") :]
    if not relative or relative.startswith("/") or any(part in ("", ".", "..") for part in Path(relative).parts):
        raise ValueError("artifact_path_invalid")
    resolved = (root / relative).resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError("artifact_path_outside_repository")
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
        value = values.get(key, COLLABORATION_DEFAULTS[key])
        return f"  {key}: {value}" if value else f"  {key}:"

    return "\n".join(
        ["collaboration:"]
        + [line(key) for key in COLLABORATION_DEFAULTS]
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
    expected_parent = root / "openspec" / "changes" / str(fields["change_id"]) / "validation" / "reviewer-executor"
    if path != expected_parent.resolve() and expected_parent.resolve() not in path.parents:
        raise ValueError("event_log_outside_validation_root")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("event_log_not_regular_file")
    existing = read_events(root, collaboration)
    event = {
        "schema_version": 1,
        "event_id": f"{event_type}-{len(existing) + 1:04d}",
        "event_type": event_type,
        "timestamp": now_iso(),
        **fields,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return event


def collaboration_event_state(collaboration: dict[str, str]) -> dict[str, str]:
    return {
        key: collaboration.get(key, COLLABORATION_DEFAULTS[key])
        for key in COLLABORATION_DEFAULTS
        if key != "event_head"
    }


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
        return all(
            str(state_after.get(key, "")) == collaboration.get(key, COLLABORATION_DEFAULTS[key])
            for key in COLLABORATION_DEFAULTS
            if key != "event_head"
        )
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
        recovered = False
        if recover_history:
            text, collaboration, recovered = reconcile_history(root, path, text, collaboration)
        collaboration["_history_recovered"] = "true" if recovered else "false"
        return (root, path, text, collaboration), None
    except ValueError as exc:
        return None, violation_result(command, str(exc), "Change 或状态路径无效")
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        return None, violation_result(command, "state_not_found", f"无法加载 Change state：{exc}")


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
    validation_root = (root / "openspec" / "changes" / args.change / "validation" / "reviewer-executor").resolve()
    if validation_root not in events_path.parents or validation_root not in matrix_path.parents:
        return violation_result("start", "artifact_path_outside_validation_root", "loop artifacts 必须位于 Change validation/reviewer-executor 下")
    if not ROUND_ID_RE.fullmatch(args.round):
        return violation_result("start", "round_id_invalid", "round id 必须使用 round-NN")
    if collaboration["profile"] == PROFILE:
        same = (
            collaboration["objective_id"] == args.objective
            and collaboration["round_id"] == args.round
            and collaboration["loop_events"] == args.events
            and collaboration["boundary_matrix"] == args.matrix
        )
        if not same:
            return violation_result("start", "objective_conflict", "已有 Reviewer–Executor objective 与请求不一致")
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
    events_path.parent.mkdir(parents=True, exist_ok=True)
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
    )
    return build_result("start", None, [], applicable=True, changed=True, phase="planned"), 0


LEGAL_TRANSITIONS = {
    "planned": {"executing"},
    "executing": {"checkpoint", "blocked"},
    "checkpoint": {"executing", "blocked"},
}


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
    if args.to == "blocked" and not args.blocker:
        return violation_result("transition", "blocker_evidence_missing", "blocked transition 必须说明真实 blocker", phase=current)
    if args.to == "blocked" and not BLOCKER_ALLOWED_RE.search(args.blocker):
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_receipt(
    root: Path, receipt_path: Path, collaboration: dict[str, str], expected_commit: str, expected_tree: str
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
    if receipt.get("objective_id") != collaboration["objective_id"] or receipt.get("round_id") != collaboration["round_id"]:
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
                    violations.append(item("receipt_artifact_hash_mismatch", f"artifact hash 不一致：{artifact['path']}"))
            except (KeyError, TypeError, ValueError, FileNotFoundError):
                violations.append(item("boundary_evidence_missing", f"receipt artifact 不可解析：{artifact}"))
    return receipt, violations


def run_receipt(args: argparse.Namespace) -> tuple[dict, int]:
    context, error = context_or_error("run-receipt", args.change, recover_history=True)
    if error:
        return error
    assert context is not None
    root, _, text, collaboration = context
    if collaboration["profile"] != PROFILE:
        return violation_result("run-receipt", "profile_not_active", "Reviewer–Executor profile 未启用")
    dirty_source = non_evidence_dirty_paths(root, args.change)
    if dirty_source:
        return violation_result(
            "run-receipt", "source_worktree_dirty", "存在 receipts 无法覆盖的源码漂移", dirty_paths=dirty_source
        )
    implementation = yaml_nested_values(text, "implementation")
    if implementation.get("isolation") != "worktree" or Path(implementation.get("worktree_path", "")).resolve() != root:
        return violation_result("run-receipt", "receipt_isolation_mismatch", "当前 worktree 与 state isolation 不一致")
    command = list(args.argv)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        return violation_result("run-receipt", "receipt_command_missing", "-- 后必须提供命令 argv")
    try:
        output = logical_repo_path(root, args.output)
        validation_root = (root / "openspec" / "changes" / args.change / "validation" / "reviewer-executor").resolve()
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
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, output)
    result = build_result("run-receipt", str(output), [], receipt=receipt)
    return result, completed.returncode


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
    if dirty_source:
        violations.append(item("source_worktree_dirty", "存在 receipts 之后的非证据源码漂移"))
    tasks_reference = yaml_nested_values(text, "openspec").get("tasks_path", "")
    tasks_repo_reference = tasks_reference if tasks_reference.startswith("repo://") else f"repo://{tasks_reference}"
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
        if top.get("schema_version") != "1" or top.get("change_id") != args.change:
            violations.append(item("boundary_matrix_invalid", "matrix schema/change 不匹配"))
        if top.get("objective_id") != collaboration["objective_id"] or top.get("round_id") != collaboration["round_id"]:
            violations.append(item("boundary_matrix_invalid", "matrix objective/round 不匹配"))
        if not rows:
            violations.append(item("boundary_matrix_open", "matrix 没有 required rows"))
        required_pairs = required_spec_pairs(root, args.change)
        row_pairs: dict[tuple[str, str], list[str]] = {}
        for row in rows:
            required_keys = ("row_id", "requirement_id", "scenario_id", "boundary_id", "owner", "invariant", "required_evidence", "evidence_refs", "status")
            if any(not row.get(key) for key in required_keys):
                violations.append(item("boundary_matrix_invalid", f"matrix row 字段不完整：{row.get('row_id', row.get('_line', '?'))}"))
                continue
            pair = (row["requirement_id"], row["scenario_id"])
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
            violations.append(item("spec_mapping_incomplete", f"matrix 缺少 delta spec scenario：{pair[0]}/{pair[1]}"))
        for pair in unknown_pairs:
            violations.append(item("spec_mapping_unknown", f"matrix 引用了未知 delta spec scenario：{pair[0]}/{pair[1]}"))
        for pair in duplicate_pairs:
            violations.append(item("spec_mapping_duplicate", f"matrix 重复映射 delta spec scenario：{pair[0]}/{pair[1]}"))

        diff_base = top.get("diff_base", "")
        diff_reference = top.get("diff_artifact", "")
        try:
            if not re.fullmatch(r"[0-9a-f]{40}", diff_base):
                raise ValueError("diff_base_invalid")
            resolved_base = git_output(root, "rev-parse", "--verify", f"{diff_base}^{{commit}}")
            if resolved_base != diff_base:
                raise ValueError("diff_base_invalid")
            diff_path = logical_repo_path(root, diff_reference, must_exist=True)
            expected_diff = subprocess.run(
                ["git", "-C", str(root), "diff", "--binary", f"{diff_base}..HEAD"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout
            if diff_path.read_bytes() != expected_diff:
                violations.append(item("diff_evidence_invalid", "matrix diff artifact 不是 diff_base 到当前 HEAD 的精确差异"))
        except (ValueError, FileNotFoundError, OSError, subprocess.CalledProcessError):
            violations.append(item("diff_evidence_invalid", "matrix diff_base/diff_artifact 不可解析"))
    except (ValueError, FileNotFoundError, OSError) as exc:
        violations.append(item("boundary_matrix_open", f"matrix 不可用：{exc}"))

    required_report_links = {tasks_repo_reference, matrix_reference}
    if 'diff_reference' in locals() and diff_reference:
        required_report_links.add(diff_reference)
    required_report_links.update(receipt_refs)
    for reference in sorted(required_report_links - report_links):
        violations.append(item("report_evidence_link_missing", f"Execution Report 缺少精确证据链接：{reference}"))

    receipts: list[dict] = []
    receipts_by_ref: dict[str, dict] = {}
    expected_commit = git_output(root, "rev-parse", "HEAD")
    expected_tree = git_output(root, "rev-parse", "HEAD^{tree}")
    for reference in dict.fromkeys(receipt_refs):
        try:
            receipt_path = logical_repo_path(root, reference, must_exist=True)
        except (ValueError, FileNotFoundError):
            violations.append(item("boundary_evidence_missing", f"matrix evidence 不存在：{reference}"))
            continue
        receipt, receipt_violations = validate_receipt(root, receipt_path, collaboration, expected_commit, expected_tree)
        violations.extend(receipt_violations)
        if receipt:
            receipts.append(receipt)
            receipts_by_ref[reference] = receipt

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
    for boundary in systemic_boundaries(events):
        if not any(
            row.get("boundary_id") == boundary
            and row.get("status") == "covered"
            and row.get("systemic_closure") == "true"
            for row in rows
        ):
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
    start = sub.add_parser("start", allow_abbrev=False)
    start.add_argument("--change", required=True)
    start.add_argument("--objective", required=True)
    start.add_argument("--round", required=True)
    start.add_argument("--events", required=True)
    start.add_argument("--matrix", required=True)
    start.add_argument("--json", action="store_true")
    transition = sub.add_parser("transition", allow_abbrev=False)
    transition.add_argument("--change", required=True)
    transition.add_argument("--to", required=True, choices=("executing", "checkpoint", "blocked"))
    transition.add_argument("--blocker")
    transition.add_argument("--json", action="store_true")
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
    receipt.add_argument("argv", nargs=argparse.REMAINDER)
    receipt.add_argument("--json", action="store_true")
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
        "start": start_objective,
        "transition": transition_objective,
        "record-finding": record_finding,
        "run-receipt": run_receipt,
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
