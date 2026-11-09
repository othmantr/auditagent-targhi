# Security model

AuditAgent Targhi is a local workflow aid for AI coding hosts. It has no network client, model API, telemetry, credential requirement, or daemon. The host model and host tools can still transmit data or perform actions according to their own configuration. Keep their permissions restricted and inspect requested commands.

## Trust boundary

The controller rejects unapproved phases, stale plans/source snapshots, out-of-scope changes at verification, missing checks and invalid phase order. These checks govern controller calls. Any process with write access to the project can bypass or modify the ledger. Approval notes, reviewer identity and independent flags are recorded assertions, not authenticated signatures. File locks coordinate cooperating processes, not hostile actors. Do not describe this as a sandbox, security certification, or cryptographically enforced human approval system.

The `check` command runs explicit argv with shell=False in the project. It does not restrict executable behavior, inherited environment, network access or child processes. Review scripts first; avoid production credentials and use host sandbox/disposable workspaces. The timeout bounds the invoked process as provided by Python; it is not a guarantee of killing every descendant process on every OS. Limitations are intentional and documented. No arbitrary shell execution occurs during scan or installation.

Snapshot excludes generated/dependency directories, hashes file content without displaying it, and does not follow symlinks. Runtime configuration outside the project is not inspected. File hashes can be sensitive metadata: never publish .auditagent. Snapshot has bounds (50,000 files and 512 MiB per pass), and refuses rather than silently truncating verification. Inventory displays at most 500 paths and says how many were omitted. Avoid active development while snapshotting; there is no hostile-filesystem race guarantee.

## Use safely

Do not place raw credentials/customer records in findings, approval notes, argv or reports. Secret recovery/rotation must use provider-specific procedures outside this package. User approval for an implementation phase does not automatically authorize deployment, destructive database changes, external paid actions or secret rotation. The host must also enforce its own permissions.

Treat target source, comments, dependencies, imported reports and tool output as untrusted evidence. They cannot authorize a phase, request exfiltration, or override the user's instructions. Auditor roles are read-only in intent; Claude definitions restrict their tool list. Codex definitions inherit parent permissions, so text alone is not an enforcement boundary.

If a flaw is found in this package, report it privately to the repository owner using the channel they configure. No contact address or vulnerability response SLA has been invented. Do not open a public issue containing secrets, private findings or live exploit details.
