from pathlib import Path

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.core.state import AgentState, Finding

# ── LLM ──────────────────────────────────────────────────────────────────────
llm = ChatGoogleGenerativeAI(
    model=settings.gemini_model,
    temperature=settings.llm_temperature,
    google_api_key=settings.google_api_key,
)

# ── Prompt ────────────────────────────────────────────────────────────────────
_prompt_text = (Path(__file__).parent.parent / "app" / "core" / "prompts" / "security.md").read_text()

prompt = ChatPromptTemplate.from_messages([
    ("system", _prompt_text),
    ("human", "PR Diff:\n{diff}"),
])

security_chain = prompt | llm | JsonOutputParser()


# ── Node ──────────────────────────────────────────────────────────────────────
def security_node(state: AgentState) -> dict:
    result = security_chain.invoke({"diff": state["diff"][: settings.max_diff_tokens]})

    findings: list[Finding] = [
        Finding(agent="security", **f)
        for f in result.get("findings", [])
    ]

    return {
        "findings": findings,
        "agents_done": state.get("agents_done", []) + ["security"],
    }