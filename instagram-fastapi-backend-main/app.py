# =========================================================
# app_final.py — IG + FB Auto Reply 
# Dataset + Keyword Detection + AI Fallback + Google Sheet Logs
# NOW SHOWS DETECTED KEYWORDS BELOW REPLY
# =========================================================

import streamlit as st
import requests
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from openai import OpenAI
import pandas as pd

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(page_title="IG + Facebook Auto Reply", layout="wide")
st.title("🤖 IG + Facebook Auto Reply System (Smart Keyword + Dataset + AI)")

# =========================================================
# SIDEBAR SETTINGS
# =========================================================
with st.sidebar:
    st.header("📸 Instagram Setup")
    IG_POST_ID = st.text_input("Instagram Post ID")
    IG_TOKEN = st.text_input("Instagram Access Token", type="password")

    st.header("📘 Facebook Setup")
    FB_POST_ID = st.text_input("Facebook Post ID")
    FB_TOKEN = st.text_input("Facebook Page Token", type="password")

    st.header("📄 Dataset (keyword|reply)")
    DATASET_FILE = st.file_uploader("Upload Dataset .txt", type=["txt"])

    st.header("🧠 AI Settings")
    OPENAI_KEY = st.text_input("OpenAI API Key", type="password")

    st.header("📊 Google Sheet Setup")
    GOOGLE_SHEET_NAME = st.text_input("Sheet Name", value="LEAD AGENTE RRSS HBH")

    st.header("⚡ Auto Reply Mode")
    AUTO_IG = st.radio("Instagram Auto Reply", ["ON", "OFF"])
    AUTO_FB = st.radio("Facebook Auto Reply", ["ON", "OFF"])

    CHECK_NOW = st.button("🔄 RUN SYSTEM")

# =========================================================
# SESSION MEMORY
# =========================================================
if "replied_ids" not in st.session_state:
    st.session_state.replied_ids = set()

if "dataset_cache" not in st.session_state:
    st.session_state.dataset_cache = None

# =========================================================
# BUILT-IN KEYWORD DETECTION (NEW)
# =========================================================
KEYWORDS = {
    "price": "Thank you! 😊 Our pricing depends on service type. Can I send details in inbox?",
    "cost": "Thanks for asking! Our cost depends on requirements. Shall I DM you full details?",
    "location": "We operate globally 🌍 — Where are you located? I can guide you!",
    "help": "Of course! I'm here to help. Tell me what you need 😊",
    "info": "Sure! I can share more info. Shall I send it to your inbox?"
}

# =========================================================
# LOAD DATASET
# =========================================================
def load_dataset(file):
    if not file:
        st.session_state.dataset_cache = None
        return None
    text = file.read().decode("utf-8", errors="ignore").lower()
    dataset = []
    for line in text.splitlines():
        if "|" in line:
            k, v = line.split("|", 1)
            dataset.append({"keyword": k.strip(), "reply": v.strip()})
    st.session_state.dataset_cache = dataset
    return dataset

DATASET = load_dataset(DATASET_FILE)

# =========================================================
# AI CLIENT
# =========================================================
openai_client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

# =========================================================
# REPLY LOGIC (NOW RETURNS KEYWORDS DETECTED)
# =========================================================
def get_reply(comment_text):
    text = f" {comment_text.lower().strip()} "
    
    detected = []  # <--- COLLECT MATCHED KEYWORDS

    # 0️⃣ Check Built-In Keywords
    for k, v in KEYWORDS.items():
        if k in text:
            detected.append(k)
            reply = v
            return reply, "KEYWORD MATCH", detected

    # 1️⃣ Dataset Check
    if st.session_state.dataset_cache:
        for row in st.session_state.dataset_cache:
            if f" {row['keyword']} " in text:
                detected.append(row['keyword'])
                return row["reply"], "DATASET", detected
        
        # 2️⃣ Dataset No Match → AI Fallback
        if openai_client:
            try:
                ai_res = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Reply polite, short, human tone."},
                        {"role": "user", "content": comment_text},
                    ],
                    temperature=0.4,
                )
                return ai_res.choices[0].message.content.strip(), "AI FALLBACK", detected
            except:
                return "Thank you! 😊 Please DM us for details.", "AI ERROR", detected
        else:
            return "Thank you! 😊 Please DM us for details.", "NO AI KEY", detected

    # 3️⃣ AI ONLY MODE
    if openai_client:
        try:
            ai_res = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Reply polite, short."},
                    {"role": "user", "content": comment_text},
                ],
                temperature=0.4,
            )
            return ai_res.choices[0].message.content.strip(), "AI ONLY", detected
        except:
            return "Thanks! 😊 DM for more details.", "AI ERROR", detected

    # 4️⃣ No AI + No dataset → fallback
    return "Thank you! 🙏 Message us for details.", "FALLBACK", detected

# =========================================================
# GOOGLE SHEET
# =========================================================
SERVICE_ACCOUNT_FILE = "service_account.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
_sheet_cache = None

def get_sheet():
    global _sheet_cache
    if _sheet_cache: return _sheet_cache
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    sh = gspread.authorize(creds).open(GOOGLE_SHEET_NAME)
    _sheet_cache = sh.sheet1
    return _sheet_cache

def save_to_sheet(platform, user, comment, reply, source):
    row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), platform, user, comment, reply, source]
    try:
        get_sheet().append_row(row)
    except:
        st.warning("⚠️ Google Sheet Error — check credentials or name")

# =========================================================
# API CALLS
# =========================================================
def fetch_ig(): return requests.get(f"https://graph.facebook.com/v20.0/{IG_POST_ID}/comments", params={"access_token": IG_TOKEN}).json()
def fetch_fb(): return requests.get(f"https://graph.facebook.com/v20.0/{FB_POST_ID}/comments", params={"access_token": FB_TOKEN}).json()

def send_ig(cid, msg): return requests.post(f"https://graph.facebook.com/v20.0/{cid}/replies", data={"message":msg,"access_token":IG_TOKEN})
def send_fb(cid, msg): return requests.post(f"https://graph.facebook.com/v20.0/{cid}/comments", data={"message":msg,"access_token":FB_TOKEN})

# =========================================================
# MAIN EXECUTION
# =========================================================
st.subheader("🔔 Live Running...")

if CHECK_NOW:
    
    # 📸 INSTAGRAM
    if IG_POST_ID and IG_TOKEN:
        st.markdown("### 📸 Instagram Comments:")
        for c in fetch_ig().get("data", []):
            cid = c["id"]
            text = c.get("text","")
            user = c.get("username","Instagram_User")

            if cid in st.session_state.replied_ids or not text: continue
            reply, source, detected = get_reply(text)

            if AUTO_IG == "ON":
                send_ig(cid, reply)
                st.session_state.replied_ids.add(cid)
                save_to_sheet("instagram", user, text, reply, source)
                st.success(f"📩 IG → ({source}) {reply}")
            else:
                st.warning(f"Preview ({source}) → {reply}")

            # 🔍 SHOW DETECTED KEYWORDS
            st.write(f"**Keywords Detected:** {', '.join(detected) if detected else 'None'}")

    # 📘 FACEBOOK
    if FB_POST_ID and FB_TOKEN:
        st.markdown("### 📘 Facebook Comments:")
        for c in fetch_fb().get("data", []):
            cid = c["id"]
            text = c.get("message","")
            user = c.get("from",{}).get("name","Facebook_User")

            if cid in st.session_state.replied_ids or not text: continue
            reply, source, detected = get_reply(text)

            if AUTO_FB == "ON":
                send_fb(cid, reply)
                st.session_state.replied_ids.add(cid)
                save_to_sheet("facebook", user, text, reply, source)
                st.success(f"📩 FB → ({source}) {reply}")
            else:
                st.warning(f"Preview ({source}) → {reply}")

            # 🔍 SHOW DETECTED KEYWORDS
            st.write(f"**Keywords Detected:** {', '.join(detected) if detected else 'None'}")

# =========================================================
# SHEET PREVIEW
# =========================================================
st.subheader("📄 Last Logs (Google Sheet Preview)")
try:
    rows = get_sheet().get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    st.dataframe(df.tail(20), use_container_width=True)
except:
    st.info("⚠️ Sheet not connected")

st.success("🚀 System Ready — Keyword Detection + Display Enabled!")
