# =========================================================
# app_final.py — IG + FB Auto Reply 
# Dataset (if present) + AI Fallback + Google Sheet Logs
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
st.title("🤖 IG + Facebook Auto Reply System (Smart Dataset + AI)")

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
    st.session_state.dataset_cache = None  # None means dataset not loaded yet

# =========================================================
# LOAD DATASET IF UPLOADED
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
# REPLY LOGIC (CORE BRAIN)
# =========================================================
def get_reply(comment_text):
    text = f" {comment_text.lower().strip()} "

    # 1️⃣ If dataset exists → try dataset first
    if st.session_state.dataset_cache:
        for row in st.session_state.dataset_cache:
            if f" {row['keyword']} " in text:
                return row["reply"], "DATASET"
        
        # 2️⃣ dataset exists but no match → AI fallback
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
                return ai_res.choices[0].message.content.strip(), "AI FALLBACK"
            except:
                return "Thank you! 😊 Please DM us for details.", "AI ERROR"
        else:
            return "Thank you! 😊 Please DM us for details.", "NO AI KEY"

    # 3️⃣ If NO dataset uploaded → AI ONLY MODE
    if openai_client:
        try:
            ai_res = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Reply polite, helpful, short."},
                    {"role": "user", "content": comment_text},
                ],
                temperature=0.4,
            )
            return ai_res.choices[0].message.content.strip(), "AI ONLY"
        except:
            return "Thanks! 😊 DM for more details.", "AI ERROR"

    # 4️⃣ No AI + No dataset → safe fallback
    return "Thank you! 🙏 Message us for details.", "FALLBACK"


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
        st.warning("⚠️ Google Sheet Error — check service_account.json or sheet name")


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

    # 📌 INSTAGRAM
    if IG_POST_ID and IG_TOKEN:
        st.markdown("### 📸 Instagram Comments:")
        for c in fetch_ig().get("data", []):
            cid = c["id"]
            text = c.get("text","")
            user = c.get("username","Instagram_User")

            if cid in st.session_state.replied_ids or not text: continue
            
            reply, source = get_reply(text)

            if AUTO_IG == "ON":
                send_ig(cid, reply)
                st.session_state.replied_ids.add(cid)
                save_to_sheet("instagram", user, text, reply, source)
                st.success(f"📩 IG → ({source}) {reply}")
            else:
                st.warning(f"Preview ({source}) → {reply}")

    # 📌 FACEBOOK
    if FB_POST_ID and FB_TOKEN:
        st.markdown("### 📘 Facebook Comments:")
        for c in fetch_fb().get("data", []):
            cid = c["id"]
            text = c.get("message","")
            user = c.get("from",{}).get("name","Facebook_User")

            if cid in st.session_state.replied_ids or not text: continue
            
            reply, source = get_reply(text)

            if AUTO_FB == "ON":
                send_fb(cid, reply)
                st.session_state.replied_ids.add(cid)
                save_to_sheet("facebook", user, text, reply, source)
                st.success(f"📩 FB → ({source}) {reply}")
            else:
                st.warning(f"Preview ({source}) → {reply}")


# =========================================================
# GOOGLE SHEET PREVIEW
# =========================================================
st.subheader("📄 Last Logs (Google Sheet Preview)")
try:
    rows = get_sheet().get_all_values()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    st.dataframe(df.tail(20), use_container_width=True)
except:
    st.info("⚠️ Sheet not connected")

st.success("🚀 System Ready — Smart Auto Reply Active!")
