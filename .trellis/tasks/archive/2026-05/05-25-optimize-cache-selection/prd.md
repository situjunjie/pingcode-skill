# Optimize project and sprint cache selection

## Goal

When the workspace cache does not contain a current PingCode project or sprint, the CLI should help the agent fetch available options, present them in a machine-readable response for user selection, and persist the selected defaults into the workspace cache.

## What I already know

- The current CLI is implemented in `scripts/pingcode.py`.
- Workspace defaults live in `.pingcode-skill/cache.json` by default and are represented by `preferences.current_project_id` and `preferences.current_sprint_id`.
- Work item list queries currently apply cached current user, current project, and current sprint unless explicit params or `--all-*` opt-outs are supplied.
- Existing behavior raises static setup guidance when project or sprint defaults are missing.
- Project list caching already uses `GET /v1/project/projects`.
- Sprint list caching already uses `GET /v1/project/projects/{project_id}/sprints`.
- `set_current_project` and `set_current_sprint` already persist selected defaults from cached values.

## Assumptions

- Non-interactive agent workflows should not block on stdin prompts; they should receive JSON containing selectable options and exact follow-up commands.
- The existing `--all-projects` and `--all-sprints` opt-outs must continue to skip default filters.
- Existing explicit `project_ids` or `sprint_ids` params should not be overridden.

## Requirements

- If a work item list query needs a current project and no project is cached, the CLI fetches and caches the project list, then returns a guidance error containing available project options and a command to cache the chosen project.
- If a work item list query needs a current sprint and no sprint is cached, the CLI fetches and caches sprints for the current project, then returns a guidance error containing available sprint options and a command to cache the chosen sprint.
- Cache helper behavior should remain available directly through `--cache-projects`, `--cache-sprints`, `--set-current-project`, and `--set-current-sprint`.
- Existing successful GET cache writes for projects and sprints should continue to work.
- Tests must not depend on a live PingCode tenant.

## Acceptance Criteria

- [ ] Missing current project on a work item list query triggers project list fetch, writes projects to workspace cache, and returns selectable project options.
- [ ] Missing current sprint on a work item list query with current project triggers sprint list fetch, writes sprints to workspace cache, and returns selectable sprint options.
- [ ] Selecting a project or sprint by cached name/id still persists the corresponding id and display name.
- [ ] `--all-projects`, `--all-sprints`, and explicit params still bypass the corresponding default.
- [ ] Unit tests cover new missing-default guidance without live network calls.

## Definition of Done

- Tests added or updated for the new cache-selection flow.
- Relevant lint/type/test commands pass.
- Behavior changes are reflected in user-facing docs if needed.
- No credentials, access tokens, or workspace cache artifacts are committed.

## Out of Scope

- Adding an interactive TTY picker.
- Changing PingCode API endpoints.
- Changing current user selection behavior.
- Adding external dependencies.

## Technical Notes

- Relevant spec: `.trellis/spec/backend/quality-guidelines.md`.
- Relevant thinking guide: `.trellis/spec/guides/code-reuse-thinking-guide.md`.
- Existing missing-default logic is in `apply_default_work_item_filters`.
- Existing cache persistence is handled by `update_workspace_cache_for_response` and `save_workspace_cache`.
