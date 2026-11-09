# Validation evidence: 0.1.0

Executed in the development workspace on 2026-11-09 with Python 3.12.14 on Linux.

## Automated suite

Command: `python3 -m unittest discover -s tests -v`

Result: **41 tests passed**: 28 controller tests and 13 installer tests. The suite uses disposable local projects, genuine local Python check subprocesses, and synthetic approval/reviewer data explicitly limited to test fixtures. Fixture approval is not evidence of a real user's approval or a real independent security review.

Covered: no execution before approval; exact plan identity; source drift before/after approval; batch order; approval narrowing; successful check/review lifecycle; stale report/check rejection; independent-review contract; scope/deletion risk rules; source-mutating check rejection; immediate stop/revocation for post-check scope violations; retry/deadline limits; malformed input; copied-root refusal; locks; immutable verified prefix; persistent resume notes; both-host installation; preflight conflicts; owned-file update/removal; local-edit preservation; path/symlink rejection; dry-run; rollback on injected write failure; refreshed ownership under lock; native role file syntax.

## Forward workflow exercise

A separate agent used the bundled workflow and real controller to audit an isolated tiny Python project with a tenant lookup function. It reproduced cross-tenant access, obtained a separate read-only security review, persisted evidence and proposed a phase through the real CLI. It stopped with phase status `pending`, no approval, no application source changes, and next action `await_user`. This validates the audit/plan/approval-stop path on a small fixture, not comprehensive application security coverage.

An independent static/controller exercise found two check-integrity issues: mutating checks could be counted against the post-run snapshot, and scope changes by a check were not blocked until verification. Both were fixed and regression-tested before packaging.

## Host and platform limits

Codex CLI was present (`0.167.0-alpha.4`); no paid/model-backed Codex session was launched and the package was not installed into the developer's global host directories. Claude Code executable was unavailable, so native Claude plugin installation/validation and interactive command discovery were not executed. Manifests/native role data were parsed and inspected locally against official documentation. A user's real CLI integration remains an installation smoke test, not a verified result here.

The GitHub Actions matrix covers Python 3.11/3.12 and Linux/Windows/macOS when the repository is pushed; those remote CI jobs have not yet run. No production systems, external APIs, payment providers, mobile devices or real customer data were tested. The source archive is a repository distribution, not an upload package for the ChatGPT plugin directory.
