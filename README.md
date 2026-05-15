# Ops Runbook Automation Kit

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Ops](https://img.shields.io/badge/Use%20Case-Runbook%20Automation-2563eb)](#what-it-does)
[![Safety](https://img.shields.io/badge/Default-Dry%20Run-success)](#safety-model)

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

