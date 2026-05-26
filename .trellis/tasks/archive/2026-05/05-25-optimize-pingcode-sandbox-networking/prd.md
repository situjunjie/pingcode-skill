# Optimize PingCode Skill Sandbox Networking

## Goal

Reduce repeated Codex sandbox networking approvals when using the installed PingCode skill. The skill should guide agents toward a stable installed CLI path that can match Codex command prefix approvals, while preserving the existing credential and write-operation safety rules.

## What I Already Know

* Codex runs network access in a restricted sandbox by default; live PingCode API calls need approval unless they match an already approved command prefix.
* Current skill docs mostly recommend `python3 scripts/pingcode.py ...`, which is a relative command from the repository layout.
* The user's Codex environment already has an approved prefix for the installed script path: `python3 /Users/situjunjie/.codex/skills/pingcode/scripts/pingcode.py`.
* The npm installer copies `SKILL.md`, `references/`, and `scripts/` into the selected skill target directory.

## Requirements

* Installed skill documentation should prefer an absolute CLI command pointing at the installed `scripts/pingcode.py`.
* Source repository documentation should remain readable and usable during development.
* Do not weaken dry-run guidance, ID discovery rules, credential handling, or token secrecy.
* Keep the change local to installation/docs unless code behavior requires otherwise.

## Acceptance Criteria

* [ ] `node bin/install.js --target <tmpdir> --force` installs a skill whose docs use the installed absolute CLI path.
* [ ] Existing unit tests pass.
* [ ] Installer package check still passes.
* [ ] README/SKILL explain why absolute installed commands help Codex sandbox approval reuse.

## Out of Scope

* Bypassing Codex sandbox approvals programmatically.
* Changing PingCode authentication or API behavior.
* Adding a daemon/proxy/service.

## Technical Notes

* Relevant files: `bin/install.js`, `SKILL.md`, `README.md`, `references/workflows.md`.
* Relevant spec: `.trellis/spec/backend/quality-guidelines.md`, especially PingCode CLI and npm installer contracts.
