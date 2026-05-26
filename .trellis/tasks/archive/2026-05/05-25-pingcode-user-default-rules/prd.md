# Update PingCode Skill User Default Rules

## Goal

Update the PingCode skill so natural-language work item create/query workflows default to the configured current user unless the user explicitly asks for "所有人" / all users. Also document safer configuration options for `clientId`, `secret`, and `currentUser` beyond raw shell environment variables.

## What I already know

* The skill currently supports `PINGCODE_CLIENT_ID`, `PINGCODE_CLIENT_SECRET`, `PINGCODE_USER_ID`, and `PINGCODE_USER_NAME`.
* The CLI supports `@me` and `@me_name` placeholders that expand from environment variables.
* Current guidance only treats "我的" / "我负责的" as current-user requests.
* The requested rule is broader: creating or querying work items should use the current environment-configured user by default unless the user explicitly specifies "所有人".

## Assumptions

* For querying work items, default current user means adding an assignee/current-user filter.
* For creating work items, default current user means assigning the new work item to the configured current user when no assignee was specified.
* "所有人" means do not add an assignee/current-user filter or default assignee.
* Existing generic CLI behavior should remain backward compatible; the defaulting rule belongs in skill workflow guidance and examples unless a safe CLI convenience can be added without surprising raw API callers.

## Requirements

* Update `SKILL.md` natural-language rules so work item queries default to current user unless "所有人" is explicit.
* Update create-work-item guidance so new work items default to current user as assignee unless another assignee or "所有人" is specified.
* Update workflow references and README examples/rules to match.
* Keep credential guidance safe: do not recommend committing secrets to repo files.
* Add or update tests if code behavior changes.

## Acceptance Criteria

* [ ] Query workflow examples show default `@me` current-user filtering.
* [ ] Create workflow examples show default current-user assignee behavior.
* [ ] Documentation explains "所有人" as the opt-out from current-user default.
* [ ] Configuration guidance includes alternatives to shell env vars with clear security trade-offs.
* [ ] Existing tests pass.

## Definition of Done

* Unit tests pass.
* Skill validation passes if available.
* Docs and references are internally consistent.
* No credentials or secret material are written to tracked files.

## Out of Scope

* Adding a PingCode OAuth user-auth flow.
* Storing real client secrets in this repository.
* Changing PingCode API schemas beyond documented CLI parameters/placeholders.

## Technical Notes

* Relevant files inspected: `SKILL.md`, `README.md`, `references/workflows.md`, `scripts/pingcode.py`, `tests/test_pingcode.py`.
* This repository is a distributable skill package (`package.json` includes `SKILL.md`, `references/*`, `scripts/pingcode.py`, and `README.md`).
