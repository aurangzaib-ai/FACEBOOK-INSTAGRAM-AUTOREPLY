# =========================================================
# app2.py — Instagram Auto Reply System
# Live Session Logs + Google Sheets (Permanent)
# =========================================================

import streamlit as st
import requests
from datetime import datetime

# Google Sheets
import gspread
from google.oauth2.service_account import Credentials

# OpenAI
from openai import OpenAI

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(page_title="Instagram Auto Reply System", layout="wide")
st.title("🤖 Instagram Auto Reply System")

# =========================================================
# SIDEBAR CONFIG
# =========================================================
with st.sidebar:
    st.header("⚙️ Configuration")

    POST_ID = st.text_input("Instagram Post ID")
    PAGE_TOKEN = st.text_input("Instagram Page Access Token", type="password")
    OPENAI_KEY = st.text_input("OpenAI API Key", type="password")

    GOOGLE_SHEET_NAME = st.text_input(
        "Google Sheet Name",
        value="LEAD AGENTE RRSS HBH"
    )

    REPLY_MODE = st.radio(
        "Reply Mode",
        ["OpenAI (AI Reply)", "Dataset + Keywords"]
    )

    AUTO_MODE = st.radio("Auto Reply", ["OFF", "ON"])

    DATASET_FILE = st.file_uploader(
        "Upload Dataset (TXT)",
        type=["txt"]
    )

    st.markdown("---")
    CHECK_NOW = st.button("🔄 Check New Comments")

# =========================================================
# GLOBAL CONFIG
# =========================================================
SERVICE_ACCOUNT_FILE = "service_account.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# =========================================================
# SESSION STATE
# =========================================================
if "replied_ids" not in st.session_state:
    st.session_state.replied_ids = set()

if "live_logs" not in st.session_state:
    st.session_state.live_logs = []

# =========================================================
# OPENAI CLIENT
# =========================================================
openai_client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

# =========================================================
# DATASET READER
# =========================================================
def read_dataset(file):
    if not file:
        return ""
    return file.read().decode("utf-8", errors="ignore")

DATASET_TEXT = read_dataset(DATASET_FILE)

# =========================================================
# GOOGLE SHEETS (CACHED)
# =========================================================
_cached_sheet = None

def get_sheet():
    global _cached_sheet
    if _cached_sheet:
        return _cached_sheet

    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sh = client.open(GOOGLE_SHEET_NAME)
    _cached_sheet = sh.sheet1
    return _cached_sheet


def ensure_headers():
    headers = [
        "timestamp",
        "platform",
        "user_handle",
        "comment_text",
        "detected_keywords",
        "intent_group",
        "lead_score",
        "priority_level",
        "reply_text",
        "reply_source",
        "email",
        "phone",
    ]

    sheet = get_sheet()
    if not sheet.row_values(1):
        sheet.insert_row(headers, 1)


def save_to_sheet(data):
    ensure_headers()

    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "instagram",
        data["user"],
        data["comment"],
        ", ".join(data["keywords"]),
        data["intent"],
        data["score"],
        data["priority"],
        data["reply"],
        data["source"],
        data.get("email", ""),
        data.get("phone", ""),
    ]

    get_sheet().append_row(row)

# =========================================================
# KEYWORD ENGINE
# =========================================================
KEYWORD_MAP = {
    "pricing": {
        "keywords": ["price", "cost", "rate", "charges"],
        "intent": "pricing",
        "score": 90,
        "priority": "hot",
    },
    "availability": {
        "keywords": ["available", "in stock", "ready"],
        "intent": "availability",
        "score": 80,
        "priority": "warm",
    },
    "contact": {
        "keywords": ["contact", "number", "call", "whatsapp", "phone"],
        "intent": "contact",
        "score": 85,
        "priority": "hot",
    },
    "location": {
        "keywords": ["location", "address", "where"],
        "intent": "location",
        "score": 70,
        "priority": "warm",
    },
}

def detect_keywords(text):
    text = text.lower()
    found = []
    for data in KEYWORD_MAP.values():
        for kw in data["keywords"]:
            if kw in text:
                found.append(kw)
    return found


def detect_intent(keywords):
    for intent, data in KEYWORD_MAP.items():
        for kw in data["keywords"]:
            if kw in keywords:
                return data["intent"], data["score"], data["priority"]
    return "general", 50, "cold"

# =========================================================
# REPLY GENERATION
# =========================================================
def generate_reply(comment, keywords):
    if REPLY_MODE == "Dataset + Keywords" and DATASET_TEXT:
        system_prompt = f"""
You must answer ONLY using the dataset below.
If information is missing, politely guide the user to DM.

DATASET:
{DATASET_TEXT}
"""
        source = "dataset"
    else:
        system_prompt = (
            "You are a professional Instagram sales assistant. "
            "Reply briefly, politely, and guide the user to DM."
        )
        source = "openai"

    if not openai_client:
        return "Thank you for your comment 😊", source

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""
Comment: {comment}
Detected Keywords: {keywords}
Generate a short Instagram reply.
"""
            }
        ],
        temperature=0.4
    )

    return response.choices[0].message.content.strip(), source

# =========================================================
# INSTAGRAM API
# =========================================================
def fetch_comments():
    try:
        url = f"https://graph.facebook.com/v19.0/{POST_ID}/comments"
        return requests.get(url, params={"access_token": PAGE_TOKEN}, timeout=5).json()
    except Exception:
        return {"error": "network"}


def send_reply(comment_id, message):
    try:
        url = f"https://graph.facebook.com/v19.0/{comment_id}/replies"
        return requests.post(
            url,
            data={"message": message, "access_token": PAGE_TOKEN},
            timeout=5
        )
    except Exception:
        return None

# =========================================================
# MAIN UI
# =========================================================
st.subheader("🔔 Live Comment Monitor")

if not POST_ID or not PAGE_TOKEN:
    st.warning("Post ID and Page Access Token are required.")

elif CHECK_NOW:
    data = fetch_comments()

    if "data" not in data:
        st.error("Instagram API error.")
    elif not data["data"]:
        st.info("No new comments found.")
    else:
        for c in data["data"]:
            cid = c.get("id")
            text = c.get("text", "")
            user = c.get("username", "instagram_user")

            if cid in st.session_state.replied_ids:
                continue

            st.info(f"💬 {text}")

            keywords = detect_keywords(text)
            intent, score, priority = detect_intent(keywords)

            if AUTO_MODE == "ON":
                reply, source = generate_reply(text, keywords)
                res = send_reply(cid, reply)

                if res and res.status_code == 200:
                    save_to_sheet({
                        "user": user,
                        "comment": text,
                        "keywords": keywords,
                        "intent": intent,
                        "score": score,
                        "priority": priority,
                        "reply": reply,
                        "source": source,
                    })

                    st.session_state.live_logs.append({
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "user": user,
                        "comment": text,
                        "reply": reply,
                        "source": source,
                    })

                    st.session_state.replied_ids.add(cid)
                    st.success(f"✅ Replied → {reply}")
                else:
                    st.error("❌ Failed to send reply.")
            else:
                st.warning("Auto reply is OFF.")

# =========================================================
# LIVE SESSION LOG
# =========================================================
st.subheader("📄 Live Reply Log (Current Session Only)")

if st.session_state.live_logs:
    st.dataframe(st.session_state.live_logs, use_container_width=True)
else:
    st.info("No replies sent in this session yet.")

# =========================================================
# GOOGLE SHEET PREVIEW
# =========================================================
st.subheader("📊 Google Sheet Preview (Latest Leads)")

try:
    records = get_sheet().get_all_records()
    if records:
        st.dataframe(records[-20:], use_container_width=True)
    else:
        st.info("Google Sheet is empty.")
except Exception as e:
    st.error(f"Unable to load Google Sheet preview: {e}")
