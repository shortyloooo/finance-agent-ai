import sys
import os
import plotly.express as px

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd

from database.supabase_client import supabase
from agent.finance_agent import build_finance_agent
from agent.transaction_parser import parse_transaction_text

st.set_page_config(page_title="Finance Agent AI", layout="wide")

st.title("Finance Agent AI")

st.subheader("Upload Manual Transaction")

with st.form("manual_transaction_form"):
    date = st.date_input("Date")
    description = st.text_input("Description")
    amount = st.number_input("Amount", format="%.2f")
    transaction_type = st.selectbox("Transaction Type", ["income", "expense"])
    category = st.text_input("Category")
    payment_method = st.text_input("Payment Method")

    submitted = st.form_submit_button("Add Transaction")

    if submitted:
        record = {
            "transaction_date": str(date),
            "description": description,
            "amount": float(amount),
            "transaction_type": transaction_type,
            "category": category,
            "payment_method": payment_method,
            "source": "manual",
            "notes": "manual entry"
        }

        supabase.table("transactions").insert(record).execute()
        st.success("Transaction saved successfully!")

st.write("Upload your bank statement and save transactions into Supabase.")

st.subheader("AI Quick Add Transaction")

quick_text = st.text_input(
    "Type a transaction",
    placeholder="Example: I spent RM25 on lunch today"
)

if st.button("AI Add Transaction"):
    try:
        parsed = parse_transaction_text(quick_text)

        record = {
            "transaction_date": parsed["transaction_date"],
            "description": parsed["description"],
            "amount": float(parsed["amount"]),
            "transaction_type": parsed["transaction_type"],
            "category": parsed["category"],
            "payment_method": parsed["payment_method"],
            "source": "ai_text",
            "notes": quick_text
        }

        supabase.table("transactions").insert(record).execute()

        st.success("Transaction saved successfully!")

        st.markdown("### Added Transaction")

        col1, col2, col3 = st.columns(3)

        col1.metric("Amount", f"RM {float(parsed['amount']):,.2f}")
        col2.metric("Type", parsed["transaction_type"].title())
        col3.metric("Category", parsed["category"])

        st.write(f"**Date:** {parsed['transaction_date']}")
        st.write(f"**Description:** {parsed['description']}")

        if parsed.get("payment_method"):
            st.write(f"**Payment Method:** {parsed['payment_method']}")

    except Exception as e:
        st.error("Failed to parse transaction.")
        st.write(e)

uploaded_file = st.file_uploader(
    "Upload CSV or Excel file",
    type=["csv", "xlsx"]
)

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("Preview Uploaded File")
    st.dataframe(df)

    st.info("For now, your file must have these columns: date, description, amount, type, category")

    if st.button("Save to Supabase"):
        records = []

        for _, row in df.iterrows():
            records.append({
                "transaction_date": str(row["date"]),
                "description": str(row["description"]),
                "amount": float(row["amount"]),
                "transaction_type": str(row["type"]),
                "category": str(row["category"]),
                "payment_method": None,
                "source": uploaded_file.name,
                "notes": "uploaded file"
            })

        response = supabase.table("transactions").insert(records).execute()

        st.success(f"Inserted {len(records)} transactions successfully!")

st.divider()

st.subheader("Transactions in Database")

response = supabase.table("transactions").select("*").order("created_at", desc=True).execute()

if response.data:
    st.dataframe(response.data)
else:
    st.warning("No transactions found.")
    
if response.data:
    db_df = pd.DataFrame(response.data)

    st.subheader("📊 Finance Summary")

    total_income = db_df.loc[
        db_df["transaction_type"] == "income", "amount"
    ].sum()

    total_expense = db_df.loc[
        db_df["transaction_type"] == "expense", "amount"
    ].sum()

    balance = total_income - total_expense

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Income", f"RM {total_income:,.2f}")
    col2.metric("Total Expense", f"RM {total_expense:,.2f}")
    col3.metric("Balance", f"RM {balance:,.2f}")

    st.subheader("Spending by Category")

    expense_df = db_df[db_df["transaction_type"] == "expense"]

    category_summary = (
        expense_df.groupby("category")["amount"]
        .sum()
        .reset_index()
        .sort_values("amount", ascending=False)
    )

    st.dataframe(category_summary)

if not category_summary.empty:
    fig = px.pie(
        category_summary,
        names="category",
        values="amount",
        title="Expense Breakdown by Category"
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No expense data available for chart.")
    
st.subheader("AI Budgeting Advice")

if st.button("Generate Budget Advice"):
    finance_agent = build_finance_agent()

    result = finance_agent.invoke({
        "total_income": float(total_income),
        "total_expense": float(total_expense),
        "balance": float(balance),
        "category_summary": category_summary,
        "summary_text": "",
        "risk_flags": [],
        "budget_plan": {},
        "advice": ""
    })

    st.markdown(result["advice"])