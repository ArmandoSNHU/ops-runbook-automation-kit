from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


SUPPORTED_STEP_TYPES = {"file_exists", "file_contains", "http_status"}


@dataclass(frozen=True)
class StepResult:
    name: str
    type: str
    passed: bool
    evidence: str


def load_runbook(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_runbook(runbook: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("name", "owner", "severity", "steps"):
        if field not in runbook:
            errors.append(f"Missing required field: {field}")
    if not isinstance(runbook.get("steps", []), list):
        errors.append("Field `steps` must be a list.")
        return errors
    for index, step in enumerate(runbook.get("steps", []), start=1):
        for field in ("name", "type", "target"):
            if field not in step:
                errors.append(f"Step {index} is missing required field: {field}")
        if step.get("type") not in SUPPORTED_STEP_TYPES:
            errors.append(f"Step {index} has unsupported type: {step.get('type')}")
    return errors


def run_runbook(runbook: dict[str, Any], base_dir: Path | None = None) -> list[dict[str, Any]]:
    errors = validate_runbook(runbook)
    if errors:
        raise ValueError("; ".join(errors))
    root = base_dir or Path.cwd()
    results = [_run_step(step, root) for step in runbook["steps"]]
    return [asdict(result) for result in results]


def render_markdown_report(runbook: dict[str, Any], results: list[dict[str, Any]]) -> str:
    status = "PASS" if all(result["passed"] for result in results) else "REVIEW"
    lines = [
        f"# Runbook Report: {runbook['name']}",
        "",
        f"- Owner: {runbook['owner']}",
        f"- Severity: {runbook['severity']}",
        f"- Overall status: {status}",
        "",
        "## Step Results",
        "",
        "| Step | Type | Status | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for result in results:
        step_status = "PASS" if result["passed"] else "FAIL"
        evidence = result["evidence"].replace("|", "\\|")
        lines.append(f"| {result['name']} | {result['type']} | {step_status} | {evidence} |")
    lines.append("")
    return "\n".join(lines)


def _run_step(step: dict[str, Any], base_dir: Path) -> StepResult:
    step_type = step["type"]
    if step_type == "file_exists":
        target = _resolve(base_dir, step["target"])
        return StepResult(step["name"], step_type, target.exists(), f"Checked path: {target}")
    if step_type == "file_contains":
        target = _resolve(base_dir, step["target"])
        expected = str(step.get("contains", ""))
        if not target.exists():
            return StepResult(step["name"], step_type, False, f"Missing path: {target}")
        content = target.read_text(encoding="utf-8", errors="replace")
        return StepResult(step["name"], step_type, expected in content, f"Expected text: {expected}")
    if step_type == "http_status":
        expected_status = int(step.get("status", 200))
        try:
            with urlopen(step["target"], timeout=5) as response:  # nosec: controlled runbook input
                actual_status = response.status
        except URLError as exc:
            return StepResult(step["name"], step_type, False, f"Request failed: {exc}")
        return StepResult(
            step["name"],
            step_type,
            actual_status == expected_status,
            f"Expected HTTP {expected_status}, received HTTP {actual_status}",
        )
    raise ValueError(f"Unsupported step type: {step_type}")


def _resolve(base_dir: Path, target: str) -> Path:
    path = Path(target)
    return path if path.is_absolute() else base_dir / path

