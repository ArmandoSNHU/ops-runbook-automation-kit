# State

## 2026-09-27 — Security boundaries

Author: Armando Gomez. Branch: contribution/techops-reliability.
Status: implemented, awaiting root review; no new commit or push by this agent.
Baseline: Ran 13 tests in 0.087s; OK.
Red: Ran 22 tests in 0.105s; FAILED (failures=8, errors=13).
Final: Ran 26 tests in 0.149s; OK (no skips).
Local synthetic run: two passing checks, exit 0.

Operator policy defaults to network denial. Explicit exact hostname grants,
HTTP(S)-only URLs, no credentials/redirects/proxies, confined relative file paths,
resolved symlink checks, regular-file bounded reads (default 1 MiB), and full target
preflight are implemented. See README target security policy and
`docs/CONTRIBUTION.md` dated follow-up for compatibility and honest execution audit.

## Restart Point
2026-09-27: Security hardening and repository controls are ready on the existing contribution branch; review the latest dated entries before proceeding. Do not merge without reviewing checks.

Run `python -m unittest discover` (26 tests expected). Review runtime, tests,
README and docs/evidence/security-* together. Root owns .github changes and any
publication. Existing PR1 is the contribution destination; no main merge requested.
Do not claim OS sandboxing: DNS rebinding, allowed private hosts, mount/hardlink
exposure and concurrent filesystem races require external trust/isolation controls.
Earlier 2026-09-26 reliability evidence remains in docs/CONTRIBUTION.md.

## 2026-09-27 — repository security controls
Author: Armando Gomez. User authorized the recommended security hardening and review-branch publication. Main protection, required PR/checks, admin enforcement, strict base freshness, resolved conversations, force-push/deletion denial, secret scanning/push protection, vulnerability alerts and automatic security fixes were enabled and verified through GitHub API read-back. No extra approving reviewer is required for the solo owner; checks remain mandatory. Added pinned Actions, read-only permissions, no persisted checkout credentials, and weekly Dependabot configuration. Branch changes remain unmerged; default-branch schedules activate after merge.
No third-party runtime dependencies declared. Runtime hardening verification and compatibility details are recorded above and in docs/CONTRIBUTION.md.
