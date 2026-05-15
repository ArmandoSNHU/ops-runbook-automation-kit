# Codex Guide

## Purpose

This repository is an IT operations automation portfolio project. It should demonstrate safe runbook structure, validation, check execution, and report rendering.

## Commands

```powershell
python -m runbook_kit validate examples\sample_runbook.json
python -m runbook_kit run examples\sample_runbook.json --pretty
python -m runbook_kit render examples\sample_runbook.json
python -m unittest discover
```

## Editing Rules

- Keep default behavior non-destructive.
- Do not add steps that delete, mutate, restart, or reconfigure systems without explicit user approval.
- Keep sample runbooks fictional and sanitized.
- Every new check type needs a unit test and README documentation.
- If adding network checks, make tests avoid external internet dependencies.

