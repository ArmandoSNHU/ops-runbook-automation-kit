# Ops Runbook Automation Kit

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Ops](https://img.shields.io/badge/Use%20Case-Runbook%20Automation-2563eb)](#what-it-does)
[![Safety](https://img.shields.io/badge/Checks-Read%20Only-success)](#safety-model)

Ops Runbook Automation Kit is a lightweight runbook validation and execution framework for IT operations. It reads structured runbooks, validates required fields, runs safe checks, and renders operator-friendly Markdown reports.

The project demonstrates operations engineering patterns: repeatable procedures, preflight checks, clear evidence collection, dry-run behavior, and incident handoff documentation.

## What It Does

- Validates runbook JSON structure.
- Runs safe local checks such as file existence and text containment.
- Supports HTTP status checks for service health validation.
- Produces structured step results.
- Renders Markdown reports for handoff, ticket notes, or post-incident review.
- Defaults to non-destructive behavior.

## Quick Start

Validate a runbook:

```powershell
python -m runbook_kit validate examples\sample_runbook.json
```

Run a runbook and print JSON results:

```powershell
python -m runbook_kit run examples\sample_runbook.json --pretty
```

Render a Markdown report:

```powershell
python -m runbook_kit render examples\sample_runbook.json
```

Run tests:

```powershell
python -m unittest discover
```

## Runbook Format

```json
{
  "name": "Endpoint Health Check",
  "owner": "IT Operations",
  "severity": "medium",
  "steps": [
    {
      "name": "Confirm README exists",
      "type": "file_exists",
      "target": "README.md"
    }
  ]
}
```

## Supported Step Types

| Type | Purpose |
| --- | --- |
| `file_exists` | Confirms a file path exists |
| `file_contains` | Confirms a file contains expected text |
| `http_status` | Confirms an endpoint returns an expected status code |

## Safety Model

This kit is for checks and documentation, not destructive remediation. It does not delete files, restart services, change firewall rules, rotate secrets, or modify cloud resources.

## Repository Structure

```text
ops-runbook-automation-kit/
├── runbook_kit/
│   ├── checks.py
│   └── cli.py
├── examples/
│   └── sample_runbook.json
├── tests/
│   └── test_runbook.py
├── pyproject.toml
├── README.md
└── codex.md
```

## Verification

```powershell
python -m unittest discover
python -m runbook_kit validate examples\sample_runbook.json
python -m runbook_kit run examples\sample_runbook.json --pretty
```

## Responsible Use

Use sanitized examples only. Do not commit production hostnames, internal URLs, credentials, incident data, customer details, or operational procedures that expose sensitive infrastructure.


## Validation and exit codes

All commands validate before running checks. Runbooks must be JSON objects with
non-empty string `name`, `owner`, and `severity`, and at least one step. Every step
requires non-empty string `name`, `type`, and `target`. `file_contains` also requires
a non-empty string `contains`; whitespace-only values are rejected. `http_status`
accepts an integer `status` from 100 through 599 (default 200); strings and booleans
are rejected. Unknown extra fields remain allowed.

| Exit | Meaning |
| --- | --- |
| 0 | Validation succeeded, or every executed check passed |
| 1 | At least one executed check failed; stdout still contains the report |
| 2 | Invalid/unreadable input, invalid arguments, or execution could not complete |

Validation and loading errors go to stderr without input values or tracebacks.
`run` keeps its JSON array output; `render` keeps its Markdown report. This changes
the previous exit-zero behavior for failed checks and previous exit-one validation
errors. Shell automation should check `$LASTEXITCODE` immediately after invocation.
Empty result sets render REVIEW rather than PASS.

For a deterministic local example (no network requests):

```powershell
python -m runbook_kit run examples\local_reliability.json --pretty
$LASTEXITCODE
```

Relative targets retain the existing resolution rule: they resolve against the
runbook file's grandparent directory. Keep example runbooks under `examples/`.
HTTP steps perform real requests; non-destructive does not mean offline or dry-run.
Only execute trusted runbooks. Reports may contain configured targets and expected
text; sanitization applies to CLI input/execution errors, not general report redaction.
See [contribution evidence](docs/CONTRIBUTION.md).

## Target security policy

Network access is denied by default. Operators grant exact trusted ASCII hostnames
(or IPv4 addresses) using repeated `--allow-host` options. Grants come from the
CLI/API, never fields in the runbook. Matching ignores hostname case; wildcards,
subdomain suffix matching, Unicode names, and IPv6 literals are not supported.
Only HTTP and HTTPS URLs are accepted. Embedded credentials, control characters,
backslashes, fragments, and invalid ports are rejected. All redirects are blocked,
including redirects to the same host. Environment proxies are disabled. HTTP
response bodies are not read, and requests retain a five-second timeout.

```powershell
# Validation only: no HTTP request is sent.
python -m runbook_kit validate examples\trusted-service.json --allow-host status.example.invalid
# Choose a trusted file root independently of the runbook's location.
python -m runbook_kit run examples\local_reliability.json --base-dir . --max-file-bytes 1048576
```

The first command illustrates policy for an operator-created runbook; that file is
not shipped. File targets must be relative paths within the configured base directory
(default: runbook file's grandparent). Absolute paths, UNC/device paths, drive paths,
alternate data streams, Windows reserved device names, and resolved paths outside
the root are rejected. Existing symlinks are resolved before confinement checks.
All target policies are checked before any step executes.

File containment reads are limited to 1 MiB by default. `--max-file-bytes` permits
1 through 16 MiB. Oversized files fail execution with exit 2, even if matching text
occurs in the first bytes. Only regular files can be read. Runbook JSON documents
have a fixed 1 MiB limit. The Python API exposes the same policy:

```python
run_runbook(runbook, base_dir=trusted_root,
            allowed_hosts=["status.example.invalid"], max_file_bytes=1048576)
```

The caller must trust the configured root and hosts. This is not an OS sandbox:
concurrent changes to symlinks/files can race path checks; hard links and mounted
filesystems can expose data inside the root. Do not execute against directories
writable by an adversary. Host allowlisting does not pin DNS or restrict IP ranges
or ports; a trusted host may resolve to private/loopback addresses. Use a narrowly
reviewed allowlist and external egress controls where stronger isolation is needed.
Validation checks policy and schema but does not prove connectivity or file contents.
