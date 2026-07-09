"""LangGraph wiring for the Mentor agent.

Flow (one graph invocation advances the session by one turn):

    START ─┬─(answer present)─→ grader ─┬─ q<3 → diagnoser → adapter ─┐
           │                            └─ q>=3 →──────────  adapter ─┤
           └─(no answer)─────────────────────────────────────────────┤
                                                                      ▼
                       scheduler → planner ─┬─ done → END
                                            └─ teach → teacher → quizzer → END

The scheduler surfaces due reviews first; the planner builds/advances the path
via topological sort; grader→diagnoser→adapter runs the self-correction loop.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent.deps import Deps
from app.agent.nodes.adapter import make_adapter
from app.agent.nodes.diagnoser import make_diagnoser
from app.agent.nodes.grader import make_grader
from app.agent.nodes.planner import make_planner
from app.agent.nodes.quizzer import make_quizzer
from app.agent.nodes.scheduler import make_scheduler
from app.agent.nodes.teacher import make_teacher
from app.agent.state import AgentState


def _entry(state: AgentState) -> str:
    """Grade an incoming answer, otherwise present the next concept."""
    return "grader" if state.get("answer") else "scheduler"


def _after_grade(state: AgentState) -> str:
    grade = state.get("last_grade") or {}
    return "adapter" if int(grade.get("quality", 0)) >= 3 else "diagnoser"


def _after_planner(state: AgentState) -> str:
    return "teacher" if state.get("current_concept") else END


def build_graph(deps: Deps) -> CompiledStateGraph:
    """Compile the agent graph with dependencies bound into each node."""
    g: StateGraph = StateGraph(AgentState)

    g.add_node("scheduler", make_scheduler(deps))
    g.add_node("planner", make_planner(deps))
    g.add_node("teacher", make_teacher(deps))
    g.add_node("quizzer", make_quizzer(deps))
    g.add_node("grader", make_grader(deps))
    g.add_node("diagnoser", make_diagnoser(deps))
    g.add_node("adapter", make_adapter(deps))

    g.add_conditional_edges(START, _entry, {"grader": "grader", "scheduler": "scheduler"})
    g.add_edge("scheduler", "planner")
    g.add_conditional_edges("planner", _after_planner, {"teacher": "teacher", END: END})
    g.add_edge("teacher", "quizzer")
    g.add_edge("quizzer", END)
    g.add_conditional_edges(
        "grader", _after_grade, {"adapter": "adapter", "diagnoser": "diagnoser"}
    )
    g.add_edge("diagnoser", "adapter")
    g.add_edge("adapter", "planner")

    return g.compile()
