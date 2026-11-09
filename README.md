# AuditAgent Targhi

A reusable audit and improvement workflow for **Claude Code and Codex CLI**, created for Othmane Targhi. Install once, open an application, request an audit, approve a concrete plan, and let the coding host execute and independently verify the approved phases.

Source repository: https://github.com/othmantr/auditagent-targhi

**Release: 0.1.0.** Python 3.11+, standard library only. No API key, model API calls, extra model subscription, remote server or background daemon is added by this package. Your coding host still uses its own account, models, limits and tools.

## What you get

- One coordinator skill with eight specialist roles: architecture, security, data, reliability/DevOps, product UX/accessibility, mobile, billing/AI, and independent verification.
- Adaptive review: select relevant roles, rather than paying for every specialist to reread every file.
- Per-project memory, stable finding IDs, coverage gaps and concise resume checkpoints.
- Plans with exact file scopes, risks, acceptance criteria, checks, retry limits and phase deadlines.
- Approval of one phase or a consecutive batch, bound to the exact plan hash and current project root/source snapshot.
- Automatic progression inside the approved batch, controlled by the host coordinator; stop at unapproved work, failed verification or blockers.
- Structured implementation handoff packages for the current coding host or manual transfer to another host.
- Recorded local checks and verification reports bound to the final source snapshot.
- Non-destructive installer with dry-run, owned-file updates and safe uninstall.
- Claude Code marketplace/plugin layout and a Codex skill/agent adapter.

**This is a host-assisted workflow, not a standalone autonomous auditor.** The AI host reads code, launches supported subagents, edits files and interprets results. Python manages the workflow ledger. It does not launch Codex/Claude or independently authenticate human approval, reviewer identity or test quality. See [SECURITY.md](SECURITY.md).

## Install once for all projects

Clone or download this source repository, then open a terminal in its root. Antigravity is fine as the editor; run the actual Codex CLI or Claude Code inside it.

```bash
git clone https://github.com/othmantr/auditagent-targhi.git
cd auditagent-targhi
```

```bash
python3 --version
python3 installer.py --host both --scope user --dry-run
python3 installer.py --host both --scope user
```

On Windows use `py -3` instead of `python3` if that is how Python is installed. Choose `--host codex` or `--host claude` to install only one. No host settings, existing AGENTS.md or CLAUDE.md is overwritten. If a conflicting or locally modified file exists the installer refuses; preserve and resolve it yourself. Re-run the installer from a newer source checkout to update owned unchanged files.

| Host | Explicit invocation after discovery |
|---|---|
| Codex CLI | `$auditagent-targhi audit this project` |
| Claude Code, direct skill install above | `/auditagent-targhi audit` |
| Claude Code, native plugin install below | `/auditagent-targhi:auditagent-targhi audit` |

The hyphenated name is intentional and portable. `/auditagent_targhi` is not an installed alias. If discovery does not immediately refresh, reopen the host's skill/plugin view or start a fresh session. Do not install both the direct Claude skill and native Claude plugin unless you deliberately want duplicate entries.

Project-only installation:

```bash
python3 installer.py --host both --scope project --project /absolute/path/to/your-app --dry-run
python3 installer.py --host both --scope project --project /absolute/path/to/your-app
```

## Claude Code native plugin from GitHub

In Claude Code, add the repository as a marketplace and install the plugin:

```text
/plugin marketplace add othmantr/auditagent-targhi
/plugin install auditagent-targhi@auditagent-targhi-marketplace
/auditagent-targhi:auditagent-targhi audit
```

For local plugin development, launch Claude Code with the absolute plugin path:

```bash
claude --plugin-dir /absolute/path/to/auditagent-targhi/plugins/auditagent-targhi
```

Use the marketplace or direct installer route; they are alternatives. Codex support in this release uses its documented local skill/agent discovery paths, not the Claude marketplace format.

## First audit

Open the application root in your chosen coding host and invoke the skill. Natural-language invocation is also possible when host discovery selects the skill:

> Use AuditAgent Targhi to audit this application. Inspect code and relevant configuration, delegate relevant specialist reviews, and report evidence, uncertainty and coverage gaps. Propose small ordered improvement phases. Do not modify application code before I approve the plan.

The host should inventory the project, inspect relevant code, create `.auditagent/` records and present a plan. A file inventory is not a security audit. No runtime/production assertions should be made without appropriate access and evidence.

**Keep `.auditagent/` private and exclude it from Git before publishing your application.** It contains findings, project metadata, approval notes and source hashes. The audit workflow may create its own artifacts but may not silently edit your application or .gitignore before approval. Existing user changes must be preserved.

## Approve a phase or batch

Review the plan, affected components, risk flags, acceptance criteria and limits. Then reply, for example:

> I approve phase-1 and phase-2 of the displayed plan. Execute them in order, verify each phase with a separate reviewer, and continue automatically between those two phases. Stop for scope changes, exhausted limits or unapproved sensitive actions. Return a report when this batch finishes.

The coordinator records that actual approval against the displayed plan hash. You may instead run the generated approval command yourself. It must not fabricate your decision. Approving a plan does not authorize arbitrary deployments, database destruction or external paid actions. Sensitive flags require explicit agreement; host permissions still apply.

If phase-1 passes and phase-2 is approved, the host continues without asking you to type “phase 2.” If phase-3 is not approved, it stops and returns control. When the host session ends, execution ends; resume uses persisted state rather than a daemon.

## Status, resume and stop

Use the same entry point with natural language, for example:

```text
/auditagent-targhi status
/auditagent-targhi resume
/auditagent-targhi stop
```

In Codex prefix with `$auditagent-targhi`; in the Claude plugin route use the namespaced command. Status shows progress and next action. Resume rechecks source changes and reads a small checkpoint. Stop revokes remaining approvals and preserves partial work. A revised plan needs renewed approval.

Memory reduces repeated discovery, but is not free tokens or guaranteed context caching. The coordinator reads relevant current records instead of loading every historical report. Reaudits focus on changed code and affected boundaries; release checkpoints may require broader review.

## Local controller

For diagnostics, use the bundled CLI directly from this repository:

```bash
python3 auditagent.py --project /absolute/path/to/app init
python3 auditagent.py --project /absolute/path/to/app scan
python3 auditagent.py --project /absolute/path/to/app status --changed
```

When installed, the same controller lives at `scripts/auditagent.py` beneath the installed skill. See [JSON contracts](plugins/auditagent-targhi/skills/auditagent-targhi/references/contracts.md) and [protocol](plugins/auditagent-targhi/skills/auditagent-targhi/references/protocol.md) for finding/plan/verification formats and the full CLI lifecycle. `--project` goes before the subcommand. Findings and plans must be based on inspected evidence; the controller does not invent audit results.

The `check` command runs an inspected explicit command in the project, without shell interpolation. It is **not sandboxed** and can have side effects. Use host restrictions and disposable test environments. It records argv, exit code, timing and snapshot identity, not proof of meaningful tests. A separate verifier must inspect adequacy.

## Uninstall

Use the same scope and project as installation:

```bash
python3 installer.py --host both --scope user --uninstall --dry-run
python3 installer.py --host both --scope user --uninstall
```

Only owned unchanged installation files are removed. Unrelated files and project audit memory remain. Native Claude marketplace installs should be removed using Claude's plugin manager instead.

## Quality checks and release evidence

```bash
python3 -m unittest discover -s tests -v
```

See [TESTING.md](docs/TESTING.md) for actual execution evidence and host-level limitations. Cross-platform GitHub Actions is included; a configured CI job is not a claim that it has already run on every OS. See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for state transitions and trust boundaries.

## Publish the source to GitHub

1. Create a repository under your account with your chosen visibility.
2. Add this full source tree at its root. Keep `.claude-plugin/`, `plugins/`, `adapters/`, and the Python files; do not upload only the README or archive.
3. Run the tests and push the source through your normal Git workflow. The included CI runs after pushing.
4. Replace owner/repository placeholders only in your shared installation instructions. The marketplace uses a relative plugin path, so no repository URL edit is required in its manifest.
5. Test one real Claude install and one Codex skill discovery in your local environment before advertising compatibility broadly.

Do not publish `.auditagent` findings or credentials. MIT licensed; no claim of OWASP certification, comprehensive penetration testing, or automatic production approval.
