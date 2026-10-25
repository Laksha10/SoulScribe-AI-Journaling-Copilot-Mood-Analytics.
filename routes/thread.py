#files: routes/thread.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Blueprint, jsonify, request, g
from db.connection import db
from db.models import JournalEntry, JournalThread, Session  # ✅ FIXED: import Session
from pytz import timezone
from utils.auth2 import token_required
from sqlalchemy.orm import joinedload
from sqlalchemy import func

thread_bp = Blueprint("thread", __name__)

@thread_bp.route("/threads/<int:thread_id>", methods=["GET"])
@token_required
def get_thread(thread_id):
    try:
        user_id = g.current_user.id

        thread = (
            db.session.query(JournalThread)
            .options(joinedload(JournalThread.session))
            .filter_by(id=thread_id)
            .first()
        )

        if not thread:
            return jsonify({"error": "Thread not found"}), 404

        if thread.user_id != user_id:
            return jsonify({"error": "Access denied: Not your thread"}), 403

        entries = (
            JournalEntry.query
            .filter_by(thread_id=thread_id)
            .order_by(JournalEntry.timestamp.asc())
            .all()
        )

        if not entries:
            return jsonify({"error": "No entries found for this thread"}), 404

        result = {
            "thread_id": thread.id,
            "user_thread_number": thread.user_thread_number,
            "session_id": thread.session_id,
            "user_session_number": thread.session.user_session_number if thread.session else None,
            "entries": [
                {
                    "role": entry.role,
                    "text": entry.text,
                    "emotions": entry.predicted_emotions.split(", ") if entry.predicted_emotions else [],
                    "reflection": entry.reflection,
                    "timestamp": entry.timestamp.astimezone(timezone("Asia/Kolkata")).isoformat()
                }
                for entry in entries
            ]
        }

        return jsonify(result), 200

    except Exception as e:
        print("❌ Error fetching thread:", str(e))
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@thread_bp.route("/threads/create", methods=["POST"])
@token_required
def create_thread():
    try:
        data = request.get_json()
        session_id = data.get("session_id")

        if not session_id:
            return jsonify({"error": "Missing session_id"}), 400

        user_id = g.current_user.id

        # ✅ Validate session exists and belongs to this user
        session = db.session.query(Session).filter_by(id=session_id, user_id=user_id).first()

        if not session:
            return jsonify({"error": "Invalid session_id or unauthorized"}), 400

        # 🔧 If session.user_session_number is None, assign it now
        if session.user_session_number is None:
            max_number = db.session.query(func.max(Session.user_session_number)).filter_by(user_id=user_id).scalar()
            session.user_session_number = (max_number or 0) + 1
            db.session.commit()

        # 🔢 Find the next thread number for this user
        max_number = db.session.query(func.max(JournalThread.user_thread_number)).filter_by(user_id=user_id).scalar()
        next_number = (max_number or 0) + 1

        # ✅ Create the thread
        new_thread = JournalThread(
            user_id=user_id,
            session_id=session_id,
            user_thread_number=next_number
        )

        db.session.add(new_thread)
        db.session.commit()

        return jsonify({
            "message": "Thread created successfully",
            "thread_id": new_thread.id,
            "user_thread_number": next_number
        }), 201

    except Exception as e:
        db.session.rollback()
        print("❌ Error creating thread:", str(e))
        return jsonify({"error": f"Server error: {str(e)}"}), 500
