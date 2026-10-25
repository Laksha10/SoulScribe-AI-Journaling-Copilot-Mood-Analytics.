# File: routes/user_settings.py

from flask import Blueprint, request, jsonify, current_app
from db.connection import db
from db.models import User, UserSupportContact, UserCopingActivity, Session, UserRedZoneLog
import jwt
from datetime import datetime, timedelta
from pytz import timezone
from utils.email import send_email

user_settings_bp = Blueprint("user_settings", __name__, url_prefix="/user/settings")

def now_ist():
    return datetime.now(timezone("Asia/Kolkata"))

# Same values as routes/emotion_monitor.py
CHECKIN_GAP_HOURS = 24  # at most one check-in response logged per day
COOL_OFF_DAYS = 7       # no check-ins for 7 days after an escalation

def get_user_from_token():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        user_id = payload.get("user_id")
        return User.query.get(user_id)
    except Exception as e:
        print("❌ Invalid token:", e)
        return None

# === GET USER SETTINGS ===
@user_settings_bp.route("/", methods=["GET"])
def get_user_settings():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    contacts = UserSupportContact.query.filter_by(user_id=user.id).all()
    activities = UserCopingActivity.query.filter_by(user_id=user.id).all()

    return jsonify({
        "support_contacts": [
            {
                "id": c.id,
                "name": c.name,
                "relation": c.relationship,
                "email": c.email,
                "ok_to_notify": c.ok_to_notify
            } for c in contacts
        ],
        "coping_activities": [a.label for a in activities]
    }), 200

# === UPDATE USER SETTINGS ===
@user_settings_bp.route("/", methods=["POST"])
def update_user_settings():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    new_contacts = data.get("support_contacts", [])
    new_activities = data.get("coping_activities", [])

    UserSupportContact.query.filter_by(user_id=user.id).delete()
    UserCopingActivity.query.filter_by(user_id=user.id).delete()

    for contact in new_contacts:
        if contact.get("name") and contact.get("email"):
            db.session.add(UserSupportContact(
                user_id=user.id,
                name=contact["name"],
                relationship=contact.get("relationship", ""),
                email=contact["email"],
                ok_to_notify=bool(contact.get("ok_to_notify", False))
            ))
    for activity in new_activities:
        db.session.add(UserCopingActivity(user_id=user.id, label=activity))

    db.session.commit()
    return jsonify({"message": "User settings updated successfully"}), 200

# === LOG RED ZONE RESPONSE ===
@user_settings_bp.route("/red_zone_log", methods=["POST"])
def log_red_zone_response():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    user_session_number = data.get("user_session_number")
    if not user_session_number:
        return jsonify({"error": "Missing user_session_number"}), 400

    session = Session.query.filter_by(
        user_id=user.id,
        user_session_number=user_session_number
    ).first()
    if not session:
        return jsonify({"error": "Session not found"}), 404

    # Get current batch (always use max so it's never stale)
    last_log = (
        UserRedZoneLog.query
        .filter_by(user_id=user.id)
        .order_by(UserRedZoneLog.batch_id.desc(), UserRedZoneLog.triggered_at.desc())
        .first()
    )
    current_batch = last_log.batch_id if last_log else 1

    now = now_ist()

    # No check-ins during the cool-off after an escalation
    last_escalation = (
        UserRedZoneLog.query
        .filter_by(user_id=user.id, escalation_sent=True)
        .order_by(UserRedZoneLog.triggered_at.desc())
        .first()
    )
    if last_escalation and now - last_escalation.triggered_at < timedelta(days=COOL_OFF_DAYS):
        return jsonify({"message": "In cool-off period, response not logged", "logged": False}), 200

    # At most one check-in response per day, so 3 strikes = 3 separate days
    latest_log = (
        UserRedZoneLog.query
        .filter_by(user_id=user.id)
        .order_by(UserRedZoneLog.triggered_at.desc())
        .first()
    )
    if latest_log and now - latest_log.triggered_at < timedelta(hours=CHECKIN_GAP_HOURS):
        return jsonify({"message": "Already checked in today", "logged": False}), 200

    # Create new log
    log = UserRedZoneLog(
        user_id=user.id,
        session_id=session.id,
        did_contact=data.get("did_contact", False),
        did_activity=data.get("did_activity", False),
        did_grounding=data.get("did_grounding", False),
        escalation_sent=False,
        batch_id=current_batch
    )
    db.session.add(log)
    db.session.commit()

    escalated = False

    # Check last 3 logs in this batch
    last_logs = (
        UserRedZoneLog.query
        .filter_by(user_id=user.id, batch_id=current_batch, escalation_sent=False)
        .order_by(UserRedZoneLog.triggered_at.desc())
        .limit(3)
        .all()
    )

    ignored_streak = all(not l.did_contact and not l.did_activity for l in last_logs)

    # Escalate if 3 ignored
    if len(last_logs) == 3 and ignored_streak:
        # Only contacts who agreed to be notified
        contacts = UserSupportContact.query.filter_by(user_id=user.id, ok_to_notify=True).all()
        if contacts:
            for contact in contacts:
                send_email(
                    contact.email,
                    "🚨 SoulScribe Escalation Alert",
                    f"""
                    <div style="font-family: Arial, sans-serif; background-color: #fef6f6; padding: 20px; border-radius: 8px; border: 1px solid #f3d1d1;">
                        <h2 style="color: #b00020;">🚨 Escalation Alert</h2>
                        <p>Hello {contact.name},</p>
                        <p><strong>{user.username}</strong> has shown repeated signs of emotional distress during their recent SoulScribe sessions.</p>
                        <p>Please consider reaching out to them and offering support.</p>
                        <p style="font-size: 0.9em; color: #555;">This alert was triggered after 3 consecutive ignored emotional check-ins.</p>
                        <br>
                        <p>— SoulScribe Support System</p>
                    </div>
                    """
                )

            # Mark escalated logs
            for l in last_logs:
                l.escalation_sent = True
            db.session.commit()

            escalated = True
            print("🚨 Escalation emails sent. Cool-off started.")
        else:
            print("⚠️ No consenting support contacts found for escalation.")

    return jsonify({"message": "Red zone response logged", "logged": True, "escalated": escalated}), 200



# === CHECK RED ZONE STATUS ===
@user_settings_bp.route("/red_zone_status", methods=["GET"])
def get_red_zone_status():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    # Get the latest batch
    last_log = (
        UserRedZoneLog.query
        .filter_by(user_id=user.id)
        .order_by(UserRedZoneLog.batch_id.desc())
        .first()
    )
    current_batch = last_log.batch_id if last_log else 1

    # Count ignored logs in current batch
    ignored_logs = (
        UserRedZoneLog.query
        .filter_by(user_id=user.id, batch_id=current_batch, escalation_sent=False)
        .filter(~UserRedZoneLog.did_contact, ~UserRedZoneLog.did_activity)
        .count()
    )

    return jsonify({
        "current_batch": current_batch,
        "ignored_count": ignored_logs
    }), 200