#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://api.ouraring.com"


def default_token_path() -> Path:
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    base_dir = Path(xdg_config_home).expanduser() if xdg_config_home else Path.home() / ".config"
    return base_dir / "oura-api-local" / "tokens.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query a read-only Oura API GET endpoint using an access token or saved token file."
    )
    parser.add_argument(
        "endpoint",
        help="Path like /v2/usercollection/daily_sleep or a full https:// URL.",
    )
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        help="Query parameter in key=value form. Repeat as needed.",
    )
    parser.add_argument(
        "--access-token",
        help="Access token to use directly. Overrides OURA_ACCESS_TOKEN and the token file.",
    )
    parser.add_argument(
        "--token-path",
        help="Path to the token JSON file. Defaults to OURA_TOKEN_PATH or the config path.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Base URL for path-style endpoints. Default: https://api.ouraring.com",
    )
    parser.add_argument(
        "--print-url-only",
        action="store_true",
        help="Print the resolved request URL and exit without making the API call.",
    )
    return parser.parse_args()


def parse_params(values: list[str]) -> Dict[str, str]:
    params: Dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"Invalid --param value: {value!r}. Expected key=value.")
        key, raw = value.split("=", 1)
        if not key:
            raise SystemExit(f"Invalid --param value: {value!r}. Key cannot be empty.")
        params[key] = raw
    return params


def load_access_token(cli_token: Optional[str], token_path_value: Optional[str]) -> str:
    if cli_token:
        return cli_token

    env_token = os.environ.get("OURA_ACCESS_TOKEN")
    if env_token:
        return env_token

    token_path = Path(token_path_value or os.environ.get("OURA_TOKEN_PATH", str(default_token_path()))).expanduser()
    if not token_path.exists():
        raise SystemExit(
            f"Token file not found at {token_path}. Set OURA_ACCESS_TOKEN, pass --access-token, or authorize first."
        )

    try:
        tokens = json.loads(token_path.read_text())
    except json.JSONDecodeError as error:
        raise SystemExit(f"Token file at {token_path} is not valid JSON: {error}") from error

    access_token = tokens.get("access_token")
    if not access_token:
        raise SystemExit(f"No access_token found in {token_path}.")
    return access_token


def build_url(endpoint: str, base_url: str, params: Dict[str, str]) -> str:
    if endpoint.startswith("https://") or endpoint.startswith("http://"):
        url = endpoint
    else:
        url = base_url.rstrip("/") + "/" + endpoint.lstrip("/")

    if not params:
        return url

    separator = "&" if "?" in url else "?"
    return url + separator + urlencode(params)


def request_json(url: str, access_token: str) -> dict:
    request = Request(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )

    try:
        with urlopen(request) as response:
            return json.loads(response.read().decode())
    except HTTPError as error:
        details = error.read().decode(errors="replace")
        raise SystemExit(f"HTTP {error.code} from Oura API: {details}") from error
    except URLError as error:
        raise SystemExit(f"Failed to reach Oura API: {error.reason}") from error


def main() -> None:
    args = parse_args()
    params = parse_params(args.param)
    url = build_url(args.endpoint, args.base_url, params)

    if args.print_url_only:
        print(url)
        return

    access_token = load_access_token(args.access_token, args.token_path)
    payload = request_json(url, access_token)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
