#!/usr/bin/env python3
"""Fetch Sentry issue details, stacktrace, and context for debugging.

Uses only Python stdlib — no extra dependencies required.

Required environment variables:
    CURSOR_SENTRY_AUTH_TOKEN  - Sentry API auth token (org-level or user token)

Optional environment variables:
    SENTRY_BASE_URL    - Base URL for self-hosted Sentry (default: https://sentry.io)
    SENTRY_ORG         - Organization slug (required for short IDs like PROJECT-123)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def get_config() -> dict:
    token = os.environ.get("CURSOR_SENTRY_AUTH_TOKEN", "").strip()
    if not token:
        print(
            "ERROR: CURSOR_SENTRY_AUTH_TOKEN environment variable is not set.\n"
            "See the setup instructions in reference.md.",
            file=sys.stderr,
        )
        sys.exit(1)
    return {
        "token": token,
        "base_url": os.environ.get("SENTRY_BASE_URL", "https://sentry.io").rstrip("/"),
        "org": os.environ.get("SENTRY_ORG", ""),
    }


# ---------------------------------------------------------------------------
# URL / ID parsing
# ---------------------------------------------------------------------------

SHORT_ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*-[A-Za-z0-9]+$")
# Matches Sentry short IDs: PROJECT-123, MY-APP-4A2, etc.
# The suffix is alphanumeric (not necessarily purely numeric).
# Must start with a letter to avoid matching plain numbers or URLs.


def is_short_id(raw: str) -> bool:
    """Check if the string looks like a Sentry short ID (e.g. PROJECT-29S)."""
    return bool(SHORT_ID_PATTERN.match(raw))


def resolve_short_id(base_url: str, org: str, short_id: str, token: str) -> str | None:
    """Resolve a Sentry short ID to a numeric issue ID via the API.

    Uses: GET /api/0/organizations/{org}/short-ids/{short_id}/
    """
    if not org:
        print(
            "ERROR: SENTRY_ORG environment variable is required to resolve short IDs.\n"
            "Set it to your organization slug, e.g.:\n"
            '  export SENTRY_ORG="your-org-slug"\n'
            "The org slug is visible in Sentry URLs: https://sentry.io/organizations/<slug>/",
            file=sys.stderr,
        )
        sys.exit(1)

    data = api_get(base_url, f"/organizations/{org}/shortids/{short_id}/", token)
    if data is None:
        print(
            f"ERROR: Could not resolve short ID '{short_id}'.\n"
            "Check that SENTRY_ORG is correct and the short ID exists.",
            file=sys.stderr,
        )
        sys.exit(1)

    group = data.get("group", {})
    issue_id = str(group.get("id", "")) if isinstance(group, dict) else ""
    if not issue_id:
        print(
            f"ERROR: API returned unexpected response when resolving '{short_id}'.\n"
            f"Response: {json.dumps(data)[:500]}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Resolved {short_id} → issue {issue_id}", file=sys.stderr)
    return issue_id


def parse_sentry_input(raw: str, cfg: dict) -> tuple[str, str | None]:
    """Parse a Sentry issue URL, numeric ID, or short ID.

    Returns (base_url, issue_id_or_none).
    For short IDs, returns (base_url, None) — caller must resolve via API.

    Accepted formats:
        https://sentry.io/organizations/myorg/issues/12345/
        https://sentry.io/issues/12345/
        https://my-sentry.example.com/organizations/myorg/issues/12345/
        12345                  (plain numeric ID — uses SENTRY_BASE_URL)
        PROJECT-123            (short ID — resolved via API, needs SENTRY_ORG)
    """
    raw = raw.strip().rstrip("/")

    # Plain numeric ID
    if raw.isdigit():
        return cfg["base_url"], raw

    # Sentry short ID (e.g. PROJECT-123, PROJECT-123)
    if is_short_id(raw):
        return cfg["base_url"], None  # Signal that resolution is needed

    parsed = urlparse(raw)
    if not parsed.hostname:
        print(f"ERROR: Cannot parse input as URL, issue ID, or short ID: {raw}", file=sys.stderr)
        sys.exit(1)

    match = re.search(r"/issues/(\d+)", parsed.path)
    if not match:
        print(
            f"ERROR: Could not find an issue ID in the URL: {raw}\n"
            "Expected a URL like https://sentry.io/organizations/org/issues/12345/\n"
            "or a short ID like PROJECT-123",
            file=sys.stderr,
        )
        sys.exit(1)

    base_url = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        base_url += f":{parsed.port}"

    return base_url, match.group(1)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_get(base_url: str, path: str, token: str) -> dict | list | None:
    """GET a Sentry API endpoint. Returns parsed JSON or None on error."""
    url = f"{base_url}/api/0{path}"
    req = Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    })
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode(errors="replace")[:500]
        except Exception:
            pass
        print(
            f"WARNING: API request failed: {exc.code} {exc.reason} — {url}\n{body}",
            file=sys.stderr,
        )
        return None
    except URLError as exc:
        print(f"WARNING: Network error reaching {url}: {exc.reason}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def format_tags(tags: list[dict]) -> str:
    if not tags:
        return "_No tags_"
    lines = []
    for t in tags:
        lines.append(f"- **{t.get('key', '?')}**: {t.get('value', '?')}")
    return "\n".join(lines)


def format_breadcrumbs(breadcrumbs: list[dict], limit: int = 20) -> str:
    if not breadcrumbs:
        return "_No breadcrumbs_"
    # Take the most recent ones
    recent = breadcrumbs[-limit:]
    lines = []
    for bc in recent:
        ts = bc.get("timestamp", "")
        cat = bc.get("category", "")
        msg = bc.get("message", "")
        level = bc.get("level", "")
        data = bc.get("data", {})
        line = f"- `{ts}` [{level}] **{cat}**"
        if msg:
            line += f": {msg}"
        if data:
            # Show data compactly
            data_str = ", ".join(f"{k}={v}" for k, v in data.items() if k != "url")
            url = data.get("url", "")
            if url:
                line += f" `{url}`"
            if data_str:
                line += f" ({data_str})"
        lines.append(line)
    return "\n".join(lines)


def format_request(request: dict | None) -> str:
    if not request:
        return "_No HTTP request context_"
    lines = []
    method = request.get("method", "?")
    url = request.get("url", "?")
    lines.append(f"**{method}** `{url}`")

    headers = request.get("headers", [])
    if headers:
        lines.append("\nHeaders:")
        for h in headers:
            if isinstance(h, (list, tuple)) and len(h) == 2:
                lines.append(f"- `{h[0]}`: `{h[1]}`")

    query = request.get("query_string", "")
    if query:
        lines.append(f"\nQuery string: `{query}`")

    data = request.get("data")
    if data:
        if isinstance(data, str):
            lines.append(f"\nBody:\n```\n{data[:2000]}\n```")
        else:
            lines.append(f"\nBody:\n```json\n{json.dumps(data, indent=2)[:2000]}\n```")

    return "\n".join(lines)


def format_frame(frame: dict, index: int) -> str:
    """Format a single stacktrace frame."""
    filename = frame.get("filename") or frame.get("absPath") or "?"
    function = frame.get("function") or "?"
    lineno = frame.get("lineNo") or frame.get("lineno") or "?"
    colno = frame.get("colNo") or frame.get("colno") or ""
    module = frame.get("module") or ""
    in_app = frame.get("inApp", False)

    location = f"{filename}:{lineno}"
    if colno:
        location += f":{colno}"

    marker = " **[APP]**" if in_app else ""
    header = f"**Frame {index}**{marker}: `{function}` in `{location}`"
    if module:
        header += f" (module: `{module}`)"

    lines = [header]

    # Context lines (pre, current, post)
    pre_context = frame.get("preContext") or frame.get("pre_context") or []
    context_line = frame.get("contextLine") or frame.get("context_line") or ""
    post_context = frame.get("postContext") or frame.get("post_context") or []

    if pre_context or context_line or post_context:
        lines.append("```")
        start_line = (lineno or 0) - len(pre_context) if isinstance(lineno, int) else 0
        for i, cl in enumerate(pre_context):
            lines.append(f"  {start_line + i:>5} | {cl}")
        if context_line:
            lines.append(f"► {lineno:>5} | {context_line}")
        for i, cl in enumerate(post_context):
            post_line = (lineno or 0) + 1 + i if isinstance(lineno, int) else 0
            lines.append(f"  {post_line:>5} | {cl}")
        lines.append("```")

    # Local variables
    local_vars = frame.get("vars") or {}
    if local_vars:
        lines.append("Local variables:")
        for k, v in list(local_vars.items())[:15]:
            v_str = str(v)[:200]
            lines.append(f"- `{k}` = `{v_str}`")

    return "\n".join(lines)


def format_exception(entry: dict) -> str:
    """Format an exception entry from the event."""
    values = entry.get("values") or entry.get("value") or []
    if isinstance(values, dict):
        values = [values]

    sections = []
    for exc in values:
        exc_type = exc.get("type", "UnknownException")
        exc_value = exc.get("value", "")
        mechanism = exc.get("mechanism", {})

        header = f"### `{exc_type}`: {exc_value}"
        if mechanism:
            mtype = mechanism.get("type", "")
            handled = mechanism.get("handled")
            parts = []
            if mtype:
                parts.append(f"type={mtype}")
            if handled is not None:
                parts.append(f"handled={handled}")
            if parts:
                header += f"\n_Mechanism: {', '.join(parts)}_"

        sections.append(header)

        stacktrace = exc.get("stacktrace", {})
        frames = stacktrace.get("frames") or []
        if frames:
            sections.append("\n**Stacktrace** (oldest → newest):\n")
            # Separate app frames from library frames for clarity
            for i, frame in enumerate(frames):
                sections.append(format_frame(frame, i))
                sections.append("")  # blank line between frames

    return "\n".join(sections)


def format_event(event: dict, label: str = "Latest Event") -> str:
    """Format a full event into markdown."""
    sections = []
    event_id = event.get("eventID") or event.get("id", "?")
    timestamp = event.get("dateCreated") or event.get("timestamp", "?")
    release = event.get("release", {})
    release_version = release.get("version", "?") if isinstance(release, dict) else str(release) if release else "?"
    environment = event.get("environment", "?") or "?"

    sections.append(f"## {label}")
    sections.append(f"- **Event ID**: `{event_id}`")
    sections.append(f"- **Timestamp**: {timestamp}")
    sections.append(f"- **Release**: `{release_version}`")
    sections.append(f"- **Environment**: `{environment}`")

    # Exception / stacktrace
    entries = event.get("entries", [])
    for entry in entries:
        entry_type = entry.get("type", "")
        data = entry.get("data", {})

        if entry_type == "exception":
            sections.append("\n## Exception & Stacktrace\n")
            sections.append(format_exception(data))

        elif entry_type == "request":
            sections.append("\n## HTTP Request Context\n")
            sections.append(format_request(data))

        elif entry_type == "breadcrumbs":
            crumbs = data.get("values") or data.get("breadcrumbs") or []
            sections.append("\n## Breadcrumbs (recent)\n")
            sections.append(format_breadcrumbs(crumbs))

        elif entry_type == "message":
            msg = data.get("formatted") or data.get("message", "")
            if msg:
                sections.append(f"\n## Message\n\n{msg}")

    # Tags
    tags = event.get("tags", [])
    if tags:
        sections.append("\n## Tags\n")
        sections.append(format_tags(tags))

    # Context (extra, contexts)
    contexts = event.get("contexts", {})
    if contexts:
        sections.append("\n## Contexts\n")
        for ctx_name, ctx_data in contexts.items():
            if isinstance(ctx_data, dict):
                sections.append(f"### {ctx_name}")
                for k, v in ctx_data.items():
                    if k == "type":
                        continue
                    sections.append(f"- **{k}**: `{str(v)[:200]}`")

    extra = event.get("context", {})
    if extra:
        sections.append("\n## Extra Context\n")
        for k, v in extra.items():
            sections.append(f"- **{k}**: `{str(v)[:300]}`")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch a Sentry issue and format it for debugging.",
        epilog="Set CURSOR_SENTRY_AUTH_TOKEN env var before running.",
    )
    parser.add_argument(
        "issue",
        help="Sentry issue URL, numeric ID, or short ID (e.g. PROJECT-123)",
    )
    parser.add_argument(
        "--events",
        type=int,
        default=1,
        help="Number of recent events to fetch (default: 1, max: 5)",
    )
    args = parser.parse_args()
    cfg = get_config()

    base_url, issue_id = parse_sentry_input(args.issue, cfg)
    num_events = min(max(args.events, 1), 5)

    # Resolve short ID if needed
    if issue_id is None:
        issue_id = resolve_short_id(base_url, cfg["org"], args.issue.strip(), cfg["token"])

    # ---- Fetch issue metadata ----
    issue = api_get(base_url, f"/issues/{issue_id}/", cfg["token"])
    if issue is None:
        print("ERROR: Failed to fetch issue. Check the URL/ID and auth token.", file=sys.stderr)
        sys.exit(1)

    # ---- Fetch latest event ----
    latest_event = api_get(base_url, f"/issues/{issue_id}/events/latest/", cfg["token"])

    # ---- Fetch additional recent events if requested ----
    extra_events: list[dict] = []
    if num_events > 1:
        events_list = api_get(base_url, f"/issues/{issue_id}/events/?full=true", cfg["token"])
        if isinstance(events_list, list):
            # Skip the latest (already fetched) and take up to num_events-1 more
            for ev in events_list[:num_events]:
                ev_id = ev.get("eventID") or ev.get("id")
                latest_id = (latest_event or {}).get("eventID") or (latest_event or {}).get("id")
                if ev_id != latest_id:
                    extra_events.append(ev)
                if len(extra_events) >= num_events - 1:
                    break

    # ---- Fetch linked external issues (Jira, etc.) ----
    jira_tickets = _fetch_jira_tickets(base_url, issue_id, issue, cfg["token"])

    # ---- Format output ----
    output_parts = []

    # Issue header
    title = issue.get("title", "Unknown Issue")
    culprit = issue.get("culprit", "?")
    first_seen = issue.get("firstSeen", "?")
    last_seen = issue.get("lastSeen", "?")
    count = issue.get("count", "?")
    level = issue.get("level", "?")
    status = issue.get("status", "?")
    issue_type = issue.get("type", "?")
    project_info = issue.get("project", {})
    project_name = project_info.get("slug", "?") if isinstance(project_info, dict) else "?"
    short_id = issue.get("shortId", "?")
    permalink = issue.get("permalink", "")
    metadata = issue.get("metadata", {})

    output_parts.append(f"# Sentry Issue: {title}")
    output_parts.append("")
    output_parts.append(f"- **Short ID**: {short_id}")
    output_parts.append(f"- **Project**: {project_name}")
    output_parts.append(f"- **Level**: {level}")
    output_parts.append(f"- **Status**: {status}")
    output_parts.append(f"- **Type**: {issue_type}")
    output_parts.append(f"- **Culprit**: `{culprit}`")
    output_parts.append(f"- **First seen**: {first_seen}")
    output_parts.append(f"- **Last seen**: {last_seen}")
    output_parts.append(f"- **Event count**: {count}")
    if permalink:
        output_parts.append(f"- **Link**: {permalink}")

    # Metadata extras
    exc_type = metadata.get("type", "")
    exc_value = metadata.get("value", "")
    if exc_type or exc_value:
        output_parts.append(f"\n**Exception**: `{exc_type}: {exc_value}`")

    # Assigned to
    assigned_to = issue.get("assignedTo")
    if assigned_to:
        name = assigned_to.get("name", "?") if isinstance(assigned_to, dict) else str(assigned_to)
        output_parts.append(f"- **Assigned to**: {name}")

    # Linked Jira tickets
    if jira_tickets:
        output_parts.append("")
        output_parts.append("## Linked Jira Tickets\n")
        for ticket in jira_tickets:
            key = ticket["key"]
            url = ticket.get("url", "")
            label = ticket.get("label", "")
            line = f"- **{key}**"
            if label:
                line += f": {label}"
            if url:
                line += f" ([link]({url}))"
            output_parts.append(line)

    output_parts.append("")

    # Latest event
    if latest_event:
        output_parts.append(format_event(latest_event, "Latest Event"))
    else:
        output_parts.append("## Latest Event\n\n_Could not fetch latest event._")

    # Additional events
    for i, ev in enumerate(extra_events):
        output_parts.append(f"\n---\n")
        output_parts.append(format_event(ev, f"Additional Event {i + 2}"))

    # Footer with analysis hints
    output_parts.append("\n---\n")
    output_parts.append("## Key Files to Investigate\n")
    # Extract in-app frames from latest event for a quick reference
    if latest_event:
        app_frames = _extract_app_frames(latest_event)
        if app_frames:
            output_parts.append("Based on the stacktrace, these **in-app frames** are most relevant:\n")
            for f in app_frames:
                filename = f.get("filename") or f.get("absPath") or "?"
                function = f.get("function") or "?"
                lineno = f.get("lineNo") or f.get("lineno") or "?"
                output_parts.append(f"- `{filename}:{lineno}` in `{function}`")
        else:
            output_parts.append("_No in-app frames identified. Check all frames in the stacktrace._")

    print("\n".join(output_parts))


def _fetch_jira_tickets(
    base_url: str, issue_id: str, issue: dict, token: str
) -> list[dict]:
    """Fetch linked Jira tickets for a Sentry issue.

    Tries two sources:
    1. The external-issues API endpoint (structured data from Sentry App integrations)
    2. The issue's annotations field — supports both dict format from the native
       Jira integration ({"url": "...", "displayName": "PROJ-123"}) and legacy
       HTML strings from the old Jira plugin

    Returns a list of dicts with keys: key, url, label.
    """
    tickets: dict[str, dict] = {}  # keyed by ticket key to deduplicate

    # Source 1: External issues API
    external_issues = api_get(base_url, f"/issues/{issue_id}/external-issues/", token)
    if isinstance(external_issues, list):
        for ext in external_issues:
            display_name = ext.get("displayName", "")
            web_url = ext.get("webUrl", "")
            description = ext.get("description", "")
            # Jira tickets have a key like FOO-123
            if display_name and re.match(r"^[A-Z][A-Z0-9]+-\d+$", display_name):
                tickets[display_name] = {
                    "key": display_name,
                    "url": web_url,
                    "label": description,
                }

    # Source 2: Annotations on the issue (Jira integration links)
    # Annotations can be either:
    #   - dict with {"url": "...", "displayName": "PROJ-123"} (native Jira integration)
    #   - HTML string like '<a href="...">PROJ-123</a>' (legacy Jira plugin)
    annotations = issue.get("annotations", [])
    if isinstance(annotations, list):
        for ann in annotations:
            if isinstance(ann, dict):
                display_name = ann.get("displayName", "")
                url = ann.get("url", "")
                if display_name and re.match(r"^[A-Z][A-Z0-9]+-\d+$", display_name):
                    if display_name not in tickets:
                        tickets[display_name] = {"key": display_name, "url": url, "label": ""}
            elif isinstance(ann, str):
                match = re.search(
                    r'<a\s[^>]*href="([^"]*)"[^>]*>([A-Z][A-Z0-9]+-\d+)</a>', ann
                )
                if match:
                    url, key = match.group(1), match.group(2)
                    if key not in tickets:
                        tickets[key] = {"key": key, "url": url, "label": ""}

    return list(tickets.values())


def _extract_app_frames(event: dict) -> list[dict]:
    """Extract in-app frames from an event, newest first."""
    app_frames = []
    for entry in event.get("entries", []):
        if entry.get("type") != "exception":
            continue
        data = entry.get("data", {})
        for exc in data.get("values", []):
            frames = exc.get("stacktrace", {}).get("frames") or []
            for frame in reversed(frames):
                if frame.get("inApp", False):
                    app_frames.append(frame)
    return app_frames


if __name__ == "__main__":
    main()
