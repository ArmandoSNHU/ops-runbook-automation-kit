from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path, PureWindowsPath
from typing import Any
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler
import re
import stat


SUPPORTED_STEP_TYPES = {"file_exists", "file_contains", "http_status"}


@dataclass(frozen=True)
class StepResult:
    name: str
    type: str
    passed: bool
    evidence: str


def load_runbook(path: Path) -> dict[str, Any]:
    return json.loads(_read_bounded(path, 1024 * 1024).decode("utf-8"))


def validate_runbook(runbook: Any) -> list[str]:
    """Return schema errors without echoing potentially sensitive input values."""
    if not isinstance(runbook, dict):
        return ["Runbook must be an object."]
    errors: list[str] = []
    for field in ("name", "owner", "severity", "steps"):
        if field not in runbook:
            errors.append(f"Missing required field: {field}")
        elif field != "steps" and not _nonempty_string(runbook[field]):
            errors.append(f"Field `{field}` must be a non-empty string.")
    steps = runbook.get("steps")
    if not isinstance(steps, list):
        errors.append("Field `steps` must be a list.")
        return errors
    if not steps:
        errors.append("Field `steps` must contain at least one step.")
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            errors.append(f"Step {index} must be an object.")
            continue
        for field in ("name", "type", "target"):
            if field not in step:
                errors.append(f"Step {index} is missing required field: {field}")
            elif not _nonempty_string(step[field]):
                errors.append(f"Step {index} field `{field}` must be a non-empty string.")
        step_type = step.get("type")
        if not isinstance(step_type, str) or step_type not in SUPPORTED_STEP_TYPES:
            errors.append(f"Step {index} has unsupported type.")
        if step_type == "file_contains" and not _nonempty_string(step.get("contains")):
            errors.append(f"Step {index} field `contains` must be a non-empty string.")
        if step_type == "http_status":
            status = step.get("status", 200)
            if type(status) is not int or not 100 <= status <= 599:
                errors.append(f"Step {index} field `status` must be an integer from 100 to 599.")
    return errors


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def run_runbook(runbook: dict[str, Any], base_dir: Path | None = None, *,
                allowed_hosts: list[str] | tuple[str, ...] = (), max_file_bytes: int = 1024 * 1024) -> list[dict[str, Any]]:
    errors = validate_runbook(runbook)
    if errors:
        raise ValueError("; ".join(errors))
    root = (base_dir or Path.cwd()).resolve()
    validate_targets(runbook, root, allowed_hosts=allowed_hosts, max_file_bytes=max_file_bytes)
    results = [_run_step(step, root, max_file_bytes) for step in runbook["steps"]]
    return [asdict(result) for result in results]


def render_markdown_report(runbook: dict[str, Any], results: list[dict[str, Any]]) -> str:
    status = "PASS" if results and all(result["passed"] for result in results) else "REVIEW"
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


def _run_step(step: dict[str, Any], base_dir: Path, max_file_bytes: int) -> StepResult:
    step_type = step["type"]
    if step_type == "file_exists":
        target = _resolve(base_dir, step["target"])
        return StepResult(step["name"], step_type, target.exists(), f"Checked path: {target}")
    if step_type == "file_contains":
        target = _resolve(base_dir, step["target"])
        expected = step["contains"]
        if not target.exists():
            return StepResult(step["name"], step_type, False, f"Missing path: {target}")
        content = _read_bounded(target, max_file_bytes).decode("utf-8", errors="replace")
        return StepResult(step["name"], step_type, expected in content, f"Expected text: {expected}")
    if step_type == "http_status":
        expected_status = int(step.get("status", 200))
        try:
            with build_opener(ProxyHandler({}), _NoRedirect()).open(step["target"], timeout=5) as response:
                actual_status = response.status
        except URLError:
            return StepResult(step["name"], step_type, False, "Request failed or redirect blocked.")
        return StepResult(
            step["name"],
            step_type,
            actual_status == expected_status,
            f"Expected HTTP {expected_status}, received HTTP {actual_status}",
        )
    raise ValueError(f"Unsupported step type: {step_type}")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_targets(runbook: dict[str, Any], base_dir: Path, *,
                     allowed_hosts=(), max_file_bytes: int = 1024 * 1024) -> None:
    """Preflight all targets using operator policy, never runbook-controlled grants."""
    if type(max_file_bytes) is not int or not 1 <= max_file_bytes <= 16 * 1024 * 1024:
        raise ValueError("File byte limit must be between 1 and 16777216.")
    if not isinstance(allowed_hosts, (list, tuple)):
        raise ValueError("Allowed hosts must be a list or tuple.")
    hosts = set()
    for host in allowed_hosts:
        if not isinstance(host, str) or not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", host):
            raise ValueError("Allowed hosts must be exact ASCII hostnames or IPv4 addresses.")
        hosts.add(host.lower())
    for step in runbook["steps"]:
        if step["type"] != "http_status":
            _resolve(base_dir, step["target"])
            continue
        target = step["target"]
        if any(ord(c) <= 32 or ord(c) == 127 for c in target) or "\\" in target:
            raise ValueError("Unsafe HTTP target.")
        try:
            parts = urlsplit(target)
            port = parts.port
            valid = (parts.scheme in ("http", "https") and parts.hostname in hosts
                     and parts.username is None and parts.password is None
                     and not parts.fragment and port != 0)
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("HTTP target must use HTTP(S), an allowed host, and no credentials or fragment.")


def _read_bounded(path: Path, limit: int) -> bytes:
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("Read target must be a regular file.")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("File exceeds configured byte limit.")
    return data


def _resolve(base_dir: Path, target: str) -> Path:
    # Reject Windows drives, UNC/device paths and streams even on Unix hosts.
    windows = PureWindowsPath(target)
    if (Path(target).is_absolute() or windows.drive or windows.root or ":" in target
            or any(ord(c) < 32 for c in target)
            or any(part.rstrip(" .").split(".")[0].upper() in
                   {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(10)], *[f"LPT{i}" for i in range(10)]}
                   for part in windows.parts)):
        raise ValueError("File targets must be ordinary relative paths.")
    root = base_dir.resolve()
    path = (root / target).resolve()
    if not path.is_relative_to(root):
        raise ValueError("File target escapes the configured base directory.")
    return path
