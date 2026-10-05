from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "state" / "game.json"

COMMANDS = {
    "forward": "/forward",
    "back": "/back",
    "left": "/left",
    "right": "/right",
    "fire": "/fire",
    "use": "/use",
}
TITLE_PREFIX = "runtime/input: "


def base_payload(state: dict[str, Any]) -> dict[str, Any]:
    last_comment_id = int(state.get("last_comment_id", 0))
    return {
        "controller_issue": int(state.get("controller_issue", 1)),
        "previous_comment_id": last_comment_id,
        "max_seen_comment_id": last_comment_id,
        "processed_issue_numbers": [],
        "commands": [],
    }


def command_from_issue(issue: dict[str, Any]) -> dict[str, Any] | None:
    if "pull_request" in issue:
        return None
    try:
        issue_number = int(issue.get("number", 0))
        issue_id = int(issue.get("id", 0))
    except (TypeError, ValueError):
        return None
    if issue_number <= 0 or issue_id <= 0:
        return None

    title = str(issue.get("title") or "").strip().lower()
    body = str(issue.get("body") or "").strip().lower()
    if not title.startswith(TITLE_PREFIX):
        return None
    slug = title[len(TITLE_PREFIX):].strip()
    expected = COMMANDS.get(slug)
    if expected is None or body != expected:
        return None

    user = issue.get("user")
    actor = str(user.get("login") or "unknown") if isinstance(user, dict) else "unknown"
    return {
        "id": issue_id,
        "command": expected,
        "actor": actor,
        "source": "issue",
        "issue_number": issue_number,
    }


def collect_open_issue_commands(
    issues: list[dict[str, Any]],
    state: dict[str, Any],
) -> dict[str, Any]:
    payload = base_payload(state)
    last_processed = int(state.get("last_input_issue_number", 0))

    commands: list[dict[str, Any]] = []
    for issue in sorted(issues, key=lambda item: int(item.get("number", 0) or 0)):
        command = command_from_issue(issue)
        if command is None or int(command["issue_number"]) <= last_processed:
            continue
        commands.append(command)

    payload["commands"] = commands
    payload["processed_issue_numbers"] = [
        int(command["issue_number"]) for command in commands
    ]
    return payload


def parse_issue_event(event: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    payload = base_payload(state)
    if event.get("action") != "opened":
        return payload
    issue = event.get("issue")
    if not isinstance(issue, dict):
        return payload

    command = command_from_issue(issue)
    if command is None:
        return payload
    if int(command["issue_number"]) <= int(state.get("last_input_issue_number", 0)):
        return payload

    payload["commands"] = [command]
    payload["processed_issue_numbers"] = [int(command["issue_number"])]
    return payload


def fetch_open_issues(repo: str, token: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    page = 1
    while True:
        url = (
            f"https://api.github.com/repos/{repo}/issues"
            f"?state=open&per_page=100&page={page}&sort=created&direction=asc"
        )
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "profile-doom-controller",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise ValueError("GitHub issues response must be a list")
        issues.extend(item for item in batch if isinstance(item, dict))
        if len(batch) < 100:
            return issues
        page += 1


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: collect_issue_command.py <event.json> <output.json>")

    event_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    event = json.loads(event_path.read_text(encoding="utf-8"))
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if not isinstance(event, dict) or not isinstance(state, dict):
        raise ValueError("event and state must be JSON objects")

    # Only an opened input issue should trigger queue draining. Once triggered,
    # read every still-open valid input issue so coalesced Actions events cannot
    # silently drop turns.
    if event.get("action") != "opened":
        payload = base_payload(state)
    else:
        repo = os.environ["GITHUB_REPOSITORY"]
        token = os.environ["GH_TOKEN"]
        payload = collect_open_issue_commands(fetch_open_issues(repo, token), state)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(len(payload["commands"]))


if __name__ == "__main__":
    main()
