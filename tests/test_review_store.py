import json
from unittest.mock import MagicMock, patch

from app.core.review_store import _key, _validate_finding, load_review, save_review
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


class TestValidateFinding:
    def test_valid_finding_passes_through(self):
        raw = {"agent": "security", "severity": "high", "file": "app/main.py", "line": 10, "comment": "Issue"}
        result = _validate_finding(raw)
        assert result == Finding(agent="security", severity="high", file="app/main.py", line=10, comment="Issue")

    def test_missing_agent_defaults_to_unknown(self):
        raw = {"severity": "low", "file": "f.py", "line": 1, "comment": "x"}
        assert _validate_finding(raw)["agent"] == "unknown"

    def test_missing_severity_defaults_to_low(self):
        raw = {"agent": "security", "file": "f.py", "line": 1, "comment": "x"}
        assert _validate_finding(raw)["severity"] == "low"

    def test_missing_file_defaults_to_unknown(self):
        raw = {"agent": "security", "severity": "high", "line": 1, "comment": "x"}
        assert _validate_finding(raw)["file"] == "unknown"

    def test_missing_line_defaults_to_1(self):
        raw = {"agent": "security", "severity": "high", "file": "f.py", "comment": "x"}
        assert _validate_finding(raw)["line"] == 1

    def test_none_line_defaults_to_1(self):
        raw = {"agent": "security", "severity": "high", "file": "f.py", "line": None, "comment": "x"}
        assert _validate_finding(raw)["line"] == 1

    def test_string_line_is_cast_to_int(self):
        raw = {"agent": "security", "severity": "high", "file": "f.py", "line": "42", "comment": "x"}
        result = _validate_finding(raw)
        assert result["line"] == 42
        assert isinstance(result["line"], int)

    def test_missing_comment_defaults_to_empty_string(self):
        raw = {"agent": "security", "severity": "high", "file": "f.py", "line": 1}
        assert _validate_finding(raw)["comment"] == ""

    def test_extra_keys_are_ignored(self):
        raw = {"agent": "security", "severity": "high", "file": "f.py", "line": 1, "comment": "x", "unknown_field": "val"}
        result = _validate_finding(raw)
        assert "unknown_field" not in result


class TestLoadReviewValidation:
    @patch("app.core.review_store._client")
    def test_malformed_finding_gets_safe_defaults(self, mock_client_fn):
        payload = json.dumps({
            "findings": [{"agent": None, "severity": None, "file": None, "line": None, "comment": None}],
            "summary": "Malformed",
        })
        mock_redis = MagicMock()
        mock_redis.get.return_value = payload
        mock_client_fn.return_value = mock_redis

        findings, summary = load_review("org/repo", 1)

        assert len(findings) == 1
        assert findings[0]["agent"] == "None"
        assert findings[0]["line"] == 1

    @patch("app.core.review_store._client")
    def test_invalid_json_returns_empty(self, mock_client_fn):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "not valid json {"
        mock_client_fn.return_value = mock_redis

        findings, summary = load_review("org/repo", 1)

        assert findings == []
        assert summary == ""


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
