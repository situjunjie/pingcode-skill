# Quality Guidelines

> Code quality standards for backend development.

---

## Overview

<!--
Document your project's quality standards here.

Questions to answer:
- What patterns are forbidden?
- What linting rules do you enforce?
- What are your testing requirements?
- What code review standards apply?
-->

(To be filled by the team)

---

## Forbidden Patterns

<!-- Patterns that should never be used and why -->

(To be filled by the team)

---

## Required Patterns

<!-- Patterns that must always be used -->

(To be filled by the team)

---

## Testing Requirements

<!-- What level of testing is expected -->

(To be filled by the team)

---

## Code Review Checklist

<!-- What reviewers should check -->

(To be filled by the team)

## Scenario: PingCode Skill CLI Contracts

### 1. Scope / Trigger

- Trigger: This repository exposes a Python CLI used by AI agents to call PingCode REST APIs.
- Applies to files under `scripts/` that construct HTTP requests, parse CLI arguments, read credentials, or mutate PingCode resources.

### 2. Signatures

- Main entry point: `python3 scripts/pingcode.py --method METHOD --path PATH [options]`.
- Interactive context entry point: `python3 scripts/pingcode_ctx.py [options]` and npm bin `pingcode-ctx`.
- Skill invocation docs must point agents to `scripts/pingcode.py --help`.
- Write examples should execute directly once target IDs and payload fields are unambiguous. `--dry-run` remains available for manual previews of high-risk writes but is not the default agent workflow.

### 3. Contracts

- Required environment keys for live OAuth client credentials: `PINGCODE_CLIENT_ID`, `PINGCODE_CLIENT_SECRET`.
- Optional environment keys: `PINGCODE_BASE_URL`, `PINGCODE_ACCESS_TOKEN`, `PINGCODE_TOKEN_CACHE`, `PINGCODE_WORKSPACE_CACHE`, `PINGCODE_USER_ID`, `PINGCODE_USER_NAME`.
- CLI credential overrides: `--client-id`, `--client-secret`, `--token`.
- CLI current-user overrides: `--user-id`, `--user-name`.
- CLI workspace cache options: `--workspace-cache`, `--no-workspace-cache`, `--no-cache-read`.
- CLI cache helper commands: `--cache-users`, `--cache-projects`, `--cache-sprints`, `--cache-work-item-types`, `--cache-work-item-priorities`, `--cache-work-item-properties`, `--cache-states`, `--cache-idea-states`, `--cache-idea-priorities`, `--set-current-user`, `--set-current-project`, `--set-current-sprint`.
- CLI agent frontend helper: `--context-options project|sprint|user` prints compact JSON options for chat-based project/sprint/user selection.
- CLI default-filter opt-outs: `--all-users`, `--all-projects`, `--all-sprints`.
- Product dictionary cache helpers require `--product-id`.
- `pingcode-ctx` must interactively select and cache the current user, current project, and current sprint/iteration in the same workspace cache format as `scripts/pingcode.py`.
- The `$pingcode-ctx` skill must use agent-fronted Q&A by default: list compact options, ask the user for one numbered/id/name choice in chat, then write the selection with `--set-current-*`.
- Terminal `python3 scripts/pingcode_ctx.py` remains a fallback for users who explicitly want shell interaction.
- Default workspace cache path: `.pingcode-skill/cache.json`; this runtime artifact must remain ignored by git.
- When writing the default `.pingcode-skill/cache.json` workspace cache and the current project has a `.gitignore`, the Python CLI must automatically ensure `.pingcode-skill/` is listed there. Prefer this deterministic script behavior over asking the agent/model to remember and edit `.gitignore` manually.
- Project member API responses may wrap the actual user under `user`; display, lookup, selection-option, and current-user caching code must normalize those wrappers before reading `id`, `display_name`, or `name`.
- `client_credentials` tokens are enterprise tokens and must not be treated as a specific human user.
- Work item create/query workflows default to the configured current user unless the user explicitly asks for "所有人" / all users or names another assignee.
- Current-user identity comes from `--user-id`, `PINGCODE_USER_ID`, or cached `preferences.current_user_id`; if absent, ask the user to cache/select their PingCode identity.
- Routine work item create/query workflows must require a complete workspace context (`preferences.current_user_id`, `preferences.current_project_id`, and `preferences.current_sprint_id`) unless the user explicitly opts out with the relevant all-* flag.
- If routine work item create/query workflows find incomplete workspace context, they must guide the user to run `pingcode-ctx` before retrying rather than silently making a broad query.
- Query work items default to current user, current project, and current sprint/iteration when cached; explicit query params override cached defaults.
- Work item list queries that need current user/project/sprint defaults but lack any cached preference must exit non-zero with `pingcode-ctx` guidance so agents complete the full context before retrying.
- Use `--all-users`, `--all-projects`, or `--all-sprints` only when the user explicitly asks for all users/projects/iterations.
- Query another cached user with `@user:<name-or-id>`; refresh user cache only if the cached list cannot resolve the user.
- Create current-user work items with `assignee_id=@me`.
- Cache work item types by `project_id` and reuse cached responses before making another type dictionary API call.
- Cache work item priorities by `project_id` and reuse cached responses before making another priority dictionary API call.
- Cache work item properties by `(project_id, work_item_type_id)` and reuse cached responses before making another property dictionary API call.
- Cache states by `(project_id, work_item_type_id)` and reuse cached responses before making another state dictionary API call.
- `--cache-states --work-item-type-id TYPE_ID` refreshes one type's state dictionary. `--cache-states` without `--work-item-type-id` refreshes the current or explicit project's work item type dictionary first, then refreshes state dictionaries for every returned type id.
- `--cache-work-item-properties --work-item-type-id TYPE_ID` refreshes one type's property dictionary. `--cache-work-item-properties` without `--work-item-type-id` refreshes the current or explicit project's work item type dictionary first, then refreshes property dictionaries for every returned type id.
- Cache idea states and idea priorities by `product_id`; helper commands must fail clearly when `--product-id` is absent.
- Workspace cache stores compact dictionary data for agent lookup, not raw API responses. Drop fields that do not help resolve IDs or choose options, including `url`, `color`, avatars, email, creator/updater objects, visibility flags, and timestamps. Keep lookup fields such as `id`, `name`, `display_name`, `identifier`, `type`, `group`, nested `user`, and property `options`.
- Default base URL: `https://open.pingcode.com`.
- Output contract: print JSON to stdout for successful commands; print human-readable errors to stderr and exit non-zero for failures.
- Credentials, access tokens, token cache contents, and workspace cache contents must never be committed or included in docs examples.

### 4. Validation & Error Matrix

- Missing credentials for a live authenticated request -> non-zero exit with a credentials error.
- `@me` / `@me_name` identity placeholder without matching env vars -> non-zero exit with user identity configuration guidance.
- `@me` / `@me_name` identity placeholder with matching `--user-id` / `--user-name` -> expand from CLI args without requiring environment variables.
- `@user:<name>` without a matching cached user -> non-zero exit with cache refresh guidance.
- `--context-options sprint` without a cached or explicit project -> non-zero exit asking for `--project-id` or cached current project.
- Project member wrapper values from `/v1/project/projects/{project_id}/members` -> option output and terminal prompts show nested `user.display_name` / `user.name`, not only the member id.
- Saving default workspace cache with an existing `.gitignore` -> `.pingcode-skill/` appears exactly once; missing `.gitignore` or custom cache paths -> no `.gitignore` file is created or modified.
- Work item create/query with incomplete workspace context -> non-zero exit with `pingcode-ctx` guidance.
- Work item list query without cached current project and without `--all-projects` -> non-zero exit with `pingcode-ctx` guidance.
- Work item list query without cached current sprint and without `--all-sprints` -> non-zero exit with `pingcode-ctx` guidance.
- Cached work item type, work item priority, work item property, work item state, idea state, or idea priority dictionary request -> return cached JSON without opening a network connection.
- Successful GET for projects, project members/users, sprints, work item types, work item priorities, work item properties, work item states, idea states, or idea priorities -> update workspace cache.
- Invalid JSON passed to `--data`, `--properties`, `--plan-at`, or `--real-at` -> non-zero exit before making an HTTP request.
- `key=value` parameters without `=` or with an empty key -> non-zero exit before making an HTTP request.
- PingCode HTTP 429 -> include retry-after information when present.
- Non-JSON PingCode response -> non-zero exit with a bounded response preview.

### 5. Good/Base/Bad Cases

- Good: Resolve IDs with list commands, then execute write commands directly after target IDs and payload fields are unambiguous.
- Good: Run `pingcode-ctx` once per workspace before routine work item operations so current user/project/sprint defaults are cached.
- Good: In an agent frontend, invoke `$pingcode-ctx`, present one numbered choice list at a time, and use `--set-current-*` after each user answer.
- Good: Initialize `.pingcode-skill/cache.json` with current user/project/sprint and state dictionaries before routine work item queries.
- Good: Put repeatable local-environment hygiene such as ignoring `.pingcode-skill/` into Python script execution when it can be done deterministically and safely.
- Base: Read-only list commands may call live APIs once credentials are configured, then reuse cached list/dictionary responses.
- Bad: Guessing `state_id`, `type_id`, `project_id`, or `product_id`; repeatedly fetching dictionaries already in cache; committing a token or workspace cache; writing credentials into source files.

### 6. Tests Required

- Unit tests must cover request URL construction and query parameter mapping.
- Unit tests must cover dry-run payloads for write commands.
- Unit tests must cover `@me` / `@me_name` expansion from environment variables and CLI args.
- Unit tests must cover `@user:<name>` expansion from cached users.
- Unit tests must cover cached current user/project/sprint default filtering and explicit all-* opt-outs.
- Unit tests must cover `pingcode-ctx` writing current user/project/sprint preferences without live network calls.
- Unit tests must cover automatic `.gitignore` maintenance for the default workspace cache directory.
- Unit tests must cover `--context-options` compact option output for nested project member user responses.
- Unit tests must cover cached user lookup and current-user caching for project member wrappers whose real user object is nested under `user`.
- Unit tests must cover incomplete workspace context producing `pingcode-ctx` guidance.
- Unit tests must cover manual cache helper commands (`--cache-projects`, `--cache-sprints`, `--set-current-project`, `--set-current-sprint`) separately from routine work item operations.
- Unit tests must cover dictionary cache reads without network and cache writes after successful list/dictionary responses.
- Unit tests must cover project-scoped work item type caching and `--cache-states` refreshing states for every cached type when no single `--work-item-type-id` is supplied.
- Unit tests must cover work item priority caching, work item property caching and batched property refresh, and product-scoped idea state/priority caching.
- Unit tests must cover workspace cache compaction so unneeded API fields are removed while lookup fields remain.
- Unit tests must cover auth/token behavior without live network calls.
- Tests must not depend on a real PingCode tenant.

### 7. Wrong vs Correct

#### Wrong

Guessing a state and patching without discovery:

```bash
python3 scripts/pingcode.py --method PATCH --path /v1/project/work_items/WI --data '{"state_id":"guessed_done"}'
```

#### Correct

```bash
python3 scripts/pingcode.py --method GET --path /v1/project/work_item/states --param project_id=PROJECT_ID --param work_item_type_id=TYPE_ID
python3 scripts/pingcode.py --method PATCH --path /v1/project/work_items/WI --data '{"state_id":"STATE_ID"}'
```

#### Wrong

Repeating dictionary/user lookups and querying every project/iteration by default:

```bash
python3 scripts/pingcode.py --method GET --path /v1/project/work_item/states --param project_id=PROJECT_ID --param work_item_type_id=task
python3 scripts/pingcode.py --method GET --path /v1/project/work_items --param assignee_ids=@me
```

#### Correct

Initialize and reuse workspace defaults/cache:

```bash
python3 scripts/pingcode_ctx.py
# or, after npm installation:
pingcode-ctx
```

Manual setup remains available when an interactive terminal is not available:

```bash
python3 scripts/pingcode.py --cache-projects
python3 scripts/pingcode.py --set-current-project PROJECT_ID
python3 scripts/pingcode.py --cache-sprints
python3 scripts/pingcode.py --set-current-sprint SPRINT_ID
python3 scripts/pingcode.py --cache-users
python3 scripts/pingcode.py --set-current-user USER_ID
python3 scripts/pingcode.py --cache-states
python3 scripts/pingcode.py --method GET --path /v1/project/work_items
```

Agent frontend setup uses compact option lists instead of terminal `input()`:

```bash
python3 scripts/pingcode.py --context-options project
python3 scripts/pingcode.py --set-current-project PROJECT_ID
python3 scripts/pingcode.py --context-options sprint
python3 scripts/pingcode.py --set-current-sprint SPRINT_ID
python3 scripts/pingcode.py --context-options user
python3 scripts/pingcode.py --set-current-user USER_ID
```

## Scenario: npm Skill Installer Contracts

### 1. Scope / Trigger

- Trigger: This repository publishes an npm package so users can install the skill with `npx` into multiple AI agent skill homes from a single command.
- Applies to `package.json`, `bin/install.js`, `tests/test_install.py`, and release documentation (`README.md`, `index.html`).

### 2. Signatures

- User install command: `npx pingcode-skill` (default = install to detected existing agent homes).
- Default candidate targets (installed in one run only when the corresponding agent home already exists, unless scoped by a flag):
  - Codex: `$CODEX_HOME/skills/pingcode` when `CODEX_HOME` is set, otherwise `~/.codex/skills/pingcode`. Only this root honors an environment override.
  - Claude Code: `~/.claude/skills/pingcode`.
  - OpenClaw: `~/.openclaw/skills/pingcode`.
  - Hermes: `~/.hermes/skills/project-management/pingcode`. Hermes requires a category subdirectory; this project uses `project-management`.
- Supported installer options:
  - `--force` — overwrite existing installs at all selected roots.
  - `--target <dir>` — back-compat escape hatch; install only at the explicit path.
  - `--codex-only` / `--claude-only` / `--openclaw-only` / `--hermes-only` — scope a default install to a single agent root.
  - `--help` / `-h` — print usage including the default roots and per-agent flags.
- Flag mutex rules:
  - `--target` is mutually exclusive with all four `--*-only` flags.
  - `--codex-only` / `--claude-only` / `--openclaw-only` / `--hermes-only` are mutually exclusive with each other.
  - Violating either mutex must exit non-zero with a clear error before any filesystem writes.

### 3. Contracts

- The npm package must include only skill runtime files: `SKILL.md`, `skills/pingcode-ctx/SKILL.md`, `agents/openai.yaml`, `references/*.md`, `scripts/__init__.py`, `scripts/pingcode.py`, `scripts/pingcode_ctx.py`, `bin/install.js`, `bin/pingcode-ctx.js`, `README.md`, and `package.json`.
- The npm package must not include `.trellis/`, `.agents/`, `.claude/`, `.codex/`, tests, token caches, Python bytecode, or generated archives.
- The installer must not require network access after npm has downloaded the package.
- The installer must print PingCode credential environment variable guidance after at least one root succeeds.
- The installer must copy `README.md` into each installed skill directory because the package file list includes it and references should remain available offline.
- Per-root doc rewriting: `rewriteInstalledDocs` runs once per installed root with that root's own absolute scripts path, so each installed `SKILL.md` references its own `python3 <root>/scripts/pingcode.py`, not the codex root's path.
- Per-root alias install: `installAliasSkill` runs once per installed root and places `pingcode-ctx` as a sibling of `pingcode` in the same skills root. For Hermes, the alias also lives under the `project-management/` category — so the layout is `~/.hermes/skills/project-management/pingcode-ctx`.
- The installer must rewrite installed docs (`SKILL.md`, `README.md`, `references/workflows.md`) from `python3 scripts/pingcode.py` to the absolute installed script command. This lets Codex reuse sandbox/network approval prefixes for the stable installed CLI path instead of repeatedly approving relative repository commands.
- The source docs may keep `python3 scripts/pingcode.py` examples for repository development; only installed docs should be rewritten.
- Default detection must check the agent home directory, not the final `skills` directory: Codex checks `$CODEX_HOME` or `~/.codex`, Claude Code checks `~/.claude`, OpenClaw checks `~/.openclaw`, and Hermes checks `~/.hermes`. Missing agent homes are skipped and must not be created by the default multi-root flow.
- The `--codex-only` / `--claude-only` / `--openclaw-only` / `--hermes-only` flags are explicit user choices and may create their selected root even if that agent home does not already exist.
- Per-root failure isolation: each selected existing root is wrapped in try/catch. A failure on one root must NOT abort the others. Successes print `[ok] <agent>: <path>` to stdout; skipped missing agent homes print `[skip] <agent>: <agentHome>` to stdout; failures print `[fail] <agent>: <error>` to stderr. The final summary must list every attempted root and skipped candidate.
- The single-target flow (`--target <dir>` or any single `--*-only` flag) preserves the legacy single-line `Installed PingCode skill to <path>` output that existing tests depend on.

### 4. Validation & Error Matrix

- `--target` combined with any `--*-only` flag -> non-zero exit with mutex error before any filesystem writes.
- Two or more `--*-only` flags combined -> non-zero exit with mutex error before any filesystem writes.
- Existing install at any selected root without `--force` -> that root fails with an `EEXIST_TARGET` style error; other roots continue.
- All selected roots succeed -> exit code 0.
- Partial success (≥1 root succeeds, ≥1 root fails) -> exit code 2.
- No root succeeds, or unrecoverable arg parse error -> exit code 1.
- `CODEX_HOME` set -> only the codex default root retargets to `$CODEX_HOME/skills/pingcode`. Claude Code, OpenClaw and Hermes roots remain at their fixed `~/.<agent>/...` paths.
- No supported agent home exists during default install -> no filesystem writes, exit 0, and print guidance to create an agent home or use `--target DIR`.
- `--help` / `-h` -> print usage including all four candidate roots, detection behavior, per-agent flags, and `CODEX_HOME` note; exit 0.

### 5. Good/Base/Bad Cases

- Good: `npx pingcode-skill@latest` writes both `pingcode` and `pingcode-ctx` only to supported agent homes that already exist for the current user; Hermes lands under `project-management/`; each installed root's `SKILL.md` references its own absolute scripts path.
- Good: `npx pingcode-skill@latest --claude-only --force` overwrites only `~/.claude/skills/pingcode` and the sibling `pingcode-ctx`.
- Good: `npx pingcode-skill@latest --target ".claude/skills/pingcode"` installs into the project-local Claude skills directory and prints the legacy single-target message.
- Base: One root fails with a permission error; other three install cleanly; exit code is 2 and the summary lists the failed root with its error.
- Bad: Aborting the whole install on the first root failure; rewriting all installed `SKILL.md` files to point at the codex root's scripts path; introducing env vars analogous to `CODEX_HOME` for the other agents in this scope.

### 6. Tests Required

- `tests/test_install.py` must cover:
  - Default invocation creates `pingcode` + `pingcode-ctx` under existing agent homes only, with rewritten absolute paths in each installed root's `SKILL.md`, and skips missing agent homes without creating them.
  - Default invocation with no existing supported agent homes exits 0 without filesystem writes and prints next-step guidance.
  - Single-target back-compat: `--target <dir>` installs only at the explicit path and emits the legacy single-line output.
  - Each `--*-only` flag installs only into its corresponding root.
  - Per-root failure isolation: making one root unwritable must produce a `[fail]` line for that root, `[ok]` lines for the others, and exit code 2.
  - `CODEX_HOME` only retargets the codex root; other roots remain at fixed paths.
  - `--target` combined with any `--*-only` flag exits non-zero with the mutex error.
- `npm pack --dry-run` must succeed and the shipped file list must match `package.json` `files`.
- `node bin/install.js --help` must list every default root and every per-agent flag.

## Scenario: Long Skill Documentation Structure

### 1. Scope / Trigger

- Trigger: A skill entrypoint such as `SKILL.md` grows large enough that the model must scan many unrelated sections before acting.
- Applies to skill documentation, reference docs, workflow docs, and helper command docs shipped in this repository.

### 2. Signatures

- Required entrypoint: `SKILL.md`.
- Allowed supporting files: `references/*.md`, `scripts/*.py`, `agents/*.yaml`, and package docs such as `README.md`.
- The entrypoint may link to supporting docs with relative markdown links.

### 3. Contracts

- `SKILL.md` must remain a high-signal routing and quick-start document, not a full API dump.
- Keep frequently needed operational rules in `SKILL.md`: triggers, credential setup, primary CLI command, safety rules, and the shortest successful workflow.
- Move long endpoint catalogs, detailed natural-language workflows, troubleshooting matrices, and extended examples into `references/*.md`.
- Every moved section must be discoverable from `SKILL.md` through a clear heading and relative link.
- Supporting docs must use searchable headings and concrete keywords users/models are likely to search, such as `用户`, `状态`, `迭代`, `工作项`, `project`, `sprint`, `state`, `assignee`.
- Do not split one required workflow across so many files that execution requires back-and-forth reading; keep each workflow self-contained once linked.
- When adding a new helper command, document the command in `SKILL.md` if agents must remember it for routine use, and put extended examples in `references/workflows.md`.

### 4. Validation & Error Matrix

- `SKILL.md` exceeds practical scanning length and includes repeated endpoint tables -> move repeated/detail-heavy content to `references/*.md`.
- Supporting docs are added without links from `SKILL.md` -> invalid; models cannot reliably discover them.
- A reference file lacks task-oriented headings -> invalid; add headings that match natural language intents.
- A safety rule exists only in a deep reference file -> invalid; duplicate the short rule in `SKILL.md` and link to details.

### 5. Good/Base/Bad Cases

- Good: `SKILL.md` says "For detailed natural-language mappings, read `references/workflows.md`", and the reference file has headings like "View My Current Unfinished Tasks".
- Base: A short skill keeps all instructions in `SKILL.md` when the total content is still easy to scan.
- Bad: `SKILL.md` contains a long API catalog, scattered examples, and duplicate workflow text with no clear section boundaries.

### 6. Tests Required

- Run the skill validator after restructuring documentation.
- Check package contents with `npm pack --dry-run` when shipped docs or references change.
- Manually scan `SKILL.md` for a model-friendly path from trigger -> setup -> tool -> safety -> references.

### 7. Wrong vs Correct

#### Wrong

Putting every endpoint and every workflow directly in `SKILL.md`:

```markdown
# Skill
... long setup ...
## Endpoint 1
## Endpoint 2
## Endpoint 40
## Workflow A
## Workflow B
```

#### Correct

Keep the entrypoint short and link to task-scoped references:

```markdown
# Skill
## Setup
## Main Tool
## Workspace Cache
## Safety Rules

Detailed workflows: [references/workflows.md](references/workflows.md)
API summary: [references/api.md](references/api.md)
```
