# =========================================================
# app2.py — Instagram Auto Reply System (FINAL WORKING)
# Keywords from COMMENT | Dataset OR OpenAI | Google Sheets
# =========================================================

import streamlit as st
import requests
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials
from openai import OpenAI

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(page_title="Instagram Auto Reply System", layout="wide")
st.title("🤖 Instagram Auto Reply System")

# =========================================================
# SIDEBAR
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
        ["Dataset + Keywords", "OpenAI (AI Reply)"]
    )

    AUTO_MODE = st.radio("Auto Reply", ["OFF", "ON"])

    DATASET_FILE = st.file_uploader(
        "Upload Dataset (TXT)",
        type=["txt"]
    )

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
# OPENAI CLIENT (AI MODE ONLY)
# =========================================================
openai_client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

# =========================================================
# DATASET PARSER
# Dataset format:
# keyword|reply text
# =========================================================
def load_dataset(file):
    rows = []
    if not file:
        return rows

    text = file.read().decode("utf-8", errors="ignore")
    for line in text.splitlines():
        if "|" in line:
            k, v = line.split("|", 1)
            rows.append({
                "keyword": k.strip().lower(),
                "reply": v.strip()
            })
    return rows

DATASET = load_dataset(DATASET_FILE)

# =========================================================
# GOOGLE SHEETS
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
        "reply_text",
        "reply_source",
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
        data["reply"],
        data["source"],
    ]
    get_sheet().append_row(row)

# =========================================================
# KEYWORD DETECTION (FROM COMMENT ONLY)
# =========================================================
def detect_keywords_from_comment(text):
    text = text.lower()
    found = []

    for row in DATASET:
        if row["keyword"] in text:
            found.append(row["keyword"])

    return list(dict.fromkeys(found))

# =========================================================
# DATASET REPLY
# =========================================================
def dataset_reply(text):
    text = text.lower()
    for row in DATASET:
        if row["keyword"] in text:
            return row["reply"]
    return "Thank you for your comment 😊 Please check your DM."

# =========================================================
# OPENAI REPLY
# =========================================================
def ai_reply(text, keywords):
    if not openai_client:
        return "Thank you for your comment 😊"

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Reply briefly and politely as an Instagram sales assistant."
            },
            {
                "role": "user",
                "content": f"Comment: {text}\nKeywords: {keywords}"
            }
        ],
        temperature=0.4
    )

    return response.choices[0].message.content.strip()

# =========================================================
# INSTAGRAM API
# =========================================================
def fetch_comments():
    url = f"https://graph.facebook.com/v19.0/{POST_ID}/comments"
    return requests.get(url, params={"access_token": PAGE_TOKEN}).json()


def send_reply(cid, msg):
    url = f"https://graph.facebook.com/v19.0/{cid}/replies"
    return requests.post(
        url,
        data={"message": msg, "access_token": PAGE_TOKEN}
    )

# =========================================================
# MAIN UI
# =========================================================
st.subheader("🔔 Live Comment Monitor")

if CHECK_NOW and POST_ID and PAGE_TOKEN:
    data = fetch_comments()

    for c in data.get("data", []):
        cid = c["id"]
        text = c.get("text", "")
        user = c.get("username", "instagram_user")

        if cid in st.session_state.replied_ids:
            continue

        st.info(f"💬 {text}")

        # 🔑 KEYWORDS SECTION
        keywords = detect_keywords_from_comment(text)
        st.caption(f"🔑 Detected Keywords: {keywords if keywords else 'None'}")

        if AUTO_MODE == "ON":

            if REPLY_MODE == "Dataset + Keywords":
                reply = dataset_reply(text)
                source = "dataset"
            else:
                reply = ai_reply(text, keywords)
                source = "openai"

            res = send_reply(cid, reply)

            if res.status_code == 200:
                save_to_sheet({
                    "user": user,
                    "comment": text,
                    "keywords": keywords,
                    "reply": reply,
                    "source": source,
                })

                st.session_state.live_logs.append({
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "comment": text,
                    "reply": reply,
                    "source": source,
                })

                st.session_state.replied_ids.add(cid)
                st.success(f"✅ Replied ({source}) → {reply}")

# =========================================================
# LIVE SESSION LOG
# =========================================================
st.subheader("📄 Live Reply Log (Current Session Only)")

if st.session_state.live_logs:
    st.dataframe(st.session_state.live_logs, use_container_width=True)
else:
    st.info("No replies yet.")

# =========================================================
# GOOGLE SHEET PREVIEW
# =========================================================
st.subheader("📊 Google Sheet Preview")

try:
    records = get_sheet().get_all_records()
    if records:
        st.dataframe(records[-20:], use_container_width=True)
    else:
        st.info("Google Sheet is empty.")
except Exception as e:
    st.error(e)
