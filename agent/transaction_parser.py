import json
import re
import ollama
from datetime import date, datetime, timedelta


ALLOWED_CATEGORIES = [
    "Food",
    "Transport",
    "Salary",
    "Shopping",
    "Bills",
    "Entertainment",
    "Health",
    "Education",
    "Investment",
    "Transfer",
    "Others"
]


def extract_json_from_text(text: str):
    match = re.search(r"\{.*\}", text, re.DOTALL)

    if not match:
        raise ValueError(f"No JSON found in model response: {text}")

    return match.group(0)


def extract_amount_from_text(user_text: str):
    text = user_text.replace(",", "")

    patterns = [
        r"(?:RM|rm|Rm|rM)\s*(\d+(?:\.\d{1,2})?)",
        r"(\d+(?:\.\d{1,2})?)\s*(?:RM|rm|Rm|rM)",
        r"\b(\d+(?:\.\d{1,2})?)\b"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return float(match.group(1))

    return 0.0


def detect_transaction_type(user_text: str):
    text = user_text.lower()

    income_keywords = [
        "salary", "income", "earned", "received", "got paid",
        "allowance", "bonus", "refund", "cashback", "commission"
    ]

    expense_keywords = [
        "spent", "bought", "paid", "pay", "purchase", "ordered",
        "grab", "food", "lunch", "dinner", "breakfast", "coffee"
    ]

    if any(word in text for word in income_keywords):
        return "income"

    if any(word in text for word in expense_keywords):
        return "expense"

    return "expense"


def detect_payment_method(user_text: str):
    text = user_text.lower()

    payment_map = {
        "touch and go": "Touch n Go",
        "tng": "Touch n Go",
        "grabpay": "GrabPay",
        "grab pay": "GrabPay",
        "duitnow": "DuitNow",
        "credit card": "Credit Card",
        "debit card": "Debit Card",
        "cash": "Cash",
        "bank transfer": "Bank Transfer"
    }

    for keyword, value in payment_map.items():
        if keyword in text:
            return value

    return ""


def detect_category(user_text: str, ai_category: str = "Others"):
    text = user_text.lower()

    category_rules = {
        "Food": ["lunch", "dinner", "breakfast", "food", "coffee", "tea", "milk tea", "restaurant", "mcd", "kfc", "grabfood"],
        "Transport": ["petrol", "fuel", "grab", "taxi", "bus", "train", "parking", "toll"],
        "Salary": ["salary", "payday", "income", "bonus", "commission"],
        "Shopping": ["shirt", "bag", "shoes", "clothes", "shopping", "lazada", "shopee"],
        "Bills": ["bill", "electric", "water", "wifi", "internet", "phone", "rent", "subscription"],
        "Entertainment": ["movie", "cinema", "netflix", "spotify", "game"],
        "Health": ["clinic", "doctor", "medicine", "pharmacy", "gym"],
        "Education": ["book", "course", "tuition", "exam"],
        "Investment": ["stock", "crypto", "investment", "dividend"],
        "Transfer": ["transfer"]
    }

    for category, keywords in category_rules.items():
        if any(keyword in text for keyword in keywords):
            return category

    if ai_category in ALLOWED_CATEGORIES:
        return ai_category

    return "Others"


def clean_description(user_text: str, parsed_description: str = ""):
    text = user_text.lower()

    description_rules = {
        "milk tea": "Milk Tea",
        "lunch": "Lunch",
        "dinner": "Dinner",
        "breakfast": "Breakfast",
        "coffee": "Coffee",
        "petrol": "Petrol",
        "fuel": "Petrol",
        "salary": "Salary",
        "netflix": "Netflix",
        "spotify": "Spotify",
        "rent": "Rent",
        "gym": "Gym",
    }

    for keyword, desc in description_rules.items():
        if keyword in text:
            return desc

    if parsed_description and parsed_description.strip():
        return parsed_description.strip().title()

    return "General Transaction"


def normalize_date(ai_date):
    today = date.today()

    if not ai_date:
        return str(today)

    try:
        return str(datetime.strptime(ai_date, "%Y-%m-%d").date())
    except Exception:
        return str(today)


def parse_transaction_text(user_text: str):
    today = str(date.today())

    amount = extract_amount_from_text(user_text)
    transaction_type = detect_transaction_type(user_text)
    payment_method = detect_payment_method(user_text)

    prompt = f"""
    You are a finance transaction extraction engine.

    Your task:
    Extract exactly ONE personal finance transaction from the user's text.

    User text:
    "{user_text}"

    Today's date:
    {today}

    Return ONLY valid JSON.
    Do not include explanation.
    Do not include markdown.
    Do not wrap the JSON in ```json.
    Do not add comments.

    Required JSON format:
    {{
    "transaction_date": "{today}",
    "description": "short item or merchant name",
    "category": "Others"
    }}

    Date rules:
    1. transaction_date must always be valid ISO format: YYYY-MM-DD.
    2. If the user says "today", use: {today}.
    3. If the user gives no date, use: {today}.
    4. If the date is unclear, use: {today}.
    5. Never return words like "end", "tomorrow", "yesterday", "next week", or "unknown" inside transaction_date.
    6. Never return invalid dates.

    Description rules:
    1. Use a short clean description.
    2. Prefer the purchased item or income source.
    3. Do not include payment method in description.
    4. Do not include amount in description.
    5. Do not include date in description.
    6. Examples:
    - "spent RM15 for lunch using GrabPay" → "Lunch"
    - "bought milk tea for RM12.50" → "Milk Tea"
    - "received RM4000 salary" → "Salary"
    - "paid RM80 petrol with credit card" → "Petrol"

    Category rules:
    Choose exactly one category from this list:
    {", ".join(ALLOWED_CATEGORIES)}

    Category examples:
    - Food: lunch, dinner, breakfast, coffee, tea, milk tea, restaurant, cafe, groceries, GrabFood
    - Transport: petrol, fuel, toll, parking, Grab ride, taxi, bus, train, MRT, LRT
    - Salary: salary, payroll, wage, bonus, commission, allowance
    - Shopping: clothes, shoes, bag, Shopee, Lazada, electronics, accessories
    - Bills: rent, electricity, water, internet, phone bill, insurance, subscription
    - Entertainment: movie, cinema, Netflix, Spotify, games, concert
    - Health: clinic, hospital, doctor, medicine, pharmacy, gym
    - Education: course, book, tuition, exam, university, certification
    - Investment: stock, ETF, crypto, dividend, interest
    - Transfer: transfer to friend, bank transfer, DuitNow transfer
    - Others: use only if none of the above clearly match

    Important:
    - Do not guess extra details.
    - Do not create multiple transactions.
    - Do not return amount, transaction_type, or payment_method.
    - Python code will handle amount, transaction_type, and payment_method separately.
    """

    try:
        response = ollama.chat(
            model="phi3",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response["message"]["content"].strip()
        json_text = extract_json_from_text(content)
        parsed = json.loads(json_text)

    except Exception:
        parsed = {}

    final_result = {
        "transaction_date": normalize_date(parsed.get("transaction_date")),
        "description": clean_description(user_text, parsed.get("description", "")),
        "amount": amount,
        "transaction_type": transaction_type,
        "category": detect_category(user_text, parsed.get("category", "Others")),
        "payment_method": payment_method
    }

    return final_result