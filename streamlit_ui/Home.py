#file: streamlit_ui/Home.py
import streamlit as st

# --- Page Config ---
st.set_page_config(page_title="Home – SoulScribe", layout="centered")

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
            font-size: 2.8rem;
            font-weight: 700;
            color: #b497d6;
            margin-bottom: 0.2rem;
        }

        .subtitle {
            text-align: center;
            font-size: 1.15rem;
            color: #7a6fa3;
            margin-bottom: 2rem;
        }

        .section-title {
            font-size: 1.4rem;
            color: #a084ca;
            margin-top: 2.5rem;
            margin-bottom: 0.4rem;
            font-weight: 600;
        }

        .info-box {
            background: linear-gradient(135deg, #f7f2ff, #fffaf2);
            padding: 1.3rem 1.5rem;
            border-radius: 14px;
            border: 1px solid #d3cce3;
            box-shadow: 0 3px 8px rgba(176, 157, 220, 0.1);
            line-height: 1.7;
            font-size: 1.03rem;
        }

        .emoji {
            font-size: 1.2rem;
            margin-right: 0.3rem;
        }
    </style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown("<div class='title'>🕊️ Welcome to SoulScribe</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Your quiet space for reflection, healing, and emotional clarity.</div>", unsafe_allow_html=True)

# --- What is SoulScribe ---
st.markdown("<div class='section-title'>💡 What is SoulScribe?</div>", unsafe_allow_html=True)
st.markdown("""
<div class="info-box">
SoulScribe is your emotionally intelligent journaling companion. Whether you’re feeling overwhelmed, joyful, uncertain, or lost — SoulScribe listens with care and responds with empathy.

It helps you process your thoughts, reflect on your emotions, and gently reconnect with yourself.
</div>
""", unsafe_allow_html=True)

# --- What You Can Do Now ---
st.markdown("<div class='section-title'>✨ What You Can Do Now</div>", unsafe_allow_html=True)
st.markdown("""
<div class="info-box">
✅ Emotion-aware journaling with natural language entries<br>
✅ Insightful, emotionally fluent AI reflections<br>
✅ Threaded memory across sessions for meaningful continuity<br>
✅ Full timeline of past entries with emotional feedback<br>
✅ Visual emotion tracking and trend analysis across sessions<br>
✅ Smart detection of emotional arcs — including red zone alerts when needed
</div>
""", unsafe_allow_html=True)

# --- Start Journaling ---
# --- Start Journey ---
st.markdown("<div class='section-title'>🚀 Ready to Begin?</div>", unsafe_allow_html=True)
st.markdown("""
<div class="info-box">
Start by heading to the <strong>“Login”</strong> tab in the sidebar.<br>
Once you're signed in, you'll be able to:
<ul>
  <li>Start your journaling sessions</li>
  <li>Explore your emotional timeline</li>
  <li>Track patterns and trends with smart visualizations</li>
</ul>
Your journey begins with a single click 💫
</div>
""", unsafe_allow_html=True)
