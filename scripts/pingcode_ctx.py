#!/usr/bin/env python3
"""Interactive PingCode workspace context setup."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

try:
    from scripts import pingcode
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    import pingcode  # type: ignore[no-redef]


def page_values(payload: Any) -> list[dict[str, Any]]:
    return pingcode.page_values(payload)


def display_name(item: dict[str, Any]) -> str:
    for key in ("name", "display_name", "identifier", "email", "id"):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return "<unnamed>"


def item_id(item: dict[str, Any], label: str) -> str:
    value = item.get("id")
    if not isinstance(value, str) or not value:
        raise pingcode.PingCodeError(f"Selected {label} has no id")
    return value


def prompt_choice(label: str, items: list[dict[str, Any]], input_func=input) -> dict[str, Any]:
    if not items:
        raise pingcode.PingCodeError(f"No {label} options are available")
    print(f"\nSelect current {label}:")
    for index, item in enumerate(items, start=1):
        details = []
        item_identifier = item.get("identifier")
        item_email = item.get("email")
        if isinstance(item_identifier, str) and item_identifier:
            details.append(item_identifier)
        if isinstance(item_email, str) and item_email:
            details.append(item_email)
        suffix = f" ({', '.join(details)})" if details else ""
        print(f"  {index}. {display_name(item)} [{item_id(item, label)}]{suffix}")

    while True:
        raw = input_func(f"Enter {label} number, id, or name: ").strip()
        if not raw:
            continue
        if raw.isdigit():
            index = int(raw)
            if 1 <= index <= len(items):
                return items[index - 1]
        try:
            return pingcode.find_cached_item(items, raw, label)
        except pingcode.PingCodeError as exc:
            print(f"Invalid {label} selection: {exc}")


def fetch_projects(client: pingcode.PingCodeClient, refresh: bool = False) -> list[dict[str, Any]]:
    if refresh or not isinstance(client.workspace_cache.get("projects"), dict):
        payload = pingcode.cache_projects(client)
    else:
        payload = client.workspace_cache["projects"]
    return page_values(payload)


def fetch_sprints(client: pingcode.PingCodeClient, project_id: str, refresh: bool = False) -> list[dict[str, Any]]:
    sprints_cache = client.workspace_cache.get("sprints") or {}
    if refresh or not isinstance(sprints_cache.get(project_id), dict):
        payload = pingcode.cache_sprints(client, project_id)
    else:
        payload = sprints_cache[project_id]
    return page_values(payload)


def fetch_users(client: pingcode.PingCodeClient, project_id: str, refresh: bool = False) -> list[dict[str, Any]]:
    users_cache = client.workspace_cache.get("users")
    if (
        refresh
        or not isinstance(users_cache, dict)
        or users_cache.get("project_id") not in {None, project_id}
    ):
        payload = pingcode.cache_users(client, project_id)
    else:
        payload = users_cache
    return page_values(payload)


def cache_context(
    client: pingcode.PingCodeClient,
    project: dict[str, Any],
    sprint: dict[str, Any],
    user: dict[str, Any],
) -> dict[str, Any]:
    preferences = client.workspace_cache.setdefault("preferences", {})
    preferences["current_project_id"] = item_id(project, "project")
    preferences["current_project_name"] = display_name(project)
    preferences["current_sprint_id"] = item_id(sprint, "sprint")
    preferences["current_sprint_name"] = display_name(sprint)
    preferences["current_user_id"] = item_id(user, "user")
    preferences["current_user_name"] = display_name(user)
    client.save_workspace_cache()
    return {
        "message": "PingCode workspace context cached",
        "workspace_cache": str(client.workspace_cache_path) if client.workspace_cache_path else None,
        "preferences": preferences,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Interactively configure PingCode workspace context")
    parser.add_argument("--base-url", default=os.getenv("PINGCODE_BASE_URL", pingcode.DEFAULT_BASE_URL))
    parser.add_argument("--client-id", default=os.getenv("PINGCODE_CLIENT_ID"))
    parser.add_argument("--client-secret", default=os.getenv("PINGCODE_CLIENT_SECRET"))
    parser.add_argument("--token", default=os.getenv("PINGCODE_ACCESS_TOKEN"))
    parser.add_argument("--no-token-cache", action="store_true")
    parser.add_argument(
        "--workspace-cache",
        default=os.getenv("PINGCODE_WORKSPACE_CACHE", pingcode.DEFAULT_WORKSPACE_CACHE),
        help="Local workspace cache for users, projects, sprints, and preferences",
    )
    parser.add_argument("--refresh", action="store_true", help="Refresh project/member/sprint lists before selection")
    return parser


def run(args: argparse.Namespace, input_func=input) -> dict[str, Any]:
    token_cache = None if args.no_token_cache else os.getenv("PINGCODE_TOKEN_CACHE", pingcode.DEFAULT_TOKEN_CACHE)
    client = pingcode.PingCodeClient(
        base_url=args.base_url,
        client_id=args.client_id,
        client_secret=args.client_secret,
        token=args.token,
        token_cache=token_cache,
        workspace_cache=args.workspace_cache,
    )
    project = prompt_choice("project", fetch_projects(client, args.refresh), input_func=input_func)
    project_id = item_id(project, "project")
    sprint = prompt_choice("sprint", fetch_sprints(client, project_id, args.refresh), input_func=input_func)
    user = prompt_choice("user", fetch_users(client, project_id, args.refresh), input_func=input_func)
    return cache_context(client, project, sprint, user)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        pingcode.print_json(run(args))
    except (KeyboardInterrupt, EOFError):
        print("error: cancelled", file=sys.stderr)
        return 1
    except pingcode.PingCodeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
