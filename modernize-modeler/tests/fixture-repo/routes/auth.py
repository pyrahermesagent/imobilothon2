# Authentication routes.
from flask import Blueprint, request, jsonify
from models import User
from db import db

bp = Blueprint("auth", __name__)


@bp.post("/api/login")
def login():
    data = request.get_json(force=True)
    user = User.query.filter_by(email=data.get("email")).first()
    if not user or not user.check_password(data.get("password", "")):
        return jsonify(error="bad credentials"), 401
    return jsonify(id=user.id, email=user.email), 200
