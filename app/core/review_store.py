"""
Persistent storage for PR review history using Redis.

Each completed review is saved under a key scoped to (repo, pr_number) with a
30-day TTL. When the same PR receives a new push (synchronize event), the task
loads the previous review so the aggregator can compare what was fixed vs. what
is still open or newly introduced.

Failures are intentionally non-fatal: if Redis is unreachable, the review still
runs — it just has no historical context for that cycle.
"""
import json
import logging
from datetime import datetime, timezone

import redis

from app.core.config import settings
from app.core.state import Finding

logger = logging.getLogger(__name__)

_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days


def _key(repo: str, pr_number: int) -> str:
    return f"reviewer_ai:review:{repo}:{pr_number}"


def _client() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def save_review(repo: str, pr_number: int, findings: list[Finding], summary: str) -> None:
    """Persist the review result so it can be loaded on the next push to this PR."""
    payload = {
        "findings": list(findings),
        "summary": summary,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        _client().setex(_key(repo, pr_number), _TTL_SECONDS, json.dumps(payload))
    except Exception:
        logger.warning("review_store: failed to save review for %s#%s", repo, pr_number, exc_info=True)


def load_review(repo: str, pr_number: int) -> tuple[list[Finding], str]:
    """
    Return (findings, summary) from the last completed review of this PR.
    Returns ([], '') when no previous review exists or Redis is unavailable.
    """
    try:
        raw = _client().get(_key(repo, pr_number))
        if not raw:
            return [], ""
        data = json.loads(raw)
        findings = [Finding(**f) for f in data.get("findings", [])]
        return findings, data.get("summary", "")
    except Exception:
        logger.warning("review_store: failed to load review for %s#%s", repo, pr_number, exc_info=True)
        return [], ""
