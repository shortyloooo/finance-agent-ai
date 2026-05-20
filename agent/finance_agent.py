from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END

class FinanceState(TypedDict):
    total_income: float
    total_expense: float
    balance: float
    category_summary: Any
    summary_text: str
    risk_flags: List[str]
    budget_plan: Dict[str, float]
    advice: str


def analyze_summary_node(state: FinanceState):
    savings_rate = 0

    if state["total_income"] > 0:
        savings_rate = (state["balance"] / state["total_income"]) * 100

    summary_text = f"""
Total income: RM {state['total_income']:.2f}
Total expense: RM {state['total_expense']:.2f}
Balance: RM {state['balance']:.2f}
Savings rate: {savings_rate:.2f}%
"""

    return {
        **state,
        "summary_text": summary_text
    }


def detect_risk_node(state: FinanceState):
    risk_flags = []

    if state["total_expense"] > state["total_income"]:
        risk_flags.append("Your expenses are higher than your income.")

    if state["total_income"] > 0:
        expense_ratio = state["total_expense"] / state["total_income"]

        if expense_ratio > 0.8:
            risk_flags.append("You are spending more than 80% of your income.")

    category_summary = state["category_summary"]

    if not category_summary.empty:
        top_category = category_summary.iloc[0]
        risk_flags.append(
            f"Your highest spending category is {top_category['category']} at RM {top_category['amount']:.2f}."
        )

    return {
        **state,
        "risk_flags": risk_flags
    }


def create_budget_plan_node(state: FinanceState):
    income = state["total_income"]

    budget_plan = {
        "Needs": income * 0.50,
        "Wants": income * 0.30,
        "Savings": income * 0.20
    }

    return {
        **state,
        "budget_plan": budget_plan
    }


def generate_final_advice_node(state: FinanceState):
    category_summary = state["category_summary"]

    if not category_summary.empty:
        category_lines = []
        for _, row in category_summary.iterrows():
            category_lines.append(
                f"- {row['category']}: RM {row['amount']:.2f}"
            )
        category_text = "\n".join(category_lines)
    else:
        category_text = "- No expense category found."

    final_advice = f"""
### Finance Summary

{state["summary_text"]}

### Spending by Category

{category_text}

### Spending Risk Flags

{chr(10).join(["- " + flag for flag in state["risk_flags"]]) if state["risk_flags"] else "- No major risk detected."}

### Suggested Monthly Budget

- Needs: RM {state["budget_plan"]["Needs"]:.2f}
- Wants: RM {state["budget_plan"]["Wants"]:.2f}
- Savings: RM {state["budget_plan"]["Savings"]:.2f}

### Action Plan

- Review your highest spending category first because it has the biggest impact on your savings.
- Set a monthly limit for each major category.
- Track expenses weekly instead of waiting until month end.
- Keep your savings target separate from daily spending money.
"""

    return {
        **state,
        "advice": final_advice
    }


def build_finance_agent():
    graph = StateGraph(FinanceState)

    graph.add_node("analyze_summary", analyze_summary_node)
    graph.add_node("detect_risk", detect_risk_node)
    graph.add_node("create_budget_plan", create_budget_plan_node)
    graph.add_node("generate_final_advice", generate_final_advice_node)

    graph.set_entry_point("analyze_summary")

    graph.add_edge("analyze_summary", "detect_risk")
    graph.add_edge("detect_risk", "create_budget_plan")
    graph.add_edge("create_budget_plan", "generate_final_advice")
    graph.add_edge("generate_final_advice", END)

    return graph.compile()