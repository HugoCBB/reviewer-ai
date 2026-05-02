from pathlib import Path

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.core.state import AgentState

# ── LLM ──────────────────────────────────────────────────────────────────────
llm = ChatGoogleGenerativeAI(
    model=settings.gemini_model,
    temperature=settings.llm_temperature,
    google_api_key=settings.google_api_key,
)

# ── Prompt loaded from markdown ───────────────────────────────────────────────
_prompt_text = (Path(__file__).parent.parent / "app" / "core" / "prompts" / "orchestrator.md").read_text()

prompt = ChatPromptTemplate.from_messages([
    ("system", _prompt_text),
    ("human", "Title: {title}\nDescription: {description}\nDiff:\n{diff}"),
])

# ── Chain ─────────────────────────────────────────────────────────────────────
orchestrator_chain = prompt | llm | JsonOutputParser()

AGENTS = ["security", "quality", "tests", "docs"]


# ── Node ──────────────────────────────────────────────────────────────────────
def orchestrator_node(state: AgentState) -> dict:
    result = orchestrator_chain.invoke({
        "agents": AGENTS,
        "agents_done": state.get("agents_done", []),
        "title": state["title"],
        "description": state["description"],
        "diff": state["diff"][: settings.max_diff_tokens],
    })
    return {"next": result["next"]}