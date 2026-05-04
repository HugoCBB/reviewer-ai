import httpx

from app.core.config import settings
from app.core.state import Finding

GITHUB_API = "https://api.github.com"

HEADERS = {
    "Authorization": f"Bearer {settings.github_token}",
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def get_pr_diff(repo: str, pr_number: int) -> str:
    """Fetch the raw unified diff for a PR."""
    response = httpx.get(
        f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}",
        headers={**HEADERS, "Accept": "application/vnd.github.v3.diff"},
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def post_review(repo: str, pr_number: int, findings: list[Finding], summary: str) -> None:
    """Post a review with inline comments and a summary body."""
    comments = [
        {
            "path": f["file"],
            "position": f["line"] or 1,
            "body": f"**[{f['agent'].upper()} — {f['severity'].upper()}]** {f['comment']}",
        }
        for f in findings
        if f.get("file") and f.get("line")
    ]

    criticals = [f for f in findings if f["severity"] == "critical"]
    event = "REQUEST_CHANGES" if criticals else "COMMENT"

    payload = {
        "body": summary,
        "event": event,
        "comments": comments,
    }

    response = httpx.post(
        f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}/reviews",
        headers=HEADERS,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()