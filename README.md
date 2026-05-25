# PingCode Skill

用于让 Codex、Claude 等 AI agent 通过 PingCode 官方 REST API 操作项目管理和产品管理数据的 skill。

## 复制给 AI Agent 的安装提示词

把下面这段提示词复制给你的 AI Agent，让它在你的本机环境里完成安装：

```text
请帮我安装 PingCode skill，让当前 AI Agent 可以通过 PingCode 官方 REST API 查询和操作项目/产品数据。

安装要求：
1. 如果我是 Codex 用户，请运行：npx pingcode-skill@latest --force
2. 如果我是 Claude Code 用户，请安装到个人 skills 目录：npx pingcode-skill@latest --target "$HOME/.claude/skills/pingcode" --force
3. 如果你无法判断当前 Agent 类型，请先询问我是 Codex 还是 Claude Code，再选择对应命令。
4. 安装后请检查 skill 入口文件是否存在：
   - Codex: ~/.codex/skills/pingcode/SKILL.md
   - Claude Code: ~/.claude/skills/pingcode/SKILL.md
5. 安装完成后，引导我配置环境变量 PINGCODE_CLIENT_ID 和 PINGCODE_CLIENT_SECRET；不要把 secret 写入仓库文件，也不要在对话里回显完整 secret。
6. 如果我还需要默认查询“我的任务”，请继续引导我配置 PINGCODE_USER_NAME 或 PINGCODE_USER_ID。
```

## 能力范围

- 使用 `client_credentials` 获取 PingCode 企业令牌
- 查询项目、迭代、看板、工作项类型、状态、优先级
- 查询、创建、更新工作项
- 更新工作项状态
- 在故事下创建子工作项（通过 `parent_id`）
- 查询、创建、更新产品和产品需求
- 通过统一 `scripts/pingcode.py --method/--path` 调用 PingCode API

## 自然语言使用方式

安装并启用 skill 后，用户可以直接用自然语言描述需求，例如：

- 查看我当前没完成的任务
- 查看我的未解决缺陷
- 帮我在某个故事下新增工作项
- 把某个工作项改成已完成
- 创建一个用户故事

大模型应根据语义自动选择 `$pingcode` skill，并把自然语言转换成通用 CLI 命令和参数。不要为每个自然语言场景新增专门命令；统一使用 `scripts/pingcode.py` 的通用命令组合完成。

如果平台没有稳定的隐式 skill 选择能力，可以显式写：

```text
使用 $pingcode 查看我当前没完成的任务
```

## 凭证配置

在 PingCode 企业后台创建应用，配置数据访问范围，然后设置环境变量：

```bash
export PINGCODE_CLIENT_ID="..."
export PINGCODE_CLIENT_SECRET="..."
```

可选配置：

```bash
export PINGCODE_BASE_URL="https://open.pingcode.com"
export PINGCODE_TOKEN_CACHE="$HOME/.cache/pingcode-skill/token.json"
export PINGCODE_WORKSPACE_CACHE=".pingcode-skill/cache.json"
export PINGCODE_USER_NAME="你的 PingCode 用户名或显示名"
export PINGCODE_USER_ID="你的 PingCode 用户 ID"
```

也可以在单次调用时传入 `--client-id`、`--client-secret`、`--user-id`、`--user-name`、`--workspace-cache`。日常使用推荐放在本机 shell profile 或由 1Password、macOS Keychain、Vault、CI secret 等工具注入为环境变量；不建议把 secret 写进仓库里的配置文件。不要把 `client_secret`、access token 或 token cache 提交到仓库。

如果脚本调用时缺少 `PINGCODE_CLIENT_ID` / `PINGCODE_CLIENT_SECRET`，会直接输出 `export` 配置示例并退出。企业令牌不能代表个人身份；操作创建工作项、查询工作项时，如果用户没有明确说“所有人”或指定其他负责人，agent 应默认使用当前用户。当前用户来自 `PINGCODE_USER_ID` / `PINGCODE_USER_NAME`、`--user-id` / `--user-name` 或工作区缓存；如果没有配置，agent 应先缓存用户列表，再让用户选择自己的 PingCode 用户。

## 工作区缓存

CLI 默认把工作区偏好和常用字典缓存到 `.pingcode-skill/cache.json`，该目录已被 `.gitignore` 忽略。缓存内容包括：

- 当前用户 ID / 名称
- 当前项目 ID / 名称
- 当前迭代 ID / 名称
- 用户列表或项目成员列表
- 工作项状态字典

首次在一个工作区使用时可以按下面顺序显式初始化：

```bash
python3 scripts/pingcode.py --cache-projects
python3 scripts/pingcode.py --set-current-project PROJECT_ID
python3 scripts/pingcode.py --cache-sprints
python3 scripts/pingcode.py --set-current-sprint SPRINT_ID
python3 scripts/pingcode.py --cache-users
python3 scripts/pingcode.py --set-current-user USER_ID_OR_CACHED_NAME
python3 scripts/pingcode.py --cache-states --work-item-type-id TYPE_ID
```

如果查询工作项时缺少当前项目或当前迭代，CLI 会自动拉取并缓存项目/迭代列表，输出可选择的 JSON 选项和对应的 `--set-current-project` / `--set-current-sprint` 命令，然后以非零状态退出。agent 应把这些选项给用户选择，缓存用户选择后再重试原查询。

如果租户没有全局用户列表接口，`--cache-users --project-id PROJECT_ID` 会缓存项目成员。之后查询“某某的工作项”时可以直接使用缓存：

```bash
python3 scripts/pingcode.py --method GET --path /v1/project/work_items --param assignee_ids=@user:某某
```

查询工作项时，CLI 会自动补当前用户、当前项目、当前迭代过滤条件。用户明确要求“所有人”“全部项目”“全部迭代”时分别加 `--all-users`、`--all-projects`、`--all-sprints`。

## 安装

已发布到 npm：`pingcode-skill@0.1.0`。

安装到 Codex：

```bash
npx pingcode-skill@0.1.0
```

默认会安装到 Codex 个人 skill 目录：

```text
~/.codex/skills/pingcode
```

安装到 Claude Code：

```bash
npx pingcode-skill@0.1.0 --target "$HOME/.claude/skills/pingcode"
```

Claude Code 的个人 skills 目录是：

```text
~/.claude/skills/<skill-name>/SKILL.md
```

也可以安装成当前项目专用 skill：

```bash
npx pingcode-skill@0.1.0 --target ".claude/skills/pingcode"
```

常用安装参数：

```bash
npx pingcode-skill@0.1.0 --force
npx pingcode-skill@0.1.0 --target "$HOME/.codex/skills/pingcode"
npx pingcode-skill@0.1.0 --target "$HOME/.claude/skills/pingcode" --force
```

如果用户设置了 `CODEX_HOME`，默认安装目录会变成 `$CODEX_HOME/skills/pingcode`。

安装完成后，配置 PingCode 凭证：

```bash
export PINGCODE_CLIENT_ID="..."
export PINGCODE_CLIENT_SECRET="..."
```

创建或查询工作项时，如果没有明确指定“所有人”或其他负责人，skill 会默认使用当前用户，因此建议同时配置用户身份：

```bash
export PINGCODE_USER_NAME="你的 PingCode 用户名或显示名"
export PINGCODE_USER_ID="你的 PingCode 用户 ID"
```

更新到最新版本时可运行：

```bash
npx pingcode-skill@latest --force
```

## CLI 入口

```bash
python3 scripts/pingcode.py --help
```

常用示例：

```bash
python3 scripts/pingcode.py --method GET --path /v1/project/projects --param page_size=20
python3 scripts/pingcode.py --method GET --path /v1/project/work_items --param assignee_ids=@me --param project_ids=PROJECT_ID --param page_size=20
python3 scripts/pingcode.py --method GET --path /v1/project/work_item/types --param project_id=PROJECT_ID
python3 scripts/pingcode.py --method GET --path /v1/project/work_item/states --param project_id=PROJECT_ID --param work_item_type_id=story
python3 scripts/pingcode.py --cache-states --project-id PROJECT_ID --work-item-type-id story
python3 scripts/pingcode.py --method POST --path /v1/project/work_items --data '{"project_id":"PROJECT_ID","type_id":"story","title":"新用户故事","assignee_id":"@me"}' --dry-run
python3 scripts/pingcode.py --method POST --path /v1/project/work_items --data '{"project_id":"PROJECT_ID","type_id":"task","parent_id":"STORY_ID","title":"子任务","assignee_id":"@me"}' --dry-run
python3 scripts/pingcode.py --method PATCH --path /v1/project/work_items/WORK_ITEM_ID --data '{"state_id":"STATE_ID"}' --dry-run
python3 scripts/pingcode.py --method GET --path /v1/ship/products --param page_size=20
python3 scripts/pingcode.py --method POST --path /v1/ship/ideas --data '{"product_id":"PRODUCT_ID","title":"新产品需求"}' --dry-run
```

写操作建议先加 `--dry-run`，确认请求体无误后再执行真实请求。

## 自然语言到命令的映射原则

- 当前用户默认规则：操作创建工作项、查询工作项时，如果用户没有明确说“所有人”或指定其他负责人，默认按当前用户处理。查询工作项时 CLI 会自动加当前用户过滤；创建时在 JSON 里加 `"assignee_id":"@me"`。
- 当前项目/迭代默认规则：查询工作项时默认加缓存的当前项目和当前迭代。用户明确说“全部项目”或“全部迭代”时，用 `--all-projects` 或 `--all-sprints` 跳过对应过滤。
- “所有人”：这是当前用户默认规则的 opt-out。用户明确说“所有人”时，查询用 `--all-users`，创建时不要加 `assignee_id=@me`，但仍应尽量用项目、迭代、类型、状态等条件缩小范围。
- “我”的身份：因为使用企业令牌，不能从 token 推断具体用户。优先读取工作区缓存、`PINGCODE_USER_ID` / `PINGCODE_USER_NAME`，或使用 `--user-id` / `--user-name`；如果没有配置，就先运行 `--cache-users` 并让用户选择。
- 用户占位符：CLI 支持在参数和 JSON 请求体里使用 `@me` 表示当前用户 ID，使用 `@me_name` 表示当前用户名称，使用 `@user:<名称或邮箱>` 从缓存用户列表解析 ID。如果对应配置不存在，脚本会输出配置引导并退出。
- “未完成”：查询工作项后，由模型把 `state.type` 为 `pending`、`in_progress` 的项视为未完成，除非用户另有定义。
- “未解决缺陷”：调用 `/v1/project/work_items`，传 `type_ids=bug` 和负责人过滤，例如 `--param assignee_ids=@me`，再按状态过滤未完成项。
- “在某故事下新增工作项”：先调用 `/v1/project/work_items` 按编号或关键词找到父故事，再调用 `POST /v1/project/work_items` 并传 `parent_id`。
- 状态更新：优先用缓存状态字典；没有缓存或怀疑过期时运行 `--cache-states`，不要猜 `state_id`。

## 参考资料

- Skill 入口：[SKILL.md](SKILL.md)
- API 摘要：[references/api.md](references/api.md)
- 操作流程：[references/workflows.md](references/workflows.md)
- 官方文档：https://open.pingcode.com/

## 测试

```bash
python3 -m unittest discover -s tests -v
python3 /Users/situjunjie/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```
