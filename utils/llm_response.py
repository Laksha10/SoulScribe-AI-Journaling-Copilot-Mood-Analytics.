# File: utils/llm_response.py

import os
from google import genai
from dotenv import load_dotenv
from db.models import JournalEntry
from sqlalchemy import asc
import re
# Load environment variables
load_dotenv()

# Configure Gemini API key
api_key = os.getenv("GEMINI_API_KEY")
client = None
if not api_key:
    print("❌ GEMINI_API_KEY not found in .env")
else:
    client = genai.Client(api_key=api_key)

# Define model priorities
PRIMARY_MODEL = "gemini-3.6-flash"          # main SoulScribe reply
FALLBACK_MODEL = "gemini-3.5-flash-lite"    # backup if the primary call fails
THEME_MODEL = "gemini-3.5-flash-lite"       # recurring-themes summary
def clean_soulscribe_response(text):
    return re.sub(r"^SoulScribe:\s*", "", text.strip())

def generate_response_with_model(model_name, prompt):
    try:
        response = client.models.generate_content(model=model_name, contents=prompt)
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error with model {model_name}:", str(e))
        return None

def summarize_themes_from_history(entries, model=THEME_MODEL):
    journal_texts = [entry.text for entry in entries if entry.role == "user"]
    if not journal_texts:
        return ""

    theme_prompt = (
        "You're analyzing a sequence of emotional journal entries.\n"
        "Summarize recurring emotional themes or patterns in 5 words or phrases, separated by commas.\n"
        "Avoid generic terms like 'emotions' or 'feelings'. Focus on inner struggles, longings, states of mind, or reflections.\n\n"
        "Entries:\n" + "\n\n".join(journal_texts[-4:])
    )

    themes = generate_response_with_model(model, theme_prompt)
    if themes:
        return themes.strip()
    return ""

def get_llm_response(predicted_emotions, user_input, thread_id=None, max_history=2):
    """
    Generates a context-aware SoulScribe reflection using Gemini.
    Includes past conversation turns and a theme summary if thread_id is provided.
    """

    emotion_summary = ", ".join(predicted_emotions)

    # Build conversation history
    history_lines = []
    entries = []
    if thread_id:
        entries = (
            JournalEntry.query
            .filter_by(thread_id=thread_id)
            .order_by(asc(JournalEntry.timestamp))
            .all()
        )
        for entry in entries:
            role = entry.role or "user"
            if role == "user":
                history_lines.append(f"User: {entry.text}")
            else:
                history_lines.append(f"SoulScribe: {entry.text}")

        # Trim to last N user-soul pairs
        history_lines = history_lines[-(max_history * 2):]

    # Optional: Get thematic summary from past entries
    theme_summary = ""
    if thread_id and entries:
        theme_summary = summarize_themes_from_history(entries)

    # Construct prompt
    prompt = (
        "You are SoulScribe, a compassionate and emotionally intelligent journaling companion.\n"
        "Below is a conversation between a user and you. Your responses are emotionally fluent, calm, grounded, and reflect understanding.\n\n"
    )

    if history_lines:
        prompt += "--- Conversation History ---\n" + "\n".join(history_lines) + "\n\n"

    if theme_summary:
        prompt += f"--- Detected Recurring Themes ---\n{theme_summary}\n\n"

    prompt += f"--- Current Entry ---\nUser: \"{user_input}\"\n"
    prompt += f"Detected emotions: {emotion_summary}\n\n"
    prompt += "--- Your Response ---\nSoulScribe:"

    # Primary model attempt
    message = generate_response_with_model(PRIMARY_MODEL, prompt)
    if message:
        return clean_soulscribe_response(message)

    # Fallback to flash-lite
    print("🔁 Falling back to flash-lite model...")
    message = generate_response_with_model(FALLBACK_MODEL, prompt)
    if message:
            return clean_soulscribe_response(message)


    # Final fallback
    return (
        "I'm here with you. Sometimes just putting your feelings into words is an act of strength. "
        "You don't have to have all the answers—just being honest with yourself matters."
    )