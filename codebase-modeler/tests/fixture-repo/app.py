# Entry point for the Notes app (Flask).
import os
from flask import Flask
from db import db
from models import User, Note

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///notes.db")
db.init_app(app)

from routes import notes, auth  # noqa: E402
app.register_blueprint(notes.bp)
app.register_blueprint(auth.bp)


if __name__ == "__main__":
    app.run(debug=True)
