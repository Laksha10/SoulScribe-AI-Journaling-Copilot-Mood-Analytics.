#files: routes/entries.py
from flask import Blueprint, request, jsonify
from db.connection import db
from db.models import JournalEntry
from datetime import datetime
from pytz import timezone

def now_ist():
    return datetime.now(timezone("Asia/Kolkata"))

entries_bp = Blueprint('entries', __name__, url_prefix='/entries')

# GET all entries
@entries_bp.route('/', methods=['GET'])
def get_entries():
    entries = JournalEntry.query.all()
    return jsonify([{
        'id': entry.id,
        'text': entry.text,
        'predicted_emotions': entry.predicted_emotions,
        'role': entry.role,
        'thread_id': entry.thread_id,
        'timestamp': entry.timestamp.isoformat()
    } for entry in entries])

# GET entry by ID
@entries_bp.route('/<int:id>', methods=['GET'])
def get_entry(id):
    entry = JournalEntry.query.get_or_404(id)
    return jsonify({
        'id': entry.id,
        'text': entry.text,
        'predicted_emotions': entry.predicted_emotions,
        'role': entry.role,
        'thread_id': entry.thread_id,
        'timestamp': entry.timestamp.isoformat()
    })

# POST a new entry
@entries_bp.route('/', methods=['POST'])
def add_entry():
    data = request.get_json()

    new_entry = JournalEntry(
        text=data['text'],
        predicted_emotions=data.get('predicted_emotions', ''),
        role=data.get('role', 'user'),  # Default to user
        thread_id=data.get('thread_id'),  # Can be None
        reflection=data.get('reflection'),
        conversation=data.get('conversation'),
        timestamp=now_ist()
    )

    db.session.add(new_entry)
    db.session.commit()
    return jsonify({'message': 'Entry created successfully'}), 201

# PUT (update) an entry by ID
@entries_bp.route('/<int:id>', methods=['PUT'])
def update_entry(id):
    entry = JournalEntry.query.get_or_404(id)
    data = request.get_json()
    
    entry.text = data.get('text', entry.text)
    entry.predicted_emotions = data.get('predicted_emotions', entry.predicted_emotions)
    entry.role = data.get('role', entry.role)
    entry.thread_id = data.get('thread_id', entry.thread_id)
    entry.reflection = data.get('reflection', entry.reflection)
    entry.conversation = data.get('conversation', entry.conversation)

    db.session.commit()
    return jsonify({'message': 'Entry updated successfully'})

# DELETE an entry by ID
@entries_bp.route('/<int:id>', methods=['DELETE'])
def delete_entry(id):
    entry = JournalEntry.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    return jsonify({'message': 'Entry deleted successfully'})
