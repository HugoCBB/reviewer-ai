from unittest.mock import patch

from app.core.state import Finding
from app.modules.agents.aggregator_agent import _format_findings, aggregator_node

_BASE_STATE = {
    "pr_number": 1,
    "repo": "org/repo",
    "diff": "some diff",
    "title": "Test PR",
    "description": "",
    "agents_done": [],
    "next": "",
    "summary": "",
    "previous_findings": [],
    "previous_summary": "",
}


class TestFormatFindings:
    def test_empty_returns_none_label(self):
        assert _format_findings([]) == "None."

    def test_single_finding_format(self):
        finding = Finding(agent="security", severity="high", file="app/auth.py", line=42, comment="Hardcoded secret")
        result = _format_findings([finding])
        assert "[SECURITY][HIGH]" in result
        assert "app/auth.py:42" in result
        assert "Hardcoded secret" in result

    def test_agent_and_severity_uppercased(self):
        finding = Finding(agent="docs", severity="medium", file="f.py", line=1, comment="x")
        assert "[DOCS][MEDIUM]" in _format_findings([finding])

    def test_multiple_findings_newline_separated(self):
        findings = [
            Finding(agent="security", severity="high", file="a.py", line=1, comment="A"),
            Finding(agent="quality", severity="low", file="b.py", line=2, comment="B"),
        ]
        lines = _format_findings(findings).strip().splitlines()
        assert len(lines) == 2


class TestAggregatorNodeNoPreviousReview:
    def test_returns_summary_and_finish(self):
        state = {**_BASE_STATE, "findings": [
            Finding(agent="security", severity="high", file="app/main.py", line=10, comment="SQL injection"),
        ]}
        with patch("app.modules.agents.aggregator_agent.aggregator_chain") as mock_chain:
            mock_chain.invoke.return_value = "Security issues found."
            result = aggregator_node(state)

        assert result["next"] == "FINISH"
        assert result["summary"] == "Security issues found."

    def test_no_previous_review_sends_no_previous_review_message(self):
        state = {**_BASE_STATE, "findings": []}
        with patch("app.modules.agents.aggregator_agent.aggregator_chain") as mock_chain:
            mock_chain.invoke.return_value = "LGTM"
            aggregator_node(state)

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert "No previous review" in call_kwargs["previous_context"]

    def test_empty_findings_renders_none_label(self):
        state = {**_BASE_STATE, "findings": []}
        with patch("app.modules.agents.aggregator_agent.aggregator_chain") as mock_chain:
            mock_chain.invoke.return_value = "LGTM"
            aggregator_node(state)

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert call_kwargs["findings"] == "None."


class TestAggregatorNodeWithPreviousReview:
    _PREVIOUS = [
        Finding(agent="security", severity="critical", file="app/auth.py", line=10, comment="Hardcoded secret"),
        Finding(agent="quality", severity="low", file="app/utils.py", line=5, comment="Long function"),
    ]

    def test_previous_findings_included_in_prompt(self):
        state = {
            **_BASE_STATE,
            "previous_findings": self._PREVIOUS,
            "previous_summary": "Two issues found.",
            "findings": [
                Finding(agent="quality", severity="low", file="app/utils.py", line=5, comment="Long function"),
            ],
        }
        with patch("app.modules.agents.aggregator_agent.aggregator_chain") as mock_chain:
            mock_chain.invoke.return_value = "One fixed, one open."
            aggregator_node(state)

        call_kwargs = mock_chain.invoke.call_args[0][0]
        # Previous context must be present so the LLM can compare
        assert "SECURITY" in call_kwargs["previous_context"]
        assert "Hardcoded secret" in call_kwargs["previous_context"]
        assert "Two issues found." in call_kwargs["previous_context"]

    def test_previous_summary_included_when_present(self):
        state = {
            **_BASE_STATE,
            "previous_findings": self._PREVIOUS,
            "previous_summary": "Critical secrets issue found.",
            "findings": [],
        }
        with patch("app.modules.agents.aggregator_agent.aggregator_chain") as mock_chain:
            mock_chain.invoke.return_value = "All fixed."
            aggregator_node(state)

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert "Critical secrets issue found." in call_kwargs["previous_context"]

    def test_findings_without_previous_summary_still_uses_previous_findings(self):
        state = {
            **_BASE_STATE,
            "previous_findings": self._PREVIOUS,
            "previous_summary": "",
            "findings": [],
        }
        with patch("app.modules.agents.aggregator_agent.aggregator_chain") as mock_chain:
            mock_chain.invoke.return_value = "All fixed."
            aggregator_node(state)

        call_kwargs = mock_chain.invoke.call_args[0][0]
        # Must not fall back to "No previous review" when there ARE previous findings
        assert "No previous review" not in call_kwargs["previous_context"]
        assert "SECURITY" in call_kwargs["previous_context"]

    def test_none_previous_fields_treated_as_no_history(self):
        state = {**_BASE_STATE, "previous_findings": None, "previous_summary": None, "findings": []}
        with patch("app.modules.agents.aggregator_agent.aggregator_chain") as mock_chain:
            mock_chain.invoke.return_value = "LGTM"
            aggregator_node(state)

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert "No previous review" in call_kwargs["previous_context"]
