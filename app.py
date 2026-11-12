import json
import os
import secrets
import string
import uuid
from functools import wraps

from flask import (
    Flask, abort, flash, g, redirect, render_template, request,
    send_from_directory, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

import ledger
from db import close_db, get_db, init_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
ID_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-before-launch"),
        DATABASE=os.environ.get("DATABASE", os.path.join(BASE_DIR, "registry.sqlite3")),
        UPLOAD_DIR=os.environ.get("UPLOAD_DIR", os.path.join(BASE_DIR, "uploads")),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)
    app.teardown_appcontext(close_db)
    init_db(app)

    @app.template_filter("from_json")
    def from_json(value):
        return json.loads(value)

    def db():
        return get_db()

    def current_user():
        uid = session.get("user_id")
        if uid is None:
            return None
        return db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if current_user() is None:
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)
        return wrapped

    def allowed_file(name):
        return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    def save_upload(file_storage):
        ext = file_storage.filename.rsplit(".", 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        file_storage.save(os.path.join(app.config["UPLOAD_DIR"], filename))
        return filename

    def new_registration_id():
        while True:
            body = "".join(secrets.choice(ID_ALPHABET) for _ in range(10))
            candidate = f"CRN-{body[:5]}-{body[5:]}"
            exists = db().execute(
                "SELECT 1 FROM objects WHERE registration_id = ?", (candidate,)
            ).fetchone()
            if not exists:
                return candidate

    def get_object(reg_id):
        obj = db().execute(
            "SELECT o.*, u.display_name AS owner_name"
            " FROM objects o JOIN users u ON u.id = o.owner_id"
            " WHERE o.registration_id = ?",
            (reg_id,),
        ).fetchone()
        if obj is None:
            abort(404)
        return obj

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/signup", methods=("GET", "POST"))
    def signup():
        if request.method == "POST":
            email = request.form["email"].strip().lower()
            display_name = request.form["display_name"].strip()
            password = request.form["password"]
            error = None
            if not email or "@" not in email:
                error = "A valid email address is required."
            elif not display_name:
                error = "A display name is required."
            elif len(password) < 10:
                error = "Password must be at least 10 characters."
            if error is None:
                try:
                    cur = db().execute(
                        "INSERT INTO users (email, password_hash, display_name)"
                        " VALUES (?, ?, ?)",
                        (email, generate_password_hash(password), display_name),
                    )
                    db().commit()
                except Exception:
                    error = "That email is already registered."
                else:
                    session["user_id"] = cur.lastrowid
                    return redirect(url_for("dashboard"))
            flash(error)
        return render_template("signup.html")

    @app.route("/login", methods=("GET", "POST"))
    def login():
        if request.method == "POST":
            email = request.form["email"].strip().lower()
            password = request.form["password"]
            user = db().execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()
            if user is None or not check_password_hash(user["password_hash"], password):
                flash("Incorrect email or password.")
            else:
                session["user_id"] = user["id"]
                destination = request.args.get("next", url_for("dashboard"))
                if not destination.startswith("/"):
                    destination = url_for("dashboard")
                return redirect(destination)
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("index"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        user = current_user()
        objects = db().execute(
            "SELECT * FROM objects WHERE owner_id = ? ORDER BY created_at DESC",
            (user["id"],),
        ).fetchall()
        return render_template("dashboard.html", user=user, objects=objects)

    @app.route("/objects/new", methods=("GET", "POST"))
    @login_required
    def new_object():
        if request.method == "POST":
            user = current_user()
            category = request.form["category"].strip()
            title = request.form["title"].strip()
            description = request.form.get("description", "").strip()
            attributes = {}
            for key, value in request.form.items():
                if key.startswith("attr_") and value.strip():
                    attributes[key[5:]] = value.strip()
            if not title or not category:
                flash("Category and title are required.")
            else:
                reg_id = new_registration_id()
                cur = db().execute(
                    "INSERT INTO objects (registration_id, owner_id, category,"
                    " title, description, attributes_json)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (reg_id, user["id"], category, title, description,
                     json.dumps(attributes, sort_keys=True)),
                )
                object_id = cur.lastrowid
                for file_storage in request.files.getlist("photos"):
                    if file_storage and file_storage.filename and allowed_file(file_storage.filename):
                        filename = save_upload(file_storage)
                        db().execute(
                            "INSERT INTO photos (object_id, filename, uploaded_by)"
                            " VALUES (?, ?, ?)",
                            (object_id, filename, user["id"]),
                        )
                details = {"title": title, "category": category, "attributes": attributes}
                ledger.append_event(db(), object_id, user["id"], "registration", details)
                db().commit()
                flash(f"Object registered. Your permanent registration ID is {reg_id}.")
                return redirect(url_for("object_profile", reg_id=reg_id))
        return render_template("new_object.html")

    @app.route("/objects/<reg_id>")
    def object_profile(reg_id):
        obj = get_object(reg_id)
        photos = db().execute(
            "SELECT * FROM photos WHERE object_id = ? ORDER BY id", (obj["id"],)
        ).fetchall()
        events = db().execute(
            "SELECT e.*, u.display_name AS actor_name FROM events e"
            " LEFT JOIN users u ON u.id = e.actor_id"
            " WHERE e.object_id = ? ORDER BY e.id",
            (obj["id"],),
        ).fetchall()
        chain_ok, broken_at = ledger.verify_chain(db(), obj["id"])
        return render_template(
            "object.html", obj=obj, photos=photos, events=events,
            chain_ok=chain_ok, broken_at=broken_at,
        )

    @app.route("/objects/<reg_id>/events", methods=("POST",))
    @login_required
    def add_event(reg_id):
        obj = get_object(reg_id)
        user = current_user()
        if obj["owner_id"] != user["id"]:
            abort(403)
        event_type = request.form["event_type"]
        allowed_types = {
            "ownership_claim", "custody_transfer_claim", "condition_note", "note",
        }
        if event_type not in allowed_types:
            abort(400)
        details = {"text": request.form.get("details", "").strip()}
        evidence_filename = None
        file_storage = request.files.get("evidence")
        if file_storage and file_storage.filename and allowed_file(file_storage.filename):
            evidence_filename = save_upload(file_storage)
        ledger.append_event(
            db(), obj["id"], user["id"], event_type, details,
            evidence_filename=evidence_filename,
        )
        db().commit()
        flash("Custody event recorded as an unverified claim.")
        return redirect(url_for("object_profile", reg_id=reg_id))

    @app.route("/objects/<reg_id>/events/<int:event_id>/verify", methods=("POST",))
    @login_required
    def verify_event(reg_id, event_id):
        user = current_user()
        if not user["is_verifier"]:
            abort(403)
        obj = get_object(reg_id)
        event = db().execute(
            "SELECT * FROM events WHERE id = ? AND object_id = ?",
            (event_id, obj["id"]),
        ).fetchone()
        if event is None:
            abort(404)
        db().execute(
            "UPDATE events SET status = 'verified' WHERE id = ?", (event_id,)
        )
        ledger.append_event(
            db(), obj["id"], user["id"], "verification",
            {"verified_event_id": event_id, "verified_event_type": event["event_type"]},
            status="verified",
        )
        db().commit()
        flash("Event marked as verified. This decision is itself recorded in the ledger.")
        return redirect(url_for("object_profile", reg_id=reg_id))

    @app.route("/uploads/<filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_DIR"], filename)

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", message="Page not found."), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", message="You are not allowed to do that."), 403

    @app.cli.command("init-db")
    def init_db_command():
        init_db(app)
        print("Database initialized.")

    @app.cli.command("make-verifier")
    def make_verifier_command():
        email = input("Email of the account to make a verifier: ").strip().lower()
        cur = db().execute("UPDATE users SET is_verifier = 1 WHERE email = ?", (email,))
        db().commit()
        print(f"{cur.rowcount} account(s) updated.")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
