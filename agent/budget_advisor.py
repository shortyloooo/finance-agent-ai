import ollama

def generate_budget_advice(total_income, total_expense, balance, category_summary):
    category_text = category_summary.head(10).to_string(index=False)
    prompt = f"""
You are a personal budgeting assistant.

Finance summary:
- Total income: RM {total_income:.2f}
- Total expense: RM {total_expense:.2f}
- Balance: RM {balance:.2f}

Spending by category:
{category_text}

Give practical budgeting advice in simple bullet points.
Avoid investment advice.
"""

    response = ollama.chat(
        model="phi3",
        messages=[
            {"role": "user", "content": prompt}
        ],
        stream=False
    )

    return response["message"]["content"]