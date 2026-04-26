import streamlit as st

st.set_page_config(page_title="Finance AI Agent", page_icon=":sparkles:", layout="centered")

st.title("Finance AI Agent")
st.write("Welcome to the Finance AI Agent! This application allows you to interact with an AI agent that can assist you with various financial tasks. You can ask questions, get insights, and receive recommendations related to finance.")

uploaded_file = st.file_uploader("Upload your financial data (CSV/XLSX)", type=["csv", "xlsx"])

user_prompt = st.text_input("Enter a Transaction with Amount and Reasoning (eg. Spent RM30 on Food)")

if uploaded_file:
    st.success("File uploaded successfully!")
if user_prompt:
    st.success("You have entered: " + user_prompt)