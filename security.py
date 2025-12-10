# security.py
from functools import wraps

from flask import redirect, url_for, flash
from flask_login import login_required, current_user

from db import get_db


def role_required(role):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role != role:
                flash("You are not authorized to view this page.", "danger")
                return redirect(url_for("index"))
            if current_user.status != "active":
                flash("Your account is not active. Please contact hospital staff.", "warning")
                return redirect(url_for("logout"))
            return view_func(*args, **kwargs)
        return wrapped
    return decorator


def get_doctor_profile_for_current_user():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM doctor_profiles WHERE user_id = ?", (current_user.id,))
    doc = cur.fetchone()
    conn.close()
    return doc


def get_patient_profile_for_current_user():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM patient_profiles WHERE user_id = ?", (current_user.id,))
    patient = cur.fetchone()
    conn.close()
    return patient
