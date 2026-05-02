from celery.exceptions import SoftTimeLimitExceeded

from api.github_client import get_pr_diff, post_review
from app.core.celery_config import celery_app
from app.core.graph import pr_reviewer_graph


@celery_app.task(
    bind=True,
    max_retries=3,
    time_limit=360,       # hard kill after 6 min
    soft_time_limit=300,  # soft warning after 5 min
    queue="reviews",
)
def review_pr(self, pr_data: dict):
    """
    Main Celery task — fetches the diff, runs the LangGraph,
    and posts the review back to GitHub.

    pr_data expected keys:
        number      int
        repo        str  (e.g. "org/repo")
        title       str
        body        str  (PR description, may be None)
    """
    try:
        repo = pr_data["repo"]
        pr_number = pr_data["number"]

        # 1. fetch diff from GitHub
        diff = get_pr_diff(repo, pr_number)

        # 2. run the multi-agent graph
        result = pr_reviewer_graph.invoke({
            "pr_number":   pr_number,
            "repo":        repo,
            "diff":        diff,
            "title":       pr_data["title"],
            "description": pr_data.get("body") or "",
            "findings":    [],
            "agents_done": [],
            "next":        "",
            "summary":     "",
        })

        # 3. post review to GitHub
        post_review(
            repo=repo,
            pr_number=pr_number,
            findings=result["findings"],
            summary=result.get("summary", ""),
        )

    except SoftTimeLimitExceeded:
        # post a partial warning so the PR is not left without feedback
        post_review(
            repo=pr_data["repo"],
            pr_number=pr_data["number"],
            findings=[],
            summary="⚠️ Automated review timed out. Please trigger a manual review.",
        )

    except Exception as exc:
        # exponential backoff: 60s, 120s, 180s
        countdown = 60 * (self.request.retries + 1)
        raise self.retry(exc=exc, countdown=countdown)