# Default Work Item Assignee To Current User

## Goal

Improve PingCode workspace defaults so routine work item operations can run with less manual setup. When creating a work item and the caller does not provide an assignee, default the request body to the configured current user. Add a `pingcode-ctx` command that interactively helps users choose the current user, current project, and current sprint/iteration, then caches those choices in the workspace cache.

## What I Already Know

- The user requested: 创建工作项的时候如果没有说明负责人的情况下，默认使用当前用户作为负责人的入参.
- `SKILL.md`, `README.md`, and `references/workflows.md` already document that work item creation should include `assignee_id=@me` unless another assignee or "所有人" is explicit.
- `scripts/pingcode.py` currently applies current-user defaults only to `GET /v1/project/work_items` query params.
- Request bodies already support identity placeholder expansion through `expand_identity_placeholders`.
- Backend quality guidelines require PingCode CLI tests to cover dry-run write payloads and current-user behavior without live network calls.
- `package.json` currently exposes only the installer command; installed skill docs rewrite `python3 scripts/pingcode.py` examples to the installed absolute script path.

## Requirements

- For `POST /v1/project/work_items`, if the JSON body lacks `assignee_id`, add the configured current user as `assignee_id`.
- The configured current user must resolve through existing mechanisms: `--user-id`, `PINGCODE_USER_ID`, or cached `preferences.current_user_id`.
- If no current user is configured and the default is needed, raise the existing identity guidance error.
- If the caller provides `assignee_id`, preserve it and still expand placeholders such as `@me` or `@user:<name>`.
- If the caller passes `--all-users`, do not add a default `assignee_id`.
- Do not change non-work-item-create requests.
- Provide a `pingcode-ctx` command for interactive workspace context setup.
- `pingcode-ctx` must guide the user to select and cache:
  - current project
  - current sprint/iteration within the selected project
  - current user from project members when possible
- The interactive command must reuse the same cache format as `scripts/pingcode.py`.
- The interactive command must print JSON summary output on success and avoid printing secrets.
- The npm package/install flow must include and expose the new command.

## Acceptance Criteria

- [ ] Dry-run `POST /v1/project/work_items` without `assignee_id` includes the current user as `json.assignee_id`.
- [ ] Existing explicit `assignee_id` behavior still works.
- [ ] `--all-users` skips the create default.
- [ ] Missing current-user identity fails with existing setup guidance.
- [ ] `pingcode-ctx` can select project, sprint, and user from fetched/cached options and writes workspace preferences.
- [ ] Installer/package metadata includes the new command.
- [ ] Relevant unit tests pass without real PingCode network access.

## Out Of Scope

- Changing project, sprint, state, or type resolution behavior.
- Adding new CLI flags.
- Updating external PingCode API semantics.

## Technical Notes

- Relevant files: `scripts/pingcode.py`, `tests/test_pingcode.py`.
- Relevant spec: `.trellis/spec/backend/quality-guidelines.md`.
