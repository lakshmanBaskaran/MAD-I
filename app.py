from flask import Flask, redirect, url_for, render_template, request, flash
from flask_login import (
    LoginManager,
    current_user,
    login_user,
    logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash

from db import init_db, get_db
from admin_routes import init_admin_routes
from doctor_routes import init_doctor_routes
from patient_routes import init_patient_routes

# ------------------------------------------------
# App & DB setup
# ------------------------------------------------

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key"

# Initialize database (create tables + default admin)
init_db()

# ------------------------------------------------
# Flask-Login setup + User model
# ------------------------------------------------

login_manager = LoginManager(app)
login_manager.login_view = "login"


class UserMixinWrapper:
    """Minimal wrapper to avoid importing UserMixin separately."""

    def __init__(self):
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        return str(self.id)


class User(UserMixinWrapper):
    """Wraps a row from the users table for Flask-Login."""

    def __init__(self, row):
        super().__init__()
        self.id = row["id"]
        self.email = row["email"]
        self.role = row["role"]
        self.status = row["status"]


@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return User(row)
    return None


# ------------------------------------------------
# Index route (role-based redirect)
# ------------------------------------------------

@app.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        elif current_user.role == "doctor":
            return redirect(url_for("doctor_dashboard"))
        else:
            return redirect(url_for("patient_dashboard"))
    return redirect(url_for("login"))


# ------------------------------------------------
# Auth routes (login / logout / register)
# ------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        conn.close()

        if row and check_password_hash(row["password_hash"], password):
            if row["status"] != "active":
                flash("Your account is not active. Please contact hospital staff.", "warning")
                return redirect(url_for("login"))
            user = User(row)
            login_user(user)
            return redirect(url_for("index"))
        else:
            flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Patient registration."""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()

        if not email or not password or not name:
            flash("Please fill all required fields.", "danger")
            return redirect(url_for("register"))

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cur.fetchone():
            flash("Email already registered.", "warning")
            conn.close()
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)
        cur.execute(
            "INSERT INTO users (email, password_hash, role, status) "
            "VALUES (?, ?, 'patient', 'active')",
            (email, password_hash),
        )
        user_id = cur.lastrowid

        cur.execute(
            "INSERT INTO patient_profiles (user_id, name) VALUES (?, ?)",
            (user_id, name),
        )

        conn.commit()
        conn.close()

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# ------------------------------------------------
# Register other route groups
# ------------------------------------------------

init_admin_routes(app)
init_doctor_routes(app)
init_patient_routes(app)


if __name__ == "__main__":
    app.run(debug=True)
