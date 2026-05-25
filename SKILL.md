---
name: pingcode
description: Use this skill whenever the user mentions PingCode or asks in natural language to view their current unfinished tasks, view unresolved defects or bugs, create a work item under a story, create or update stories/work items, change work item status, query project or product progress, or operate PingCode product/project management through the official REST API using client_credentials authentication.
---

# PingCode

Use this skill to call PingCode REST APIs safely and repeatably.

## Natural Language Triggers

Use this skill implicitly when the user mentions `PingCode`, `pingcode`, `工作项`, `故事`, `缺陷`, `任务`, `迭代`, `项目进度`, `产品需求`, or asks for actions such as:

* "查看我当前没完成的任务"
* "查看我的未解决缺陷"
* "帮我在 xxx 故事下新增工作项"
* "把某个工作项改成已完成/进行中"
* "创建一个故事/任务/缺陷"

When the request is natural language, map it to the closest CLI workflow below. Do not ask the user to provide a command unless a required ID or target remains ambiguous after lookup.

## Setup

Set credentials in the environment before running scripts:

```bash
export PINGCODE_CLIENT_ID="..."
export PINGCODE_CLIENT_SECRET="..."
```

Optional environment variables:

```bash
export PINGCODE_BASE_URL="https://open.pingcode.com"
export PINGCODE_TOKEN_CACHE="$HOME/.cache/pingcode-skill/token.json"
export PINGCODE_WORKSPACE_CACHE=".pingcode-skill/cache.json"
export PINGCODE_USER_NAME="your PingCode display/name"
export PINGCODE_USER_ID="your PingCode user id"
```

You may also pass one-off values with `--client-id`, `--client-secret`, `--user-id`, `--user-name`, and `--workspace-cache` when invoking `scripts/pingcode.py`. Prefer environment variables or a local shell profile for repeated use; prefer a password manager / secret manager that injects environment variables for shared machines or CI. Do not write credentials into tracked files, prompts, or skill docs.

`client_credentials` returns an enterprise token with broad permissions and does not represent a specific human user. For work item create/query requests, default to the configured current user unless the user explicitly says "所有人", "all users", or names another assignee. Use `PINGCODE_USER_ID` / `PINGCODE_USER_NAME`, CLI flags, or the workspace cache; if missing, ask the user to choose their PingCode user after caching users. The CLI supports `@me` for the current user id, `@me_name` for the current user name, and `@user:<name-or-email>` for cached user lookup; it will print setup guidance if the matching value is absent.

## Workspace Cache

The CLI keeps a local workspace cache at `.pingcode-skill/cache.json` by default. This file stores user/project/sprint preferences plus cached user lists and status dictionaries, so agents can avoid repeat list/dictionary API calls.

Initial setup for a workspace:

```bash
python3 scripts/pingcode.py --cache-projects
python3 scripts/pingcode.py --set-current-project PROJECT_ID
python3 scripts/pingcode.py --cache-sprints
python3 scripts/pingcode.py --set-current-sprint SPRINT_ID
python3 scripts/pingcode.py --cache-users
python3 scripts/pingcode.py --set-current-user USER_ID_OR_CACHED_NAME
python3 scripts/pingcode.py --cache-states --work-item-type-id TYPE_ID
```

If the global user-list endpoint is unavailable for a tenant, `--cache-users --project-id PROJECT_ID` caches project members instead. When the user asks for another person's work items, prefer cached lookup such as `--param assignee_ids=@user:Alice`; refresh with `--cache-users` only if the person is not in the cache.

For `GET /v1/project/work_items`, the CLI automatically adds `assignee_ids=<current user>`, cached `project_ids=<current project>`, and cached `sprint_ids=<current sprint>` unless those parameters are already supplied. When the user explicitly asks for all users, all projects, or all iterations, pass `--all-users`, `--all-projects`, or `--all-sprints` respectively.

## Main Tool

Use the bundled CLI:

```bash
python3 scripts/pingcode.py --help
```

Common commands:

```bash
python3 scripts/pingcode.py --method GET --path /v1/project/projects --param page_size=20
python3 scripts/pingcode.py --method GET --path /v1/project/work_items --param assignee_ids=@me --param project_ids=PROJECT_ID --param page_size=20
python3 scripts/pingcode.py --method GET --path /v1/project/work_item/types --param project_id=PROJECT_ID
python3 scripts/pingcode.py --method GET --path /v1/project/work_item/states --param project_id=PROJECT_ID --param work_item_type_id=TYPE_ID
python3 scripts/pingcode.py --method POST --path /v1/project/work_items --data '{"project_id":"PROJECT_ID","type_id":"story","title":"New story","assignee_id":"@me"}' --dry-run
python3 scripts/pingcode.py --method POST --path /v1/project/work_items --data '{"project_id":"PROJECT_ID","type_id":"task","parent_id":"STORY_ID","title":"New task","assignee_id":"@me"}' --dry-run
python3 scripts/pingcode.py --method PATCH --path /v1/project/work_items/WORK_ITEM_ID --data '{"state_id":"STATE_ID"}' --dry-run
python3 scripts/pingcode.py --method GET --path /v1/ship/products --param page_size=20
python3 scripts/pingcode.py --method POST --path /v1/ship/ideas --data '{"product_id":"PRODUCT_ID","title":"New idea"}' --dry-run
```

All output is JSON by default so agents can parse it reliably.

## Workflow

1. Read [`references/workflows.md`](references/workflows.md) before mutating PingCode data.
2. Resolve names to IDs using list commands. PingCode write APIs usually require IDs.
3. Run write commands with `--dry-run` first and inspect the JSON body.
4. Run the same command without `--dry-run` only after the target project/product/work item and state IDs are unambiguous.
5. For any endpoint, use the single `scripts/pingcode.py --method/--path` command and consult [`references/api.md`](references/api.md).

## Safety Rules

* Never guess `state_id`, `type_id`, `priority_id`, `project_id`, or `product_id`.
* Never infer a human user from an enterprise token. For work item create/query requests, default to `@me` only when a current user is configured; if the user explicitly asks for "所有人" / all users, do not add `assignee_ids=@me` or `assignee_id=@me`.
* For status changes, use cached states when present; otherwise fetch valid states for the work item project and type before patching. Refresh stale dictionaries with `--cache-states`.
* Treat HTTP 429 as rate limit. Wait for `x-pc-retry-after` seconds before retrying.
* Prefer the narrowest query possible. Pagination defaults to 30 and maxes at 100.
* Do not echo token values in final answers.
