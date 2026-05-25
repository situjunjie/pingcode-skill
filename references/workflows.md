# PingCode Workflows

## Natural Language Mapping

| User says | Use |
|---|---|
| "查看当前没完成的任务" | Unless the user says "所有人", require the configured current user and list work items filtered by `assignee_ids=@me`, then interpret non-completed states |
| "查看所有人当前没完成的任务" | Do not add the current-user assignee filter; narrow by project/type/status if available |
| "查看我的未解决缺陷" | Require the configured current user, list work items filtered by `assignee_ids=@me` and `type_ids=bug`, then interpret non-completed states |
| "帮我在 xxx 故事下新增工作项" | Find the story, then create a child work item with `POST /v1/project/work_items`, `parent_id`, and `assignee_id=@me` unless another assignee or "所有人" is explicit |
| "把某个工作项改成已完成/进行中" | Resolve states, then patch the work item with `state_id` |
| "创建一个故事/任务/缺陷" | Resolve project/type, then create via `POST /v1/project/work_items` with `assignee_id=@me` unless another assignee or "所有人" is explicit |

This skill uses `client_credentials`, so the token is an enterprise token and does not represent a specific human user. For work item create/query requests, default to the configured current user unless the user explicitly says "所有人" / all users or names another assignee. Use `PINGCODE_USER_ID` / `PINGCODE_USER_NAME`, the matching CLI flags, or the workspace cache if present. If none is set, cache users first and ask the user to choose their PingCode user before filtering or assigning.

The CLI accepts identity placeholders:

* `@me` expands to `PINGCODE_USER_ID`.
* `@me_name` expands to `PINGCODE_USER_NAME`.
* `@user:<name-or-email>` expands from cached users.
* If the required variable is missing, the CLI exits with setup guidance instead of guessing.

## Workspace Cache Setup

Use the workspace cache before routine queries so repeated API calls stay low. Setup can be explicit:

```bash
python3 scripts/pingcode.py --cache-projects
python3 scripts/pingcode.py --set-current-project PROJECT_ID
python3 scripts/pingcode.py --cache-sprints
python3 scripts/pingcode.py --set-current-sprint SPRINT_ID
python3 scripts/pingcode.py --cache-users
python3 scripts/pingcode.py --set-current-user USER_ID_OR_CACHED_NAME
python3 scripts/pingcode.py --cache-states --work-item-type-id TYPE_ID
```

If a work item query needs a current project or sprint and the preference is missing, the CLI fetches and caches the relevant list, returns selectable JSON options plus the exact `--set-current-project` or `--set-current-sprint` command, and exits non-zero. Ask the user to choose one returned option, cache that selection, then retry the original query.

`--cache-users` uses the cached current project or `--project-id` to cache project members. It falls back to `/v1/directory/users` only when no project is available. Cached user lists let agents answer "xxx 的工作项" with `--param assignee_ids=@user:xxx` without another lookup.

For `GET /v1/project/work_items`, the CLI automatically applies cached defaults:

* current user as `assignee_ids`
* current project as `project_ids`
* current sprint/iteration as `sprint_ids`

If the user explicitly asks for all users, all projects, or all iterations, pass `--all-users`, `--all-projects`, or `--all-sprints`.

## View My Current Unfinished Tasks

```bash
python3 scripts/pingcode.py --method GET --path /v1/project/work_items --param page_size=100
```

Use this same current-user filter for generic work item queries unless the user explicitly asks for "所有人" / all users.

Optional filters:

```bash
python3 scripts/pingcode.py --method GET --path /v1/project/work_items --param type_ids=story,task --param page_size=100
```

The model should treat state types `pending` and `in_progress` as unfinished unless the user defines a different rule.

## View My Unresolved Defects

```bash
python3 scripts/pingcode.py --method GET --path /v1/project/work_items --param type_ids=bug --param page_size=100
```

This returns assigned bugs whose state type is `pending` or `in_progress`.

## Create a Work Item Under a Story

1. Find the parent story by identifier or keywords:

   ```bash
   python3 scripts/pingcode.py --method GET --path /v1/project/work_items --param identifier=MND-123
   ```

2. Read `id`, `project.id`, and choose child `type_id`.
3. Dry run:

   ```bash
   python3 scripts/pingcode.py --method POST --path /v1/project/work_items --data '{"project_id":"PROJECT_ID","type_id":"task","parent_id":"STORY_ID","title":"Child task","assignee_id":"@me"}' --dry-run
   ```

4. Execute only after the parent story is unambiguous. Omit `assignee_id` only when the user explicitly asks for "所有人" / unassigned behavior or names a different assignee.

## Update a Work Item Status

1. Locate the work item:

   ```bash
   python3 scripts/pingcode.py --method GET --path /v1/project/work_items --param identifier=SCR-123
   ```

2. Read the work item's `project.id` and `type`.
3. Fetch available states from cache, or refresh cache if needed:

   ```bash
   python3 scripts/pingcode.py --cache-states --project-id PROJECT_ID --work-item-type-id TYPE_ID
   python3 scripts/pingcode.py --method GET --path /v1/project/work_item/states --param project_id=PROJECT_ID --param work_item_type_id=TYPE_ID
   ```

4. Choose the exact `state_id`.
5. Dry run the patch:

   ```bash
   python3 scripts/pingcode.py --method PATCH --path /v1/project/work_items/WORK_ITEM_ID --data '{"state_id":"STATE_ID"}' --dry-run
   ```

6. Execute only after target item and state are unambiguous.

## Create a Work Item or Story

1. Resolve the project:

   ```bash
   python3 scripts/pingcode.py --method GET --path /v1/project/projects --param keywords="Project name"
   ```

2. Resolve the work item type:

   ```bash
   python3 scripts/pingcode.py --method GET --path /v1/project/work_item/types --param project_id=PROJECT_ID
   ```

3. Resolve optional state, priority, sprint, board, entry, and assignee IDs.
4. Dry run:

   ```bash
   python3 scripts/pingcode.py --method POST --path /v1/project/work_items --data '{"project_id":"PROJECT_ID","type_id":"story","title":"Title","assignee_id":"@me"}' --dry-run
   ```

5. Execute without `--dry-run`. Omit `assignee_id` only when the user explicitly asks for "所有人" / unassigned behavior or names a different assignee.

## Create a Product Idea

1. Resolve the product:

   ```bash
   python3 scripts/pingcode.py --method GET --path /v1/ship/products --param keywords="Product name"
   ```

2. Resolve optional suites, states, priorities, and assignee IDs.
3. Dry run:

   ```bash
   python3 scripts/pingcode.py --method POST --path /v1/ship/ideas --data '{"product_id":"PRODUCT_ID","title":"Idea title"}' --dry-run
   ```

4. Execute without `--dry-run`.

## Use an Unwrapped Endpoint

Call any supported PingCode REST endpoint with the single CLI command:

```bash
python3 scripts/pingcode.py --method GET --path /v1/project/projects --param page_size=20
python3 scripts/pingcode.py --method PATCH --path /v1/project/projects/PROJECT_ID --data '{"description":"Updated"}' --dry-run
```

For write operations, always run `--dry-run` first.
