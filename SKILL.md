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
export PINGCODE_USER_NAME="your PingCode display/name"
export PINGCODE_USER_ID="your PingCode user id"
```

Do not write credentials into files or prompts. `client_credentials` returns an enterprise token with broad permissions and does not represent a specific human user. When the user says "我的" or "我负责的", use `PINGCODE_USER_ID` / `PINGCODE_USER_NAME` if present; otherwise ask the user for their PingCode user name or user id before filtering by assignee.

If credentials are missing, tell the user to configure `PINGCODE_CLIENT_ID` and `PINGCODE_CLIENT_SECRET` as environment variables. For "我的" requests, tell the user to configure `PINGCODE_USER_ID` / `PINGCODE_USER_NAME`, or ask them to provide their PingCode user id/name before continuing. The CLI supports `@me` for `PINGCODE_USER_ID` and `@me_name` for `PINGCODE_USER_NAME`; it will print setup guidance if the matching environment variable is absent.

## Main Tool

Use the bundled CLI:

```bash
python3 scripts/pingcode.py --help
```

Common commands:

```bash
python3 scripts/pingcode.py --method GET --path /v1/project/projects --param page_size=20
python3 scripts/pingcode.py --method GET --path /v1/project/work_items --param project_ids=PROJECT_ID --param page_size=20
python3 scripts/pingcode.py --method GET --path /v1/project/work_item/types --param project_id=PROJECT_ID
python3 scripts/pingcode.py --method GET --path /v1/project/work_item/states --param project_id=PROJECT_ID --param work_item_type_id=TYPE_ID
python3 scripts/pingcode.py --method POST --path /v1/project/work_items --data '{"project_id":"PROJECT_ID","type_id":"story","title":"New story"}' --dry-run
python3 scripts/pingcode.py --method POST --path /v1/project/work_items --data '{"project_id":"PROJECT_ID","type_id":"task","parent_id":"STORY_ID","title":"New task"}' --dry-run
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
* Never infer a human user from an enterprise token. For "我的" requests, require `PINGCODE_USER_ID` / `PINGCODE_USER_NAME`, or ask the user and guide them to configure those variables.
* For status changes, fetch valid states for the work item project and type before patching.
* Treat HTTP 429 as rate limit. Wait for `x-pc-retry-after` seconds before retrying.
* Prefer the narrowest query possible. Pagination defaults to 30 and maxes at 100.
* Do not echo token values in final answers.
