# PingCode Skill

用于让 Codex、Claude 等 AI agent 通过 PingCode 官方 REST API 操作项目管理和产品管理数据的 skill。

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
export PINGCODE_USER_NAME="你的 PingCode 用户名或显示名"
export PINGCODE_USER_ID="你的 PingCode 用户 ID"
```

不要把 `client_secret`、access token 或 token cache 提交到仓库。

如果脚本调用时缺少 `PINGCODE_CLIENT_ID` / `PINGCODE_CLIENT_SECRET`，会直接输出 `export` 配置示例并退出。涉及“我的”“我负责的”这类请求时，企业令牌不能代表个人身份；如果没有 `PINGCODE_USER_ID` / `PINGCODE_USER_NAME`，agent 应先引导用户配置环境变量，或请用户提供自己的 PingCode 用户名称/用户 ID 后再继续。

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

涉及“我的”“我负责的”这类请求时，还需要配置用户身份：

```bash
export PINGCODE_USER_NAME="你的 PingCode 用户名或显示名"
export PINGCODE_USER_ID="你的 PingCode 用户 ID"
```

更新到最新版本时可运行：

```bash
npx pingcode-skill@latest --force
```

## 发布到 npm

发布前检查：

```bash
python3 -m unittest discover -s tests -v
python3 /Users/situjunjie/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
npm pack --dry-run
```

登录并发布：

```bash
npm login
npm publish --access public
```

如果包名 `pingcode-skill` 已被占用，把 [package.json](package.json) 的 `name` 改成 scoped 包名，例如 `@your-scope/pingcode-skill`。用户安装命令也相应变为：

```bash
npx @your-scope/pingcode-skill
```

## CLI 入口

```bash
python3 scripts/pingcode.py --help
```

常用示例：

```bash
python3 scripts/pingcode.py --method GET --path /v1/project/projects --param page_size=20
python3 scripts/pingcode.py --method GET --path /v1/project/work_items --param project_ids=PROJECT_ID --param page_size=20
python3 scripts/pingcode.py --method GET --path /v1/project/work_item/types --param project_id=PROJECT_ID
python3 scripts/pingcode.py --method GET --path /v1/project/work_item/states --param project_id=PROJECT_ID --param work_item_type_id=story
python3 scripts/pingcode.py --method POST --path /v1/project/work_items --data '{"project_id":"PROJECT_ID","type_id":"story","title":"新用户故事"}' --dry-run
python3 scripts/pingcode.py --method POST --path /v1/project/work_items --data '{"project_id":"PROJECT_ID","type_id":"task","parent_id":"STORY_ID","title":"子任务"}' --dry-run
python3 scripts/pingcode.py --method PATCH --path /v1/project/work_items/WORK_ITEM_ID --data '{"state_id":"STATE_ID"}' --dry-run
python3 scripts/pingcode.py --method GET --path /v1/ship/products --param page_size=20
python3 scripts/pingcode.py --method POST --path /v1/ship/ideas --data '{"product_id":"PRODUCT_ID","title":"新产品需求"}' --dry-run
```

写操作建议先加 `--dry-run`，确认请求体无误后再执行真实请求。

## 自然语言到命令的映射原则

- “我”的身份：因为使用企业令牌，不能从 token 推断具体用户。优先读取 `PINGCODE_USER_ID` / `PINGCODE_USER_NAME`；如果没有配置，就要求用户告知自己的 PingCode 用户名称或用户 ID。
- 用户占位符：CLI 支持在参数和 JSON 请求体里使用 `@me` 表示 `PINGCODE_USER_ID`，使用 `@me_name` 表示 `PINGCODE_USER_NAME`。如果对应环境变量不存在，脚本会输出配置引导并退出。
- “未完成”：查询工作项后，由模型把 `state.type` 为 `pending`、`in_progress` 的项视为未完成，除非用户另有定义。
- “未解决缺陷”：调用 `/v1/project/work_items`，传 `type_ids=bug` 和负责人过滤，例如 `--param assignee_ids=@me`，再按状态过滤未完成项。
- “在某故事下新增工作项”：先调用 `/v1/project/work_items` 按编号或关键词找到父故事，再调用 `POST /v1/project/work_items` 并传 `parent_id`。
- 状态更新：先查 `/v1/project/work_item/states`，不要猜 `state_id`。

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
