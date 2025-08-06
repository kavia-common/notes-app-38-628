"""
Flask Backend for the Notes App Monolith.
Features:
- User authentication (JWT)
- Rich text notes CRUD (with folders, tags, categories)
- File/image attachments (uploads/downloads)
- Notes search/filtering
- Import/export (JSON, Markdown, Text)
- User preferences (theme, layout)
- Accessibility/data privacy controls
- SQLite embedded database
"""
import os
import uuid
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, request, jsonify, send_from_directory, send_file, abort
)
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt

# --- Config ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ATTACHMENTS_DIR = os.path.join(BASE_DIR, "attachments")
if not os.path.exists(ATTACHMENTS_DIR):
    os.makedirs(ATTACHMENTS_DIR)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "dev_secret")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'notes.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['ATTACHMENTS_DIR'] = ATTACHMENTS_DIR
CORS(app, supports_credentials=True)

db = SQLAlchemy(app)

# --- Models ---

tags_notes = db.Table(
    "tags_notes",
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id"), primary_key=True),
    db.Column("note_id", db.Integer, db.ForeignKey("note.id"), primary_key=True)
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    preferences = db.Column(db.Text, default="{}")

class Folder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)  # Supports HTML or Markdown
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    folder_id = db.Column(db.Integer, db.ForeignKey("folder.id"), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=True)
    tags = db.relationship("Tag", secondary=tags_notes, backref=db.backref("notes", lazy="dynamic"))
    attachments = db.relationship("Attachment", backref="note", lazy=True)

class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey("note.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- Utilities ---

def create_jwt(user_id):
    token = jwt.encode({
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=1)
    }, app.config['SECRET_KEY'], algorithm="HS256")
    return token

def decode_jwt(token):
    try:
        return jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
    except Exception:
        return None

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header and "Bearer" in auth_header:
            token = auth_header.replace("Bearer ", "", 1)
        if not token:
            return jsonify({'message': 'Token missing'}), 401
        data = decode_jwt(token)
        if data is None:
            return jsonify({'message': "Token invalid or expired"}), 401
        user = User.query.get(data["user_id"])
        if not user:
            return jsonify({'message': "User not found"}), 401
        return f(current_user=user, *args, **kwargs)
    return decorated

# --- User Auth Routes ---

# PUBLIC_INTERFACE
@app.route('/api/auth/register', methods=['POST'])
def register():
    """
    Register a new account.
    json: {username, password}
    """
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()
    if user:
        return jsonify({'message': "Username exists"}), 400
    user = User(
        username=data['username'],
        password_hash=generate_password_hash(data['password'])
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'Registration successful'}), 201

# PUBLIC_INTERFACE
@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    Login and receive JWT.
    json: {username, password}
    """
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'message': 'Bad credentials'}), 401
    token = create_jwt(user.id)
    return jsonify({'token': token, 'user_id': user.id})

# --- Notes CRUD Routes (Rich text supported) ---

# PUBLIC_INTERFACE
@app.route('/api/notes', methods=['GET'])
@auth_required
def get_notes(current_user):
    """
    Get all notes for current user. Supports search/filter.
    Query params: search, folder, category, tags (comma), sort
    """
    query = Note.query.filter_by(user_id=current_user.id)
    search = request.args.get("search")
    if search:
        query = query.filter(Note.title.ilike(f"%{search}%") | Note.content.ilike(f"%{search}%"))
    folder = request.args.get("folder")
    if folder:
        query = query.filter_by(folder_id=folder)
    category = request.args.get("category")
    if category:
        query = query.filter_by(category_id=category)
    tags = request.args.get("tags")
    if tags:
        tag_ids = [int(t) for t in tags.split(",")]
        query = query.filter(Note.tags.any(Tag.id.in_(tag_ids)))
    notes = query.order_by(Note.timestamp.desc()).all()
    return jsonify([serialize_note(note) for note in notes])

# PUBLIC_INTERFACE
@app.route('/api/notes/<int:note_id>', methods=['GET'])
@auth_required
def get_note(current_user, note_id):
    """
    Get a note by id.
    """
    note = Note.query.get_or_404(note_id)
    if note.user_id != current_user.id:
        return jsonify({'message': 'Forbidden'}), 403
    return jsonify(serialize_note(note))

# PUBLIC_INTERFACE
@app.route('/api/notes', methods=['POST'])
@auth_required
def create_note(current_user):
    """
    Create new note (supports folder, category, tags).
    json: {title, content, folder_id, category_id, tag_ids}
    """
    data = request.json
    note = Note(
        title=data['title'],
        content=data['content'],
        user_id=current_user.id,
        folder_id=data.get('folder_id'),
        category_id=data.get('category_id')
    )
    if data.get('tag_ids'):
        note.tags = Tag.query.filter(Tag.id.in_(data['tag_ids'])).all()
    db.session.add(note)
    db.session.commit()
    return jsonify(serialize_note(note)), 201

# PUBLIC_INTERFACE
@app.route('/api/notes/<int:note_id>', methods=['PUT'])
@auth_required
def update_note(current_user, note_id):
    """
    Update note details/content/tags.
    """
    data = request.json
    note = Note.query.get_or_404(note_id)
    if note.user_id != current_user.id:
        return jsonify({'message': 'Forbidden'}), 403
    note.title = data.get('title', note.title)
    note.content = data.get('content', note.content)
    note.folder_id = data.get('folder_id', note.folder_id)
    note.category_id = data.get('category_id', note.category_id)
    if 'tag_ids' in data:
        note.tags = Tag.query.filter(Tag.id.in_(data['tag_ids'])).all()
    db.session.commit()
    return jsonify(serialize_note(note))

# PUBLIC_INTERFACE
@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
@auth_required
def delete_note(current_user, note_id):
    """
    Delete a note and its attachments.
    """
    note = Note.query.get_or_404(note_id)
    if note.user_id != current_user.id:
        return jsonify({'message': 'Forbidden'}), 403
    # Delete attachments files
    for att in note.attachments:
        att_path = os.path.join(app.config['ATTACHMENTS_DIR'], att.filename)
        if os.path.exists(att_path):
            os.remove(att_path)
        db.session.delete(att)
    db.session.delete(note)
    db.session.commit()
    return jsonify({'message': 'Note deleted'})

# --- Attachments ---

# PUBLIC_INTERFACE
@app.route('/api/notes/<int:note_id>/attachments', methods=['POST'])
@auth_required
def upload_attachment(current_user, note_id):
    """
    Attach a file/image to a note (multipart/form-data: file)
    """
    note = Note.query.get_or_404(note_id)
    if note.user_id != current_user.id:
        return jsonify({'message': 'Forbidden'}), 403
    file = request.files.get('file')
    if not file:
        return jsonify({'message': 'Missing file'}), 400
    ext = file.filename.split('.')[-1]
    fname = f"{uuid.uuid4().hex}.{ext}"
    attachment = Attachment(
        note_id=note.id,
        filename=fname,
        original_filename=file.filename
    )
    file.save(os.path.join(app.config['ATTACHMENTS_DIR'], fname))
    db.session.add(attachment)
    db.session.commit()
    return jsonify({
        'id': attachment.id,
        'filename': attachment.filename,
        'original_filename': attachment.original_filename
    }), 201

# PUBLIC_INTERFACE
@app.route('/api/attachments/<int:att_id>', methods=['GET'])
@auth_required
def download_attachment(current_user, att_id):
    """
    Download an attachment by id.
    """
    att = Attachment.query.get_or_404(att_id)
    note = Note.query.get(att.note_id)
    if note.user_id != current_user.id:
        return jsonify({'message': 'Forbidden'}), 403
    file_path = os.path.join(app.config['ATTACHMENTS_DIR'], att.filename)
    if not os.path.exists(file_path):
        return abort(404)
    return send_file(file_path, as_attachment=True, download_name=att.original_filename)

# --- Folders, Categories, Tags ---

# PUBLIC_INTERFACE
@app.route('/api/folders', methods=["GET", "POST"])
@auth_required
def folders(current_user):
    """
    Get or create folders.
    """
    if request.method == "GET":
        items = Folder.query.filter_by(user_id=current_user.id).all()
        return jsonify([{"id": f.id, "name": f.name} for f in items])
    data = request.json
    folder = Folder(name=data['name'], user_id=current_user.id)
    db.session.add(folder)
    db.session.commit()
    return jsonify({"id": folder.id, "name": folder.name}), 201

@app.route('/api/categories', methods=["GET", "POST"])
@auth_required
def categories(current_user):
    """
    Get or create categories.
    """
    if request.method == "GET":
        items = Category.query.filter_by(user_id=current_user.id).all()
        return jsonify([{"id": c.id, "name": c.name} for c in items])
    data = request.json
    category = Category(name=data['name'], user_id=current_user.id)
    db.session.add(category)
    db.session.commit()
    return jsonify({"id": category.id, "name": category.name}), 201

@app.route('/api/tags', methods=["GET", "POST"])
@auth_required
def tags(current_user):
    """
    Get or create tags.
    """
    if request.method == "GET":
        items = Tag.query.filter_by(user_id=current_user.id).all()
        return jsonify([{"id": t.id, "name": t.name} for t in items])
    data = request.json
    tag = Tag(name=data['name'], user_id=current_user.id)
    db.session.add(tag)
    db.session.commit()
    return jsonify({"id": tag.id, "name": tag.name}), 201

# --- Import/Export ---

import json
from io import BytesIO

@app.route('/api/notes/export', methods=["GET"])
@auth_required
def export_notes(current_user):
    """
    Export all user notes and metadata. format=[json|md|txt]
    """
    fmt = request.args.get("format", "json")
    notes = Note.query.filter_by(user_id=current_user.id).all()
    if fmt == "json":
        data = [serialize_note(n) for n in notes]
        bio = BytesIO(json.dumps(data, indent=2).encode("utf-8"))
        return send_file(bio, as_attachment=True, download_name="notes.json")
    elif fmt == "md":
        md = ""
        for n in notes:
            md += f"# {n.title}\n\n{n.content}\n\n---\n"
        bio = BytesIO(md.encode("utf-8"))
        return send_file(bio, as_attachment=True, download_name="notes.md")
    elif fmt == "txt":
        result = "\n\n".join(f"{n.title}\n{n.content}" for n in notes)
        bio = BytesIO(result.encode("utf-8"))
        return send_file(bio, as_attachment=True, download_name="notes.txt")
    return jsonify({"message": "Unknown format"}), 400

@app.route('/api/notes/import', methods=["POST"])
@auth_required
def import_notes(current_user):
    """
    Import notes (Accepts JSON file). Overwrites/adds notes.
    """
    file = request.files.get("file")
    if not file or not file.filename.endswith('.json'):
        return jsonify({"message": "JSON file required"}), 400
    try:
        data = json.load(file)
        for n in data:
            note = Note(
                title=n['title'],
                content=n['content'],
                user_id=current_user.id,
                folder_id=n.get('folder_id'),
                category_id=n.get('category_id')
            )
            db.session.add(note)
        db.session.commit()
        return jsonify({"message": "Import successful"})
    except Exception as ex:
        return jsonify({"message": "Import error", "error": str(ex)}), 500

# --- User Preferences ---

@app.route('/api/preferences', methods=["GET", "PUT"])
@auth_required
def preferences(current_user):
    """
    Get or update user preferences.
    """
    if request.method == "GET":
        return jsonify(json.loads(current_user.preferences))
    data = request.json
    current_user.preferences = json.dumps(data)
    db.session.commit()
    return jsonify({"message": "Preferences updated"})

# --- Helper Serializers ---

def serialize_note(note):
    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "timestamp": note.timestamp.isoformat() if note.timestamp else None,
        "folder_id": note.folder_id,
        "category_id": note.category_id,
        "tag_ids": [t.id for t in note.tags],
        "attachments": [
            {
                "id": att.id,
                "filename": att.filename,
                "original_filename": att.original_filename
            } for att in note.attachments
        ]
    }

# --- Accessibility/Data Privacy/Info ---

@app.route('/api/info/accessibility', methods=["GET"])
def accessibility_info():
    """Return app accessibility features."""
    return jsonify({
        'high_contrast': True,
        'keyboard_navigation': True,
        'aria_labels': True
    })

@app.route('/api/info/privacy', methods=["GET"])
def privacy_info():
    """Explain how user data is used on device."""
    return jsonify({
        'local_data': True,
        'cloud_sync': False,
        'encryption_in_transit': True,
        'encryption_at_rest': False
    })

# --- DB Initialization (for dev/demo) ---
@app.cli.command("init-db")
def init_db_cmd():
    db.drop_all()
    db.create_all()
    print("Database initialized.")

if __name__ == "__main__":
    app.run(port=5000, debug=True)
