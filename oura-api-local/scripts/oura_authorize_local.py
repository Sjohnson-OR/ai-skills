#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import threading
import webbrowser
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://api.ouraring.com"
DEFAULT_REDIRECT_URI = "http://localhost:8787/callback"
DEFAULT_VERIFY_ENDPOINT = "/v2/usercollection/daily_sleep"


def default_token_path() -> Path:
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    base_dir = Path(xdg_config_home).expanduser() if xdg_config_home else Path.home() / ".config"
    return base_dir / "oura-api-local" / "tokens.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Complete a local Oura OAuth flow and optionally verify the saved token with a GET request."
    )
    parser.add_argument(
        "--auth-url-only",
        action="store_true",
        help="Print the authorize URL and exit without starting the callback server.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the authorize URL automatically.",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip the follow-up verification request after saving tokens.",
    )
    parser.add_argument(
        "--verify-endpoint",
        default=DEFAULT_VERIFY_ENDPOINT,
        help="Verification endpoint path or full URL. Default: /v2/usercollection/daily_sleep",
    )
    parser.add_argument(
        "--verify-param",
        action="append",
        default=[],
        help="Verification query parameter in key=value form. Repeat as needed.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="When verifying daily_sleep without explicit verify params, request this many days. Default: 7.",
    )
    parser.add_argument(
        "--state",
        help="Provide an explicit OAuth state value instead of generating one.",
    )
    return parser.parse_args()


def get_env(name: str, default: Optional[str] = None) -> str:
    value = os.environ.get(name, default)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def parse_params(values: list[str]) -> Dict[str, str]:
    params: Dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"Invalid parameter value: {value!r}. Expected key=value.")
        key, raw = value.split("=", 1)
        if not key:
            raise SystemExit(f"Invalid parameter value: {value!r}. Key cannot be empty.")
        params[key] = raw
    return params


def build_url(base_url: str, endpoint: str, params: Dict[str, str]) -> str:
    if endpoint.startswith("https://") or endpoint.startswith("http://"):
        url = endpoint
    else:
        url = base_url.rstrip("/") + "/" + endpoint.lstrip("/")

    if not params:
        return url

    separator = "&" if "?" in url else "?"
    return url + separator + urlencode(params)


def default_verify_params(endpoint: str, explicit_params: Dict[str, str], days: int) -> Dict[str, str]:
    if explicit_params:
        return explicit_params

    parsed_path = urlparse(endpoint).path if endpoint.startswith(("http://", "https://")) else endpoint
    if parsed_path.rstrip("/") != DEFAULT_VERIFY_ENDPOINT:
        return {}

    end_date = date.today()
    start_date = end_date - timedelta(days=max(days, 1))
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }


def build_auth_url(client_id: str, redirect_uri: str, state: str) -> str:
    return "https://cloud.ouraring.com/oauth/authorize?" + urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
        }
    )


def make_handler(
    callback_path: str,
    result: Dict[str, str],
    done: threading.Event,
) -> type[BaseHTTPRequestHandler]:
    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != callback_path:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not found")
                return

            params = parse_qs(parsed.query)
            if "error" in params:
                result["error"] = params["error"][0]
                result["error_description"] = params.get("error_description", [""])[0]
            else:
                result["code"] = params.get("code", [""])[0]
                result["scope"] = params.get("scope", [""])[0]
                result["state"] = params.get("state", [""])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Authorization received. You can close this tab.")
            done.set()

        def log_message(self, format: str, *args: object) -> None:
            return

    return CallbackHandler


def request_json(
    url: str,
    *,
    method: str = "GET",
    data: Optional[Dict[str, str]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    encoded_data = urlencode(data).encode() if data is not None else None
    request = Request(url, data=encoded_data, headers=headers or {}, method=method)

    try:
        with urlopen(request) as response:
            return json.loads(response.read().decode())
    except HTTPError as error:
        details = error.read().decode(errors="replace")
        raise SystemExit(f"HTTP {error.code} from Oura API: {details}") from error
    except URLError as error:
        raise SystemExit(f"Failed to reach Oura API: {error.reason}") from error


def exchange_code_for_tokens(client_id: str, client_secret: str, code: str, redirect_uri: str) -> Dict[str, Any]:
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    return request_json(
        "https://api.ouraring.com/oauth/token",
        method="POST",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )


def summarize_verification_payload(payload: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    rows = payload.get("data")
    if isinstance(rows, list):
        if not rows:
            return "Verification payload", payload
        if all(isinstance(row, dict) for row in rows):
            def sort_key(row: Dict[str, Any]) -> str:
                for key in ("day", "timestamp", "start_datetime", "end_datetime"):
                    value = row.get(key)
                    if isinstance(value, str):
                        return value
                return ""

            return "Latest verification row", sorted(rows, key=sort_key)[-1]
    return "Verification payload", payload


def save_tokens(token_path: Path, tokens: Dict[str, Any]) -> None:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps(tokens, indent=2) + "\n")
    os.chmod(token_path, 0o600)


def main() -> None:
    args = parse_args()

    client_id = get_env("OURA_CLIENT_ID")
    client_secret = get_env("OURA_CLIENT_SECRET")
    redirect_uri = get_env("OURA_REDIRECT_URI", DEFAULT_REDIRECT_URI)
    token_path = Path(get_env("OURA_TOKEN_PATH", str(default_token_path()))).expanduser()
    state = args.state or secrets.token_urlsafe(24)

    auth_url = build_auth_url(client_id, redirect_uri, state)

    if args.auth_url_only:
        print(auth_url)
        return

    parsed_redirect = urlparse(redirect_uri)
    host = parsed_redirect.hostname or "localhost"
    port = parsed_redirect.port or 8787
    callback_path = parsed_redirect.path or "/callback"

    result: Dict[str, str] = {}
    done = threading.Event()
    handler = make_handler(callback_path, result, done)

    try:
        server = HTTPServer((host, port), handler)
    except OSError as error:
        raise SystemExit(f"Failed to bind callback server at {redirect_uri}: {error}") from error

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        print(f"Listening for callback on {redirect_uri}")
        print("Authorize URL:")
        print(auth_url)
        if not args.no_browser:
            webbrowser.open(auth_url)

        done.wait()
    except KeyboardInterrupt:
        raise SystemExit("Interrupted before OAuth completed.")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    if "error" in result:
        error_description = result.get("error_description", "")
        raise SystemExit(f"OAuth failed: {result['error']} {error_description}".strip())

    if result.get("state") != state:
        raise SystemExit("State mismatch. Refusing to exchange the authorization code.")

    code = result.get("code")
    if not code:
        raise SystemExit("No authorization code returned.")

    tokens = exchange_code_for_tokens(client_id, client_secret, code, redirect_uri)
    save_tokens(token_path, tokens)

    print("\nGranted scopes:")
    print(result.get("scope", "(not returned)"))
    print(f"\nTokens saved to {token_path}")

    if args.skip_verify:
        return

    explicit_verify_params = parse_params(args.verify_param)
    verify_params = default_verify_params(args.verify_endpoint, explicit_verify_params, args.days)
    verify_url = build_url(DEFAULT_BASE_URL, args.verify_endpoint, verify_params)
    payload = request_json(
        verify_url,
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    title, content = summarize_verification_payload(payload)

    print("\nVerification URL:")
    print(verify_url)
    print(f"\n{title}:")
    print(json.dumps(content, indent=2))

    rows = payload.get("data")
    if isinstance(rows, list) and not rows:
        print("\nVerification returned no rows. Sync the ring in the Oura app or query a different endpoint and try again.")


if __name__ == "__main__":
    main()
