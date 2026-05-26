# PingCode API Research

Source: official PingCode REST API docs at `https://open.pingcode.com/`, including `api_project.js` and `api_data.json`, checked on 2026-05-24.

## Platform Facts

* Public cloud REST root: `https://open.pingcode.com`.
* Private deployment REST root pattern: `https://<host>/open`.
* OAuth page root for public cloud: `https://open.pingcode.com/oauth2`.
* Standard HTTP verbs supported: `OPTIONS`, `GET`, `PUT`, `PATCH`, `POST`, `DELETE`.
* `GET` and `DELETE` pass parameters through query string.
* `POST`, `PUT`, and `PATCH` use `content-type: application/json` and JSON body.
* Pagination defaults to `page_size=30`, maximum `page_size=100`, and `page_index=0` means first page.
* Rate limit: 200 requests per minute per identity. Over-limit returns HTTP 429 with `x-pc-retry-after`.

## Authentication

Client credentials endpoint:

```http
GET /v1/auth/token?grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}
```

The docs call the returned token an enterprise token. It does not distinguish user identity and has system administrator permissions, so scripts must treat credentials and tokens as secrets.

Protected requests use:

```http
Authorization: Bearer {access_token}
```

Docs state the access token lifetime is 30 days; deleting the PingCode app or resetting its secret invalidates the token.

## Project Management Endpoints

Projects:

| Operation | Method | Path |
|---|---:|---|
| List projects | GET | `/v1/project/projects` |
| Create project | POST | `/v1/project/projects` |
| Update project | PATCH | `/v1/project/projects/{project_id}` |
| Project progress | GET | `/v1/project/projects/{project_id}/progress` |
| Project states | GET | `/v1/project/project/states?project_id={project_id}` |
| Project members | GET | `/v1/project/projects/{project_id}/members` |

Scrum:

| Operation | Method | Path |
|---|---:|---|
| List sprints | GET | `/v1/project/projects/{project_id}/sprints` |
| Create sprint | POST | `/v1/project/projects/{project_id}/sprints` |
| Update sprint | PATCH | `/v1/project/projects/{project_id}/sprints/{sprint_id}` |

Kanban:

| Operation | Method | Path |
|---|---:|---|
| List boards | GET | `/v1/project/projects/{project_id}/boards` |
| List board entries | GET | `/v1/project/projects/{project_id}/boards/{board_id}/entries` |
| List swimlanes | GET | `/v1/project/projects/{project_id}/boards/{board_id}/swimlanes` |

Work items:

| Operation | Method | Path |
|---|---:|---|
| List work items | GET | `/v1/project/work_items` |
| Create work item | POST | `/v1/project/work_items` |
| Update work item | PATCH | `/v1/project/work_items/{work_item_id}` |
| Bulk property update | PATCH | `/v1/project/work_items` |
| Delete work item | DELETE | `/v1/project/work_items/{work_item_id}` |
| Work item types | GET | `/v1/project/work_item/types?project_id={project_id}` |
| Work item states | GET | `/v1/project/work_item/states?project_id={project_id}&work_item_type_id={work_item_type_id}` |
| Work item priorities | GET | `/v1/project/work_item/priorities?project_id={project_id}` |
| Work item properties | GET | `/v1/project/work_item/properties?project_id={project_id}&work_item_type_id={work_item_type_id}` |
| Transition history | GET | `/v1/project/work_items/{work_item_id}/transition_histories` |

Important fields for creating a work item:

* Required: `project_id`, `type_id`, `title`.
* Common optional fields: `description`, `start_at`, `end_at`, `priority_id`, `state_id`, `assignee_id`, `parent_id`, `sprint_id`, `board_id`, `entry_id`, `swimlane_id`, `story_points`, `estimated_workload`, `remaining_workload`, `properties`, `participant_ids`.
* Status updates are performed with `PATCH /v1/project/work_items/{work_item_id}` and body `{"state_id": "..."}`.
* Docs warn that `state_id` must satisfy both the work item type state scheme and allowed state transitions.

## Product Management Endpoints

Products:

| Operation | Method | Path |
|---|---:|---|
| List products | GET | `/v1/ship/products` |
| Create product | POST | `/v1/ship/products` |
| Update product | PATCH | `/v1/ship/products/{product_id}` |
| Product members | GET | `/v1/ship/products/{product_id}/members` |
| Product idea suites | GET | `/v1/ship/products/{product_id}/suites` |
| Product idea plans | GET | `/v1/ship/products/{product_id}/plans` |
| Product tags | GET | `/v1/ship/products/{product_id}/tags` |

Ideas:

| Operation | Method | Path |
|---|---:|---|
| List ideas | GET | `/v1/ship/ideas` |
| Create idea | POST | `/v1/ship/ideas` |
| Update idea | PATCH | `/v1/ship/ideas/{idea_id}` |
| Idea states | GET | `/v1/ship/idea/states?product_id={product_id}` |
| Idea priorities | GET | `/v1/ship/idea/priorities?product_id={product_id}` |
| Idea properties | GET | `/v1/ship/idea/properties?product_id={product_id}` |
| Idea plans | GET | `/v1/ship/idea/plans?product_id={product_id}` |
| Idea suites | GET | `/v1/ship/idea/suites?product_id={product_id}` |
| Transition history | GET | `/v1/ship/ideas/{idea_id}/transition_histories` |

Important fields for creating an idea:

* Required: `product_id`, `title`.
* Common optional fields: `assignee_id`, `description`, `suite_id`, `properties`.
* Updating an idea can set `title`, `description`, `state_id`, `priority_id`, `assignee_id`, `progress`, `plan_at`, `real_at`, `plan_id`, `suite_id`, `properties`.

## Skill Design Consequences

* Mutating commands should support `--dry-run` because enterprise tokens have broad permissions.
* Scripts should help fetch valid type/state/priority IDs before create/update.
* For ambiguous user requests like "move SCR-12 to done", the AI should list matching work items, list states for that work item's project/type, then patch with the chosen `state_id`.
* Keep the full official docs outside context; only load this focused reference unless the user needs an unwrapped endpoint.
