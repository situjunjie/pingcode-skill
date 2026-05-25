#!/usr/bin/env python3
"""Single-command PingCode REST API CLI for AI agents."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://open.pingcode.com"
DEFAULT_TOKEN_CACHE = "~/.cache/pingcode-skill/token.json"
DEFAULT_WORKSPACE_CACHE = ".pingcode-skill/cache.json"
CLI_COMMAND = f"python3 {shlex.quote(str(Path(__file__).resolve()))}"
CTX_COMMAND = f"python3 {shlex.quote(str(Path(__file__).with_name('pingcode_ctx.py').resolve()))}"
CTX_COMMAND_ALIAS = "pingcode-ctx"
MAX_TOKEN_TTL_SECONDS = 29 * 24 * 60 * 60
HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
USER_LOOKUP_RE = re.compile(r"@user:([^,]+)")
AUTH_ENV_GUIDANCE = (
    "Configure PingCode OAuth client credentials first:\n"
    "  export PINGCODE_CLIENT_ID=\"...\"\n"
    "  export PINGCODE_CLIENT_SECRET=\"...\"\n"
    "Optional for private deployments:\n"
    "  export PINGCODE_BASE_URL=\"https://open.pingcode.com\""
)
USER_ENV_GUIDANCE = (
    "This request needs a human PingCode identity, but client_credentials is an enterprise token.\n"
    "Ask the user for their PingCode user ID/name, pass --user-id/--user-name, cache a workspace user, "
    "or configure one of:\n"
    "  export PINGCODE_USER_ID=\"...\"\n"
    "  export PINGCODE_USER_NAME=\"...\"\n"
    "Use @me for current-user-id fields; use @me_name when a name lookup is needed.\n"
    "To discover IDs, run:\n"
    f"  {CLI_COMMAND} --cache-users\n"
    "Then save your current user with:\n"
    f"  {CLI_COMMAND} --set-current-user USER_ID\n"
    "For guided workspace setup, run:\n"
    f"  {CTX_COMMAND_ALIAS}\n"
    "Or use the bundled script directly:\n"
    f"  {CTX_COMMAND}"
)
WORKSPACE_DEFAULT_GUIDANCE = (
    "PingCode workspace context is incomplete. Run the interactive setup command first:\n"
    f"  {CTX_COMMAND_ALIAS}\n"
    "Or use the bundled script directly:\n"
    f"  {CTX_COMMAND}\n"
    "It caches the current user, project, and sprint/iteration in .pingcode-skill/cache.json.\n"
    "Use --all-projects or --all-sprints when the user explicitly asks for all projects or all iterations."
)
MAX_SELECTION_OPTIONS = 20


def empty_workspace_cache() -> dict[str, Any]:
    return {
        "version": 1,
        "preferences": {},
        "users": None,
        "projects": None,
        "sprints": {},
        "work_item_types": {},
        "work_item_states": {},
        "work_item_priorities": {},
        "work_item_properties": {},
        "idea_states": {},
        "idea_priorities": {},
    }


class PingCodeError(RuntimeError):
    """Raised when a PingCode request cannot be completed."""


def parse_json_object(raw: str | None, label: str) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PingCodeError(f"{label} must be valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise PingCodeError(f"{label} must be a JSON object")
    return data


def parse_key_values(items: list[str] | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in items or []:
        if "=" not in item:
            raise PingCodeError(f"Expected key=value, got: {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise PingCodeError(f"Empty key in parameter: {item}")
        result[key] = value
    return result


def load_workspace_cache(cache_path: Path | None) -> dict[str, Any]:
    if cache_path is None:
        return empty_workspace_cache()
    try:
        payload = json.loads(cache_path.read_text())
    except (OSError, json.JSONDecodeError):
        return empty_workspace_cache()
    if not isinstance(payload, dict):
        return empty_workspace_cache()
    cache = empty_workspace_cache()
    cache.update(payload)
    if not isinstance(cache.get("preferences"), dict):
        cache["preferences"] = {}
    if not isinstance(cache.get("sprints"), dict):
        cache["sprints"] = {}
    if not isinstance(cache.get("work_item_types"), dict):
        cache["work_item_types"] = {}
    if not isinstance(cache.get("work_item_states"), dict):
        cache["work_item_states"] = {}
    if not isinstance(cache.get("work_item_priorities"), dict):
        cache["work_item_priorities"] = {}
    if not isinstance(cache.get("work_item_properties"), dict):
        cache["work_item_properties"] = {}
    if not isinstance(cache.get("idea_states"), dict):
        cache["idea_states"] = {}
    if not isinstance(cache.get("idea_priorities"), dict):
        cache["idea_priorities"] = {}
    return cache


def merge_workspace_cache(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in incoming.items():
        existing_value = merged.get(key)
        if isinstance(existing_value, dict) and isinstance(value, dict):
            merged[key] = merge_workspace_cache(existing_value, value)
        elif value is None and existing_value is not None:
            continue
        else:
            merged[key] = value
    return merged


def compact_workspace_cache_value(value: Any) -> Any:
    drop_keys = {
        "avatar",
        "color",
        "created_at",
        "created_by",
        "description",
        "is_archived",
        "is_deleted",
        "members",
        "scope_id",
        "scope_type",
        "updated_at",
        "updated_by",
        "url",
        "visibility",
    }
    if isinstance(value, list):
        return [compact_workspace_cache_value(item) for item in value]
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if key in drop_keys:
                continue
            result[key] = compact_workspace_cache_value(item)
        return result
    return value


def save_workspace_cache(cache_path: Path | None, cache: dict[str, Any]) -> None:
    if cache_path is None:
        raise PingCodeError("Workspace cache is disabled")
    latest = load_workspace_cache(cache_path)
    if latest:
        cache = merge_workspace_cache(latest, cache)
    cache = compact_workspace_cache_value(cache)
    cache["updated_at"] = int(time.time())
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cache_path.with_name(f".{cache_path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    tmp_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    tmp_path.replace(cache_path)
    try:
        cache_path.chmod(0o600)
    except OSError:
        pass


def current_user_id(user_id: str | None = None, workspace_cache: dict[str, Any] | None = None) -> str:
    preferences = (workspace_cache or {}).get("preferences") or {}
    user_id = user_id or os.getenv("PINGCODE_USER_ID") or preferences.get("current_user_id")
    if not user_id:
        raise PingCodeError(USER_ENV_GUIDANCE)
    return user_id


def current_user_name(user_name: str | None = None, workspace_cache: dict[str, Any] | None = None) -> str:
    preferences = (workspace_cache or {}).get("preferences") or {}
    user_name = user_name or os.getenv("PINGCODE_USER_NAME") or preferences.get("current_user_name")
    if not user_name:
        raise PingCodeError(USER_ENV_GUIDANCE)
    return user_name


def page_values(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    values = payload.get("values")
    if not isinstance(values, list):
        return []
    return [item for item in values if isinstance(item, dict)]


def normalized_entity(item: dict[str, Any]) -> dict[str, Any]:
    nested_user = item.get("user")
    if not isinstance(nested_user, dict):
        return item
    merged = dict(nested_user)
    for key, value in item.items():
        if key not in {"user", "project", "role"} and key not in merged:
            merged[key] = value
    return merged


def item_names(item: dict[str, Any]) -> list[str]:
    entity = normalized_entity(item)
    names: list[str] = []
    for key in ("id", "display_name", "name", "email", "identifier"):
        value = entity.get(key)
        if isinstance(value, str) and value:
            names.append(value)
    return names


def selection_item(item: dict[str, Any]) -> dict[str, Any]:
    entity = normalized_entity(item)
    result: dict[str, Any] = {}
    for key in ("id", "display_name", "name", "email", "identifier"):
        value = entity.get(key)
        if isinstance(value, str) and value:
            result[key] = value
    project = item.get("project")
    if isinstance(project, dict):
        project_name = project.get("name")
        project_id = project.get("id")
        if isinstance(project_name, str) and project_name:
            result["project_name"] = project_name
        if isinstance(project_id, str) and project_id:
            result["project_id"] = project_id
    return result


def selection_options(payload: Any) -> tuple[list[dict[str, Any]], int]:
    values = page_values(payload)
    options = [selection_item(item) for item in values[:MAX_SELECTION_OPTIONS]]
    return [item for item in options if item], len(values)


def selection_guidance(
    label: str,
    payload: Any,
    command: str,
    cache_message: str,
) -> str:
    options, total = selection_options(payload)
    suffix = "" if total <= len(options) else f" Showing first {len(options)} of {total}."
    return (
        f"Current PingCode {label} is not cached. {cache_message}\n"
        "Ask the user to choose one option, then run:\n"
        f"  {command}\n"
        f"Available {label} options ({total} total).{suffix}\n"
        f"{json.dumps(options, ensure_ascii=False, indent=2)}"
    )


def find_cached_item(items: list[dict[str, Any]], query: str, label: str) -> dict[str, Any]:
    normalized = query.strip().lower()
    if not normalized:
        raise PingCodeError(f"Empty {label} lookup")
    exact = [item for item in items if any(name.lower() == normalized for name in item_names(item))]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise PingCodeError(f"Ambiguous {label} lookup: {query}")
    partial = [item for item in items if any(normalized in name.lower() for name in item_names(item))]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        names = ", ".join(item_names(item)[0] for item in partial[:8] if item_names(item))
        raise PingCodeError(f"Ambiguous {label} lookup: {query}. Matches: {names}")
    raise PingCodeError(f"No cached {label} matched {query}. Refresh the workspace cache first.")


def cached_user_id(query: str, workspace_cache: dict[str, Any] | None = None) -> str:
    users = page_values((workspace_cache or {}).get("users"))
    item = find_cached_item(users, query, "user")
    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id:
        raise PingCodeError(f"Cached user {query} has no id")
    return item_id


def expand_identity_placeholder(
    value: Any,
    user_id: str | None = None,
    user_name: str | None = None,
    workspace_cache: dict[str, Any] | None = None,
) -> Any:
    if isinstance(value, str):
        if value == "@me":
            return current_user_id(user_id, workspace_cache=workspace_cache)
        if value in {"@me_name", "@me-name"}:
            return current_user_name(user_name, workspace_cache=workspace_cache)
        if value.startswith("@user:"):
            return cached_user_id(value.removeprefix("@user:"), workspace_cache)
        if "@me" in value:
            return value.replace("@me", current_user_id(user_id, workspace_cache=workspace_cache))
        if "@user:" in value:
            return USER_LOOKUP_RE.sub(lambda match: cached_user_id(match.group(1), workspace_cache), value)
        return value
    if isinstance(value, list):
        return [
            expand_identity_placeholder(
                item,
                user_id=user_id,
                user_name=user_name,
                workspace_cache=workspace_cache,
            )
            for item in value
        ]
    if isinstance(value, dict):
        return {
            key: expand_identity_placeholder(
                item,
                user_id=user_id,
                user_name=user_name,
                workspace_cache=workspace_cache,
            )
            for key, item in value.items()
        }
    return value


def expand_identity_placeholders(
    data: dict[str, Any] | None,
    user_id: str | None = None,
    user_name: str | None = None,
    workspace_cache: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if data is None:
        return None
    return expand_identity_placeholder(
        data,
        user_id=user_id,
        user_name=user_name,
        workspace_cache=workspace_cache,
    )


def load_cached_token(cache_path: Path) -> str | None:
    try:
        payload = json.loads(cache_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    token = payload.get("access_token")
    expires_at = payload.get("expires_at")
    if not isinstance(token, str) or not isinstance(expires_at, (int, float)):
        return None
    if expires_at <= time.time():
        return None
    return token


def save_cached_token(cache_path: Path, token: str, expires_in: Any) -> None:
    try:
        ttl = int(expires_in)
    except (TypeError, ValueError):
        ttl = MAX_TOKEN_TTL_SECONDS
    ttl = max(60, min(ttl, MAX_TOKEN_TTL_SECONDS))
    payload = {"access_token": token, "expires_at": int(time.time()) + ttl}
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(payload, indent=2) + "\n")
    try:
        cache_path.chmod(0o600)
    except OSError:
        pass


def build_url(base_url: str, path: str, params: dict[str, Any] | None = None) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        base = path
    else:
        base = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    split = urllib.parse.urlsplit(base)
    query = dict(urllib.parse.parse_qsl(split.query, keep_blank_values=True))
    for key, value in (params or {}).items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            query[key] = ",".join(str(part) for part in value)
        else:
            query[key] = str(value)
    return urllib.parse.urlunsplit(
        (split.scheme, split.netloc, split.path, urllib.parse.urlencode(query), split.fragment)
    )


def normalize_path(path: str, base_url: str = DEFAULT_BASE_URL) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return urllib.parse.urlsplit(path).path
    return urllib.parse.urlsplit(build_url(base_url, path)).path


def state_cache_key(project_id: str, work_item_type_id: str) -> str:
    return f"{project_id}::{work_item_type_id}"


def sprint_project_id(path: str, base_url: str = DEFAULT_BASE_URL) -> str | None:
    normalized = normalize_path(path, base_url=base_url)
    match = re.fullmatch(r"/v1/project/projects/([^/]+)/sprints", normalized)
    return urllib.parse.unquote(match.group(1)) if match else None


def member_project_id(path: str, base_url: str = DEFAULT_BASE_URL) -> str | None:
    normalized = normalize_path(path, base_url=base_url)
    match = re.fullmatch(r"/v1/project/projects/([^/]+)/members", normalized)
    return urllib.parse.unquote(match.group(1)) if match else None


def cached_response(
    method: str,
    path: str,
    params: dict[str, Any],
    workspace_cache: dict[str, Any],
    base_url: str,
) -> dict[str, Any] | None:
    if method.upper() != "GET":
        return None
    normalized = normalize_path(path, base_url=base_url)
    project_id = member_project_id(path, base_url=base_url)
    if project_id and isinstance(workspace_cache.get("users"), dict):
        users = workspace_cache["users"]
        if users.get("project_id") in {None, project_id}:
            return users
    if normalized == "/v1/directory/users" and isinstance(workspace_cache.get("users"), dict):
        return workspace_cache["users"]
    if normalized == "/v1/project/projects" and isinstance(workspace_cache.get("projects"), dict):
        return workspace_cache["projects"]
    project_id = sprint_project_id(path, base_url=base_url)
    if project_id:
        sprints = workspace_cache.get("sprints") or {}
        cached = sprints.get(project_id)
        return cached if isinstance(cached, dict) else None
    if normalized == "/v1/project/work_item/types":
        project_id_value = params.get("project_id")
        if isinstance(project_id_value, str):
            work_item_types = workspace_cache.get("work_item_types") or {}
            cached = work_item_types.get(project_id_value)
            return cached if isinstance(cached, dict) else None
    if normalized == "/v1/project/work_item/priorities":
        project_id_value = params.get("project_id")
        if isinstance(project_id_value, str):
            priorities = workspace_cache.get("work_item_priorities") or {}
            cached = priorities.get(project_id_value)
            return cached if isinstance(cached, dict) else None
    if normalized == "/v1/project/work_item/states":
        project_id_value = params.get("project_id")
        type_id_value = params.get("work_item_type_id")
        if isinstance(project_id_value, str) and isinstance(type_id_value, str):
            states = workspace_cache.get("work_item_states") or {}
            cached = states.get(state_cache_key(project_id_value, type_id_value))
            return cached if isinstance(cached, dict) else None
    if normalized == "/v1/project/work_item/properties":
        project_id_value = params.get("project_id")
        type_id_value = params.get("work_item_type_id")
        if isinstance(project_id_value, str) and isinstance(type_id_value, str):
            properties = workspace_cache.get("work_item_properties") or {}
            cached = properties.get(state_cache_key(project_id_value, type_id_value))
            return cached if isinstance(cached, dict) else None
    if normalized == "/v1/ship/idea/states":
        product_id_value = params.get("product_id")
        if isinstance(product_id_value, str):
            idea_states = workspace_cache.get("idea_states") or {}
            cached = idea_states.get(product_id_value)
            return cached if isinstance(cached, dict) else None
    if normalized == "/v1/ship/idea/priorities":
        product_id_value = params.get("product_id")
        if isinstance(product_id_value, str):
            idea_priorities = workspace_cache.get("idea_priorities") or {}
            cached = idea_priorities.get(product_id_value)
            return cached if isinstance(cached, dict) else None
    return None


def update_workspace_cache_for_response(
    method: str,
    path: str,
    params: dict[str, Any],
    response: dict[str, Any],
    workspace_cache: dict[str, Any],
    base_url: str,
) -> bool:
    if method.upper() != "GET" or not isinstance(response, dict):
        return False
    normalized = normalize_path(path, base_url=base_url)
    project_id = member_project_id(path, base_url=base_url)
    if project_id:
        cached = dict(response)
        cached["project_id"] = project_id
        workspace_cache["users"] = cached
        return True
    if normalized == "/v1/directory/users":
        workspace_cache["users"] = response
        return True
    if normalized == "/v1/project/projects":
        workspace_cache["projects"] = response
        return True
    project_id = sprint_project_id(path, base_url=base_url)
    if project_id:
        workspace_cache.setdefault("sprints", {})[project_id] = response
        return True
    if normalized == "/v1/project/work_item/types":
        project_id_value = params.get("project_id")
        if isinstance(project_id_value, str):
            workspace_cache.setdefault("work_item_types", {})[project_id_value] = response
            return True
    if normalized == "/v1/project/work_item/priorities":
        project_id_value = params.get("project_id")
        if isinstance(project_id_value, str):
            workspace_cache.setdefault("work_item_priorities", {})[project_id_value] = response
            return True
    if normalized == "/v1/project/work_item/states":
        project_id_value = params.get("project_id")
        type_id_value = params.get("work_item_type_id")
        if isinstance(project_id_value, str) and isinstance(type_id_value, str):
            workspace_cache.setdefault("work_item_states", {})[
                state_cache_key(project_id_value, type_id_value)
            ] = response
            return True
    if normalized == "/v1/project/work_item/properties":
        project_id_value = params.get("project_id")
        type_id_value = params.get("work_item_type_id")
        if isinstance(project_id_value, str) and isinstance(type_id_value, str):
            workspace_cache.setdefault("work_item_properties", {})[
                state_cache_key(project_id_value, type_id_value)
            ] = response
            return True
    if normalized == "/v1/ship/idea/states":
        product_id_value = params.get("product_id")
        if isinstance(product_id_value, str):
            workspace_cache.setdefault("idea_states", {})[product_id_value] = response
            return True
    if normalized == "/v1/ship/idea/priorities":
        product_id_value = params.get("product_id")
        if isinstance(product_id_value, str):
            workspace_cache.setdefault("idea_priorities", {})[product_id_value] = response
            return True
    return False


class PingCodeClient:
    def __init__(
        self,
        base_url: str,
        client_id: str | None = None,
        client_secret: str | None = None,
        token: str | None = None,
        token_cache: str | None = DEFAULT_TOKEN_CACHE,
        workspace_cache: str | None = DEFAULT_WORKSPACE_CACHE,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = token
        self.token_cache = Path(token_cache).expanduser() if token_cache else None
        self.workspace_cache_path = Path(workspace_cache).expanduser() if workspace_cache else None
        self.workspace_cache = load_workspace_cache(self.workspace_cache_path)

    def access_token(self) -> str:
        if self.token:
            return self.token
        if self.token_cache:
            cached = load_cached_token(self.token_cache)
            if cached:
                self.token = cached
                return cached
        if not self.client_id or not self.client_secret:
            raise PingCodeError(
                "Missing credentials. Set PINGCODE_CLIENT_ID and PINGCODE_CLIENT_SECRET, "
                "or pass --token.\n"
                f"{AUTH_ENV_GUIDANCE}"
            )
        response = self.raw_request(
            "GET",
            "/v1/auth/token",
            params={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            auth=False,
        )
        token = response.get("access_token")
        if not isinstance(token, str) or not token:
            raise PingCodeError("Token response did not include access_token")
        self.token = token
        if self.token_cache:
            save_cached_token(self.token_cache, token, response.get("expires_in"))
        return token

    def raw_request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        auth: bool = True,
    ) -> dict[str, Any]:
        url = build_url(self.base_url, path, params)
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if auth:
            headers["Authorization"] = f"Bearer {self.access_token()}"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            retry_after = exc.headers.get("x-pc-retry-after")
            suffix = f" retry_after={retry_after}" if retry_after else ""
            raise PingCodeError(f"HTTP {exc.code} {exc.reason}.{suffix} {detail}") from exc
        except urllib.error.URLError as exc:
            raise PingCodeError(f"Request failed: {exc.reason}") from exc
        if not content:
            return {}
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise PingCodeError(f"Response was not JSON: {content[:300]}") from exc
        if not isinstance(parsed, dict):
            return {"value": parsed}
        return parsed

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        dry_run: bool = False,
        use_workspace_cache: bool = True,
    ) -> dict[str, Any]:
        method = method.upper()
        if method not in HTTP_METHODS:
            raise PingCodeError(f"Unsupported method: {method}")
        if dry_run:
            return {
                "dry_run": True,
                "method": method,
                "url": build_url(self.base_url, path, params),
                "path": path,
                "params": params or {},
                "json": body,
            }
        request_params = params or {}
        if use_workspace_cache:
            cached = cached_response(method, path, request_params, self.workspace_cache, self.base_url)
            if cached is not None:
                return cached
        response = self.raw_request(method, path, params=params, body=body)
        if self.workspace_cache_path is not None and update_workspace_cache_for_response(
            method,
            path,
            request_params,
            response,
            self.workspace_cache,
            self.base_url,
        ):
            save_workspace_cache(self.workspace_cache_path, self.workspace_cache)
        return response

    def save_workspace_cache(self) -> None:
        save_workspace_cache(self.workspace_cache_path, self.workspace_cache)

    def fetch_project_users(self, project_id: str) -> dict[str, Any]:
        path = f"/v1/project/projects/{urllib.parse.quote(project_id)}/members"
        response = self.request("GET", path, params={"page_size": 100}, use_workspace_cache=False)
        update_workspace_cache_for_response(
            "GET",
            path,
            {"page_size": 100},
            response,
            self.workspace_cache,
            self.base_url,
        )
        self.save_workspace_cache()
        return response


def list_command(client: PingCodeClient, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    return client.request("GET", path, params=params or {})


def refresh_command(client: PingCodeClient, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    return client.request("GET", path, params=params or {}, use_workspace_cache=False)


def cache_projects(client: PingCodeClient) -> dict[str, Any]:
    return refresh_command(client, "/v1/project/projects", {"page_size": 100})


def cache_sprints(client: PingCodeClient, project_id: str) -> dict[str, Any]:
    return refresh_command(
        client,
        f"/v1/project/projects/{urllib.parse.quote(project_id)}/sprints",
        {"page_size": 100},
    )


def cache_work_item_types(client: PingCodeClient, project_id: str) -> dict[str, Any]:
    return refresh_command(
        client,
        "/v1/project/work_item/types",
        {"project_id": project_id, "page_size": 100},
    )


def cache_work_item_priorities(client: PingCodeClient, project_id: str) -> dict[str, Any]:
    return refresh_command(
        client,
        "/v1/project/work_item/priorities",
        {"project_id": project_id, "page_size": 100},
    )


def cache_work_item_states(client: PingCodeClient, project_id: str, work_item_type_id: str) -> dict[str, Any]:
    return refresh_command(
        client,
        "/v1/project/work_item/states",
        {"project_id": project_id, "work_item_type_id": work_item_type_id},
    )


def cache_all_work_item_states(client: PingCodeClient, project_id: str) -> dict[str, Any]:
    types_payload = cache_work_item_types(client, project_id)
    states: dict[str, Any] = {}
    for item in page_values(types_payload):
        type_id = item.get("id")
        if not isinstance(type_id, str) or not type_id:
            continue
        states[type_id] = cache_work_item_states(client, project_id, type_id)
    return {
        "project_id": project_id,
        "work_item_types": types_payload,
        "work_item_states": states,
    }


def cache_work_item_properties(client: PingCodeClient, project_id: str, work_item_type_id: str) -> dict[str, Any]:
    return refresh_command(
        client,
        "/v1/project/work_item/properties",
        {"project_id": project_id, "work_item_type_id": work_item_type_id, "page_size": 100},
    )


def cache_all_work_item_properties(client: PingCodeClient, project_id: str) -> dict[str, Any]:
    types_payload = cache_work_item_types(client, project_id)
    properties: dict[str, Any] = {}
    for item in page_values(types_payload):
        type_id = item.get("id")
        if not isinstance(type_id, str) or not type_id:
            continue
        properties[type_id] = cache_work_item_properties(client, project_id, type_id)
    return {
        "project_id": project_id,
        "work_item_types": types_payload,
        "work_item_properties": properties,
    }


def cache_idea_states(client: PingCodeClient, product_id: str) -> dict[str, Any]:
    return refresh_command(
        client,
        "/v1/ship/idea/states",
        {"product_id": product_id, "page_size": 100},
    )


def cache_idea_priorities(client: PingCodeClient, product_id: str) -> dict[str, Any]:
    return refresh_command(
        client,
        "/v1/ship/idea/priorities",
        {"product_id": product_id, "page_size": 100},
    )


def cache_users(client: PingCodeClient, project_id: str | None = None) -> dict[str, Any]:
    selected_project_id = project_id or (client.workspace_cache.get("preferences") or {}).get("current_project_id")
    if isinstance(selected_project_id, str) and selected_project_id:
        return client.fetch_project_users(selected_project_id)
    try:
        return refresh_command(client, "/v1/directory/users", {"page_size": 100})
    except PingCodeError as exc:
        raise PingCodeError(
            f"{exc}\n"
            "If this tenant does not expose a global user-list endpoint, set a current project first or pass "
            "--project-id so the CLI can cache project members."
        ) from exc


def context_options(client: PingCodeClient, kind: str, project_id: str | None = None) -> dict[str, Any]:
    if kind == "project":
        payload = cache_projects(client)
    elif kind == "sprint":
        selected_project_id = project_id or (client.workspace_cache.get("preferences") or {}).get("current_project_id")
        if not isinstance(selected_project_id, str) or not selected_project_id:
            raise PingCodeError("Provide --project-id or set a cached current project before listing sprint options")
        payload = cache_sprints(client, selected_project_id)
    elif kind == "user":
        payload = cache_users(client, project_id)
    else:
        raise PingCodeError(f"Unsupported context option kind: {kind}")
    options, total = selection_options(payload)
    return {"kind": kind, "total": total, "options": options}


def set_current_user(client: PingCodeClient, user_id: str) -> dict[str, Any]:
    users_payload = client.workspace_cache.get("users")
    users = page_values(users_payload)
    found = None
    if users:
        try:
            found = find_cached_item(users, user_id, "user")
        except PingCodeError:
            found = next((item for item in users if item.get("id") == user_id), None)
    preferences = client.workspace_cache.setdefault("preferences", {})
    entity = normalized_entity(found) if found else None
    preferences["current_user_id"] = (
        entity.get("id") if entity and isinstance(entity.get("id"), str) else user_id
    )
    if found:
        for key in ("display_name", "name", "email"):
            value = entity.get(key) if entity else None
            if isinstance(value, str) and value:
                preferences["current_user_name"] = value
                break
    client.save_workspace_cache()
    return {"preferences": preferences, "message": "current user cached"}


def set_current_project(client: PingCodeClient, project_id: str) -> dict[str, Any]:
    projects = page_values(client.workspace_cache.get("projects"))
    found = None
    if projects:
        try:
            found = find_cached_item(projects, project_id, "project")
        except PingCodeError:
            found = next((item for item in projects if item.get("id") == project_id), None)
    preferences = client.workspace_cache.setdefault("preferences", {})
    preferences["current_project_id"] = found.get("id") if found and isinstance(found.get("id"), str) else project_id
    if found and isinstance(found.get("name"), str):
        preferences["current_project_name"] = found["name"]
    client.save_workspace_cache()
    return {"preferences": preferences, "message": "current project cached"}


def set_current_sprint(client: PingCodeClient, sprint_id: str) -> dict[str, Any]:
    preferences = client.workspace_cache.setdefault("preferences", {})
    all_sprints = []
    for payload in (client.workspace_cache.get("sprints") or {}).values():
        all_sprints.extend(page_values(payload))
    found = None
    if all_sprints:
        try:
            found = find_cached_item(all_sprints, sprint_id, "sprint")
        except PingCodeError:
            found = next((item for item in all_sprints if item.get("id") == sprint_id), None)
    preferences["current_sprint_id"] = found.get("id") if found and isinstance(found.get("id"), str) else sprint_id
    if found and isinstance(found.get("name"), str):
        preferences["current_sprint_name"] = found["name"]
    client.save_workspace_cache()
    return {"preferences": preferences, "message": "current sprint cached"}


def apply_default_work_item_filters(
    path: str,
    params: dict[str, Any],
    client: PingCodeClient,
    user_id: str | None = None,
    user_name: str | None = None,
    current_user: bool = True,
    all_projects: bool = False,
    all_sprints: bool = False,
    discover_missing_defaults: bool = True,
) -> dict[str, Any]:
    if (
        normalize_path(path, base_url=client.base_url) != "/v1/project/work_items"
        or not path_is_list_work_items(path, base_url=client.base_url)
    ):
        return params
    result = dict(params)
    preferences = client.workspace_cache.get("preferences") or {}
    if current_user and "assignee_ids" not in result:
        result["assignee_ids"] = current_user_id(user_id, workspace_cache=client.workspace_cache)
    if not all_projects and "project_ids" not in result:
        project_id = preferences.get("current_project_id")
        if not isinstance(project_id, str) or not project_id:
            raise PingCodeError(WORKSPACE_DEFAULT_GUIDANCE)
        result["project_ids"] = project_id
    if not all_sprints and "sprint_ids" not in result:
        sprint_id = preferences.get("current_sprint_id")
        if not isinstance(sprint_id, str) or not sprint_id:
            raise PingCodeError(WORKSPACE_DEFAULT_GUIDANCE)
        result["sprint_ids"] = sprint_id
    return expand_identity_placeholders(
        result,
        user_id=user_id,
        user_name=user_name,
        workspace_cache=client.workspace_cache,
    ) or {}


def ensure_work_item_workspace_context(
    path: str,
    client: PingCodeClient,
    method: str = "GET",
    current_user: bool = True,
    all_projects: bool = False,
    all_sprints: bool = False,
) -> None:
    if normalize_path(path, base_url=client.base_url) != "/v1/project/work_items":
        return
    if method.upper() not in {"GET", "POST"}:
        return
    preferences = client.workspace_cache.get("preferences") or {}
    required = []
    if current_user:
        required.append("current_user_id")
    if not all_projects:
        required.append("current_project_id")
    if not all_sprints:
        required.append("current_sprint_id")
    missing = [key for key in required if not isinstance(preferences.get(key), str) or not preferences.get(key)]
    if missing:
        raise PingCodeError(f"{WORKSPACE_DEFAULT_GUIDANCE}\nMissing preferences: {', '.join(missing)}")


def apply_default_work_item_create_body(
    method: str,
    path: str,
    body: dict[str, Any] | None,
    client: PingCodeClient,
    user_id: str | None = None,
    current_user: bool = True,
) -> dict[str, Any] | None:
    if (
        method.upper() != "POST"
        or normalize_path(path, base_url=client.base_url) != "/v1/project/work_items"
        or body is None
    ):
        return body
    result = dict(body)
    if current_user and "assignee_id" not in result:
        result["assignee_id"] = current_user_id(user_id, workspace_cache=client.workspace_cache)
    return result


def path_is_list_work_items(path: str, base_url: str = DEFAULT_BASE_URL) -> bool:
    return normalize_path(path, base_url=base_url) == "/v1/project/work_items"


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Single-command PingCode REST API caller",
        epilog=(
            "Examples: "
            f"{CLI_COMMAND} --method GET --path /v1/project/projects --param page_size=20; "
            f"{CLI_COMMAND} --method POST --path /v1/project/work_items "
            "--data '{\"project_id\":\"...\",\"type_id\":\"story\",\"title\":\"...\"}'"
        ),
    )
    parser.add_argument("--base-url", default=os.getenv("PINGCODE_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--client-id", default=os.getenv("PINGCODE_CLIENT_ID"))
    parser.add_argument("--client-secret", default=os.getenv("PINGCODE_CLIENT_SECRET"))
    parser.add_argument("--token", default=os.getenv("PINGCODE_ACCESS_TOKEN"))
    parser.add_argument("--user-id", default=os.getenv("PINGCODE_USER_ID"))
    parser.add_argument("--user-name", default=os.getenv("PINGCODE_USER_NAME"))
    parser.add_argument("--no-token-cache", action="store_true")
    parser.add_argument(
        "--workspace-cache",
        default=os.getenv("PINGCODE_WORKSPACE_CACHE", DEFAULT_WORKSPACE_CACHE),
        help="Local workspace cache for users, dictionaries, and current project/sprint preferences",
    )
    parser.add_argument("--no-workspace-cache", action="store_true")
    parser.add_argument("--no-cache-read", action="store_true", help="Bypass cached API responses")
    parser.add_argument("--cache-users", action="store_true", help="Fetch and cache PingCode users")
    parser.add_argument("--cache-projects", action="store_true", help="Fetch and cache projects")
    parser.add_argument("--cache-sprints", action="store_true", help="Fetch and cache project sprints")
    parser.add_argument("--cache-work-item-types", action="store_true", help="Fetch and cache work item types")
    parser.add_argument("--cache-work-item-priorities", action="store_true", help="Fetch and cache work item priorities")
    parser.add_argument("--cache-work-item-properties", action="store_true", help="Fetch and cache work item properties")
    parser.add_argument("--cache-states", action="store_true", help="Fetch and cache work item states")
    parser.add_argument("--cache-idea-states", action="store_true", help="Fetch and cache product idea states")
    parser.add_argument("--cache-idea-priorities", action="store_true", help="Fetch and cache product idea priorities")
    parser.add_argument(
        "--context-options",
        choices=("project", "sprint", "user"),
        help="Print compact project/sprint/user options for agent frontend workspace setup",
    )
    parser.add_argument("--set-current-user", help="Save current PingCode user id in the workspace cache")
    parser.add_argument("--set-current-project", help="Save current project id in the workspace cache")
    parser.add_argument("--set-current-sprint", help="Save current sprint/iteration id in the workspace cache")
    parser.add_argument("--project-id", help="Project id for cache helper commands")
    parser.add_argument("--product-id", help="Product id for product/idea cache helper commands")
    parser.add_argument("--work-item-type-id", help="Work item type id for state/property cache helper commands")
    parser.add_argument(
        "--all-users",
        action="store_true",
        help="Do not apply the default current-user assignee filter to work item list queries",
    )
    parser.add_argument(
        "--all-projects",
        action="store_true",
        help="Do not apply the cached current-project filter to work item list queries",
    )
    parser.add_argument(
        "--all-sprints",
        action="store_true",
        help="Do not apply the cached current-sprint filter to work item list queries",
    )
    parser.add_argument("--method", default="GET", type=str.upper, choices=HTTP_METHODS)
    parser.add_argument("--path", help="API path, for example /v1/project/projects")
    parser.add_argument("--param", action="append", help="Query parameter as key=value; repeatable")
    parser.add_argument("--data", help="JSON object request body for POST/PUT/PATCH")
    parser.add_argument("--dry-run", action="store_true", help="Print request without sending it")
    return parser


def client_from_args(args: argparse.Namespace) -> PingCodeClient:
    token_cache = None if args.no_token_cache else os.getenv("PINGCODE_TOKEN_CACHE", DEFAULT_TOKEN_CACHE)
    workspace_cache = None if args.no_workspace_cache else args.workspace_cache
    return PingCodeClient(
        base_url=args.base_url,
        client_id=args.client_id,
        client_secret=args.client_secret,
        token=args.token,
        token_cache=token_cache,
        workspace_cache=workspace_cache,
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    client = client_from_args(args)
    if args.context_options:
        return context_options(client, args.context_options, args.project_id)
    if args.cache_users:
        return cache_users(client, args.project_id)
    if args.cache_projects:
        return cache_projects(client)
    if args.cache_sprints:
        project_id = args.project_id or (client.workspace_cache.get("preferences") or {}).get("current_project_id")
        if not isinstance(project_id, str) or not project_id:
            raise PingCodeError("Provide --project-id or set a cached current project before --cache-sprints")
        return cache_sprints(client, project_id)
    if args.cache_work_item_types:
        project_id = args.project_id or (client.workspace_cache.get("preferences") or {}).get("current_project_id")
        if not isinstance(project_id, str) or not project_id:
            raise PingCodeError("Provide --project-id or set a cached current project before --cache-work-item-types")
        return cache_work_item_types(client, project_id)
    if args.cache_work_item_priorities:
        project_id = args.project_id or (client.workspace_cache.get("preferences") or {}).get("current_project_id")
        if not isinstance(project_id, str) or not project_id:
            raise PingCodeError("Provide --project-id or set a cached current project before --cache-work-item-priorities")
        return cache_work_item_priorities(client, project_id)
    if args.cache_work_item_properties:
        project_id = args.project_id or (client.workspace_cache.get("preferences") or {}).get("current_project_id")
        if not isinstance(project_id, str) or not project_id:
            raise PingCodeError("Provide --project-id or set a cached current project before --cache-work-item-properties")
        if not args.work_item_type_id:
            return cache_all_work_item_properties(client, project_id)
        return cache_work_item_properties(client, project_id, args.work_item_type_id)
    if args.cache_states:
        project_id = args.project_id or (client.workspace_cache.get("preferences") or {}).get("current_project_id")
        if not isinstance(project_id, str) or not project_id:
            raise PingCodeError("Provide --project-id or set a cached current project before --cache-states")
        if not args.work_item_type_id:
            return cache_all_work_item_states(client, project_id)
        return cache_work_item_states(client, project_id, args.work_item_type_id)
    if args.cache_idea_states:
        if not args.product_id:
            raise PingCodeError("Provide --product-id before --cache-idea-states")
        return cache_idea_states(client, args.product_id)
    if args.cache_idea_priorities:
        if not args.product_id:
            raise PingCodeError("Provide --product-id before --cache-idea-priorities")
        return cache_idea_priorities(client, args.product_id)
    if args.set_current_user:
        return set_current_user(client, args.set_current_user)
    if args.set_current_project:
        return set_current_project(client, args.set_current_project)
    if args.set_current_sprint:
        return set_current_sprint(client, args.set_current_sprint)
    if not args.path:
        raise PingCodeError("--path is required unless using a cache helper command")
    workspace_cache = client.workspace_cache
    params = expand_identity_placeholders(
        parse_key_values(args.param),
        user_id=args.user_id,
        user_name=args.user_name,
        workspace_cache=workspace_cache,
    ) or {}
    ensure_work_item_workspace_context(
        args.path,
        client,
        method=args.method,
        current_user=not args.all_users,
        all_projects=args.all_projects,
        all_sprints=args.all_sprints,
    )
    if args.method == "GET":
        params = apply_default_work_item_filters(
            args.path,
            params,
            client,
            user_id=args.user_id,
            user_name=args.user_name,
            current_user=not args.all_users,
            all_projects=args.all_projects,
            all_sprints=args.all_sprints,
            discover_missing_defaults=not args.dry_run,
        )
    body = expand_identity_placeholders(
        parse_json_object(args.data, "--data"),
        user_id=args.user_id,
        user_name=args.user_name,
        workspace_cache=workspace_cache,
    )
    body = apply_default_work_item_create_body(
        args.method,
        args.path,
        body,
        client,
        user_id=args.user_id,
        current_user=not args.all_users,
    )
    return client.request(
        args.method,
        args.path,
        params=params,
        body=body,
        dry_run=args.dry_run,
        use_workspace_cache=not args.no_cache_read,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        print_json(run(args))
    except PingCodeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
