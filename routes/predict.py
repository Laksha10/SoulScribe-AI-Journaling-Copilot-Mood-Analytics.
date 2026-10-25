#files. routes/predict.py
from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from transformers import RobertaTokenizer
from pytz import timezone
from collections import Counter
import torch
import numpy as np
import json
import re

from utils.auth2 import token_required
from db.connection import db
from db.models import JournalEntry, JournalThread, Session
from models.soulscribe_v8 import SoulScribeV8
from utils.llm_response import get_llm_response
from sqlalchemy import func

predict_bp = Blueprint("predict", __name__)

def now_ist():
    return datetime.now(timezone("Asia/Kolkata"))

def load_model(base_path="models", device_str="cpu"):
    device = torch.device(device_str)
    model = SoulScribeV8().to(device)
    model.load_state_dict(torch.load(f"{base_path}/model_weights.pt", map_location=device))
    model.eval()
    tokenizer = RobertaTokenizer.from_pretrained("roberta-large")

    with open(f"{base_path}/label_list.json") as f:
        label_list = json.load(f)
    with open(f"{base_path}/thresholds.json") as f:
        thresholds = json.load(f)

    if "neutral" in label_list:
        print("⚠️ Removing 'neutral' from label_list and thresholds (not used in training)")
        filtered = [(label, t) for label, t in zip(label_list, thresholds) if label != "neutral"]
        label_list, thresholds = zip(*filtered)
        label_list, thresholds = list(label_list), list(thresholds)

    return model, tokenizer, label_list, thresholds, device

model, tokenizer, label_list, best_thresholds, device = load_model()

def split_sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s]

def predict_emotions(text, model, tokenizer, label_list, thresholds, device, top_k=3):
    sentences = split_sentences(text)
    all_logits = []

    for sent in sentences:
        tokens = tokenizer(sent, return_tensors='pt', truncation=True, max_length=256, padding='max_length')
        ids = tokens['input_ids'].to(device)
        mask = tokens['attention_mask'].to(device)
        with torch.no_grad():
            probs = model(ids, mask).cpu().numpy()[0]
            all_logits.append(probs)

    avg_probs = np.mean(all_logits, axis=0)
    print("🧪 Probabilities:", avg_probs)
    print("📉 Thresholds:", thresholds)

    subtle_boost_labels = {"realization", "relief", "optimism", "caring", "pride"}
    soft_thresholds = []

    for i, label in enumerate(label_list):
        base = thresholds[i]
        adjusted = base * 0.85 if label in subtle_boost_labels else base
        soft_thresholds.append(adjusted)

    soft_thresholds = np.array(soft_thresholds)

    detected = []
    for i, prob in enumerate(avg_probs):
        if prob >= soft_thresholds[i]:
            detected.append((label_list[i], round(prob, 4)))

    if len(detected) < top_k:
        top_indices = np.argsort(avg_probs)[-top_k:][::-1]
        for i in top_indices:
            if label_list[i] not in [label for label, _ in detected]:
                detected.append((label_list[i], round(avg_probs[i], 4)))

    return [label for label, _ in detected]

@predict_bp.route("/predict", methods=["POST"])
@token_required
def predict():
    try:
        data = request.get_json()
        if not data or "text" not in data:
            return jsonify({"error": "Missing 'text' in request body"}), 400

        text = data["text"]
        provided_thread_id = data.get("thread_id")
        session_id = data.get("session_id")

        print("📥 Input text:", text)

        predicted_emotions = predict_emotions(
            text, model, tokenizer, label_list, best_thresholds, device
        )
        print("🌈 Predicted emotions:", predicted_emotions)

        # === THREAD SETUP ===
        if provided_thread_id:
            thread = JournalThread.query.get(provided_thread_id)
            if not thread:
                return jsonify({"error": "Thread not found"}), 404
        else:
            user_id = g.current_user.id

            # === ✅ Create session if missing ===
            if not session_id:
                max_number = db.session.query(func.max(Session.user_session_number))\
                    .filter_by(user_id=user_id).scalar()
                next_session_number = (max_number or 0) + 1

                new_session = Session(
                    user_id=user_id,
                    user_session_number=next_session_number,
                    start_time=now_ist()
                )
                db.session.add(new_session)
                db.session.flush()
                session_id = new_session.id

            # === ✅ Create new thread with incremental user_thread_number ===
            max_thread_number = db.session.query(func.max(JournalThread.user_thread_number))\
                .filter_by(user_id=user_id).scalar()
            next_thread_number = (max_thread_number or 0) + 1

            thread = JournalThread(
                created_at=now_ist(),
                user_id=user_id,
                session_id=session_id,
                user_thread_number=next_thread_number
            )
            db.session.add(thread)
            db.session.commit()
            print(f"🧵 Created new thread: {thread.id}")

        # === ENTRIES ===
        soul_response = get_llm_response(predicted_emotions, text, thread_id=thread.id)
        print(soul_response)

        user_entry = JournalEntry(
            text=text,
            predicted_emotions=", ".join(predicted_emotions),
            role="user",
            thread_id=thread.id,
            timestamp=now_ist()
        )
        db.session.add(user_entry)

        soul_entry = JournalEntry(
            text=soul_response,
            predicted_emotions=", ".join(predicted_emotions),
            role="soul",
            thread_id=thread.id,
            reflection=soul_response,
            timestamp=now_ist()
        )
        db.session.add(soul_entry)

        db.session.commit()

        # === 🧠 Update session-level emotion summary ===
        session = thread.session
        if session:
            all_emotions = []
            for t in session.threads:
                for e in t.entries:
                    if e.role == "user" and e.predicted_emotions:
                        all_emotions.extend(e.predicted_emotions.split(", "))

            if all_emotions:
                emotion_counts = Counter(all_emotions)
                dominant_emotion = emotion_counts.most_common(1)[0][0]
                top_emotions = [emotion for emotion, _ in emotion_counts.most_common(5)]

                session.dominant_emotion = dominant_emotion
                session.top_emotions = top_emotions
                db.session.commit()
                print(f"💾 Session {session.id} updated with dominant emotion: {dominant_emotion}, top: {top_emotions}")

        return jsonify({
            "emotions": predicted_emotions,
            "message": soul_response,
            "thread_id": thread.id
        }), 200

    except Exception as e:
        print("❌ Error during prediction:", str(e))
        return jsonify({"error": f"Server error: {str(e)}"}), 500
