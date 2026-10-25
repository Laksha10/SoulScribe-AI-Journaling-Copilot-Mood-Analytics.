#files: routes/session.py
from flask import Blueprint, jsonify, g
from utils.auth2 import token_required
from db.models import Session
from db.connection import db
from datetime import datetime
from pytz import timezone
from sqlalchemy import func  # ✅ Required for func.max()

session_bp = Blueprint("session", __name__, url_prefix="/session")

def now_ist():
    return datetime.now(timezone("Asia/Kolkata"))

# === CREATE SESSION ===
@session_bp.route("/create_session", methods=["POST"])
@token_required
def create_session():
    try:
        user_id = g.current_user.id

        # ✅ Find current max session number for this user
        max_number = db.session.query(func.max(Session.user_session_number)).filter_by(user_id=user_id).scalar()
        next_number = (max_number or 0) + 1

        # ✅ Create new session with next user_session_number
        new_session = Session(
            user_id=user_id,
            user_session_number=next_number,
            start_time=now_ist()
        )
        db.session.add(new_session)
        db.session.commit()

        return jsonify({
            "message": "Session created successfully",
            "session_id": new_session.id,
            "user_session_number": next_number
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# === GET ALL SESSIONS FOR CURRENT USER ===
@session_bp.route("/my_sessions", methods=["GET"])
@token_required
def get_my_sessions():
    try:
        user_id = g.current_user.id

        sessions = (
            Session.query
            .filter_by(user_id=user_id)
            .order_by(Session.start_time.desc())
            .all()
        )

        return jsonify([
            {
                "session_id": s.id,
                "user_session_number": s.user_session_number,
                "start_time": s.start_time.isoformat() if s.start_time else None,
                # "end_time": s.end_time.isoformat() if s.end_time else None
            }
            for s in sessions
        ]), 200

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500
