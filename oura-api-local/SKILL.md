---
name: oura-api-local
description: >
  Authenticate a local Oura Developer app with OAuth 2.0, save and refresh
  user-scoped Oura API tokens, and query Oura Cloud API endpoints from bundled
  scripts or curl. Use when setting up an Oura Developer app, fetching sleep,
  readiness, activity, heartrate, stress, SpO2, workout, heart health, or ring
  configuration data, inspecting raw Oura API payloads, or debugging Oura OAuth
  redirects and API requests.
---

# Oura API Local

Work with user-scoped Oura Cloud API data from local tools. This skill covers
app registration, localhost OAuth, token storage, refresh, and read-only
endpoint queries for common Oura data domains.

## Official references

Prefer the official Oura docs for exact schemas, endpoint availability,
authentication behavior, and scope details:

- `V2 docs` — `https://cloud.ouraring.com/v2/docs`
- `OpenAPI spec` — `https://cloud.ouraring.com/v2/static/json/openapi-1.28.json`
- `Authentication docs` — `https://cloud.ouraring.com/docs/authentication`
- Personal access tokens are deprecated; prefer OAuth for all new local setups.

Use the examples in this skill for workflow and local tooling, but defer to the
official docs when a field name, scope, or endpoint behavior is unclear.

## Prerequisites

- `python3` 3.9+ available in `PATH`
- Access to create or use an Oura Developer app. Quick check: sign in to `https://cloud.ouraring.com/` and verify you can view or create an app in the developer portal before starting the OAuth flow.
- A redirect URI you control, usually `http://localhost:8787/callback`
- Network access to `cloud.ouraring.com` and `api.ouraring.com`

Both bundled scripts use only Python standard-library modules.

## App registration

Use these values when registering the Oura Developer app:

- `Display Name` — choose a clear app name that describes the tool from the
  user's perspective. Prefer a simple, accurate name such as a project name,
  team tool name, or local-tool name. Avoid names that imply the app is
  official Oura software unless it actually is.
- `Description` — write a short description of what the app does, who it is
  for, and whether it is read-only. Mention the main Oura data categories the
  app will access if that helps clarify its purpose. Example pattern:
  `Read-only app for accessing and analyzing Oura data in local tools.`
- `Contact Email` — use an email address controlled by the app owner.
- `Website` — use a page controlled by the app owner that describes the app.
  For local or personal apps, a simple GitHub profile, repo, or static site is
  enough.
- `Privacy Policy` — use a page controlled by the app owner. For local or
  personal apps, a short static page describing token handling and local-only
  storage is usually enough.
- `Terms of Service` — use a page controlled by the app owner. For local or
  personal apps, a short page stating the app's intended usage is usually
  enough.
- `Redirect URIs` — register exactly one URI and keep it identical to
  `OURA_REDIRECT_URI`. Recommended local default:
  `http://localhost:8787/callback`.
- `Scopes` — select the scopes the app should request. For broad exploratory
  access, select all available scopes in the portal. Keep the selected scopes
  aligned with the data domains the app actually needs.

If the app still uses placeholder or third-party URLs, update those fields
before sharing or publishing the app configuration.

## Environment

Export these values before running the bundled scripts:

```bash
export OURA_CLIENT_ID='...'
export OURA_CLIENT_SECRET='...'
export OURA_REDIRECT_URI='http://localhost:8787/callback'
```

Optional:

```bash
export OURA_TOKEN_PATH="${XDG_CONFIG_HOME:-$HOME/.config}/oura-api-local/tokens.json"
export OURA_ACCESS_TOKEN='...'
```

- `OURA_TOKEN_PATH` overrides the token file used by both scripts.
- `OURA_ACCESS_TOKEN` lets the query helper skip the token file.

## Security

- Rotate any client secret that has been pasted into chat, checked into a file, logged, or otherwise exposed. If a secret was shared during setup, prefer creating or rotating a fresh secret before real use.
- Do not commit the token file or client secret to a repository.
- Prefer storing the token file outside the working repository. The default
  scripts path uses `~/.config/oura-api-local/tokens.json` unless overridden.
- If you intentionally keep tokens in a repo-local file, add that file to
  `.gitignore` first.

## Quick start

1. Export `OURA_CLIENT_ID`, `OURA_CLIENT_SECRET`, and `OURA_REDIRECT_URI`.
2. Authorize the app and save tokens:

```bash
python3 <skill-directory>/scripts/oura_authorize_local.py
```

3. Query user data with the generic GET helper:

```bash
python3 <skill-directory>/scripts/oura_api_get.py /v2/usercollection/personal_info
python3 <skill-directory>/scripts/oura_api_get.py /v2/usercollection/daily_sleep --param start_date=YYYY-MM-DD --param end_date=YYYY-MM-DD
```

## OAuth workflow

### Authorize

- Omit the `scope` query parameter to request all scopes configured on the app.
- If you explicitly pass scopes outside the script, treat the app
  configuration as the source of truth and keep the request aligned with it.
- Keep `OURA_REDIRECT_URI` exactly equal to the redirect URI saved in the Oura
  Developer Portal.
- Use `--auth-url-only` to print the authorize URL without starting the
  callback server.
- Use `--no-browser` if you want to open the authorize URL manually.
- Use `--skip-verify` if you only want tokens and do not want a follow-up
  verification request.
- Use `--verify-endpoint` and `--verify-param` to customize the post-auth
  verification request.

### Verify

- The authorization helper verifies the token after OAuth by making a read-only
  GET request.
- Default verification uses `daily_sleep` for the last 7 days because it is
  easy to sanity-check, but any read-only endpoint can be used.
- If verification returns no rows, sync the ring in the Oura app or query a
  different endpoint and run again.

### Refresh tokens

Refresh tokens manually with:

```bash
curl -u "$OURA_CLIENT_ID:$OURA_CLIENT_SECRET" \
  -X POST https://api.ouraring.com/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=$OURA_REFRESH_TOKEN"
```

- Treat refresh tokens as single-use.
- Overwrite the saved token file after each refresh.

## Query user data

### Generic query helper

Use the bundled GET helper for most read-only API exploration:

```bash
python3 <skill-directory>/scripts/oura_api_get.py /v2/usercollection/personal_info
python3 <skill-directory>/scripts/oura_api_get.py /v2/usercollection/daily_activity --param start_date=YYYY-MM-DD --param end_date=YYYY-MM-DD
python3 <skill-directory>/scripts/oura_api_get.py /v2/usercollection/daily_readiness --param start_date=YYYY-MM-DD --param end_date=YYYY-MM-DD
python3 <skill-directory>/scripts/oura_api_get.py /v2/usercollection/daily_stress --param start_date=YYYY-MM-DD --param end_date=YYYY-MM-DD
python3 <skill-directory>/scripts/oura_api_get.py /v2/usercollection/ring_configuration
```

Notes:

- Pass each query parameter as `--param key=value`.
- The helper resolves tokens in this order: `--access-token`,
  `OURA_ACCESS_TOKEN`, `OURA_TOKEN_PATH`, then the default config path.
- Use `--print-url-only` to verify the resolved request URL without making the
  API call.
- Use a full URL instead of a path if you already copied a URL from the docs.

### Common endpoints

Use these paths with the helper or with curl:

- `GET /v2/usercollection/personal_info`
- `GET /v2/usercollection/daily_sleep?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- `GET /v2/usercollection/daily_readiness?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- `GET /v2/usercollection/daily_activity?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- `GET /v2/usercollection/daily_stress?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- `GET /v2/usercollection/daily_spo2?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- `GET /v2/usercollection/workout?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- `GET /v2/usercollection/heartrate?start_datetime=ISO8601&end_datetime=ISO8601`
- `GET /v2/usercollection/ring_configuration`
- `GET /v2/usercollection/daily_cardiovascular_age?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

### Curl pattern

If you already have an access token, use curl directly:

```bash
curl -H "Authorization: Bearer $OURA_ACCESS_TOKEN" \
  "https://api.ouraring.com/v2/usercollection/daily_sleep?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD"
```

Prefer the bundled helper when you want the token loaded automatically from the
saved token file or when you want a quick dry run with `--print-url-only`.

## Failure modes

- **Browser opens but callback never completes** — check that the registered
  redirect URI exactly matches `OURA_REDIRECT_URI`, and that port `8787` is not
  already in use.
- **Bind error on localhost callback** — choose a different local port, update
  both the app configuration and `OURA_REDIRECT_URI`, then retry.
- **401/403 from the API** — verify the token is current and the app has the
  required scopes for that endpoint.
- **No data returned** — sync the ring in the Oura app, widen the requested
  date range, or verify the endpoint supports the requested data type.
- **Token file missing or invalid** — re-run the authorization helper or point
  `OURA_TOKEN_PATH` at the correct file.

## Resources

### scripts/

- `scripts/oura_authorize_local.py` — Local OAuth callback helper that saves
  tokens and verifies access with a configurable GET request.
- `scripts/oura_api_get.py` — Generic GET helper for querying Oura API
  endpoints with an access token or saved token file.
