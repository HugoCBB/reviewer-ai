from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_llm
from app.core.state import AgentState, Finding

_prompt_text = (Path(__file__).parent.parent.parent / "core" / "prompts" / "aggregator.md").read_text()

prompt = ChatPromptTemplate.from_messages([
    ("system", _prompt_text),
    ("human", (
        "Previous review:\n{previous_context}\n\n"
        "Current findings:\n{findings}"
    )),
])

aggregator_chain = prompt | get_llm() | StrOutputParser()


def _format_findings(findings: list[Finding]) -> str:
    if not findings:
        return "None."
    return "\n".join(
        f"[{f['agent'].upper()}][{f['severity'].upper()}] {f['file']}:{f['line']} — {f['comment']}"
        for f in findings
    )


def aggregator_node(state: AgentState) -> dict:
    previous_findings: list[Finding] = state.get("previous_findings") or []
    previous_summary: str = state.get("previous_summary") or ""

    if previous_findings or previous_summary:
        previous_context = (
            f"Summary: {previous_summary}\n\nFindings:\n{_format_findings(previous_findings)}"
            if previous_summary
            else _format_findings(previous_findings)
        )
    else:
        previous_context = "No previous review for this PR."

    current_findings: list[Finding] = state.get("findings", [])

    summary = aggregator_chain.invoke({
        "previous_context": previous_context,
        "findings": _format_findings(current_findings),
    })

    return {"summary": summary, "next": "FINISH"}
