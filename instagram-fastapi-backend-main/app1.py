import streamlit as st
import requests
import csv
import os
from datetime import datetime
from openai import OpenAI

# =========================
# PAGE SETUP
# =========================
st.set_page_config(page_title="Instagram Auto Reply System", layout="wide")
st.title("🤖 Instagram Auto Reply System (Stable & Live)")

# =========================
# SIDEBAR SETTINGS
# =========================
with st.sidebar:
    st.header("⚙️ Settings")

    POST_ID = st.text_input("Instagram Post ID")
    PAGE_TOKEN = st.text_input("Instagram Page Access Token", type="password")
    IG_BUSINESS_ID = st.text_input("Instagram Business ID")
    OPENAI_KEY = st.text_input("OpenAI API Key", type="password")

    REPLY_SOURCE = st.radio(
        "Reply Source",
        ["OpenAI (AI Reply)", "Dataset (Rules Reply)"]
    )

    AUTO_MODE = st.radio("Auto Reply", ["OFF", "ON"])

    st.markdown("---")
    CHECK_NOW = st.button("🔄 Check New Comments")

# =========================
# CONFIG
# =========================
LOG_FILE = "autoreply_log.csv"

client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

# =========================
# INIT LOG FILE
# =========================
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Time",
            "Post ID",
            "Username",
            "Comment",
            "Reply",
            "Comment ID",
            "Source"
        ])

# =========================
# SESSION STATE
# =========================
if "replied_ids" not in st.session_state:
    st.session_state.replied_ids = set()

# =========================
# FUNCTIONS (SAFE)
# =========================
def fetch_comments():
    try:
        url = f"https://graph.facebook.com/v19.0/{POST_ID}/comments"
        params = {"access_token": PAGE_TOKEN}
        r = requests.get(url, params=params, timeout=5)
        return r.json()
    except requests.exceptions.Timeout:
        return {"error": "timeout"}
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
    except:
        return None

def ai_reply(text):
    if not client:
        return "Thank you for your comment 😊"

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional Instagram assistant. "
                    "Reply briefly, politely, and guide to DM if details are needed."
                )
            },
            {"role": "user", "content": text}
        ],
        temperature=0.4
    )
    return res.choices[0].message.content.strip()

def dataset_reply(text):
    t = text.lower()
    if "price" in t or "cost" in t:
        return "Please check your inbox for pricing details 📩"
    if "location" in t:
        return "Location details have been sent via DM 📍"
    if "available" in t:
        return "Yes, it’s available 😊 Please check DM."
    return "Thank you for your comment! Please check your DM 😊"

def log_reply(username, comment, reply, cid, source):
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            POST_ID,
            username,
            comment,
            reply,
            cid,
            source
        ])

# =========================
# MAIN SECTION
# =========================
st.subheader("🔔 Live Comment Monitor")

if not POST_ID or not PAGE_TOKEN:
    st.warning("Please enter Post ID and Page Access Token.")
elif CHECK_NOW:
    data = fetch_comments()

    if "error" in data:
        st.warning("⏳ Instagram API is slow. Please try again.")
    elif "data" in data and len(data["data"]) > 0:
        for c in data["data"]:
            cid = c.get("id")
            text = c.get("text", "")
            username = c.get("username", "instagram_user")

            if cid in st.session_state.replied_ids:
                continue

            st.info(f"💬 New Comment: {text}")

            if AUTO_MODE == "ON":
                if REPLY_SOURCE == "OpenAI (AI Reply)":
                    reply = ai_reply(text)
                    source = "OpenAI"
                else:
                    reply = dataset_reply(text)
                    source = "Dataset"

                res = send_reply(cid, reply)

                if res and res.status_code == 200:
                    st.success(f"✅ Replied ({source}) → {reply}")
                    log_reply(username, text, reply, cid, source)
                    st.session_state.replied_ids.add(cid)
                else:
                    st.error("❌ Failed to send reply")
            else:
                st.warning("Auto Reply is OFF")
    else:
        st.info("No new comments found.")

# =========================
# LOG VIEW
# =========================
st.subheader("📄 Reply Log")

if os.path.exists(LOG_FILE):
    with open(LOG_FILE, encoding="utf-8") as f:
        rows = list(csv.reader(f))
        st.dataframe(rows[1:], use_container_width=True)
