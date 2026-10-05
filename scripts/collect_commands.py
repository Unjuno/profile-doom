from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

VALID = {"/forward", "/back", "/left", "/right", "/fire", "/use"}

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "state" / "game.json"


def fetch_comments(repo: str, issue: int, token: str) -> list[dict]:
    comments: list[dict] = []
    page = 1
    while True:
        url = (
            f"https://api.github.com/repos/{repo}/issues/{issue}/comments"
            f"?per_page=100&page={page}"
        )
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "profile-doom-controller",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            batch = json.load(response)
        comments.extend(batch)
        if len(batch) < 100:
            return comments
        page += 1


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: collect_commands.py <output.json>")

    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GH_TOKEN"]
    issue = int(os.environ.get("CONTROLLER_ISSUE", "1"))
    output = Path(sys.argv[1])

    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    last_seen = int(state.get("last_comment_id", 0))

    all_comments = fetch_comments(repo, issue, token)
    unseen = [c for c in all_comments if int(c["id"]) > last_seen]
    unseen.sort(key=lambda c: int(c["id"]))

    commands = []
    max_seen = last_seen
    for comment in unseen:
        cid = int(comment["id"])
        max_seen = max(max_seen, cid)
        body = str(comment.get("body") or "").strip().lower()
        if body not in VALID:
            continue
        commands.append(
            {
                "id": cid,
                "command": body,
                "actor": comment["user"]["login"],
                "created_at": comment.get("created_at"),
            }
        )

    payload = {
        "controller_issue": issue,
        "previous_comment_id": last_seen,
        "max_seen_comment_id": max_seen,
        "commands": commands,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(len(commands))


if __name__ == "__main__":
    main()
