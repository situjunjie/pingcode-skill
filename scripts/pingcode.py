#!/usr/bin/env python3
"""Single-command PingCode REST API CLI for AI agents."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://open.pingcode.com"
DEFAULT_TOKEN_CACHE = "~/.cache/pingcode-skill/token.json"
MAX_TOKEN_TTL_SECONDS = 29 * 24 * 60 * 60
HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
AUTH_ENV_GUIDANCE = (
    "Configure PingCode OAuth client credentials first:\n"
    "  export PINGCODE_CLIENT_ID=\"...\"\n"
    "  export PINGCODE_CLIENT_SECRET=\"...\"\n"
    "Optional for private deployments:\n"
    "  export PINGCODE_BASE_URL=\"https://open.pingcode.com\""
)
USER_ENV_GUIDANCE = (
    "This request needs a human PingCode identity, but client_credentials is an enterprise token.\n"
    "Ask the user for their PingCode user ID/name, pass --user-id/--user-name, or configure one of:\n"
    "  export PINGCODE_USER_ID=\"...\"\n"
    "  export PINGCODE_USER_NAME=\"...\"\n"
    "Use @me for current-user-id fields; use @me_name when a name lookup is needed."
)


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


def current_user_id(user_id: str | None = None) -> str:
    user_id = user_id or os.getenv("PINGCODE_USER_ID")
    if not user_id:
        raise PingCodeError(USER_ENV_GUIDANCE)
    return user_id


def current_user_name(user_name: str | None = None) -> str:
    user_name = user_name or os.getenv("PINGCODE_USER_NAME")
    if not user_name:
        raise PingCodeError(USER_ENV_GUIDANCE)
    return user_name


def expand_identity_placeholder(value: Any, user_id: str | None = None, user_name: str | None = None) -> Any:
    if isinstance(value, str):
        if value == "@me":
            return current_user_id(user_id)
        if value in {"@me_name", "@me-name"}:
            return current_user_name(user_name)
        if "@me" in value:
            return value.replace("@me", current_user_id(user_id))
        return value
    if isinstance(value, list):
        return [expand_identity_placeholder(item, user_id=user_id, user_name=user_name) for item in value]
    if isinstance(value, dict):
        return {
            key: expand_identity_placeholder(item, user_id=user_id, user_name=user_name)
            for key, item in value.items()
        }
    return value


def expand_identity_placeholders(
    data: dict[str, Any] | None,
    user_id: str | None = None,
    user_name: str | None = None,
) -> dict[str, Any] | None:
    if data is None:
        return None
    return expand_identity_placeholder(data, user_id=user_id, user_name=user_name)


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


class PingCodeClient:
    def __init__(
        self,
        base_url: str,
        client_id: str | None = None,
        client_secret: str | None = None,
        token: str | None = None,
        token_cache: str | None = DEFAULT_TOKEN_CACHE,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = token
        self.token_cache = Path(token_cache).expanduser() if token_cache else None

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
        return self.raw_request(method, path, params=params, body=body)


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Single-command PingCode REST API caller",
        epilog=(
            "Examples: "
            "python3 scripts/pingcode.py --method GET --path /v1/project/projects --param page_size=20; "
            "python3 scripts/pingcode.py --method POST --path /v1/project/work_items "
            "--data '{\"project_id\":\"...\",\"type_id\":\"story\",\"title\":\"...\"}' --dry-run"
        ),
    )
    parser.add_argument("--base-url", default=os.getenv("PINGCODE_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--client-id", default=os.getenv("PINGCODE_CLIENT_ID"))
    parser.add_argument("--client-secret", default=os.getenv("PINGCODE_CLIENT_SECRET"))
    parser.add_argument("--token", default=os.getenv("PINGCODE_ACCESS_TOKEN"))
    parser.add_argument("--user-id", default=os.getenv("PINGCODE_USER_ID"))
    parser.add_argument("--user-name", default=os.getenv("PINGCODE_USER_NAME"))
    parser.add_argument("--no-token-cache", action="store_true")
    parser.add_argument("--method", default="GET", type=str.upper, choices=HTTP_METHODS)
    parser.add_argument("--path", required=True, help="API path, for example /v1/project/projects")
    parser.add_argument("--param", action="append", help="Query parameter as key=value; repeatable")
    parser.add_argument("--data", help="JSON object request body for POST/PUT/PATCH")
    parser.add_argument("--dry-run", action="store_true", help="Print request without sending it")
    return parser


def client_from_args(args: argparse.Namespace) -> PingCodeClient:
    token_cache = None if args.no_token_cache else os.getenv("PINGCODE_TOKEN_CACHE", DEFAULT_TOKEN_CACHE)
    return PingCodeClient(
        base_url=args.base_url,
        client_id=args.client_id,
        client_secret=args.client_secret,
        token=args.token,
        token_cache=token_cache,
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    client = client_from_args(args)
    return client.request(
        args.method,
        args.path,
        params=expand_identity_placeholders(
            parse_key_values(args.param),
            user_id=args.user_id,
            user_name=args.user_name,
        ),
        body=expand_identity_placeholders(
            parse_json_object(args.data, "--data"),
            user_id=args.user_id,
            user_name=args.user_name,
        ),
        dry_run=args.dry_run,
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
