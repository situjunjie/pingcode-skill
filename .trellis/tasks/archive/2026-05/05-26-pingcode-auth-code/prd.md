# Support PingCode Authorization Code Auth

## Goal

Update the PingCode skill CLI to support PingCode's official OAuth2 authorization-code user-token flow, so agents can use a user-scoped token instead of only the current enterprise `client_credentials` token.

## What I Already Know

* The user asked to use PingCode's authorization-code authentication method for development.
* The current CLI supports explicit bearer tokens and `client_credentials`.
* Official PingCode REST docs include `授权码`, `获取用户令牌`, and `刷新用户令牌` sections.
* User tokens represent a specific PingCode user and are constrained by that user's permissions.

## Requirements

* Add CLI/env support for an authorization code:
  * `--auth-code`
  * `PINGCODE_AUTH_CODE`
* Add CLI/env support for a refresh token:
  * `--refresh-token`
  * `PINGCODE_REFRESH_TOKEN`
* Exchange `authorization_code` with `client_id`, `client_secret`, and `code` at `/v1/auth/token`.
* Persist returned `refresh_token` in the token cache together with access token metadata.
* When cached access token expires, refresh via `grant_type=refresh_token` before trying an authorization code or client credentials.
* Keep `--token` / `PINGCODE_ACCESS_TOKEN` as the highest-priority auth input.
* Preserve backwards compatibility with `client_credentials` as fallback when no user-token inputs exist.
* Update user-facing docs and skill instructions to describe the authorization-code flow and env vars.
* Add or update tests for token exchange, refresh, cache behavior, and fallback behavior.

## Acceptance Criteria

* [ ] `PingCodeClient.access_token()` can exchange an auth code and cache `access_token` plus `refresh_token`.
* [ ] `PingCodeClient.access_token()` can refresh with a refresh token and cache the new access token.
* [ ] A cached refresh token is used after an expired access token.
* [ ] Existing client-credentials tests still pass.
* [ ] CLI and context setup entry points accept the new env vars/flags.
* [ ] README, `SKILL.md`, and API/workflow references no longer describe client credentials as the only supported auth path.

## Definition of Done

* Tests added/updated and passing.
* Documentation updated.
* No secrets or tokens written to repo files.
* Trellis quality/spec review completed.

## Technical Approach

Implement user-token auth inside the existing `PingCodeClient` rather than adding a second client. Extend token cache shape in a backwards-compatible way: older cache files with only `access_token` and `expires_at` remain valid, while new cache files also store `refresh_token`.

## Decision (ADR-lite)

**Context**: PingCode supports both enterprise tokens and user tokens. The existing skill only implements enterprise tokens and compensates with separate current-user configuration.

**Decision**: Add authorization-code and refresh-token support while retaining explicit token and client-credentials compatibility.

**Consequences**: The CLI can run with user-scoped permissions. A first-time auth-code value is still a manual prerequisite; this task intentionally does not add a browser callback server.

## Out of Scope

* Launching a browser.
* Hosting a local OAuth callback server.
* Automatically creating PingCode OAuth applications or redirect URI registrations.

## Research References

* [`research/pingcode-oauth-authorization-code.md`](research/pingcode-oauth-authorization-code.md) - Official REST docs confirm authorization-code and refresh-token endpoints.

## Technical Notes

* Main implementation file: `scripts/pingcode.py`.
* Context setup client wrapper: `scripts/pingcode_ctx.py`.
* Tests: `tests/test_pingcode.py`.
* Docs: `README.md`, `SKILL.md`, `references/api.md`, `references/workflows.md`, `skills/pingcode-ctx/SKILL.md`.
