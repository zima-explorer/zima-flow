"""Public-safe, local-only Golden-case Eval protocol helpers."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
RESULTS = {"passed", "failed", "inconclusive"}
EVALUATION_MODES = {"mechanical", "semantic_review_required"}
CASE_ID_RE = re.compile(r"^[a-z][a-z0-9-]{1,80}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SECRET_FIELD_RE = re.compile(
    r"(?:^|[_-])(?:secret|password|api[_-]?key|access[_-]?token|private[_-]?key)(?:$|[_-])",
    re.IGNORECASE,
)


class EvalProtocolError(ValueError):
    """A stable, machine-readable protocol error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON deterministically without host-specific whitespace."""
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .encode("utf-8")
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_json(path: Path, error_code: str) -> Any:
    try:
        with path.open("r", encoding="utf-8", newline=None) as handle:
            return json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EvalProtocolError(error_code, f"Invalid JSON document: {path.name}") from error


def _require_mapping(value: Any, field: str, error_code: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvalProtocolError(error_code, f"{field} must be an object")
    return value


def _require_string(value: Any, field: str, error_code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvalProtocolError(error_code, f"{field} must be a non-empty string")
    return value


def _require_list(value: Any, field: str, error_code: str) -> list[Any]:
    if not isinstance(value, list):
        raise EvalProtocolError(error_code, f"{field} must be an array")
    return value


def _reject_secret_field_names(value: Any, error_code: str) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if not isinstance(key, str) or SECRET_FIELD_RE.search(key):
                raise EvalProtocolError(error_code, "Secret-shaped field names are not allowed")
            _reject_secret_field_names(nested, error_code)
    elif isinstance(value, list):
        for nested in value:
            _reject_secret_field_names(nested, error_code)


def _relative_path(value: Any, field: str, error_code: str) -> Path:
    text = _require_string(value, field, error_code)
    candidate = Path(text)
    if (
        candidate.is_absolute()
        or "\\" in text
        or ":" in text
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise EvalProtocolError(error_code, f"{field} must be a confined relative path")
    return candidate


def _confined_path(root: Path, relative: Path, field: str, error_code: str, *, must_file: bool) -> Path:
    root_resolved = root.resolve(strict=True)
    candidate = root / relative
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise EvalProtocolError(error_code, f"{field} must not traverse a symlink")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise EvalProtocolError(error_code, f"{field} does not exist") from error
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise EvalProtocolError(error_code, f"{field} escapes its declared root")
    if must_file and not resolved.is_file():
        raise EvalProtocolError(error_code, f"{field} must name a regular file")
    if not must_file and not resolved.is_dir():
        raise EvalProtocolError(error_code, f"{field} must name a directory")
    return resolved


def _validate_case_shape(case: Any) -> dict[str, Any]:
    error_code = "case_schema_invalid"
    case = _require_mapping(case, "case", error_code)
    _reject_secret_field_names(case, error_code)
    if case.get("schema_version") != SCHEMA_VERSION:
        raise EvalProtocolError(error_code, "Unsupported case schema_version")
    case_id = _require_string(case.get("case_id"), "case_id", error_code)
    if not CASE_ID_RE.fullmatch(case_id):
        raise EvalProtocolError(error_code, "case_id must be a stable lowercase identifier")
    _require_string(case.get("title"), "title", error_code)
    _require_string(case.get("task"), "task", error_code)

    tags = _require_list(case.get("tags"), "tags", error_code)
    if not tags or any(not isinstance(tag, str) or not tag.strip() for tag in tags):
        raise EvalProtocolError(error_code, "tags must contain non-empty strings")

    fixture = _require_mapping(case.get("fixture"), "fixture", error_code)
    _relative_path(fixture.get("root"), "fixture.root", error_code)
    inputs = _require_list(fixture.get("inputs"), "fixture.inputs", error_code)
    if not inputs:
        raise EvalProtocolError(error_code, "fixture.inputs must not be empty")
    input_paths = [_relative_path(item, "fixture.inputs[]", error_code) for item in inputs]
    if len({path.as_posix() for path in input_paths}) != len(input_paths):
        raise EvalProtocolError(error_code, "fixture.inputs must not contain duplicates")

    expected = _require_mapping(case.get("expected"), "expected", error_code)
    assertions = _require_list(expected.get("assertions"), "expected.assertions", error_code)
    if not assertions:
        raise EvalProtocolError(error_code, "expected.assertions must not be empty")
    assertion_ids: set[str] = set()
    for assertion in assertions:
        assertion = _require_mapping(assertion, "expected.assertions[]", error_code)
        assertion_id = _require_string(assertion.get("id"), "expected.assertions[].id", error_code)
        if assertion_id in assertion_ids or "expected" not in assertion:
            raise EvalProtocolError(error_code, "expected assertions need unique ids and expected values")
        assertion_ids.add(assertion_id)

    prohibited = _require_list(case.get("prohibited_outcomes"), "prohibited_outcomes", error_code)
    if any(not isinstance(item, str) or not item.strip() for item in prohibited):
        raise EvalProtocolError(error_code, "prohibited_outcomes must contain non-empty strings")
    evidence = _require_list(case.get("required_evidence"), "required_evidence", error_code)
    if not evidence or any(not isinstance(item, str) or not item.strip() for item in evidence):
        raise EvalProtocolError(error_code, "required_evidence must contain non-empty strings")
    if len(set(evidence)) != len(evidence):
        raise EvalProtocolError(error_code, "required_evidence must not contain duplicates")
    if case.get("evaluation_mode") not in EVALUATION_MODES:
        raise EvalProtocolError(error_code, "Unknown evaluation_mode")
    return case


def _fixture_digests(case: dict[str, Any], root: Path) -> dict[str, str]:
    fixture = case["fixture"]
    fixture_root_relative = _relative_path(fixture["root"], "fixture.root", "fixture_boundary_invalid")
    fixture_root = _confined_path(root, fixture_root_relative, "fixture.root", "fixture_boundary_invalid", must_file=False)
    digests: dict[str, str] = {}
    for item in fixture["inputs"]:
        relative = _relative_path(item, "fixture.inputs[]", "fixture_boundary_invalid")
        resolved = _confined_path(fixture_root, relative, "fixture.inputs[]", "fixture_boundary_invalid", must_file=True)
        try:
            digests[relative.as_posix()] = _sha256_bytes(resolved.read_bytes())
        except OSError as error:
            raise EvalProtocolError("fixture_boundary_invalid", "Unable to read a declared fixture") from error
    return dict(sorted(digests.items()))


def case_digest(case: dict[str, Any], fixture_digests: dict[str, str]) -> str:
    """Bind a normalized Case to exactly its declared fixture input bytes."""
    return _sha256_bytes(canonical_json_bytes({"case": case, "fixture_digests": dict(sorted(fixture_digests.items()))}))


def load_valid_case(case_path: str | Path, root: str | Path) -> tuple[dict[str, Any], dict[str, str], str]:
    root_path = Path(root)
    try:
        root_path.resolve(strict=True)
    except OSError as error:
        raise EvalProtocolError("fixture_boundary_invalid", "Eval root must exist") from error
    case = _validate_case_shape(_read_json(Path(case_path), "case_schema_invalid"))
    fixture_digests = _fixture_digests(case, root_path)
    return case, fixture_digests, case_digest(case, fixture_digests)


def validate_case(case_path: str | Path, root: str | Path) -> dict[str, Any]:
    try:
        case, fixture_digests, digest = load_valid_case(case_path, root)
        return {
            "valid": True,
            "case_id": case["case_id"],
            "case_digest": digest,
            "fixture_digest": _sha256_bytes(canonical_json_bytes(fixture_digests)),
            "reasons": [],
        }
    except EvalProtocolError as error:
        return {"valid": False, "reasons": [error.code]}


def render_brief(case: dict[str, Any], digest: str) -> str:
    """Render a portable briefing that does not disclose local host paths."""
    review = "An independent reviewer decision is required." if case["evaluation_mode"] == "semantic_review_required" else "No independent semantic review is required for this mechanical Case."
    prohibited = ", ".join(case["prohibited_outcomes"]) or "none declared"
    evidence = ", ".join(case["required_evidence"])
    return "\n".join(
        [
            f"Golden Eval: {case['case_id']}",
            f"Case digest: {digest}",
            f"Task: {case['task']}",
            f"Fixture boundary: {case['fixture']['root']} (declared inputs only)",
            f"Expected assertions: {', '.join(item['id'] for item in case['expected']['assertions'])}",
            f"Prohibited outcomes: {prohibited}",
            f"Required evidence: {evidence}",
            f"Review: {review}",
            "No model API, credential, external write, publication, real installation, or production authority is granted by this Eval.",
        ]
    )


def _result(status: str, case_id: str | None, digest: str | None, *reasons: str) -> dict[str, Any]:
    result: dict[str, Any] = {"status": status, "reasons": list(reasons)}
    if case_id is not None:
        result["case_id"] = case_id
    if digest is not None:
        result["case_digest"] = digest
    return result


def _validate_receipt_shape(receipt: Any) -> dict[str, Any]:
    error_code = "receipt_schema_invalid"
    receipt = _require_mapping(receipt, "receipt", error_code)
    _reject_secret_field_names(receipt, error_code)
    if receipt.get("schema_version") != SCHEMA_VERSION:
        raise EvalProtocolError(error_code, "Unsupported receipt schema_version")
    _require_string(receipt.get("case_id"), "case_id", error_code)
    for field in ("case_digest", "fixture_digest"):
        value = _require_string(receipt.get(field), field, error_code)
        if not SHA256_RE.fullmatch(value):
            raise EvalProtocolError(error_code, f"{field} must be a sha256 digest")
    executor = _require_mapping(receipt.get("executor"), "executor", error_code)
    _require_string(executor.get("host"), "executor.host", error_code)
    _require_string(executor.get("protocol_version"), "executor.protocol_version", error_code)
    _require_list(receipt.get("assertions"), "assertions", error_code)
    _require_list(receipt.get("artifacts"), "artifacts", error_code)
    _require_list(receipt.get("evidence"), "evidence", error_code)
    if receipt.get("result") not in RESULTS:
        raise EvalProtocolError(error_code, "Unknown receipt result")
    return receipt


def _receipt_containment_complete(receipt: dict[str, Any]) -> bool:
    containment = receipt.get("containment")
    return isinstance(containment, dict) and all(
        containment.get(field) is True
        for field in ("isolated_fixture", "no_credentials", "no_external_writes")
    )


def _receipt_artifacts_match(receipt: dict[str, Any], fixture_root: Path) -> str | None:
    artifacts = receipt["artifacts"]
    seen: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            return "receipt_schema_invalid"
        try:
            relative = _relative_path(artifact.get("path"), "artifacts[].path", "receipt_artifact_invalid")
        except EvalProtocolError as error:
            return error.code
        path_text = relative.as_posix()
        digest = artifact.get("sha256")
        if path_text in seen or not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            return "receipt_schema_invalid"
        seen.add(path_text)
        try:
            resolved = _confined_path(fixture_root, relative, "artifacts[].path", "receipt_artifact_invalid", must_file=True)
            actual_digest = _sha256_bytes(resolved.read_bytes())
        except EvalProtocolError as error:
            return error.code
        except OSError:
            return "receipt_artifact_invalid"
        if actual_digest != digest:
            return "receipt_artifact_tampered"
    return None


def check_receipt(case_path: str | Path, receipt_path: str | Path, root: str | Path) -> dict[str, Any]:
    """Check only explicit local evidence; executor prose is deliberately ignored."""
    try:
        case, fixture_digests, digest = load_valid_case(case_path, root)
    except EvalProtocolError as error:
        return _result("failed", None, None, error.code)

    try:
        receipt = _validate_receipt_shape(_read_json(Path(receipt_path), "receipt_schema_invalid"))
    except EvalProtocolError as error:
        return _result("failed", case["case_id"], digest, error.code)
    if receipt["case_id"] != case["case_id"]:
        return _result("failed", case["case_id"], digest, "receipt_case_id_mismatch")
    if receipt["case_digest"] != digest:
        return _result("failed", case["case_id"], digest, "receipt_case_digest_mismatch")
    fixture_digest = _sha256_bytes(canonical_json_bytes(fixture_digests))
    if receipt["fixture_digest"] != fixture_digest:
        return _result("failed", case["case_id"], digest, "fixture_digest_mismatch")

    required_evidence = set(case["required_evidence"])
    supplied_evidence = receipt["evidence"]
    if not all(isinstance(item, str) for item in supplied_evidence) or not required_evidence.issubset(supplied_evidence):
        return _result("failed", case["case_id"], digest, "receipt_evidence_missing")
    required_artifacts = {
        evidence.removeprefix("artifact:")
        for evidence in required_evidence
        if evidence.startswith("artifact:")
    }
    receipt_artifacts = {
        artifact.get("path")
        for artifact in receipt["artifacts"]
        if isinstance(artifact, dict) and isinstance(artifact.get("path"), str)
    }
    if not required_artifacts.issubset(receipt_artifacts):
        return _result("failed", case["case_id"], digest, "receipt_evidence_missing")
    if not _receipt_containment_complete(receipt):
        return _result("inconclusive", case["case_id"], digest, "containment_evidence_missing")

    fixture_root_relative = _relative_path(case["fixture"]["root"], "fixture.root", "fixture_boundary_invalid")
    fixture_root = _confined_path(Path(root), fixture_root_relative, "fixture.root", "fixture_boundary_invalid", must_file=False)
    artifact_error = _receipt_artifacts_match(receipt, fixture_root)
    if artifact_error is not None:
        return _result("failed", case["case_id"], digest, artifact_error)

    actual_assertions = receipt["assertions"]
    actual_by_id: dict[str, Any] = {}
    for assertion in actual_assertions:
        if not isinstance(assertion, dict) or not isinstance(assertion.get("id"), str) or "actual" not in assertion:
            return _result("failed", case["case_id"], digest, "receipt_schema_invalid")
        if assertion["id"] in actual_by_id:
            return _result("failed", case["case_id"], digest, "receipt_schema_invalid")
        actual_by_id[assertion["id"]] = assertion["actual"]
    for expected in case["expected"]["assertions"]:
        if actual_by_id.get(expected["id"], object()) != expected["expected"]:
            return _result("failed", case["case_id"], digest, "deterministic_assertion_failed")

    if case["evaluation_mode"] == "semantic_review_required":
        review = receipt.get("semantic_review")
        if not isinstance(review, dict) or review.get("independent") is not True or "decision" not in review:
            return _result("inconclusive", case["case_id"], digest, "semantic_review_missing")
        if review["decision"] != "approved":
            return _result("failed", case["case_id"], digest, "semantic_review_rejected")
    return _result("passed", case["case_id"], digest)
