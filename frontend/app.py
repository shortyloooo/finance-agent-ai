import sys
import os
from datetime import date, timedelta

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
# CSS
# =========================

st.markdown("""
<style>
div[data-testid="stFormSubmitButton"] button[kind="primary"] {
    background-color: #16a34a;
    border-color: #16a34a;
    color: white;
}

div[data-testid="stFormSubmitButton"] button[kind="secondary"] {
    background-color: #dc2626;
    border-color: #dc2626;
    color: white;
}
</style>
""", unsafe_allow_html=True)


# =========================
# Auth Functions
# =========================

def get_previous_month_range():
    today = date.today()
    first_day_current_month = today.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    first_day_previous_month = last_day_previous_month.replace(day=1)

    return first_day_previous_month, last_day_previous_month


def get_previous_month_transactions(user_id):
    start_date, end_date = get_previous_month_range()

    response = (
        supabase.table("transactions")
        .select("*")
        .eq("user_id", user_id)
        .gte("transaction_date", str(start_date))
        .lte("transaction_date", str(end_date))
        .execute()
    )

    return response.data


def delete_previous_month_transactions(user_id):
    start_date, end_date = get_previous_month_range()

    return (
        supabase.table("transactions")
        .delete()
        .eq("user_id", user_id)
        .gte("transaction_date", str(start_date))
        .lte("transaction_date", str(end_date))
        .execute()
    )

def restore_auth_session():
    if "access_token" in st.session_state and "refresh_token" in st.session_state:
        try:
            supabase.auth.set_session(
                st.session_state["access_token"],
                st.session_state["refresh_token"]
            )
        except Exception:
            pass


def auth_page():
    st.title("💰 Finance Agent AI")
    st.caption("Login or register to manage your personal finances.")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", use_container_width=True):
            if not email.strip() or not password.strip():
                st.warning("Please enter both email and password.")
            else:
                try:
                    response = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })

                    st.session_state["user"] = response.user
                    st.session_state["access_token"] = response.session.access_token
                    st.session_state["refresh_token"] = response.session.refresh_token

                    st.success("Login successful.")
                    st.rerun()

                except Exception:
                    st.error("Login failed. Please check your email and password.")

    with tab2:
        email = st.text_input("Email", key="register_email")
        password = st.text_input("Password", type="password", key="register_password")

        if st.button("Register", use_container_width=True):
            if not email.strip() or not password.strip():
                st.warning("Please enter both email and password.")
            elif len(password) < 6:
                st.warning("Password must be at least 6 characters.")
            else:
                try:
                    supabase.auth.sign_up({
                        "email": email,
                        "password": password
                    })

                    st.success("Account created. Please check your email if confirmation is required.")

                except Exception:
                    st.error("Registration failed. Please try again.")


restore_auth_session()

if "user" not in st.session_state:
    auth_page()
    st.stop()

user = st.session_state["user"]
user_id = user.id

today = date.today()

if today.day <= 7:
    previous_month_data = get_previous_month_transactions(user_id)

    if previous_month_data:
        st.warning(
            "Monthly reset reminder: Please download last month’s transactions before they are cleared after the 7th."
        )

        previous_month_df = pd.DataFrame(previous_month_data)

        if "id" in previous_month_df.columns:
            previous_month_df = previous_month_df.drop(columns=["id"])

        if "user_id" in previous_month_df.columns:
            previous_month_df = previous_month_df.drop(columns=["user_id"])

        csv = previous_month_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Last Month Transactions",
            data=csv,
            file_name="last_month_transactions.csv",
            mime="text/csv"
        )

elif today.day > 7:
    previous_month_data = get_previous_month_transactions(user_id)

    if previous_month_data:
        delete_previous_month_transactions(user_id)
        st.info("Previous month’s transactions have been cleared after the 7-day download period.")
        st.rerun()

# =========================
# Helper Functions
# =========================

def load_transactions(user_id):
    response = (
        supabase.table("transactions")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


def insert_transaction(record):
    return supabase.table("transactions").insert(record).execute()


def update_transaction(transaction_id, record):
    return (
        supabase.table("transactions")
        .update(record)
        .eq("id", transaction_id)
        .execute()
    )


def delete_transaction(transaction_id):
    return (
        supabase.table("transactions")
        .delete()
        .eq("id", transaction_id)
        .execute()
    )


def load_budget_goals(user_id):
    response = (
        supabase.table("budget_goals")
        .select("*")
        .eq("user_id", user_id)
        .order("category")
        .execute()
    )
    return response.data


def insert_budget_goal(record):
    return supabase.table("budget_goals").insert(record).execute()


def update_budget_goal(goal_id, record):
    return (
        supabase.table("budget_goals")
        .update(record)
        .eq("id", goal_id)
        .execute()
    )


def find_similar_transaction(record):
    response = (
        supabase.table("transactions")
        .select("*")
        .eq("user_id", record["user_id"])
        .eq("transaction_date", record["transaction_date"])
        .eq("description", record["description"])
        .eq("amount", record["amount"])
        .eq("transaction_type", record["transaction_type"])
        .execute()
    )
    return response.data


def normalize_transaction_type(value):
    value = str(value).lower().strip()

    if value in ["expense", "expenses", "spent", "spending"]:
        return "expense"

    if value in ["income", "incomes", "earned", "received"]:
        return "income"

    return "expense"


def prepare_dataframe(transactions):
    df = pd.DataFrame(transactions) if transactions else pd.DataFrame()

    if not df.empty:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
        df["transaction_type"] = df["transaction_type"].apply(normalize_transaction_type)

    return df


def get_column_config():
    return {
        "No.": st.column_config.NumberColumn("No.", width=60),
        "category": st.column_config.TextColumn("Category", width="medium"),
        "amount": st.column_config.NumberColumn("Amount", width="small", format="RM %.2f")
    }


def get_display_df(df):
    display_df = df.copy()

    if "id" in display_df.columns:
        display_df = display_df.drop(columns=["id"])

    if "user_id" in display_df.columns:
        display_df = display_df.drop(columns=["user_id"])

    display_df.insert(0, "No.", range(1, len(display_df) + 1))
    return display_df


def get_category_display_df(category_summary):
    display_df = category_summary.reset_index(drop=True).copy()
    display_df.insert(0, "No.", range(1, len(display_df) + 1))
    return display_df


def validate_upload_columns(upload_df):
    required_columns = ["date", "description", "amount", "type", "category"]
    return [col for col in required_columns if col not in upload_df.columns]


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
st.sidebar.caption(f"Logged in as: {user.email}")

if st.sidebar.button("Logout", use_container_width=True):
    supabase.auth.sign_out()
    st.session_state.clear()
    st.rerun()

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "AI Quick Entry",
        "Manual Entry",
        "CSV / Excel Upload",
        "Budget Goals",
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

transactions = load_transactions(user_id)
db_df = prepare_dataframe(transactions)

budget_goals = load_budget_goals(user_id)
budget_df = pd.DataFrame(budget_goals) if budget_goals else pd.DataFrame()

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

            st.subheader("Monthly Income vs Expense Trend")

            trend_df = filtered_df.copy()
            trend_df["month"] = trend_df["transaction_date"].dt.to_period("M").astype(str)

            monthly_summary = (
                trend_df.groupby(["month", "transaction_type"])["amount"]
                .sum()
                .reset_index()
            )

            fig_trend = px.bar(
                monthly_summary,
                x="month",
                y="amount",
                color="transaction_type",
                barmode="group",
                title="Monthly Income vs Expense"
            )
            st.plotly_chart(fig_trend, use_container_width=True)

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

            st.divider()
            st.subheader("Budget vs Actual Spending")

            if budget_df.empty:
                st.info("No budget goals set yet. Add budget goals from the Budget Goals page.")
            else:
                actual_spending = (
                    filtered_df[filtered_df["transaction_type"] == "expense"]
                    .groupby("category")["amount"]
                    .sum()
                    .reset_index()
                    .rename(columns={"amount": "actual_spending"})
                )

                budget_compare = budget_df.merge(
                    actual_spending,
                    on="category",
                    how="left"
                )

                budget_compare["actual_spending"] = budget_compare["actual_spending"].fillna(0)
                budget_compare["remaining_budget"] = (
                    budget_compare["monthly_budget"] - budget_compare["actual_spending"]
                )
                budget_compare["usage_percent"] = (
                    budget_compare["actual_spending"] / budget_compare["monthly_budget"] * 100
                ).round(2)

                display_budget_compare = budget_compare[
                    ["category", "monthly_budget", "actual_spending", "remaining_budget", "usage_percent"]
                ].copy()

                display_budget_compare.insert(0, "No.", range(1, len(display_budget_compare) + 1))

                st.dataframe(
                    display_budget_compare,
                    use_container_width=True,
                    hide_index=True
                )

                fig_budget = px.bar(
                    budget_compare,
                    x="category",
                    y=["monthly_budget", "actual_spending"],
                    barmode="group",
                    title="Budget vs Actual Spending"
                )

                st.plotly_chart(fig_budget, use_container_width=True)

            st.subheader("Filtered Transactions")
            st.dataframe(
                get_display_df(filtered_df),
                use_container_width=True,
                hide_index=True,
                column_config=get_column_config()
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
                    "transaction_type": normalize_transaction_type(parsed["transaction_type"]),
                    "category": parsed["category"],
                    "payment_method": parsed["payment_method"],
                    "source": "ai_text",
                    "notes": quick_text,
                    "user_id": user_id
                }

                similar_records = find_similar_transaction(record)

                if similar_records:
                    st.warning("A similar transaction already exists. This may be a duplicate.")
                    insert_transaction(record)
                    st.info("Saved anyway because repeated expenses can be valid.")
                    display_transaction_card(parsed)
                else:
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
                "notes": "manual entry",
                "user_id": user_id
            }

            similar_records = find_similar_transaction(record)

            if similar_records:
                st.warning("A similar transaction exists, but manual entries are still saved.")

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

    sample_df = pd.DataFrame({
        "date": ["2026-05-20"],
        "description": ["Lunch"],
        "amount": [15.00],
        "type": ["expense"],
        "category": ["Food"]
    })

    st.write("Sample format:")
    st.dataframe(sample_df, hide_index=True, use_container_width=True)

    if uploaded_file:
        if uploaded_file.name.endswith(".csv"):
            upload_df = pd.read_csv(uploaded_file)
        else:
            upload_df = pd.read_excel(uploaded_file)

        missing_columns = validate_upload_columns(upload_df)

        if missing_columns:
            st.error(f"Missing required columns: {', '.join(missing_columns)}")
            st.stop()

        st.subheader("Preview")
        st.dataframe(upload_df, use_container_width=True)

        if st.button("Save Uploaded Transactions"):
            records = []

            for _, row in upload_df.iterrows():
                records.append({
                    "transaction_date": str(row["date"]),
                    "description": str(row["description"]),
                    "amount": float(row["amount"]),
                    "transaction_type": normalize_transaction_type(row["type"]),
                    "category": str(row["category"]),
                    "payment_method": None,
                    "source": uploaded_file.name,
                    "notes": "uploaded file",
                    "user_id": user_id
                })

            new_records = []
            possible_duplicates = []

            for record in records:
                similar_records = find_similar_transaction(record)

                if similar_records:
                    possible_duplicates.append(record)
                else:
                    new_records.append(record)

            if new_records:
                supabase.table("transactions").insert(new_records).execute()

            st.success(f"Inserted {len(new_records)} new transactions.")
            st.warning(f"Skipped {len(possible_duplicates)} possible duplicates.")


# =========================
# Budget Goals
# =========================

elif page == "Budget Goals":
    st.header("🎯 Budget Goals")

    st.subheader("Set Monthly Budget")

    with st.form("budget_goal_form"):
        category = st.selectbox(
            "Category",
            [
                "Food",
                "Transport",
                "Shopping",
                "Bills",
                "Entertainment",
                "Health",
                "Education",
                "Investment",
                "Others"
            ]
        )

        monthly_budget = st.number_input(
            "Monthly Budget (RM)",
            min_value=0.0,
            format="%.2f"
        )

        save_budget = st.form_submit_button(
            "Save Budget Goal",
            use_container_width=True
        )

        if save_budget:
            existing = budget_df[
                budget_df["category"] == category
            ] if not budget_df.empty else pd.DataFrame()

            if not existing.empty:
                goal_id = int(existing.iloc[0]["id"])

                update_budget_goal(goal_id, {
                    "monthly_budget": float(monthly_budget)
                })

                st.success(f"Updated {category} budget.")
            else:
                insert_budget_goal({
                    "category": category,
                    "monthly_budget": float(monthly_budget),
                    "user_id": user_id
                })

                st.success(f"Added {category} budget.")

            st.rerun()

    st.divider()

    st.subheader("Current Budget Goals")

    if budget_df.empty:
        st.info("No budget goals set yet.")
    else:
        display_budget_df = budget_df.copy()

        if "id" in display_budget_df.columns:
            display_budget_df = display_budget_df.drop(columns=["id"])

        if "user_id" in display_budget_df.columns:
            display_budget_df = display_budget_df.drop(columns=["user_id"])

        display_budget_df.insert(0, "No.", range(1, len(display_budget_df) + 1))

        st.dataframe(
            display_budget_df,
            use_container_width=True,
            hide_index=True
        )


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
        st.write("Click one row in the table, then edit or delete it.")

        display_df = get_display_df(db_df)

        selected_table = st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config=get_column_config()
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
            col2.metric("Type", normalize_transaction_type(selected_transaction["transaction_type"]).title())
            col3.metric("Category", selected_transaction["category"])

            st.write(f"**Description:** {selected_transaction['description']}")
            st.write(f"**Date:** {selected_transaction['transaction_date']}")

            payment_value = selected_transaction.get("payment_method", "")

            if pd.isna(payment_value):
                payment_value = ""

            if payment_value:
                st.write(f"**Payment Method:** {payment_value}")

            st.divider()
            st.subheader("Edit or Delete Transaction")

            with st.form("edit_delete_transaction_form"):
                edit_col1, edit_col2 = st.columns(2)

                with edit_col1:
                    edit_date = st.date_input(
                        "Date",
                        pd.to_datetime(selected_transaction["transaction_date"]).date()
                    )

                    edit_description = st.text_input(
                        "Description",
                        str(selected_transaction["description"])
                    )

                    edit_amount = st.number_input(
                        "Amount",
                        min_value=0.0,
                        value=float(selected_transaction["amount"]),
                        format="%.2f"
                    )

                with edit_col2:
                    current_type = normalize_transaction_type(
                        selected_transaction["transaction_type"]
                    )

                    edit_type = st.selectbox(
                        "Type",
                        ["income", "expense"],
                        index=["income", "expense"].index(current_type)
                    )

                    edit_category = st.text_input(
                        "Category",
                        str(selected_transaction["category"])
                    )

                    edit_payment_method = st.text_input(
                        "Payment Method",
                        str(payment_value)
                    )

                action_col1, action_col2 = st.columns(2)

                with action_col1:
                    save_edit = st.form_submit_button(
                        "Save Changes",
                        use_container_width=True,
                        type="primary"
                    )

                with action_col2:
                    delete_selected = st.form_submit_button(
                        "Delete Transaction",
                        use_container_width=True,
                        type="secondary"
                    )

                if save_edit:
                    updated_record = {
                        "transaction_date": str(edit_date),
                        "description": edit_description,
                        "amount": float(edit_amount),
                        "transaction_type": edit_type,
                        "category": edit_category,
                        "payment_method": edit_payment_method
                    }

                    update_transaction(selected_id, updated_record)
                    st.success("Transaction updated successfully.")
                    st.rerun()

                if delete_selected:
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