from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.core.state import AgentState

llm = ChatGoogleGenerativeAI(
    model=settings.gemini_model,
    temperature=settings.llm_temperature,
    google_api_key=settings.google_api_key,
)

_prompt_text = (Path(__file__).parent.parent / "" / "core" / "prompts" / "aggregator.md").read_text()

prompt = ChatPromptTemplate.from_messages([
    ("system", _prompt_text),
    ("human", "Findings from all agents:\n{findings}"),
])

aggregator_chain = prompt | llm | StrOutputParser()


def aggregator_node(state: AgentState) -> dict:
    findings = state.get("findings", [])

    formatted = "\n".join(
        f"[{f['agent'].upper()}] [{f['severity'].upper()}] {f['file']}:{f['line']} — {f['comment']}"
        for f in findings
    ) or "No issues found by any agent."

    summary = aggregator_chain.invoke({"findings": formatted})

    return {"summary": summary, "next": "FINISH"}