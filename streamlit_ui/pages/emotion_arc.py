#file: streamlit_ui/pages/emotion_arc.py
# 🔸 EMOTIONAL ARC PAGE
import os
import streamlit as st
import requests
import plotly.graph_objects as go
import numpy as np
from collections import Counter
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5050")
# --- Page Setup ---
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center;">
    <h1 style="margin: 0;">🎢 Emotional Arc</h1>
</div>
""", unsafe_allow_html=True)
st.markdown("""
<p style="font-size: 16px; font-weight: 600; color: #2E2E38; margin-top: 0rem;">
    Each session reveals a journey — let's see how your emotions evolved.
</p>
""", unsafe_allow_html=True)



# --- Custom CSS ---
st.markdown("""
    <style>
        .stApp {
            background-color: #fefae0;
            color: #1e1e1e;
        }
        
        .plot-container {
            background-color: #2E2E38;
            border: 2px solid #c084fc;
            border-radius: 15px;
            padding: 1.5rem;
            margin: 1rem;
            height: 100%;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .stPlotlyChart {
            flex-grow: 1;
        }
        .element-container > div {
            border-radius: 15px !important;
            overflow: hidden !important;
        }
        .explanation-bubble {
            padding: 1rem;
            border-radius: 10px;
            margin: 1rem 0 2rem 0;
            font-size: 0.95rem;
            color: #1e1e1e;
            min-height: 160px;
        }
        .bubble-left {
            background-color: #fcd5ce;
            border-left: 5px solid #ffafcc;
        }
        .bubble-right {
            background-color: #d6e2e9;
            border-left: 5px solid #b0c4de;
        }
        .legend-patch {
            display: inline-block;
            width: 12px;
            height: 12px;
            margin-right: 5px;
            border-radius: 2px;
        }
        .legend-container {
            float: right;
            margin-top: -40px;
        }
    </style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
div[data-testid="stSelectbox"] > label {
    color: #1e1e1e !important;  /* dark text */
    font-weight: 600;
    font-size: 18px;
}
</style>
""", unsafe_allow_html=True)

# --- Auth Check ---
if "jwt_token" not in st.session_state or not st.session_state.jwt_token:
    st.error("🔒 Please log in to view your emotional arc.")
    st.stop()

if "auth_token" not in st.session_state:
    st.session_state["auth_token"] = st.session_state.get("jwt_token", None)

st.markdown("### 🎭 Explore Your Emotional Patterns")

view_option = st.selectbox(
    "Choose what to explore:",
    ["Overall Emotional View", "Entry-Level View"],
    index=0,
    key="emotion_view_toggle"
)

# --- Backend API ---
API_ARC_URL = "http://localhost:5050/emotion_arc"
headers = {"Authorization": f"Bearer {st.session_state.jwt_token}"}

try:
    response = requests.get(API_ARC_URL, headers=headers)
    response.raise_for_status()
    sessions = response.json()
except Exception as e:
    st.error(f"❌ Could not fetch emotional arc: {e}")
    st.stop()

if not sessions:
    st.info("📭 No emotion data yet. Try journaling a few entries first!")
    st.stop()

POSITIVE_EMOTIONS = {"admiration", "amusement", "approval", "caring", "curiosity", "excitement", "gratitude", "joy", "love", "optimism", "pride", "relief"}
NEGATIVE_EMOTIONS = {"anger", "annoyance", "disappointment", "disapproval", "disgust", "embarrassment", "fear", "grief", "remorse", "sadness","confusion", "nervousness"}
NEUTRAL_EMOTIONS = {"desire","surprise", "realization"}

# === Net score calculation (for the scoreboard chart) ===
net_scores = []
for s in sessions:
    score = 0
    for entry in s["entry_emotions"]:
        for e in entry["emotions"]:
            if e in POSITIVE_EMOTIONS:
                score += 1
            elif e in NEGATIVE_EMOTIONS:
                score -= 1
    net_scores.append(score)

# Red zone detection: decided by the backend (last up to 14 sessions from the
# past 30 days, min 5, 60%+ net negative, one check-in a day, 7-day cool-off)
red_zone_status = {}
try:
    status_res = requests.get(f"{BACKEND_URL}/emotional_status", headers=headers)
    if status_res.status_code == 200:
        red_zone_status = status_res.json()
except Exception:
    red_zone_status = {}

red_zone_triggered = (
    red_zone_status.get("status") == "red_zone" and red_zone_status.get("show_checkin", False)
)


# === Emotion Definitions ===
positive_emotions ={"admiration", "amusement", "approval", "caring", "curiosity", "excitement", "gratitude", "joy", "love", "optimism", "pride", "relief"}
negative_emotions = {"anger", "annoyance", "disappointment", "disapproval", "disgust", "embarrassment", "fear", "grief", "remorse", "sadness","confusion", "nervousness"}
neutral_emotions = {"desire","surprise", "realization"}

# === Emotion Heatmap ===
def get_colorscale(emotion):
    if emotion in positive_emotions:
        return [[0, "#bbf7d0"], [1, "#22c55e"]]
    elif emotion in negative_emotions:
        return [[0, "#fecaca"], [1, "#dc2626"]]
    else:
        return [[0, "#ddd6fe"], [1, "#7c3aed"]]



# === Global Emotion Donut Chart ===
NEUTRAL_EMOTIONS = {"desire","surprise", "realization"}

color_map = {"Positive": "#7dd3fc", "Negative": "#f87171", "Neutral": "#a3e635"}
def summarize_session(entry_emotions):
    if not entry_emotions:
        return "You haven’t written anything yet, but I’m here when you’re ready."

    all_emotions = [e for entry in entry_emotions for e in entry["emotions"]]
    emotion_counts = Counter(all_emotions)
    top_emotions = [e for e, _ in emotion_counts.most_common(3)]

    first = set(entry_emotions[0]["emotions"])
    last = set(entry_emotions[-1]["emotions"])

    added = list(last - first)
    faded = list(first - last)

    first_neg = sum(1 for e in first if e in NEGATIVE_EMOTIONS)
    last_neg = sum(1 for e in last if e in NEGATIVE_EMOTIONS)
    first_pos = sum(1 for e in first if e in POSITIVE_EMOTIONS)
    last_pos = sum(1 for e in last if e in POSITIVE_EMOTIONS)

    summary = "<strong>🧾 Emotional Summary:</strong><br><br>"

    if top_emotions:
        summary += "🔐 <b>What stood out today:</b><br>"
        summary += "• " + ", ".join(f"<b>{e}</b>" for e in top_emotions[:3]) + "<br><br>"

    if added:
        summary += "🕊️ <b>New feelings that found their way in:</b><br>"
        summary += "• " + ", ".join(f"<b>{e}</b>" for e in added[:3]) + "<br><br>"

    if faded:
        summary += "🌔 <b>Emotions that gently stepped back:</b><br>"
        summary += "• " + ", ".join(f"<b>{e}</b>" for e in faded[:2]) + "<br><br>"

    if first_neg > last_neg and last_pos > first_pos:
        summary += "🦄 <b>The shift I noticed:</b><br>• A quiet move toward something lighter.<br><br>"

    summary += "🫂Thanks for opening up — I’m here with you!"

    return summary




def get_emotion_type(emotion):
    if emotion in POSITIVE_EMOTIONS:
        return "Positive"
    elif emotion in NEGATIVE_EMOTIONS:
        return "Negative"
    elif emotion in NEUTRAL_EMOTIONS:
        return "Neutral"
    else:
        return "Neutral"

all_emotions_flat = [e for s in sessions for entry in s["entry_emotions"] for e in entry["emotions"]]
emotion_type_counts = Counter(get_emotion_type(e) for e in all_emotions_flat)

labels = list(emotion_type_counts.keys())
values = [emotion_type_counts[label] for label in labels]
colors = [color_map[label] for label in labels]

fig_donut = go.Figure(
    data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.55,  # Thinner ring
        marker=dict(colors=colors),
        textinfo="label+percent",
        domain=dict(x=[0.15, 0.85], y=[0.15, 0.85])  # Shrinks chart inside container
    )]
)


fig_donut.update_layout(
    title=dict(
        text="🔮 Your Emotional Journey in Full Circle ",
        x=0.5,  # Center the title horizontally (0 = left, 1 = right)
        xanchor="center",  # Anchor the title relative to its x position
        font=dict(color="#fefae0")
    ),
    margin=dict(t=40, l=20, r=20, b=20),
    paper_bgcolor="#2E2E38",
    plot_bgcolor="#2E2E38",
    font=dict(color="#fefae0"),
    height=450
)

# === Conditional Session Selector ===
if view_option == "Entry-Level View":
    session_labels = [f"Session {s['user_session_number']}" for s in sessions]
    selected_label = st.selectbox(
        "Choose a session to view the emotional arc:",
        session_labels,
        key="arc_session_selector"
    )
    selected_session = next(s for s in sessions if f"Session {s['user_session_number']}" == selected_label)

    entry_emotions = selected_session["entry_emotions"]
    all_emotions = [e for entry in entry_emotions for e in entry["emotions"]]
    unique_emotions = sorted(set(all_emotions))

    emotion_matrix = np.zeros((len(unique_emotions), len(entry_emotions)))
    emotion_index = {emotion: i for i, emotion in enumerate(unique_emotions)}

    for entry_idx, entry in enumerate(entry_emotions):
        emotions = entry["emotions"]
        weight = 1 / len(emotions) if emotions else 0
        for e in emotions:
            emotion_matrix[emotion_index[e], entry_idx] += weight

    thread_labels = [
        f"Thread {entry.get('user_thread_number', '?')} - Entry {i + 1}"
        for i, entry in enumerate(entry_emotions)
    ]

    # Filter only non-zero emotion rows
    filtered_emotions = []
    filtered_matrix = []
    for i, emotion in enumerate(unique_emotions):
        if any(val > 0 for val in emotion_matrix[i]):
            filtered_emotions.append(emotion)
            filtered_matrix.append(emotion_matrix[i])

    fig_heatmap = go.Figure()

    # Use spaced-out y values for vertical gaps
    spacing = 1.5  # control spacing between rows
    y_positions = [i * spacing for i in range(len(filtered_emotions))]

    for i, emotion in enumerate(filtered_emotions):
        fig_heatmap.add_trace(go.Heatmap(
            z=[filtered_matrix[i]],
            x=thread_labels,
            y=[y_positions[i]],
            colorscale=get_colorscale(emotion),
            zmin=0, zmax=1,
            showscale=False,
            hoverinfo='x+y+z',
            xgap=1,
            ygap=1
        ))

    fig_heatmap.update_layout(
        title=dict(
            text="🔍 A Closer Look at What You Felt, Moment by Moment",
            x=0.5,
            xanchor='center',
            pad=dict(t=10),
        ),
        yaxis=dict(
            tickmode='array',
            tickvals=y_positions,
            ticktext=filtered_emotions,
            autorange='reversed',
            showgrid=False
        ),
        xaxis=dict(tickangle=-40),
        plot_bgcolor="#2E2E38",
        paper_bgcolor="#2E2E38",
        font=dict(color="#fefae0"),
        margin=dict(t=60, b=90, l=40, r=40),
        height=40 + spacing * 30 * len(filtered_emotions)

    )


# === Row 1: Donut or Heatmap (based on toggle) ===
if view_option == "Overall Emotional View":
    st.plotly_chart(fig_donut, use_container_width=True, key="fig_donut_main")
else:
    with st.expander("🧠 How to interpret this heatmap"):
         st.markdown("""
    This heatmap shows how different emotions appeared and fluctuated across your journal entries.

    #### 🔍 How to Read It:
    - Each **row** represents one emotion (e.g., anger, pride, grief).
    - Each **column** represents one journal entry, shown chronologically.
    - The **color shade** indicates how strongly you felt that specific emotion in that entry.
        - **Lighter shades** mean less intense feelings.
        - **Darker shades** mean stronger intensity.
    - ⚠️ **Colors do not reflect positive or negative emotion** — each emotion has its own color scale.

    #### 📌 What This Means:
    - Focus on **how the shades change across time** within a row to understand emotional shifts.
    - If a row gets darker over time, that emotion is becoming more prominent.
    - If a row lightens, it means that emotion is fading.

    <em>You're not meant to memorize colors — instead, trace each emotion's flow across your experience.</em>
    """, unsafe_allow_html=True)

    st.plotly_chart(fig_heatmap, use_container_width=True, key="fig_heatmap_main")
    # === Emotion Summary Bubble (below heatmap) ===
    st.markdown("""
<div style="
    background-color: #fcd5ce;
    border-left: 6px solid #ffafcc;
    padding: 1.2rem 1.5rem;
    margin: 2rem 0 2.5rem 0;
    border-radius: 12px;
    font-size: 16px;
    color: #1e1e1e;
    line-height: 1.6;
">
""" + summarize_session(entry_emotions) + "</div>""", unsafe_allow_html=True)


# === Interactive Emotional Scoreboard ===
st.markdown("""
    <h3 style='color: #2E2E38; margin-top: 3rem; margin-bottom: 10px; font-weight: 600;'>
        🧮 Emotional Scoreboard: Track Your Inner Wins & Warnings
    </h3>
""", unsafe_allow_html=True)



# === CUSTOM CSS TO STYLE EXPANDER HEADER AND BODY ===
# === FORCEFUL CUSTOM CSS FOR EXPANDER STYLING ===
st.markdown("""
    <style>
    /* Expander container header */
    [data-testid="stExpander"] > details > summary {
        background-color: #2E2E38 !important;  
        color: #fefae0 !important;
        font-weight: 600;
        padding: 0.6rem 1rem;
        border-radius: 0.5rem 0.5rem 0 0;
    }

    /* Expander inner content bubble */
    [data-testid="stExpander"] > details > div {
        background-color: #d6e2e9 !important;  /* Blue-gray */
        color: #1e1e1e !important;
        padding: 1rem;
        border-radius: 0 0 0.5rem 0.5rem;
    }

    /* Optional: tighten spacing at top */
    section.main > div:first-child {
        padding-top: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

# === TITLE ABOVE DROPDOWN ===

# === EXPANDER BOX ===
with st.expander("What is the Emotional Scoreboard?", expanded=True):
    st.markdown("""
**🎯 What is the Emotional Scoreboard?**  
The Emotional Scoreboard gives you a quick snapshot of your emotional health over time by assigning a net score to each journaling session.

**🧮 How are scores calculated?**  
Each emotion in your entries is scored as:  
✅ Positive → +1  ⚠️ Negative → -1  😐 Neutral → 0  

**Example:**  
5 Positive + 2 Negative = **Net Score: +3**

**📈 Why does it matter?**  
• Track emotional trends across sessions  
• Identify high or low emotional phases  
• Detect critical patterns — if **60% of your sessions** have a negative score,  
you'll enter a **Red Zone** and be gently advised to reflect or seek support.
""", unsafe_allow_html=True)

st.markdown("""
<style>
  /* Question container */
  .question-container {
    background-color: #fcd5ce;
    border-radius: 12px;
    padding: 1rem 1.5rem;
    max-width: 100%;
    overflow: visible;
    margin-bottom: 0.5rem;
  }

  .question-text {
    color: #2E2E38;
    font-size: 18px;
    font-weight: 600;
    margin: 0;
  }

  /* Style radio container */
  div[data-testid="stRadio"] {
    display: flex !important;
    gap: 2rem !important;
    overflow: visible !important;
    margin-top: 0 !important;
    background-color: #fcd5ce;
    border-radius: 8px;
    padding: 0.4rem 1rem 0.2rem 1rem;
  }

  /* Style individual radio label */
  div[data-testid="stRadio"] label {
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    color: #2E2E38 !important;
    font-size: 16px !important;
    font-weight: 500 !important;
  }

</style>

<div class="question-container">
  <p class="question-text">Would you like to check your emotional scoreboard?</p>
</div>
""", unsafe_allow_html=True)

# Use a UNIQUE key here, for example 'check_score_toggle_2'
check_scoreboard = st.radio(
    label="",
    options=["No", "Yes"],
    index=0,
    horizontal=True,
    key="check_score_toggle_2"
)


if check_scoreboard == "Yes":
    session_labels = []

    for s in sessions:
        label = f"Session {s['user_session_number']}"
        session_labels.append(label)

        emotions = s["entry_emotions"]
        score = 0
        for entry in emotions:
            for e in entry["emotions"]:
                if e in POSITIVE_EMOTIONS:
                    score += 1
                elif e in NEGATIVE_EMOTIONS:
                    score -= 1
    


    fig_line = go.Figure()
    # Glowing shadow layer (bigger, transparent)
    fig_line.add_trace(go.Scatter(
    x=session_labels,
    y=net_scores,
    mode='markers',
    marker=dict(
        size=28,  # Larger for glow
        color='rgba(221, 160, 221, 0.3)',  # Lavender glow with transparency
        line=dict(width=0),
    ),
    hoverinfo='skip',
    showlegend=False
))

# Actual line and markers
    fig_line.add_trace(go.Scatter(
    x=session_labels,
    y=net_scores,
    mode='lines+markers',
    line=dict(color='#ff4ecb', width=3),
    marker=dict(
        size=10,
        color='rgba(221, 160, 221, 1)',  # Solid lavender
        line=dict(width=2, color='#ffffff')
    ),
    name="Net Emotion Score",
    line_shape='spline'
))




    fig_line.update_layout(
    title={
        'text': "📈 Net Emotion Score per Session",
        'x': 0.5,
        'xanchor': 'center'
    },
    xaxis_title="Session",
    yaxis_title="Net Emotion Score",
    yaxis=dict(range=[min(net_scores) - 2, max(net_scores) + 2]),  # expanded Y-axis
    plot_bgcolor="#2E2E38",
    paper_bgcolor="#2E2E38",
    font=dict(color="#fefae0", size=14),
    height=400,
    margin=dict(t=40, b=40)  # controls title spacing
)



    # Wrap line graph in styled container
    with st.container():
     st.plotly_chart(fig_line, use_container_width=True)

    import requests

# Cool-off after an escalation: tell the user, no check-in
if red_zone_status.get("status") == "cool_off":
    st.info("💌 " + red_zone_status.get("message", "Your trusted contacts were sent a gentle note recently."))

# Red Zone Trigger Check
if red_zone_triggered:
    headers = {"Authorization": f"Bearer {st.session_state['auth_token']}"}
    response = requests.get(f"{BACKEND_URL}/user/settings/", headers=headers)

    support_contacts, coping_activities = [], []
    if response.status_code == 200:
        data = response.json()
        support_contacts = data.get("support_contacts", [])
        coping_activities = data.get("coping_activities", [])
    else:
        st.error("⚠️ Could not fetch support contacts or coping activities.")

    # Styling
    st.markdown("""
        <style>
        .red-zone-box {
            background-color: #2E2E38;
            border: 2px solid #cdb4db;
            border-radius: 12px;
            padding: 24px;
            color: #fefae0;
            font-size: 16px;
            line-height: 1.6;
            margin-bottom: 24px;
        }
        .red-zone-box strong {
            color: #ffccd5;
            font-size: 18px;
        }
        .red-zone-box em {
            display: block;
            margin-top: 16px;
            color: #cdb4db;
            font-style: italic;
        }
        input, textarea {
            background-color: #2E2E38 !important;
            color: #fefae0 !important;
        }
        .stTextInput > div > div > input {
            color: #fefae0 !important;
        }
        .stButton button {
            background-color: #cdb4db;
            color: #2E2E38;
            font-weight: bold;
            border-radius: 8px;
            padding: 0.5rem 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="red-zone-box">
        <strong>🚨 Emotional Red Zone:</strong><br>
        60% or more of your recent sessions show a net negative emotional score. This may signal emotional fatigue or stress accumulation.<br><br>
        You may want to talk to someone you trust or try a calming activity.
        <em>"Even storms pass. Let yourself rest."</em>
    </div>
    """, unsafe_allow_html=True)

    red_zone_choice = st.radio(
    "What would you like to do now?",
    options=[
        "Contact a support person", 
        "Try a coping activity", 
        "Ignore this alert"
    ],
    index=None,
    key="red_zone_choice"
)


    selected_support = None
    selected_activity = None
    message = ""

    if red_zone_choice == "Contact a support person":
        if support_contacts:
            selected_support = st.selectbox(
                "Choose someone to contact:",
                support_contacts,
                format_func=lambda x: f"{x['name']} ({x['relation']})"
            )

            if selected_support:
                st.markdown(f"""
                <div style="background-color: #2E2E38; border-left: 5px solid #cdb4db; padding: 1rem; border-radius: 10px; margin-top: 1rem; color: #fefae0;">
                    <strong style="color: #ffccd5;">You’ve selected:</strong> 
                    <span>{selected_support['name']} ({selected_support['relation']})</span><br><br>
                    Consider sending them a message or making a quick call.<br>
                    Even just sharing how you're feeling can lighten the emotional load. 💬📞
                </div>
                """, unsafe_allow_html=True)

                st.markdown("""
                    <div style="
                        background-color: #fcd5ce;
                        color: #2E2E38;
                        border-radius: 8px;
                        padding: 0.6rem 1rem;
                        font-weight: 500;
                        margin-top: 1rem;
                        margin-bottom: 0.5rem;
                    ">
                    📬 You can contact them here:
                    </div>
                """, unsafe_allow_html=True)
                st.text_input("Their Email:", selected_support["email"], disabled=True, label_visibility="collapsed")

                st.markdown("""
                    <div style="
                        background-color: #fcd5ce;
                        color: #2E2E38;
                        border-radius: 8px;
                        padding: 0.6rem 1rem;
                        font-weight: 500;
                        margin-top: 1rem;
                        margin-bottom: 0.5rem;
                    ">
                    🧘‍♀️ Why don’t you try drafting a message?
                    </div>
                """, unsafe_allow_html=True)

                message = st.text_area(
                    "Draft a message to them (optional):",
                    placeholder="Hey, I’m going through something and could use someone to talk to...",
                    label_visibility="collapsed"
                )

                if message.strip():
                    mailto_link = f"mailto:{selected_support['email']}?subject=Just%20Checking%20In&body={requests.utils.quote(message)}"
                else:
                    mailto_link = f"mailto:{selected_support['email']}?subject=Just%20Checking%20In"

                st.markdown(f"""
                    <a href="{mailto_link}" target="_blank">
                        <button style="
                            background-color: #cdb4db;
                            color: #2E2E38;
                            border: none;
                            padding: 0.6rem 1.2rem;
                            border-radius: 8px;
                            font-weight: bold;
                            cursor: pointer;
                            margin-top: 10px;
                            margin-bottom: 10px;
                        ">
                        ✉️ Send Email
                        </button>
                    </a>
                """, unsafe_allow_html=True)

        else:
            st.warning("⚠️ No support contacts found. Please add one in your settings.")

    elif red_zone_choice == "Try a coping activity" and coping_activities:
        selected_activity = st.selectbox("Choose an activity to try:", coping_activities)

    elif red_zone_choice == "Ignore this alert":
        st.write( "That's okay. I'll stay here if you need me later.")
           

    if st.button("Submit Response"):
        payload = {
            "user_session_number": sessions[-1]["user_session_number"],
            "did_contact": False,
            "did_activity": False,
            "did_grounding": False
        }

        if red_zone_choice == "Contact a support person" and selected_support:
            payload["did_contact"] = True
            payload["support_id"] = selected_support["id"]
        elif red_zone_choice == "Try a coping activity" and selected_activity:
            payload["did_activity"] = True
            payload["activity_name"] = selected_activity
        elif red_zone_choice == "Ignore this alert":
            payload["did_grounding"] = True

        res = requests.post(f"{BACKEND_URL}/user/settings/red_zone_log", json=payload, headers=headers)
        res_data = res.json() if res.status_code == 200 else {}

        if res.status_code == 200 and not res_data.get("logged", True):
            st.info(res_data.get("message", "Response already noted today."))
        elif res.status_code == 200:
            if payload["did_contact"]:
              st.markdown("""
            <div style='background-color: #e0fbfc; color: #2e2e38;
            border-left: 5px solid #98c1d9; padding: 1rem;
            border-radius: 8px; font-size: 16px; font-weight: 500;'>
            ✅ You’ve reached out to someone who cares.
            </div>
        """, unsafe_allow_html=True)
            elif payload["did_activity"]:
             st.markdown(f"""
            <div style='background-color: #e0fbfc; color: #2e2e38;
            border-left: 5px solid #98c1d9; padding: 1rem;
            border-radius: 8px; font-size: 16px; font-weight: 500;'>
            🎯 You've chosen to try: {selected_activity}. Be gentle with yourself.
            </div>
        """, unsafe_allow_html=True)
            elif payload["did_grounding"]:
             st.markdown("""
            <div style='background-color: #e0fbfc; color: #2e2e38;
            border-left: 5px solid #98c1d9; padding: 1rem;
            border-radius: 8px; font-size: 16px; font-weight: 500;'>
            🫶 Noted. No pressure — I'm here when you’re ready.
            </div>
        """, unsafe_allow_html=True)
        else:
             st.markdown("""
        <div style='background-color: #fde2e4; color: #2e2e38;
        border-left: 5px solid #e29578; padding: 1rem;
        border-radius: 8px; font-size: 16px; font-weight: 500;'>
        ❌ Failed to log your response. Please try again.
        </div>
    """, unsafe_allow_html=True)

        if res_data.get("escalated"):
            st.info("💌 Since the last few check-ins were skipped, we sent your trusted contacts a gentle note to check in on you. Check-ins will pause for a week.")