# PingCode OAuth Authorization Code Research

Source: `https://open.pingcode.com/`, static assets fetched on 2026-05-26:

* `https://open.pingcode.com/api_project.js`
* `https://open.pingcode.com/api_data.js`

## Official Documentation Findings

The official REST API docs include an `授权码` section under `鉴权`.

Relevant documented endpoints:

* Request authorization: `GET https://oauth2_root/authorize?response_type=code`
  * Required query parameters include `response_type=code` and `client_id`.
  * Private deployments use an authorize page like `https://xxxxxx/oauth2/authorize`.
* Exchange authorization code: `GET /v1/auth/token?grant_type=authorization_code`
  * Required query parameters: `grant_type=authorization_code`, `client_id`, `client_secret`, `code`.
  * Response includes `access_token`, `refresh_token`, `token_type`, and `expires_in`.
  * Access token validity is documented as 30 days.
* Refresh user token: `GET /v1/auth/token?grant_type=refresh_token`
  * Required query parameters: `grant_type=refresh_token`, `refresh_token`.
  * Refresh token validity is documented as 90 days.

The docs distinguish:

* Enterprise token from `client_credentials`.
* User token from `authorization_code`, owned by a specific user and limited to data the user can operate.

## Repo Mapping

Current implementation in `scripts/pingcode.py` only supports:

* Explicit bearer token via `PINGCODE_ACCESS_TOKEN` / `--token`.
* Client credentials via `PINGCODE_CLIENT_ID` and `PINGCODE_CLIENT_SECRET`.
* Access token cache storing only `access_token` and `expires_at`.

For authorization-code support, the CLI should:

* Accept an authorization code and exchange it for a user token.
* Persist the returned `refresh_token` in the local token cache with restrictive permissions.
* Use a refresh token to renew expired access tokens before falling back to one-time authorization code exchange.
* Keep explicit `--token` as highest priority.
* Keep `client_credentials` as backwards-compatible fallback only when no user-token inputs exist.

## Recommended MVP

Add user-token support through:

* `PINGCODE_AUTH_CODE` / `--auth-code`
* `PINGCODE_REFRESH_TOKEN` / `--refresh-token`

Token selection order:

1. Explicit access token.
2. Valid cached access token.
3. Refresh token from env/CLI or cache.
4. Authorization code from env/CLI.
5. Backwards-compatible client credentials.

This implements the user's request while avoiding an embedded browser/callback server flow in this CLI task.
