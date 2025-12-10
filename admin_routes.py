from flask import render_template, request, redirect, url_for, flash

from db import get_db
from security import role_required


def init_admin_routes(app):
    @app.route("/admin/dashboard")
    @role_required("admin")
    def admin_dashboard():
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) AS c FROM doctor_profiles")
        doctor_count = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) AS c FROM patient_profiles")
        patient_count = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) AS c FROM appointments")
        appointment_count = cur.fetchone()["c"]

        doc_q = request.args.get("doc_q", "").strip()
        pat_q = request.args.get("pat_q", "").strip()
        appt_status = request.args.get("status", "").strip()

        if doc_q:
            like = f"%{doc_q}%"
            cur.execute(
                """
                SELECT dp.id,
                       dp.name,
                       dp.specialization,
                       dp.phone,
                       dp.department_id,
                       d.name AS department_name,
                       u.email,
                       u.status,
                       u.id AS user_id
                FROM doctor_profiles dp
                JOIN users u ON dp.user_id = u.id
                LEFT JOIN departments d ON dp.department_id = d.id
                WHERE dp.name LIKE ?
                   OR dp.specialization LIKE ?
                   OR d.name LIKE ?
                ORDER BY dp.name
                """,
                (like, like, like),
            )
        else:
            cur.execute(
                """
                SELECT dp.id,
                       dp.name,
                       dp.specialization,
                       dp.phone,
                       dp.department_id,
                       d.name AS department_name,
                       u.email,
                       u.status,
                       u.id AS user_id
                FROM doctor_profiles dp
                JOIN users u ON dp.user_id = u.id
                LEFT JOIN departments d ON dp.department_id = d.id
                ORDER BY dp.name
                """,
            )
        doctors = cur.fetchall()

        if pat_q:
            like = f"%{pat_q}%"
            try:
                pid = int(pat_q)
            except ValueError:
                pid = -1
            cur.execute(
                """
                SELECT p.id,
                       p.name,
                       p.age,
                       p.gender,
                       p.phone,
                       p.address,
                       u.email,
                       u.status,
                       u.id AS user_id
                FROM patient_profiles p
                JOIN users u ON p.user_id = u.id
                WHERE p.name LIKE ?
                   OR p.phone LIKE ?
                   OR u.email LIKE ?
                   OR p.id = ?
                ORDER BY p.name
                """,
                (like, like, like, pid),
            )
        else:
            cur.execute(
                """
                SELECT p.id,
                       p.name,
                       p.age,
                       p.gender,
                       p.phone,
                       p.address,
                       u.email,
                       u.status,
                       u.id AS user_id
                FROM patient_profiles p
                JOIN users u ON p.user_id = u.id
                ORDER BY p.name
                """,
            )
        patients = cur.fetchall()

        if appt_status:
            cur.execute(
                """
                SELECT a.id,
                       a.date,
                       a.time,
                       a.status,
                       a.created_at,
                       d.name AS doctor_name,
                       p.name AS patient_name
                FROM appointments a
                JOIN doctor_profiles d ON a.doctor_id = d.id
                JOIN patient_profiles p ON a.patient_id = p.id
                WHERE a.status = ?
                ORDER BY a.date DESC, a.time DESC
                """,
                (appt_status,),
            )
        else:
            cur.execute(
                """
                SELECT a.id,
                       a.date,
                       a.time,
                       a.status,
                       a.created_at,
                       d.name AS doctor_name,
                       p.name AS patient_name
                FROM appointments a
                JOIN doctor_profiles d ON a.doctor_id = d.id
                JOIN patient_profiles p ON a.patient_id = p.id
                ORDER BY a.date DESC, a.time DESC
                """,
            )
        appointments = cur.fetchall()

        conn.close()

        return render_template(
            "admin/dashboard.html",
            doctor_count=doctor_count,
            patient_count=patient_count,
            appointment_count=appointment_count,
            doctors=doctors,
            patients=patients,
            appointments=appointments,
            doc_q=doc_q,
            pat_q=pat_q,
            status=appt_status,
        )

    @app.route("/admin/doctors")
    @role_required("admin")
    def admin_doctors():
        q = request.args.get("q", "").strip()
        conn = get_db()
        cur = conn.cursor()

        base_query = """
            SELECT d.*, u.email, u.status, dept.name AS department_name
            FROM doctor_profiles d
            JOIN users u ON d.user_id = u.id
            LEFT JOIN departments dept ON d.department_id = dept.id
        """
        params = []

        if q:
            base_query += " WHERE d.name LIKE ? OR d.specialization LIKE ? OR dept.name LIKE ?"
            like = f"%{q}%"
            params = [like, like, like]

        base_query += " ORDER BY d.name"
        cur.execute(base_query, params)
        doctors = cur.fetchall()
        conn.close()
        return render_template("admin/doctors_list.html", doctors=doctors, q=q)

    @app.route("/admin/doctors/new", methods=["GET", "POST"])
    @role_required("admin")
    def admin_add_doctor():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM departments ORDER BY name")
        departments = cur.fetchall()

        if request.method == "POST":
            from werkzeug.security import generate_password_hash

            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            name = request.form.get("name", "").strip()
            specialization = request.form.get("specialization", "").strip()
            department_id = request.form.get("department_id") or None
            phone = request.form.get("phone", "").strip()
            bio = request.form.get("bio", "").strip()

            if not email or not password or not name:
                flash("Email, password and name are required.", "danger")
                conn.close()
                return redirect(url_for("admin_add_doctor"))

            cur.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cur.fetchone():
                flash("Email already in use.", "warning")
                conn.close()
                return redirect(url_for("admin_add_doctor"))

            password_hash = generate_password_hash(password)
            cur.execute(
                "INSERT INTO users (email, password_hash, role, status) "
                "VALUES (?, ?, 'doctor', 'active')",
                (email, password_hash),
            )
            user_id = cur.lastrowid

            cur.execute(
                """
                INSERT INTO doctor_profiles (user_id, department_id, name, specialization, phone, bio)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, department_id, name, specialization, phone, bio),
            )

            conn.commit()
            conn.close()
            flash("Doctor created successfully.", "success")
            return redirect(url_for("admin_dashboard"))

        conn.close()
        return render_template("admin/doctor_form.html", departments=departments, doctor=None)

    @app.route("/admin/doctors/<int:doctor_id>/edit", methods=["GET", "POST"])
    @role_required("admin")
    def admin_edit_doctor(doctor_id):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM departments ORDER BY name")
        departments = cur.fetchall()

        cur.execute(
            """
            SELECT d.*, u.email
            FROM doctor_profiles d
            JOIN users u ON d.user_id = u.id
            WHERE d.id = ?
            """,
            (doctor_id,),
        )
        doctor = cur.fetchone()
        if not doctor:
            conn.close()
            flash("Doctor not found.", "danger")
            return redirect(url_for("admin_dashboard"))

        if request.method == "POST":
            from werkzeug.security import generate_password_hash

            email = request.form.get("email", "").strip()
            name = request.form.get("name", "").strip()
            specialization = request.form.get("specialization", "").strip()
            department_id = request.form.get("department_id") or None
            phone = request.form.get("phone", "").strip()
            bio = request.form.get("bio", "").strip()
            new_password = request.form.get("password", "")

            if not email or not name:
                flash("Email and name are required.", "danger")
                conn.close()
                return redirect(url_for("admin_edit_doctor", doctor_id=doctor_id))

            if new_password:
                password_hash = generate_password_hash(new_password)
                cur.execute(
                    "UPDATE users SET email = ?, password_hash = ? WHERE id = ?",
                    (email, password_hash, doctor["user_id"]),
                )
            else:
                cur.execute(
                    "UPDATE users SET email = ? WHERE id = ?",
                    (email, doctor["user_id"]),
                )

            cur.execute(
                """
                UPDATE doctor_profiles
                SET name = ?, specialization = ?, department_id = ?, phone = ?, bio = ?
                WHERE id = ?
                """,
                (name, specialization, department_id, phone, bio, doctor_id),
            )

            conn.commit()
            conn.close()
            flash("Doctor updated successfully.", "success")
            return redirect(url_for("admin_dashboard"))

        conn.close()
        return render_template(
            "admin/doctor_form.html",
            departments=departments,
            doctor=doctor,
        )

    @app.route("/admin/patients")
    @role_required("admin")
    def admin_patients():
        q = request.args.get("q", "").strip()
        conn = get_db()
        cur = conn.cursor()

        base_query = """
            SELECT p.*, u.email, u.status
            FROM patient_profiles p
            JOIN users u ON p.user_id = u.id
        """
        params = []
        if q:
            base_query += " WHERE p.name LIKE ? OR p.phone LIKE ? OR u.email LIKE ? OR p.id = ?"
            like = f"%{q}%"
            try:
                pid = int(q)
            except ValueError:
                pid = -1
            params = [like, like, like, pid]

        base_query += " ORDER BY p.name"
        cur.execute(base_query, params)
        patients = cur.fetchall()
        conn.close()
        return render_template("admin/patients_list.html", patients=patients, q=q)

    @app.route("/admin/patients/<int:patient_id>/edit", methods=["GET", "POST"])
    @role_required("admin")
    def admin_edit_patient(patient_id):
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT p.*, u.email
            FROM patient_profiles p
            JOIN users u ON p.user_id = u.id
            WHERE p.id = ?
            """,
            (patient_id,),
        )
        patient = cur.fetchone()
        if not patient:
            conn.close()
            flash("Patient not found.", "danger")
            return redirect(url_for("admin_dashboard"))

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            age = request.form.get("age") or None
            gender = request.form.get("gender", "").strip()
            phone = request.form.get("phone", "").strip()
            address = request.form.get("address", "").strip()
            emergency_contact = request.form.get("emergency_contact", "").strip()
            email = request.form.get("email", "").strip()

            if not name or not email:
                flash("Name and email are required.", "danger")
                conn.close()
                return redirect(url_for("admin_edit_patient", patient_id=patient_id))

            cur.execute(
                """
                UPDATE patient_profiles
                SET name = ?, age = ?, gender = ?, phone = ?, address = ?, emergency_contact = ?
                WHERE id = ?
                """,
                (name, age, gender, phone, address, emergency_contact, patient_id),
            )

            cur.execute(
                "UPDATE users SET email = ? WHERE id = ?",
                (email, patient["user_id"]),
            )

            conn.commit()
            conn.close()
            flash("Patient updated successfully.", "success")
            return redirect(url_for("admin_dashboard"))

        conn.close()
        return render_template("admin/patient_form.html", patient=patient)

    @app.route("/admin/users/<int:user_id>/toggle_status", methods=["POST"])
    @role_required("admin")
    def admin_toggle_user_status(user_id):
        from flask import request as _req

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT status FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            flash("User not found.", "danger")
            return redirect(_req.referrer or url_for("admin_dashboard"))

        new_status = "blacklisted" if row["status"] == "active" else "active"
        cur.execute("UPDATE users SET status = ? WHERE id = ?", (new_status, user_id))
        conn.commit()
        conn.close()
        flash(f"User status updated to {new_status}.", "success")
        return redirect(_req.referrer or url_for("admin_dashboard"))

    @app.route("/admin/appointments")
    @role_required("admin")
    def admin_appointments():
        status = request.args.get("status", "").strip()
        conn = get_db()
        cur = conn.cursor()

        query = """
            SELECT a.*, d.name AS doctor_name, p.name AS patient_name
            FROM appointments a
            JOIN doctor_profiles d ON a.doctor_id = d.id
            JOIN patient_profiles p ON a.patient_id = p.id
        """
        params = []
        if status:
            query += " WHERE a.status = ?"
            params.append(status)
        query += " ORDER BY a.date DESC, a.time DESC"

        cur.execute(query, params)
        appointments = cur.fetchall()
        conn.close()
        return render_template(
            "admin/appointments_list.html",
            appointments=appointments,
            status=status,
        )
