from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.config import settings

THINK_PROMPT = (
    "You are preparing a short, visible Thinking scratchpad for the user. "
    "Reason step-by-step about the user's latest question using prior conversation "
    "as context. Be concrete (what matters, what to check, what approach to take). "
    "If the question needs live/current data (weather, news, prices, sports scores), "
    "note that browse_web should be used. "
    "Do NOT write the final answer—only the thinking notes. Keep it under 180 words."
)

AGENT_PROMPT = (
    "You are a helpful assistant in the Portal app. "
    "Use prior messages as context. "
    "For current events, weather, live facts, or anything that changes over time, "
    "you MUST call browse_web before answering—do not say you lack real-time data "
    "without searching first. "
    "You may call summarize_text or generalize_ideas when condensation or pattern "
    "extraction would help. "
    "A Thinking scratchpad is provided for your own planning—do not repeat it verbatim; "
    "write a clear final answer for the user, citing what the search found when relevant."
)


@dataclass(frozen=True)
class HistoryMessage:
    role: str
    content: str


@dataclass
class TurnResult:
    content: str
    thinking: str
    tools_used: list[str] = field(default_factory=list)


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    thinking: str


def _require_api_key() -> str:
    key = settings.openai_api_key.strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return key


def _as_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict):
                parts.append(str(part.get("text", "")))
            else:
                parts.append(str(part))
        return "".join(parts)
    return str(content)


def _make_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=_require_api_key(),
        temperature=0.3,
    )


def _duckduckgo_search(query: str, *, max_results: int = 5) -> str:
    """Run a DuckDuckGo text search; return a compact multi-line summary."""
    try:
        from ddgs import DDGS
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("ddgs is not installed") from exc

    try:
        with DDGS() as ddgs:
            rows = list(ddgs.text(query, max_results=max_results))
    except Exception as exc:  # network / rate-limit / parsing
        return f"Web search failed: {exc}"

    if not rows:
        return "No web results found."

    lines: list[str] = []
    for i, row in enumerate(rows, start=1):
        title = (row.get("title") or "").strip()
        href = (row.get("href") or row.get("link") or "").strip()
        body = (row.get("body") or row.get("snippet") or "").strip()
        lines.append(f"{i}. {title}\n   {body}\n   {href}".rstrip())
    return "\n".join(lines)


def _build_tools(llm: ChatOpenAI):
    @tool
    def browse_web(query: str) -> str:
        """Search the public web (DuckDuckGo) for current information.

        Use for weather, news, live facts, prices, sports, or anything that
        needs up-to-date information. Pass a focused search query.
        """
        return _duckduckgo_search(query)

    @tool
    def summarize_text(text: str) -> str:
        """Condense a passage or older conversation turns into a short summary."""
        response = llm.invoke(
            [
                SystemMessage(
                    content="Summarize the text clearly and briefly. Keep key facts."
                ),
                HumanMessage(content=text),
            ]
        )
        return _as_text(response.content)

    @tool
    def generalize_ideas(focus: str) -> str:
        """Extract patterns, principles, or general takeaways from the given focus text."""
        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "Extract general patterns, principles, and reusable takeaways. "
                        "Be concise and concrete."
                    )
                ),
                HumanMessage(content=focus),
            ]
        )
        return _as_text(response.content)

    return [browse_web, summarize_text, generalize_ideas]


def _build_graph():
    llm = _make_llm()
    tools = _build_tools(llm)
    llm_with_tools = llm.bind_tools(tools)
    tool_node = ToolNode(tools)

    def think_node(state: AgentState) -> dict[str, str]:
        response = llm.invoke([SystemMessage(content=THINK_PROMPT), *state["messages"]])
        return {"thinking": _as_text(response.content).strip()}

    def agent_node(state: AgentState) -> dict[str, list[BaseMessage]]:
        scratch = state.get("thinking") or ""
        system = SystemMessage(
            content=f"{AGENT_PROMPT}\n\nThinking scratchpad:\n{scratch}"
        )
        response = llm_with_tools.invoke([system, *state["messages"]])
        return {"messages": [response]}

    def route_after_agent(state: AgentState) -> Literal["tools", "__end__"]:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return "__end__"

    builder = StateGraph(AgentState)
    builder.add_node("think", think_node)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "think")
    builder.add_edge("think", "agent")
    builder.add_conditional_edges(
        "agent",
        route_after_agent,
        {"tools": "tools", "__end__": END},
    )
    builder.add_edge("tools", "agent")
    return builder.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


def reset_graph_for_tests() -> None:
    """Clear cached graph so tests can reconfigure settings/mocks."""
    global _graph
    _graph = None


def _to_lc_messages(history: list[HistoryMessage]) -> list[BaseMessage]:
    out: list[BaseMessage] = []
    for item in history:
        if item.role == "user":
            out.append(HumanMessage(content=item.content))
        elif item.role == "assistant":
            out.append(AIMessage(content=item.content))
    return out


def _tools_used(messages: list[BaseMessage]) -> list[str]:
    names: list[str] = []
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for call in msg.tool_calls:
                name = (
                    call.get("name")
                    if isinstance(call, dict)
                    else getattr(call, "name", None)
                )
                if name and name not in names:
                    names.append(name)
    return names


def run_turn(history: list[HistoryMessage], user_text: str) -> TurnResult:
    """Run one chat turn with thinking + optional tools; return answer and scratchpad."""
    graph = get_graph()
    messages = _to_lc_messages(history) + [HumanMessage(content=user_text)]
    result = graph.invoke({"messages": messages, "thinking": ""})
    thinking = (result.get("thinking") or "").strip()
    final_messages: list[BaseMessage] = result["messages"]
    last = final_messages[-1]
    content = _as_text(last.content).strip()
    return TurnResult(
        content=content,
        thinking=thinking,
        tools_used=_tools_used(final_messages),
    )
