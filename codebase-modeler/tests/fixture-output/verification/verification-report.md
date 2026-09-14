# Verification Report

- Repo: `tests/fixture-repo` (pinned tree for citations)
- Generated: 2026-09-13T20:41:58+00:00

## Specification.md

**Status: PASS** - citations 43/43 ok; mermaid blocks: 0 (none)

### Resolved citations (verify by eye against the code)
| Doc line | Citation | Context at cited line |
| --: | :-- | :-- |
| 14 | `app.py:7-10` | - |
| 19 | `routes/auth.py:9-15` | - |
| 20 | `routes/notes.py:9-21` | - |
| 21 | `migrations/0001_init.sql:1-18` | -- Initial schema for the Notes app. |
| 25 | `app.py:17-18` | - |
| 25 | `models.py:4` | from db import db |
| 29 | `app.py:7` | - |
| 29 | `app.py:13-14` | from routes import notes, auth  # noqa: E402 |
| 30 | `db.py:4` | - |
| 30 | `app.py:8-9` | app = Flask(__name__) |
| 33 | `requirements.txt:1` | flask==3.0.0 |
| 34 | `routes/auth.py:6` | - |
| 34 | `routes/notes.py:6` | - |
| 35 | `requirements.txt:2` | flask==3.0.0 |
| 40 | `app.py:18` | if __name__ == "__main__": |
| 46 | `routes/notes.py:9-15` | - |
| 47 | `routes/notes.py:18-21` | - |
| 48 | `models.py:16-20` | - |
| 49 | `models.py:14` | created_at = db.Column(db.DateTime, default=datetime.utcnow) |
| 49 | `models.py:26` | id = db.Column(db.Integer, primary_key=True) |
| 53 | `routes/auth.py:15` | return jsonify(error="bad credentials"), 401 |
| 57 | `requirements.txt:1-2` | flask==3.0.0 |
| 62 | `migrations/0001_init.sql:18` | - |
| 64 | `app.py:9` | app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get( |
| 65 | `models.py:11` | email = db.Column(db.String(255), unique=True, nullable=False) |
| 66 | `models.py:10` | id = db.Column(db.Integer, primary_key=True) |
| 72 | `models.py:7-20` | - |
| 73 | `models.py:23-29` | - |
| 74 | `migrations/0001_init.sql:12` | id INTEGER PRIMARY KEY, |
| 76 | `routes/notes.py:11-15` | def create_note(): |

## ClassModel.md

**Status: PASS** - citations 28/28 ok; mermaid blocks: 1 (classDiagram)

### Resolved citations (verify by eye against the code)
| Doc line | Citation | Context at cited line |
| --: | :-- | :-- |
| 13 | `models.py:7-20` | - |
| 14 | `models.py:23-29` | - |
| 18 | `routes/auth.py:12` | data = request.get_json(force=True) |
| 18 | `routes/notes.py:20` | def get_note(note_id): |
| 22 | `routes/auth.py:10-15` | @bp.post("/api/login") |
| 28 | `routes/auth.py:6` | - |
| 28 | `routes/auth.py:9-15` | - |
| 29 | `routes/notes.py:6` | - |
| 29 | `routes/notes.py:9-21` | - |
| 30 | `db.py:3-4` | from flask_sqlalchemy import SQLAlchemy |
| 34 | `routes/auth.py:11` | def login(): |
| 34 | `routes/notes.py:11` | def create_note(): |
| 35 | `routes/auth.py:15` | return jsonify(error="bad credentials"), 401 |
| 35 | `routes/notes.py:15` | db.session.commit() |
| 39 | `app.py:1` | # Entry point for the Notes app (Flask). |
| 79 | `routes/notes.py:9-15` | - |
| 80 | `routes/notes.py:18-21` | - |
| 86 | `models.py:14` | created_at = db.Column(db.DateTime, default=datetime.utcnow) |
| 87 | `routes/auth.py:13` | user = User.query.filter_by(email=data.get("email")).first() |
| 88 | `routes/notes.py:12` | data = request.get_json(force=True) |
| 90 | `models.py:3` | from datetime import datetime |
| 96 | `routes/notes.py:21` | note = Note.query.get_or_404(note_id) |
| 97 | `models.py:7` | - |

## DatabaseModel.md

**Status: PASS** - citations 43/43 ok; mermaid blocks: 1 (erDiagram)

### Resolved citations (verify by eye against the code)
| Doc line | Citation | Context at cited line |
| --: | :-- | :-- |
| 6 | `migrations/0001_init.sql:2-16` | -- Initial schema for the Notes app. |
| 6 | `db.py:3` | from flask_sqlalchemy import SQLAlchemy |
| 9 | `db.py:2-4` | # SQLAlchemy engine + session setup. |
| 10 | `app.py:8-9` | app = Flask(__name__) |
| 11 | `requirements.txt:2` | flask==3.0.0 |
| 12 | `migrations/0001_init.sql:1` | -- Initial schema for the Notes app. |
| 15 | `migrations/0001_init.sql:2` | -- Initial schema for the Notes app. |
| 15 | `migrations/0001_init.sql:10` | - |
| 16 | `migrations/0001_init.sql:4` | id INTEGER PRIMARY KEY, |
| 17 | `migrations/0001_init.sql:3` | CREATE TABLE users ( |
| 17 | `migrations/0001_init.sql:11` | CREATE TABLE notes ( |
| 18 | `migrations/0001_init.sql:12` | id INTEGER PRIMARY KEY, |
| 19 | `migrations/0001_init.sql:7` | is_active BOOLEAN DEFAULT 1, |
| 19 | `migrations/0001_init.sql:15` | body TEXT, |
| 40 | `migrations/0001_init.sql:2-8` | -- Initial schema for the Notes app. |
| 41 | `migrations/0001_init.sql:10-16` | - |
| 46 | `models.py:7-8` | - |
| 52 | `migrations/0001_init.sql:5` | email VARCHAR(255) NOT NULL UNIQUE, |
| 53 | `migrations/0001_init.sql:6` | password_hash VARCHAR(255) NOT NULL, |
| 57 | `models.py:23-24` | - |
| 63 | `migrations/0001_init.sql:13` | user_id INTEGER NOT NULL REFERENCES users(id), |
| 64 | `migrations/0001_init.sql:14` | title VARCHAR(120) NOT NULL, |
| 70 | `models.py:14` | created_at = db.Column(db.DateTime, default=datetime.utcnow) |
| 75 | `migrations/0001_init.sql:18` | - |
| 79 | `models.py:4` | from db import db |
| 79 | `models.py:16-17` | - |

## DomainModel.md

**Status: PASS** - citations 32/32 ok; mermaid blocks: 1 (classDiagram)

### Resolved citations (verify by eye against the code)
| Doc line | Citation | Context at cited line |
| --: | :-- | :-- |
| 8 | `routes/notes.py:9-21` | - |
| 11 | `models.py:7-11` | - |
| 12 | `models.py:23-27` | - |
| 13 | `models.py:14` | created_at = db.Column(db.DateTime, default=datetime.utcnow) |
| 15 | `models.py:12` | password_hash = db.Column(db.String(255), nullable=False) |
| 15 | `routes/auth.py:12-15` | data = request.get_json(force=True) |
| 18 | `routes/auth.py:1` | # Authentication routes. |
| 19 | `models.py:7-20` | - |
| 20 | `routes/notes.py:1` | # Notes CRUD routes. |
| 20 | `models.py:23-29` | - |
| 26 | `models.py:9` | __tablename__ = "users" |
| 27 | `models.py:10-13` | id = db.Column(db.Integer, primary_key=True) |
| 28 | `models.py:16-17` | - |
| 28 | `models.py:19-20` | - |
| 29 | `models.py:25` | __tablename__ = "notes" |
| 30 | `models.py:26-29` | id = db.Column(db.Integer, primary_key=True) |
| 35 | `models.py:1` | # ORM models for the Notes app. |
| 43 | `migrations/0001_init.sql:12` | id INTEGER PRIMARY KEY, |
| 46 | `migrations/0001_init.sql:4` | id INTEGER PRIMARY KEY, |
| 48 | `routes/auth.py:12-14` | data = request.get_json(force=True) |
| 50 | `migrations/0001_init.sql:12-13` | id INTEGER PRIMARY KEY, |
| 56 | `routes/notes.py:13-14` | note = Note(user_id=data["user_id"], title=data["title"], body=data.get("body", "")) |
| 60 | `routes/auth.py:10` | @bp.post("/api/login") |
| 60 | `routes/notes.py:10` | @bp.post("/api/notes") |

## UseCaseModel.md

**Status: PASS** - citations 55/55 ok; mermaid blocks: 1 (flowchart)

### Resolved citations (verify by eye against the code)
| Doc line | Citation | Context at cited line |
| --: | :-- | :-- |
| 6 | `app.py:13-14` | from routes import notes, auth  # noqa: E402 |
| 10 | `routes/auth.py:9` | - |
| 11 | `routes/notes.py:9` | - |
| 11 | `routes/notes.py:18` | - |
| 14 | `models.py:7-14` | - |
| 15 | `routes/auth.py:6` | - |
| 20 | `routes/auth.py:10-15` | @bp.post("/api/login") |
| 23 | `app.py:8-9` | app = Flask(__name__) |
| 23 | `db.py:3` | from flask_sqlalchemy import SQLAlchemy |
| 24 | `models.py:4` | from db import db |
| 47 | `routes/auth.py:10` | @bp.post("/api/login") |
| 48 | `app.py:7-14` | - |
| 49 | `routes/auth.py:9-15` | - |
| 50 | `routes/notes.py:9-15` | - |
| 51 | `routes/notes.py:18-21` | - |
| 56 | `routes/notes.py:11-12` | def create_note(): |
| 69 | `migrations/0001_init.sql:5` | email VARCHAR(255) NOT NULL UNIQUE, |
| 70 | `routes/auth.py:11` | def login(): |
| 73 | `routes/auth.py:15` | return jsonify(error="bad credentials"), 401 |
| 74 | `routes/auth.py:13-14` | user = User.query.filter_by(email=data.get("email")).first() |
| 79 | `routes/auth.py:12` | data = request.get_json(force=True) |
| 80 | `routes/auth.py:13` | user = User.query.filter_by(email=data.get("email")).first() |
| 80 | `models.py:19-20` | - |
| 91 | `models.py:20` | def check_password(self, raw): |
| 99 | `routes/notes.py:10` | @bp.post("/api/notes") |
| 108 | `routes/notes.py:13-14` | note = Note(user_id=data["user_id"], title=data["title"], body=data.get("body", "")) |
| 109 | `routes/notes.py:15` | db.session.commit() |
| 118 | `routes/notes.py:12` | data = request.get_json(force=True) |
| 123 | `routes/notes.py:11-14` | def create_note(): |
| 133 | `routes/notes.py:19` | @bp.get("/api/notes/<int:note_id>") |
| 136 | `routes/notes.py:20` | def get_note(note_id): |
| 139 | `routes/notes.py:20-21` | def get_note(note_id): |
| 144 | `routes/notes.py:21` | note = Note.query.get_or_404(note_id) |

## ActivityDiagram.md

**Status: PASS** - citations 40/40 ok; mermaid blocks: 2 (flowchart, flowchart)

### Resolved citations (verify by eye against the code)
| Doc line | Citation | Context at cited line |
| --: | :-- | :-- |
| 9 | `routes/auth.py:9-15` | - |
| 10 | `routes/notes.py:9-15` | - |
| 40 | `routes/auth.py:9` | - |
| 41 | `routes/auth.py:11` | def login(): |
| 42 | `routes/auth.py:9-10` | - |
| 43 | `routes/auth.py:13` | user = User.query.filter_by(email=data.get("email")).first() |
| 44 | `routes/auth.py:15` | return jsonify(error="bad credentials"), 401 |
| 45 | `routes/auth.py:14` | if not user or not user.check_password(data.get("password", "")): |
| 46 | `migrations/0001_init.sql:2-8` | -- Initial schema for the Notes app. |
| 51 | `routes/auth.py:12` | data = request.get_json(force=True) |
| 53 | `models.py:19-20` | - |
| 53 | `models.py:4` | from db import db |
| 81 | `routes/notes.py:9` | - |
| 82 | `routes/notes.py:11` | def create_note(): |
| 83 | `routes/notes.py:9-10` | - |
| 84 | `routes/notes.py:15` | db.session.commit() |
| 85 | `routes/notes.py:12` | data = request.get_json(force=True) |
| 86 | `migrations/0001_init.sql:10-16` | - |
| 91 | `routes/notes.py:13` | note = Note(user_id=data["user_id"], title=data["title"], body=data.get("body", "")) |
| 92 | `routes/notes.py:14` | db.session.add(note) |
| 97 | `app.py:1` | # Entry point for the Notes app (Flask). |
| 98 | `app.py:7` | - |
| 99 | `app.py:13-14` | from routes import notes, auth  # noqa: E402 |
| 99 | `db.py:4` | - |
| 100 | `app.py:8-9` | app = Flask(__name__) |
| 101 | `migrations/0001_init.sql:1-16` | -- Initial schema for the Notes app. |
| 106 | `routes/auth.py:13-14` | user = User.query.filter_by(email=data.get("email")).first() |
| 116 | `routes/notes.py:20` | def get_note(note_id): |

