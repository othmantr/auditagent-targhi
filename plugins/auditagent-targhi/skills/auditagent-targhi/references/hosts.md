# Host adapters

## Codex CLI

Install via the repository installer to `.agents/skills/auditagent-targhi` (project) or `~/.agents/skills/auditagent-targhi` (user). Explicit invocation: `$auditagent-targhi audit this project`. Natural-language discovery depends on the skill description and host configuration. Eight native role definitions are copied to .codex/agents or ~/.codex/agents. Probe whether the installed version recognizes them. If not, pass the relevant specialist instructions to supported generic subagents; if delegation unavailable, disclose sequential review. Codex roles inherit actual parent permissions; their text is not a read-only sandbox.

## Claude Code

Local skill installation: `/auditagent-targhi audit`. Native plugin installation: `/auditagent-targhi:auditagent-targhi audit`. The namespace is expected; do not promise the underscore alias or silently edit host config. Use either local skill installation or plugin installation, not both, to avoid duplicate discovery. Plugin contains native Claude reviewer definitions restricted to Read/Grep/Glob. The parent runs requested checks, reviewers inspect evidence; they do not get Bash by default. Select roles explicitly; do not assume plugin-prefix names equal the unqualified names.

Skill path is displayed by the host; scripts are under its scripts/ directory. Claude supports `${CLAUDE_SKILL_DIR}` but the canonical shared skill does not require that substitution on Codex. Do not install hooks that silently autoapprove writes.

## Antigravity and other IDEs

When Codex CLI or Claude Code runs inside an IDE terminal, use the adapter for that CLI. This package does not claim native integration with every IDE agent or with the Claude consumer chat. There is no automatic cross-product RPC, no API key, no remote model API, and no background daemon. Different tools can exchange the persisted handoff and state sequentially, but must share the same project root and respect ownership/locks.

## Compatibility references

- https://learn.chatgpt.com/docs/build-skills
- https://learn.chatgpt.com/docs/agent-configuration/subagents
- https://code.claude.com/docs/en/skills
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/plugins-reference
- https://code.claude.com/docs/en/plugin-marketplaces

Checked when authoring on 2026-11-09. Host versions and features evolve; verify installed tooling. Never claim live host compatibility solely from parsing manifest syntax.
