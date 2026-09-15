# Notes CRUD routes.
from flask import Blueprint, request, jsonify
from models import Note
from db import db

bp = Blueprint("notes", __name__)


@bp.post("/api/notes")
def create_note():
    data = request.get_json(force=True)
    note = Note(user_id=data["user_id"], title=data["title"], body=data.get("body", ""))
    db.session.add(note)
    db.session.commit()
    return jsonify(id=note.id), 201


@bp.get("/api/notes/<int:note_id>")
def get_note(note_id):
    note = Note.query.get_or_404(note_id)
    return jsonify(id=note.id, title=note.title, body=note.body), 200
