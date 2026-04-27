import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
from database.supabase_client import supabase

st.set_page_config(page_title="Finance Agent AI", layout="wide")

st.title("💰 Finance Agent AI")

st.write("Upload your bank statement and save transactions into Supabase.")

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