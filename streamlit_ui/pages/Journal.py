#file: streamlit_ui/pages/Journal.py
import streamlit as st
import requests
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Page Configuration ---
st.set_page_config(page_title="Journal – SoulScribe", layout="centered")

# --- Show JWT Token for testing ---
if "jwt_token" not in st.session_state:
    st.session_state.jwt_token = None
if not st.session_state.jwt_token:
    st.error("⚠️ You must be logged in to access the journal.")
    st.markdown("[🔐 Go to Login Page](login)")
    st.stop()

# --- Initialize Session ID if not already set ---
if "session_id" not in st.session_state or st.session_state.session_id is None:
    session_response = requests.post(
        "http://localhost:5050/session/create_session",
        headers={"Authorization": f"Bearer {st.session_state.jwt_token}"}
    )

    if session_response.status_code == 200:
        st.session_state.session_id = session_response.json()["session_id"]
    else:
        st.error("⚠️ Failed to initialize journaling session.")
        st.stop()

# --- Custom CSS ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600&display=swap');
        .stApp {
            background-color: #fefae0;
            color: #3c3c3c;
            font-family: 'Quicksand', sans-serif;
        }
        .title {
            text-align: center;
            font-size: 2.5rem;
            font-weight: 700;
            color: #b497d6;
            margin-bottom: 0.3rem;
        }
        .subtitle {
            text-align: center;
            font-size: 1rem;
            color: #7a6fa3;
            margin-bottom: 2rem;
        }
        .message-bubble {
            border-radius: 12px;
            padding: 12px 16px;
            margin: 10px 0;
            border: 1px solid #d3cce3;
            max-width: 90%;
            word-wrap: break-word;
        }
        .user {
            background-color: #fcd5ce;
            align-self: flex-end;
            margin-left: auto;
        }
        .soul {
            background-color: #d6e2e9;
            align-self: flex-start;
            margin-right: auto;
        }
        .stButton > button {
            background-color: #e0c3fc !important;
            color: #3c3c3c !important;
            font-weight: bold;
            border: none;
            border-radius: 10px;
            padding: 0.5rem 1.5rem;
        }
        .stButton > button:hover {
            background-color: #d1b3ff !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- UI Header ---
st.markdown("<div class='title'>📝 Journal Your Emotions</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Write what’s on your mind and let SoulScribe feel with you.</div>", unsafe_allow_html=True)

# --- Session State Initialization ---
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "last_emotions" not in st.session_state:
    st.session_state.last_emotions = []

# --- Show Existing Conversation ---
if st.session_state.conversation:
    st.markdown("---")
    st.markdown("### 🧵 Conversation so far:")
    for turn in st.session_state.conversation:
        role = turn.get("role")
        text = turn.get("text", "")
        bubble_class = "user" if role == "user" else "soul"
        role_label = "🧍‍♀️ You" if role == "user" else "🌈 SoulScribe"

        st.markdown(
            f"<div class='message-bubble {bubble_class}'><strong>{role_label}:</strong> {text}</div>",
            unsafe_allow_html=True
        )

# --- Show last emotions if available ---
if st.session_state.last_emotions:
    st.markdown("#### Predicted Emotions (latest):")
    st.markdown(f"`{', '.join(st.session_state.last_emotions)}`")

# --- Input Area ---
st.markdown("---")
st.markdown("#### Add a new journal entry...")
user_input = st.text_area("What's on your mind?", height=200, label_visibility="collapsed")

API_URL = "http://localhost:5050/predict"

# --- Submit Button ---
if st.button("Reflect with SoulScribe"):
    if not user_input.strip():
        st.warning("Please write something first.")
    else:
        with st.spinner("SoulScribe is reflecting..."):
            try:
                payload = {
                    "text": user_input,
                    "thread_id": st.session_state.thread_id,
                    "session_id": st.session_state.session_id  # ensure it's sent
                }

                headers = {
                    "Authorization": f"Bearer {st.session_state.jwt_token}"
                }

                response = requests.post(API_URL, json=payload, headers=headers)

                if response.status_code == 200:
                    result = response.json()

                    # Only update thread_id if it was not set before
                    if st.session_state.thread_id is None and result.get("thread_id"):
                        st.session_state.thread_id = result["thread_id"]

                    # Append user + soul messages
                    st.session_state.conversation.append({"role": "user", "text": user_input})
                    st.session_state.conversation.append({"role": "soul", "text": result.get("message", "")})
                    st.session_state.last_emotions = result.get("emotions", [])
                    st.rerun()
                else:
                    st.error(f"⚠️ SoulScribe error {response.status_code}: {response.text}")
            except Exception as e:
                st.error(f"❌ Network or server error: {e}")


# --- Start New Conversation Button ---
if st.button("🔁 End Conversation, Begin Anew"):
    st.session_state.conversation = []
    st.session_state.thread_id = None
    st.session_state.last_emotions = []
    st.rerun()
