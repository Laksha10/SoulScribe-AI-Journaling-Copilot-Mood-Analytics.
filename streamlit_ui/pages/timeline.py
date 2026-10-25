#file: streamlit_ui/pages/timeline.py
import sys
import os
import streamlit as st
import requests
import html
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
load_dotenv()

API_URL = "http://localhost:5050/timeline"

# --- Auth Check ---
if "jwt_token" not in st.session_state or not st.session_state.jwt_token:
    st.error("⚠️ You must be logged in to view your timeline.")
    st.stop()

# --- Page Config ---
st.set_page_config(page_title="🧭 Emotion Timeline", layout="centered")

# --- Custom Styles ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600&display=swap');
    .stApp {
        background-color: #fefae0;
        color: #3c3c3c;
        font-family: 'Quicksand', sans-serif;
    }
    h1, h2, h3 {
        color: #b497d6;
    }
    .entry-bubble {
        background-color: #fffaf2;
        border-left: 5px solid #d3cce3;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
    }
    .user {
        background-color: #fcd5ce;
    }
    .soul {
        background-color: #d6e2e9;
    }
    .timestamp {
        font-size: 0.85rem;
        color: #777;
        margin-top: 0.5rem;
    }
    .entry-bubble div {
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Page Header ---
st.markdown("<h1>🧭 Emotion Timeline</h1>", unsafe_allow_html=True)

# --- Fetch & Render Timeline ---
try:
    headers = {"Authorization": f"Bearer {st.session_state.jwt_token}"}
    response = requests.get(API_URL, headers=headers)

    if response.status_code != 200:
        st.error(f"Failed to load timeline: {response.text}")
    else:
        timeline_data = response.json()

        if not timeline_data:
            st.info("No journal threads yet. Entries will appear here as you reflect with SoulScribe.")
        else:
            for thread in timeline_data:
                thread_number = thread.get("user_thread_number", thread["thread_id"])
                session_number = thread.get("user_session_number", "–")

                st.markdown(f"<h3>🌱 Thread {thread_number} (Session {session_number})</h3>", unsafe_allow_html=True)

                for entry in thread["entries"]:
                    role = entry["role"]
                    text = entry["text"] if role == "user" else entry.get("reflection", "")
                    safe_text = html.escape(text)

                    emotions = entry.get("predicted_emotions", [])
                    if isinstance(emotions, str):
                        try:
                            emotions = eval(emotions)
                        except:
                            emotions = emotions.strip("[]").replace("'", "").split(",")
                    emotion_str = ", ".join([e.strip() for e in emotions if e.strip()])

                    bubble_class = "user" if role == "user" else "soul"
                    role_label = "🧍‍♀️ You" if role == "user" else "🌈 SoulScribe"

                    st.markdown(f"""
                        <div class="entry-bubble {bubble_class}">
                            <strong>{role_label}:</strong>
                            <div>{safe_text}</div>
                            <div class="timestamp">🕒 {entry["timestamp"]} | 🫀 <em>{emotion_str}</em></div>
                        </div>
                    """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"❌ Error loading timeline: {e}")
