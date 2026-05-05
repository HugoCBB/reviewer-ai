import json
from unittest.mock import MagicMock, patch

from app.core.review_store import _key, load_review, save_review
from app.core.state import Finding

_REPO = "org/repo"
_PR = 42

_FINDING: Finding = Finding(
    agent="security",
    severity="high",
    file="app/main.py",
    line=10,
    comment="SQL injection",
)


class TestRedisKey:
    def test_key_includes_repo_and_pr(self):
        key = _key("org/repo", 42)
        assert "org/repo" in key
        assert "42" in key

    def test_different_prs_produce_different_keys(self):
        assert _key("org/repo", 1) != _key("org/repo", 2)

    def test_different_repos_produce_different_keys(self):
        assert _key("org/repo", 1) != _key("other/repo", 1)


class TestSaveReview:
    def _make_client(self):
        mock = MagicMock()
        return mock

    @patch("app.core.review_store._client")
    def test_calls_setex_with_correct_key(self, mock_client_fn):
        mock_redis = self._make_client()
        mock_client_fn.return_value = mock_redis

        save_review(_REPO, _PR, [_FINDING], "All good.")

        mock_redis.setex.assert_called_once()
        key_arg, ttl_arg, _ = mock_redis.setex.call_args[0]
        assert key_arg == _key(_REPO, _PR)
        assert ttl_arg == 30 * 24 * 60 * 60

    @patch("app.core.review_store._client")
    def test_payload_contains_findings_and_summary(self, mock_client_fn):
        mock_redis = self._make_client()
        mock_client_fn.return_value = mock_redis

        save_review(_REPO, _PR, [_FINDING], "Summary text")

        raw = mock_redis.setex.call_args[0][2]
        data = json.loads(raw)
        assert data["summary"] == "Summary text"
        assert len(data["findings"]) == 1
        assert data["findings"][0]["agent"] == "security"
        assert "reviewed_at" in data

    @patch("app.core.review_store._client")
    def test_redis_failure_is_silenced(self, mock_client_fn):
        mock_client_fn.side_effect = ConnectionError("Redis down")
        # Must not raise
        save_review(_REPO, _PR, [_FINDING], "Summary")


class TestLoadReview:
    @patch("app.core.review_store._client")
    def test_returns_findings_and_summary(self, mock_client_fn):
        payload = json.dumps({
            "findings": [dict(_FINDING)],
            "summary": "Previous summary",
            "reviewed_at": "2026-01-01T00:00:00+00:00",
        })
        mock_redis = MagicMock()
        mock_redis.get.return_value = payload
        mock_client_fn.return_value = mock_redis

        findings, summary = load_review(_REPO, _PR)

        assert len(findings) == 1
        assert findings[0]["agent"] == "security"
        assert summary == "Previous summary"

    @patch("app.core.review_store._client")
    def test_returns_empty_when_no_previous_review(self, mock_client_fn):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_client_fn.return_value = mock_redis

        findings, summary = load_review(_REPO, _PR)

        assert findings == []
        assert summary == ""

    @patch("app.core.review_store._client")
    def test_redis_failure_returns_empty(self, mock_client_fn):
        mock_client_fn.side_effect = ConnectionError("Redis down")

        findings, summary = load_review(_REPO, _PR)

        assert findings == []
        assert summary == ""

    @patch("app.core.review_store._client")
    def test_uses_correct_key(self, mock_client_fn):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_client_fn.return_value = mock_redis

        load_review(_REPO, _PR)

        mock_redis.get.assert_called_once_with(_key(_REPO, _PR))
