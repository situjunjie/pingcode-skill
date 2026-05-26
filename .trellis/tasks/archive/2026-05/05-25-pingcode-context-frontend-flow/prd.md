# PingCode Context Frontend Flow

## Goal

Make PingCode workspace context setup usable from agent frontends such as Codex and Claude Code, while preserving the terminal `pingcode-ctx` workflow for manual use. Agents should guide the user through project, sprint, and user selection in the chat frontend, then write the same `.pingcode-skill/cache.json` preferences through deterministic CLI commands.

## What I Already Know

- `$pingcode-ctx` is not available today because the installed Codex skill is named `pingcode`; `pingcode-ctx` is only an npm package bin.
- `npx pingcode-skill` installs files into `~/.codex/skills/pingcode` but does not globally link `pingcode-ctx`.
- Python `input()` prompts in `scripts/pingcode_ctx.py` run in the tool terminal, not as Codex or Claude frontend choices.
- The project member endpoint returns member wrapper objects where the actual user fields are nested under `user`.
- Current display/matching helpers only inspect top-level fields, so project members can appear as raw IDs.

## Requirements

- Add an agent-friendly `pingcode-ctx` skill entrypoint so users can invoke `$pingcode-ctx` in Codex-like skill systems.
- Keep the existing `pingcode` skill as the normal REST workflow entrypoint.
- Define a generic agent frontend Q&A protocol that works for Codex, Claude Code, and similar agents without relying on platform-specific UI widgets.
- The protocol should list numbered options in chat, ask the user to reply with a number/id/name, and then run non-interactive CLI commands to cache the selection.
- Provide machine-readable/list-friendly option output from the CLI so agents do not need to parse full raw API payloads.
- Fix manual `pingcode-ctx` user choices so project member results show display names/usernames/emails instead of only IDs.
- Ensure cached user lookup and `--set-current-user` work for both top-level directory user objects and project member wrapper objects.
- Update install packaging so the new skill files are copied by `npx pingcode-skill`.
- Update tests and docs for the new flow.

## Acceptance Criteria

- [ ] Installed package can include a `pingcode-ctx` skill directory with its own `SKILL.md`.
- [ ] `scripts/pingcode.py` exposes option-list helper commands for projects, sprints, and users suitable for agent frontend prompts.
- [ ] Agent docs describe the three-step frontend flow: list options, ask user, write selection.
- [ ] `scripts/pingcode_ctx.py` displays nested project member user names correctly.
- [ ] Unit tests cover nested member display/lookup and agent option list output.
- [ ] `python3 -m unittest discover -s tests -v` passes.
- [ ] `npm pack --dry-run` shows the shipped files include the new skill docs and exclude runtime cache files.

## Out of Scope

- Implementing a native Codex or Claude plugin UI picker.
- Globally installing the npm `pingcode-ctx` binary.
- Changing PingCode API authentication semantics.

## Technical Notes

- Relevant spec: `.trellis/spec/backend/quality-guidelines.md`, especially PingCode Skill CLI Contracts and npm Skill Installer Contracts.
- Existing CLI entrypoint: `scripts/pingcode.py`.
- Existing terminal interactive entrypoint: `scripts/pingcode_ctx.py`.
- Installer: `bin/install.js`.
- Tests: `tests/test_pingcode.py`, `tests/test_install.py`.
