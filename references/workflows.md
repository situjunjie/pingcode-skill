# PingCode Workflows

## Natural Language Mapping

| User says | Use |
|---|---|
| "查看我当前没完成的任务" | Require `PINGCODE_USER_ID` or ask for the user's PingCode identity, list work items filtered by `assignee_ids`, then interpret non-completed states |
| "查看我的未解决缺陷" | Require `PINGCODE_USER_ID` or ask for the user's PingCode identity, list work items filtered by `assignee_ids` and `type_ids=bug`, then interpret non-completed states |
| "帮我在 xxx 故事下新增工作项" | Find the story, then create a child work item with `POST /v1/project/work_items` and `parent_id` |
| "把某个工作项改成已完成/进行中" | Resolve states, then patch the work item with `state_id` |
| "创建一个故事/任务/缺陷" | Resolve project/type, then create via `POST /v1/project/work_items` |

This skill uses `client_credentials`, so the token is an enterprise token and does not represent a specific human user. For "my" requests, use `PINGCODE_USER_ID` / `PINGCODE_USER_NAME` if present. If neither is set, guide the user to configure those environment variables or ask for their PingCode user name/user id before filtering by assignee.

The CLI accepts identity placeholders:

* `@me` expands to `PINGCODE_USER_ID`.
* `@me_name` expands to `PINGCODE_USER_NAME`.
* If the required variable is missing, the CLI exits with setup guidance instead of guessing.

## View My Current Unfinished Tasks

```bash
python3 scripts/pingcode.py --method GET --path /v1/project/work_items --param assignee_ids=@me --param page_size=100
```

Optional filters:

```bash
python3 scripts/pingcode.py --method GET --path /v1/project/work_items --param assignee_ids=@me --param project_ids=PROJECT_ID --param type_ids=story,task --param page_size=100
```

The model should treat state types `pending` and `in_progress` as unfinished unless the user defines a different rule.

## View My Unresolved Defects

```bash
python3 scripts/pingcode.py --method GET --path /v1/project/work_items --param assignee_ids=@me --param type_ids=bug --param page_size=100
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
   python3 scripts/pingcode.py --method POST --path /v1/project/work_items --data '{"project_id":"PROJECT_ID","type_id":"task","parent_id":"STORY_ID","title":"Child task"}' --dry-run
   ```

4. Execute only after the parent story is unambiguous.

## Update a Work Item Status

1. Locate the work item:

   ```bash
   python3 scripts/pingcode.py --method GET --path /v1/project/work_items --param identifier=SCR-123
   ```

2. Read the work item's `project.id` and `type`.
3. Fetch available states:

   ```bash
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
   python3 scripts/pingcode.py --method POST --path /v1/project/work_items --data '{"project_id":"PROJECT_ID","type_id":"story","title":"Title"}' --dry-run
   ```

5. Execute without `--dry-run`.

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
