# PingCode Skill Multi-Agent Install

## Goal

Make a single `npx pingcode-skill@latest` invocation install both the `pingcode` and `pingcode-ctx` skills into every supported agent's user-level skill home in one shot, so users no longer need to remember per-agent `--target` paths. Also refresh the public landing page (`index.html`) and `README.md` to match the simpler one-command story and surface an explicit update command.

## What I Already Know

- Today `bin/install.js` writes to a single `targetDir`, defaulting to `~/.codex/skills/pingcode` (`CODEX_HOME` override supported), and creates a sibling `pingcode-ctx` alias skill via `installAliasSkill`.
- Claude Code, OpenClaw and Hermes use different user-level skill roots:
  - Codex: `~/.codex/skills/<name>/SKILL.md`
  - Claude Code: `~/.claude/skills/<name>/SKILL.md`
  - OpenClaw: `~/.openclaw/skills/<name>/SKILL.md`
  - Hermes: `~/.hermes/skills/<category>/<name>/SKILL.md` (category subdirectory is required; we will use `project-management`)
- The README and `index.html` currently show two separate commands ("Codex 安装" / "Claude Code 安装") and do not mention OpenClaw or Hermes. There is no first-class "update" command — README only says "更新到最新版本时可运行 `npx pingcode-skill@latest --force`".
- `rewriteInstalledDocs` rewrites doc examples to absolute paths under the install root. Each agent root needs its own rewrite, because the absolute path differs per root.
- `tests/test_install.py` covers the current single-target behavior; it needs to be extended to cover the new multi-root behavior and the existing single-target `--target` escape hatch must keep working.

## Requirements

### Installer (`bin/install.js`)

- Default behavior of `npx pingcode-skill@latest` (no flags): install into all four agent roots:
  - `~/.codex/skills/pingcode` + `~/.codex/skills/pingcode-ctx`
  - `~/.claude/skills/pingcode` + `~/.claude/skills/pingcode-ctx`
  - `~/.openclaw/skills/pingcode` + `~/.openclaw/skills/pingcode-ctx`
  - `~/.hermes/skills/project-management/pingcode` + `~/.hermes/skills/project-management/pingcode-ctx`
- Each agent root is independent: a failure on one (permission denied, disk full, etc.) MUST NOT abort the others. Print a per-root success/failure summary at the end.
- Doc rewriting (`rewriteInstalledDocs`) and alias install (`installAliasSkill`) run once per agent root, so each installed `SKILL.md` references its own absolute scripts path.
- Existing flags keep working with adjusted semantics:
  - `--force`: applies to all default roots; overwrites any existing install.
  - `--target <dir>`: opt-out of multi-root, install only into the given directory (back-compat for advanced users / project-local installs like `.claude/skills/pingcode`).
  - `--help`/`-h`: updated usage text.
- Add per-agent opt-in flags so users can scope the install when they want to:
  - `--codex-only`, `--claude-only`, `--openclaw-only`, `--hermes-only` (mutually exclusive with each other and with `--target`).
- Honor `CODEX_HOME` override for the codex root; analogous env vars are NOT introduced for the other agents in this task (they can use `--target`).
- Final summary lines must clearly list which roots were written, including the `pingcode-ctx` alias path for each.

### Landing page (`index.html`)

- Replace the per-agent "常用命令" entries with a single "一键安装" command. Drop "Codex 安装" / "Claude Code 安装" rows.
- Add an "更新" row: `npx pingcode-skill@latest --force`.
- Keep "初始化上下文" (`pingcode-ctx`) and "查看 CLI 帮助" rows.
- Update the hero `.meta` chips so they no longer say "默认安装到 Codex skill 目录" / "支持 Claude Code target". Replace with messaging that conveys "一条命令同时安装到 Codex / Claude Code / OpenClaw / Hermes". Keep "Node.js 18+".
- Update the eyebrow line and three-step section to match: step 1 "安装到 Agent" should describe one-shot install across all supported agents.
- Update the console preview line `Installed to ~/.codex/skills/pingcode` to convey multi-target install (e.g. show 2-3 lines listing different roots) without making the box overflow.

### README.md

- Restructure the 安装 section: lead with the one-shot command and the four destination paths. Demote the `--target` examples to an "高级用法" subsection. Remove or revise the "复制给 AI Agent 的安装提示词" block so it no longer asks the agent to choose between Codex and Claude Code.
- Add an explicit "更新" subsection with `npx pingcode-skill@latest --force`.
- Update CLI 入口 section so the example absolute path note acknowledges that multiple roots may exist and shows the codex example as one of several.

### Tests

- `tests/test_install.py` updates:
  - default invocation creates `pingcode` + `pingcode-ctx` under all four roots, with rewritten absolute paths in each root's `SKILL.md`.
  - `--target` still installs only at the explicit path (back-compat).
  - `--codex-only` / `--claude-only` / `--openclaw-only` / `--hermes-only` each install only into their respective root.
  - Per-root failure does not abort other roots (simulate by creating an unwritable target directory).
  - `CODEX_HOME` override still works for the codex root and does not affect other roots.
- `python3 -m unittest discover -s tests -v` must pass.
- `npm pack --dry-run` must still pass and the shipped file list (in `package.json` `files`) must remain valid.

## Acceptance Criteria

- [ ] `npx pingcode-skill@latest` (no flags) installs `pingcode` + `pingcode-ctx` into Codex, Claude Code, OpenClaw and Hermes user-level skill homes, with the Hermes destination under the `project-management` category.
- [ ] Each installed `SKILL.md` rewrites doc examples to its own absolute scripts path, not the codex path.
- [ ] One root failing does not abort the others; the final summary clearly distinguishes succeeded vs failed roots.
- [ ] `--target`, `--force`, `--codex-only`, `--claude-only`, `--openclaw-only`, `--hermes-only`, `--help` all behave as specified.
- [ ] `CODEX_HOME` override still controls the codex root only.
- [ ] `index.html` shows one-shot install + update command, no per-agent install rows.
- [ ] `README.md` leads with one-shot install, has an "更新" subsection, and demotes `--target` to advanced usage; the AI agent prompt no longer branches by agent type.
- [ ] `tests/test_install.py` covers default multi-root install, single-target back-compat, per-agent opt-in flags, and per-root failure isolation.
- [ ] `python3 -m unittest discover -s tests -v` passes.
- [ ] `npm pack --dry-run` succeeds and shipped files list stays valid.

## Out of Scope

- Adding env vars analogous to `CODEX_HOME` for `~/.claude`, `~/.openclaw`, `~/.hermes`.
- Auto-discovery that skips a root if the agent isn't installed locally — we always create the directory; agents that aren't installed simply ignore the unused dir.
- Bumping `package.json` version or publishing to npm.
- Changes to `scripts/pingcode.py` or `scripts/pingcode_ctx.py` runtime behavior.
- A native Hermes / OpenClaw plugin UI integration beyond dropping a `SKILL.md` into the right path.

## Technical Notes

- Relevant spec: `.trellis/spec/backend/quality-guidelines.md` (npm Skill Installer Contracts section).
- Installer entry: `bin/install.js`.
- Doc files to keep in sync: `README.md`, `index.html`, `SKILL.md`, `skills/pingcode-ctx/SKILL.md`, `references/workflows.md` — only the documentation prose around install should change; the embedded CLI examples already get rewritten by `rewriteInstalledDocs`.
- Tests: `tests/test_install.py` is the source of truth for installer behavior; extend rather than replace.
- This task is intentionally decoupled from the still-in-progress task `05-25-pingcode-context-frontend-flow`; it should not modify that task's scope or PRD.
