from typing import TypedDict
from langgraph.graph import StateGraph, END
from agent.budget_advisor import generate_budget_advice


class FinanceState(TypedDict):
    total_income: float
    total_expense: float
    balance: float
    category_summary: object
    advice: str


def generate_advice_node(state: FinanceState):
    advice = generate_budget_advice(
        state["total_income"],
        state["total_expense"],
        state["balance"],
        state["category_summary"]
    )

    return {
        **state,
        "advice": advice
    }


def build_finance_agent():
    graph = StateGraph(FinanceState)

    graph.add_node("generate_advice", generate_advice_node)

    graph.set_entry_point("generate_advice")
    graph.add_edge("generate_advice", END)

    return graph.compile()