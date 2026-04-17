# .project (Platform-Neutral Guidance)

This directory is the single reusable toolkit for any assistant (Cursor, Claude, Warp, etc.). It contains role playbooks and command playbooks that do **not** depend on a specific IDE or agent host.

## Structure
- `agents/` – role playbooks (analyzer, locator, pattern-finder, thoughts-analyzer, web-search, etc.).
- `commands/` – operational playbooks (research, plan, implement, validate, debug, commit, etc.).
- `README.md` (this file) – how to use/bind these playbooks from any platform.

## How to Bind from Platforms
- Cursor/Claude/Warp/Kiro/Qoder/Codex:
  - Load `.project/agents/` for role prompts.
  - Load `.project/commands/` for workflow commands.
  - Add project context via `notes/INDEX.md` and `thoughts/` (plans/PRDs/research).
- Keep platform-specific guides (e.g., `WARP.md`, `AGENTS.md`, `.cursor/`, `.kiro/`) slim: they should mainly point here and to the project indexes.

## Quick Start (Any Agent)
1) Identify project context from `notes/INDEX.md` and `thoughts/`.
2) Pick a role playbook from `.project/agents/`.
3) Pick a workflow command from `.project/commands/`.
4) For codebase specifics, follow links in the `notes` indexes.

## Templates
- Agents: see `agents/TEMPLATE.md` for the one-pager skeleton.
- Commands: see `commands/TEMPLATE.md` for the command playbook skeleton.

## Guidance Principles
- Generic, reusable, and platform-neutral.
- Keep platform bindings thin—only pointers, no duplication.
- Keep project specifics in `notes/` (with indexes) and history/PRDs in `thoughts/`.


