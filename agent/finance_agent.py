from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
import os
import streamlit as st
from groq import Groq
from dotenv import load_dotenv

def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
    return Groq(api_key=api_key)

load_dotenv()

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


import ollama


def generate_final_advice_node(state: FinanceState):

    category_text = ""

    for _, row in state["category_summary"].iterrows():
        category_text += f"- {row['category']}: RM {row['amount']:.2f}\n"

    risk_text = "\n".join(state["risk_flags"])

    prompt = f"""
    You are an experienced personal financial advisor.

    Analyze the user's financial situation naturally like a real human advisor.

    User Financial Summary:
    - Total Income: RM {state['total_income']:.2f}
    - Total Expense: RM {state['total_expense']:.2f}
    - Balance: RM {state['balance']:.2f}

    Spending Categories:
    {category_text}

    Detected Risks:
    {risk_text}

    Budget Recommendation:
    - Needs: RM {state["budget_plan"]["Needs"]:.2f}
    - Wants: RM {state["budget_plan"]["Wants"]:.2f}
    - Savings: RM {state["budget_plan"]["Savings"]:.2f}

    Instructions:
    - Give realistic financial advice.
    - Mention specific categories and spending behavior.
    - Explain what the user is doing well.
    - Explain what should improve.
    - Give practical next steps.
    - Sound natural and human.
    - Avoid generic advice.
    - Use tables if it makes the advice clearer.
    - Be detailed but concise.

    Response format:
    ## Quick Financial Health Summary

    ## Key Spending Insights

    ## Budget Recommendation Table

    ## Action Plan Table

    ## Final Advice

    Output rules:
    - Keep response under 350 words.
    - Prioritize the top 3 most important insights.
    - Use markdown tables where useful.
    - Avoid repeating the same point.
    """

    client = get_groq_client()

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.4,
        max_tokens=700
    )

    advice = response.choices[0].message.content

    return {
        **state,
        "advice": advice
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