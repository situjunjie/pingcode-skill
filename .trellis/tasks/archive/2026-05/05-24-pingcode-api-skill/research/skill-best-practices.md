# Skill Best Practices Research

Source: local `skill-creator` skill instructions.

## Packaging Decisions

* A skill should be a self-contained folder with required `SKILL.md`.
* Optional resources should be split by purpose:
  * `scripts/` for deterministic executable helpers.
  * `references/` for detailed docs that are loaded only when needed.
  * `agents/openai.yaml` for UI metadata.
* `SKILL.md` should stay concise and route the agent to relevant resources instead of embedding all API details.
* Avoid extra docs such as README, installation guides, and changelogs unless directly needed by the skill.

## Application to This Skill

* Root `SKILL.md` provides the workflow and command examples.
* `references/api.md` contains endpoint summaries and data model notes.
* `references/workflows.md` contains AI operational playbooks for safe PingCode mutations.
* `scripts/pingcode.py` is the single deterministic CLI entry point.
* Tests live in the repository for development quality, but are not required runtime skill context.
