# File: routes/emotion_monitor.py

import os
import jwt
from flask import Blueprint, request, jsonify
from db.models import (
    JournalEntry, JournalThread, Session,
    UserRedZoneLog, UserSupportContact, UserCopingActivity, now_ist
)
from datetime import timedelta

emotion_monitor_bp = Blueprint("emotion_monitor", __name__)

# Emotions that push a session's net score up or down (neutral ones count 0)
POSITIVE_EMOTIONS = {
    "admiration", "amusement", "approval", "caring", "curiosity", "excitement",
    "gratitude", "joy", "love", "optimism", "pride", "relief"
}
NEGATIVE_EMOTIONS = {
    "anger", "annoyance", "confusion", "disappointment", "disapproval",
    "disgust", "embarrassment", "fear", "grief", "nervousness",
    "remorse", "sadness"
}

# === Configurable parameters ===
MAX_SESSIONS = 14          # look at the most recent sessions, up to 14
WINDOW_DAYS = 30           # ...but only sessions from the last 30 days
MIN_SESSIONS = 5           # no check until there are at least 5 sessions
RED_ZONE_THRESHOLD = 0.60  # red zone when 60%+ of those sessions are net negative
CHECKIN_GAP_HOURS = 24     # at most one check-in per day
COOL_OFF_DAYS = 7          # no check-ins for 7 days after an escalation


def session_net_score(session_id):
    """+1 per positive emotion, -1 per negative, across the session's user entries.
    Returns None if the session has no predicted emotions."""
    thread_ids = [t.id for t in JournalThread.query.filter_by(session_id=session_id).all()]
    if not thread_ids:
        return None

    entries = (
        JournalEntry.query
        .filter(JournalEntry.thread_id.in_(thread_ids), JournalEntry.role == "user")
        .all()
    )

    score = 0
    found_emotions = False
    for entry in entries:
        if not entry.predicted_emotions:
            continue
        for emotion in entry.predicted_emotions.split(", "):
            found_emotions = True
            if emotion in POSITIVE_EMOTIONS:
                score += 1
            elif emotion in NEGATIVE_EMOTIONS:
                score -= 1

    return score if found_emotions else None


@emotion_monitor_bp.route("/emotional_status", methods=["GET"])
def get_emotional_status():
    try:
        # === Auth ===
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Missing Authorization header"}), 401

        token = auth_header.split(" ")[1] if " " in auth_header else auth_header
        try:
            payload = jwt.decode(token, os.getenv("JWT_SECRET_KEY"), algorithms=["HS256"])
            user_id = payload["user_id"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        now = now_ist()

        # === 1. Cool-off after an escalation ===
        last_escalation = (
            UserRedZoneLog.query
            .filter_by(user_id=user_id, escalation_sent=True)
            .order_by(UserRedZoneLog.triggered_at.desc())
            .first()
        )
        escalated_at = last_escalation.triggered_at if last_escalation else None

        if escalated_at and now - escalated_at < timedelta(days=COOL_OFF_DAYS):
            return jsonify({
                "status": "cool_off",
                "show_checkin": False,
                "recently_escalated": True,
                "message": "Your trusted contacts were sent a gentle note recently. Take the space you need."
            }), 200

        # === 2. Pick the sessions to judge ===
        # Last 30 days, newest first, at most 14. After an escalation, only
        # sessions that started after it count (a fresh start).
        cutoff = now - timedelta(days=WINDOW_DAYS)
        if escalated_at and escalated_at > cutoff:
            cutoff = escalated_at

        recent_sessions = (
            Session.query
            .filter(Session.user_id == user_id, Session.start_time >= cutoff)
            .order_by(Session.start_time.desc())
            .limit(MAX_SESSIONS)
            .all()
        )

        # === 3. Net score per session ===
        net_scores = []
        for session in recent_sessions:
            score = session_net_score(session.id)
            if score is not None:
                net_scores.append(score)

        total_sessions = len(net_scores)
        if total_sessions < MIN_SESSIONS:
            return jsonify({
                "status": "neutral",
                "show_checkin": False,
                "message": "Not enough recent sessions to judge a pattern yet."
            }), 200

        negative_sessions = sum(1 for score in net_scores if score < 0)
        distress_ratio = negative_sessions / total_sessions

        if distress_ratio < RED_ZONE_THRESHOLD:
            return jsonify({
                "status": "neutral",
                "show_checkin": False,
                "message": "Emotionally stable in recent sessions."
            }), 200

        # === 4. Red zone: show a check-in at most once a day ===
        last_log = (
            UserRedZoneLog.query
            .filter_by(user_id=user_id)
            .order_by(UserRedZoneLog.triggered_at.desc())
            .first()
        )
        show_checkin = (
            last_log is None
            or now - last_log.triggered_at >= timedelta(hours=CHECKIN_GAP_HOURS)
        )

        contacts = UserSupportContact.query.filter_by(user_id=user_id).all()
        activities = UserCopingActivity.query.filter_by(user_id=user_id).all()

        return jsonify({
            "status": "red_zone",
            "show_checkin": show_checkin,
            "message": f"{negative_sessions} out of your last {total_sessions} sessions had a net negative mood.",
            "support_contacts": [
                {"id": c.id, "name": c.name, "relation": c.relationship, "email": c.email}
                for c in contacts
            ],
            "coping_activities": [a.label for a in activities]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500