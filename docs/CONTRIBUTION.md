# Contribution: truthful runbook validation and process status

Author: Armando Gomez
Date: 2026-09-26
Branch: contribution/techops-reliability

## Operational problem and root cause

A scheduled health check must distinguish success from failure. Previously `run`
and `render` returned zero even when their report showed a failed check. Missing
`contains` defaulted to the empty string, which matches every file. Validation
assumed object shapes and could raise TypeError/AttributeError; empty steps passed
validation and `all([])` produced a misleading PASS. JSON decoding errors escaped
as tracebacks.

The change validates shape before accessing fields, requires meaningful string
fields and `contains`, validates HTTP status values, rejects empty step lists, and
sends sanitized CLI errors to stderr. Exit codes are 0 for success, 1 for completed
checks with failures, and 2 for invalid inputs or incomplete execution. The JSON
result array remains compatible. Empty result reports show REVIEW.

## Reproduce and verify

Run from the repository root. The Python installation used for this contribution
was `D:\TechOpsagent\.venv\Scripts\python.exe`; no dependencies were installed.

```powershell
& D:\TechOpsagent\.venv\Scripts\python.exe -m unittest discover
& D:\TechOpsagent\.venv\Scripts\python.exe -m runbook_kit run examples\local_reliability.json --pretty
$LASTEXITCODE
& D:\TechOpsagent\.venv\Scripts\python.exe -m runbook_kit render examples\local_reliability.json
$LASTEXITCODE
git diff --check
```

Evidence captured during the change:

- Baseline suite: `Ran 3 tests in 0.011s` / `OK`.
- Regression tests before implementation: `Ran 11 tests in 0.080s` /
  `FAILED (failures=7, errors=10)`; see [red test snapshot](evidence/red-tests.txt).
- Final suite including unreadable input and execution errors:
  `Ran 13 tests in 0.067s` / `OK`; see [green snapshot](evidence/green-tests.txt).
- Local example: two checks passed, exit 0; [JSON](evidence/local-results.json)
  and [Markdown](evidence/local-report.md) snapshots contain only synthetic/repository data.
- `git diff --check`: exit 0, no output.

`test_failed_checks_return_one_and_keep_report` reproduces the original false
success using a missing temporary fixture, without any network call. Before the
fix, assertions reported `0 != 1` for both run and render. Afterward both retain
the failed report and return 1. Tests also check malformed JSON across all commands,
invalid schemas preventing execution, wrong types, empty results, absent contains,
HTTP status boundaries, and sanitized errors. Temporary fixtures are removed by
the test framework. The original three tests still pass.

## TechOps relevance and skills practiced

Truthful process status lets schedulers and incident pipelines alert on actual
failed checks. Validation before execution avoids ambiguous partial work and makes
operator errors actionable. Structured evidence supports ticket handoff and review.
Skills exercised: Python standard-library CLI design, unittest regression testing,
mocking side effects, input validation, exit-code contracts, JSON/Markdown reporting,
and reproducible operational documentation.

## Limits and compatibility

No remediation, service changes, network execution, credentials, models, external
requests, or private incident data were used. HTTP behavior itself is unchanged:
this contribution does not redesign URL restrictions, redirects, or HTTPError
handling. File/network report evidence is not globally redacted. Unreadable targets
abort execution with code 2 rather than promising a complete partial-results report.

Input validation intentionally tightens the contract: empty runbooks, blank strings,
missing contains, and numeric-string HTTP statuses are now invalid. Validation
errors now return 2 rather than 1. The public validation function still returns a
list of errors; `run_runbook` still raises ValueError for invalid schemas. Existing
relative-path resolution and output array shape remain unchanged.

## 2026-09-27 security follow-up — Armando Gomez

User-approved scope: explicit network policy, filesystem confinement, bounded reads.
The baseline was `Ran 13 tests in 0.087s` / `OK`. Regression evidence:
`Ran 22 tests in 0.105s` / `FAILED (failures=8, errors=13)` in
[evidence/security-red-tests.txt](evidence/security-red-tests.txt). Final evidence:
`Ran 26 tests in 0.149s` / `OK` in
[evidence/security-green-tests.txt](evidence/security-green-tests.txt).

The earlier HTTP-security limitation above describes the first contribution only.
Current runtime defaults to no network unless the operator provides exact host
permissions outside the runbook. It rejects unsafe URL forms, blocks all redirects,
and disables environment proxies. Files must resolve within a trusted root and be
ordinary relative targets. Reads are bounded; oversized data cannot produce a PASS
from a matching prefix. Whole-runbook target preflight occurs before any execution.

Reproduce with the same unittest command above. The final suite uses mock HTTP
openers and synthetic local temporary files; symlink tests run where the OS permits
creation (no skips in this Windows run). Coverage includes URL credential/scheme/host
bypasses, redirects, root traversal, special Windows paths, real symlink escape,
size limits, API policy provenance, preflight ordering, and CLI validate behavior.
Local synthetic run still returns two passing checks and exit 0.

Execution audit: the first pre-implementation red attempt accidentally omitted the
network mock in one default-denial test and attempted an `example.invalid` request.
The omission was corrected immediately; the saved red rerun and subsequent runs use
mock network calls. No real service response or credentials were used.

Compatibility changes: existing HTTP runbooks require `--allow-host`/`allowed_hosts`;
absolute/out-of-root file targets must be rewritten relative to an explicit trusted
`--base-dir`; large files need an explicit byte limit (maximum 16 MiB). HTTP redirects
fail rather than being followed. File evidence now contains resolved absolute paths.
JSON output shape and exit-code meanings are unchanged. Review README's target
security policy for DNS, mount/hardlink, race, and report-redaction limitations.
These controls improve operator safety without claiming a sandbox or full SSRF defense.
