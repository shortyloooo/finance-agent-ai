import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
import plotly.express as px

from database.supabase_client import supabase
from agent.finance_agent import build_finance_agent
from agent.transaction_parser import parse_transaction_text


st.set_page_config(
    page_title="Finance Agent AI",
    page_icon="💰",
    layout="wide"
)


# =========================
# Helper Functions
# =========================

def load_transactions():
    response = (
        supabase.table("transactions")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


def insert_transaction(record):
    return supabase.table("transactions").insert(record).execute()


def delete_transaction(transaction_id):
    return (
        supabase.table("transactions")
        .delete()
        .eq("id", transaction_id)
        .execute()
    )


def prepare_dataframe(transactions):
    df = pd.DataFrame(transactions) if transactions else pd.DataFrame()

    if not df.empty:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    return df


def get_column_config():
    return {
        "No.": st.column_config.NumberColumn(
            "No.",
            width=60
        ),
        "category": st.column_config.TextColumn(
            "Category",
            width="medium"
        ),
        "amount": st.column_config.NumberColumn(
            "Amount",
            width="small",
            format="RM %.2f"
        )
    }
    

def get_display_df(df):
    display_df = df.copy()

    if "id" in display_df.columns:
        display_df = display_df.drop(columns=["id"])

    display_df.insert(0, "No.", range(1, len(display_df) + 1))

    return display_df


def get_category_display_df(category_summary):
    display_df = category_summary.reset_index(drop=True).copy()
    display_df.insert(0, "No.", range(1, len(display_df) + 1))
    return display_df


def display_transaction_card(parsed):
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


# =========================
# Sidebar
# =========================

st.sidebar.title("💰 Finance Agent AI")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "AI Quick Entry",
        "Manual Entry",
        "CSV / Excel Upload",
        "AI Budget Advice",
        "Transactions"
    ]
)

st.sidebar.divider()
st.sidebar.caption(
    "Personal finance tracker powered by Supabase, Streamlit, Ollama, and LangGraph."
)


# =========================
# Load Data
# =========================

transactions = load_transactions()
db_df = prepare_dataframe(transactions)

st.title("Finance Agent AI")
st.caption("Track income, expenses, spending categories, and get budgeting advice.")


# =========================
# Dashboard
# =========================

if page == "Dashboard":
    st.header("📊 Finance Dashboard")

    if db_df.empty:
        st.warning("No transactions found. Add transactions using AI Quick Entry, Manual Entry, or CSV Upload.")
    else:
        st.subheader("Filters")

        col_f1, col_f2, col_f3 = st.columns(3)

        with col_f1:
            start_date = st.date_input(
                "Start Date",
                db_df["transaction_date"].min().date()
            )

        with col_f2:
            end_date = st.date_input(
                "End Date",
                db_df["transaction_date"].max().date()
            )

        with col_f3:
            transaction_filter = st.selectbox(
                "Transaction Type",
                ["All", "income", "expense"]
            )

        filtered_df = db_df[
            (db_df["transaction_date"].dt.date >= start_date) &
            (db_df["transaction_date"].dt.date <= end_date)
        ]

        if transaction_filter != "All":
            filtered_df = filtered_df[
                filtered_df["transaction_type"] == transaction_filter
            ]

        if filtered_df.empty:
            st.warning("No transactions found for the selected filters.")
        else:
            total_income = filtered_df.loc[
                filtered_df["transaction_type"] == "income", "amount"
            ].sum()

            total_expense = filtered_df.loc[
                filtered_df["transaction_type"] == "expense", "amount"
            ].sum()

            balance = total_income - total_expense

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Income", f"RM {total_income:,.2f}")
            col2.metric("Total Expense", f"RM {total_expense:,.2f}")
            col3.metric("Balance", f"RM {balance:,.2f}")

            st.divider()

            expense_df = filtered_df[filtered_df["transaction_type"] == "expense"]

            category_summary = (
                expense_df.groupby("category")["amount"]
                .sum()
                .reset_index()
                .sort_values("amount", ascending=False)
            )

            col_left, col_right = st.columns([1, 1])

            with col_left:
                st.subheader("Spending by Category")
                st.dataframe(
                    get_category_display_df(category_summary),
                    width=500,
                    hide_index=True,
                    column_config=get_column_config()
                )

            with col_right:
                if not category_summary.empty:
                    fig = px.pie(
                        category_summary,
                        names="category",
                        values="amount",
                        title="Expense Breakdown by Category"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No expense data available.")

            st.subheader("Filtered Transactions")
            st.dataframe(
                get_display_df(filtered_df),
                use_container_width=True,
                hide_index=True
            )


# =========================
# AI Quick Entry
# =========================

elif page == "AI Quick Entry":
    st.header("🤖 AI Quick Entry")
    st.write("Type your transaction naturally, and the AI will extract the details.")

    quick_text = st.text_area(
        "Transaction text",
        placeholder="Example: Spent RM15 for lunch today, paid with GrabPay",
        height=120
    )

    if st.button("Add Transaction", use_container_width=True):
        if not quick_text.strip():
            st.warning("Please enter a transaction first.")
        else:
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

                insert_transaction(record)
                display_transaction_card(parsed)

            except Exception as e:
                st.error("Failed to parse or save transaction.")
                st.exception(e)

    st.divider()
    st.subheader("Examples")
    st.info("Spent RM12.50 on milk tea today using Touch n Go")
    st.info("Received RM4000 salary today")
    st.info("Paid RM80 for petrol using credit card")


# =========================
# Manual Entry
# =========================

elif page == "Manual Entry":
    st.header("➕ Manual Transaction Entry")

    with st.form("manual_transaction_form"):
        col1, col2 = st.columns(2)

        with col1:
            transaction_date = st.date_input("Date")
            description = st.text_input("Description")
            amount = st.number_input("Amount", min_value=0.0, format="%.2f")

        with col2:
            transaction_type = st.selectbox("Transaction Type", ["income", "expense"])
            category = st.text_input("Category")
            payment_method = st.text_input("Payment Method")

        submitted = st.form_submit_button("Save Transaction")

        if submitted:
            record = {
                "transaction_date": str(transaction_date),
                "description": description,
                "amount": float(amount),
                "transaction_type": transaction_type,
                "category": category,
                "payment_method": payment_method,
                "source": "manual",
                "notes": "manual entry"
            }

            insert_transaction(record)
            st.success("Manual transaction saved successfully!")


# =========================
# CSV / Excel Upload
# =========================

elif page == "CSV / Excel Upload":
    st.header("📁 CSV / Excel Upload")

    uploaded_file = st.file_uploader(
        "Upload CSV or Excel file",
        type=["csv", "xlsx"]
    )

    st.info("Required columns: date, description, amount, type, category")

    if uploaded_file:
        if uploaded_file.name.endswith(".csv"):
            upload_df = pd.read_csv(uploaded_file)
        else:
            upload_df = pd.read_excel(uploaded_file)

        st.subheader("Preview")
        st.dataframe(upload_df, use_container_width=True)

        if st.button("Save Uploaded Transactions"):
            records = []

            for _, row in upload_df.iterrows():
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

            supabase.table("transactions").insert(records).execute()
            st.success(f"Inserted {len(records)} transactions successfully!")


# =========================
# AI Budget Advice
# =========================

elif page == "AI Budget Advice":
    st.header("🧠 AI Budget Advice")

    if db_df.empty:
        st.warning("No transactions found.")
    else:
        total_income = db_df.loc[
            db_df["transaction_type"] == "income", "amount"
        ].sum()

        total_expense = db_df.loc[
            db_df["transaction_type"] == "expense", "amount"
        ].sum()

        balance = total_income - total_expense

        expense_df = db_df[db_df["transaction_type"] == "expense"]

        category_summary = (
            expense_df.groupby("category")["amount"]
            .sum()
            .reset_index()
            .sort_values("amount", ascending=False)
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("Income", f"RM {total_income:,.2f}")
        col2.metric("Expense", f"RM {total_expense:,.2f}")
        col3.metric("Balance", f"RM {balance:,.2f}")

        st.divider()

        if st.button("Generate Budget Advice", use_container_width=True):
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


# =========================
# Transactions
# =========================

elif page == "Transactions":
    st.header("📄 Transactions")

    if db_df.empty:
        st.warning("No transactions found.")
    else:
        st.write("Click one row in the table, then press delete.")

        display_df = get_display_df(db_df)

        selected_table = st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )

        selected_rows = selected_table.selection.rows

        if selected_rows:
            selected_index = selected_rows[0]
            selected_transaction = db_df.iloc[selected_index]
            selected_id = int(selected_transaction["id"])

            st.divider()
            st.subheader("Selected Transaction")

            col1, col2, col3 = st.columns(3)
            col1.metric("Amount", f"RM {float(selected_transaction['amount']):,.2f}")
            col2.metric("Type", str(selected_transaction["transaction_type"]).title())
            col3.metric("Category", selected_transaction["category"])

            st.write(f"**Description:** {selected_transaction['description']}")
            st.write(f"**Date:** {selected_transaction['transaction_date']}")

            if selected_transaction.get("payment_method"):
                st.write(f"**Payment Method:** {selected_transaction['payment_method']}")

            if st.button("Delete Selected Transaction", type="primary"):
                delete_transaction(selected_id)
                st.success("Transaction deleted successfully.")
                st.rerun()
        else:
            st.info("No transaction selected yet.")

        st.divider()

        csv = get_display_df(db_df).to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Transactions as CSV",
            data=csv,
            file_name="transactions.csv",
            mime="text/csv"
        )