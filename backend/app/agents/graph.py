"""Grafo explícito del agente RAG; no necesita red para generar su diagrama."""

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.rag_nodes import RAGNodes
from app.agents.state import AgentState


def route_context(state: AgentState):
    return "generate_answer" if state["context_sufficient"] else "reject_question"


def route_answer(state: AgentState):
    return "reject_question" if state["status"] == "needs_rejection" else "save_interaction"


def build_graph(retriever, llm, grader, interactions, max_context_chars=6000, *, single_pass=False, min_relevance_score=0.65):
    nodes = RAGNodes(retriever, llm, grader, interactions, max_context_chars,
                     single_pass=single_pass, min_relevance_score=min_relevance_score)
    builder = StateGraph(AgentState)
    # Nodos: cada nombre representa una responsabilidad del flujo.
    for name in ("receive_question", "validate_question", "retrieve_context", "grade_context",
                 "generate_answer", "reject_question", "save_interaction"):
        builder.add_node(name, getattr(nodes, name))
    # START y edges lineales de recepción, validación y recuperación.
    builder.add_edge(START, "receive_question")
    builder.add_edge("receive_question", "validate_question")
    builder.add_edge("validate_question", "retrieve_context")
    builder.add_edge("retrieve_context", "grade_context")
    # Conditional edges: el grader decide si hay evidencia suficiente.
    builder.add_conditional_edges("grade_context", route_context, {
        "generate_answer": "generate_answer", "reject_question": "reject_question",
    })
    # El generador también puede negarse si no encuentra respaldo para responder.
    builder.add_conditional_edges("generate_answer", route_answer, {
        "reject_question": "reject_question", "save_interaction": "save_interaction",
    })
    builder.add_edge("reject_question", "save_interaction")
    # END: ambas ramas pasan por el registro antes de finalizar.
    builder.add_edge("save_interaction", END)
    return builder.compile()


def graph_mermaid(graph) -> str:
    return graph.get_graph().draw_mermaid()


if __name__ == "__main__":
    from app.services.rag_service import get_rag_service
    print(graph_mermaid(get_rag_service().graph))
