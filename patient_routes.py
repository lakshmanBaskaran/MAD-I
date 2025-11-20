from datetime import date, datetime, timedelta

from flask import render_template, request, redirect, url_for, flash

from db import get_db
from security import (
    role_required,
    get_doctor_profile_for_current_user,
    get_patient_profile_for_current_user,
)


def init_patient_routes(app):

    # ==========================
    # DASHBOARD
    # ==========================
    @app.route("/patient/dashboard")
    @role_required("patient")
    def patient_dashboard():
        patient = get_patient_profile_for_current_user()
        if not patient:
            flash("Patient profile not found.", "danger")
            return redirect(url_for("logout"))

        today_str = date.today().isoformat()

        conn = get_db()
        cur = conn.cursor()

        # All departments (for display / filtering if needed)
        cur.execute("SELECT * FROM departments ORDER BY name")
        departments = cur.fetchall()

        # Upcoming appointments
        cur.execute(
            """
            SELECT a.*, d.name AS doctor_name
            FROM appointments a
            JOIN doctor_profiles d ON a.doctor_id = d.id
            WHERE a.patient_id = ? AND a.date >= ?
            ORDER BY a.date, a.time
            """,
            (patient["id"], today_str),
        )
        upcoming = cur.fetchall()

        # Past appointments + treatments
        cur.execute(
            """
            SELECT a.*, d.name AS doctor_name, t.diagnosis, t.prescription
            FROM appointments a
            JOIN doctor_profiles d ON a.doctor_id = d.id
            LEFT JOIN treatments t ON t.appointment_id = a.id
            WHERE a.patient_id = ? AND a.date < ?
            ORDER BY a.date DESC, a.time DESC
            """,
            (patient["id"], today_str),
        )
        past = cur.fetchall()

        conn.close()
        return render_template(
            "patient/dashboard.html",
            patient=patient,
            departments=departments,
            upcoming=upcoming,
            past=past,
        )

    # ==========================
    # PROFILE
    # ==========================
    @app.route("/patient/profile", methods=["GET", "POST"])
    @role_required("patient")
    def patient_profile():
        patient = get_patient_profile_for_current_user()
        if not patient:
            flash("Patient profile not found.", "danger")
            return redirect(url_for("logout"))

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT email FROM users WHERE id = ?", (patient["user_id"],))
        user_row = cur.fetchone()
        email = user_row["email"] if user_row else ""

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            age = request.form.get("age") or None
            gender = request.form.get("gender", "").strip()
            phone = request.form.get("phone", "").strip()
            address = request.form.get("address", "").strip()
            emergency_contact = request.form.get("emergency_contact", "").strip()
            new_email = request.form.get("email", "").strip()

            if not name or not new_email:
                flash("Name and email are required.", "danger")
            else:
                cur.execute(
                    """
                    UPDATE patient_profiles
                    SET name = ?, age = ?, gender = ?, phone = ?, address = ?, emergency_contact = ?
                    WHERE id = ?
                    """,
                    (name, age, gender, phone, address, emergency_contact, patient["id"]),
                )
                cur.execute(
                    "UPDATE users SET email = ? WHERE id = ?",
                    (new_email, patient["user_id"]),
                )
                conn.commit()
                flash("Profile updated.", "success")

        conn.close()
        patient = get_patient_profile_for_current_user()
        return render_template("patient/profile.html", patient=patient, email=email)

    # ==========================
    # DOCTORS LIST + SEARCH
    # ==========================
    @app.route("/patient/doctors")
    @role_required("patient")
    def patient_doctors():
        """Search doctors by name/specialization/department."""
        q = request.args.get("q", "").strip()
        conn = get_db()
        cur = conn.cursor()

        base_query = """
            SELECT d.*, dept.name AS department_name
            FROM doctor_profiles d
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
        return render_template("patient/doctors_list.html", doctors=doctors, q=q)

    # ==========================
    # DOCTOR AVAILABILITY (NEXT 7 DAYS)
    # ==========================
    @app.route("/patient/doctors/<int:doctor_id>/availability")
    @role_required("patient")
    def patient_doctor_availability(doctor_id):
        """Show doctor's availability for the next 7 days, excluding already booked slots."""
        conn = get_db()
        cur = conn.cursor()

        # Doctor + department info
        cur.execute(
            """
            SELECT d.*, dept.name AS department_name
            FROM doctor_profiles d
            LEFT JOIN departments dept ON d.department_id = dept.id
            WHERE d.id = ?
            """,
            (doctor_id,),
        )
        doctor = cur.fetchone()
        if not doctor:
            conn.close()
            flash("Doctor not found.", "danger")
            return redirect(url_for("patient_doctors"))

        today_str = date.today().isoformat()
        next_week_str = (date.today() + timedelta(days=7)).isoformat()

        # Only slots that:
        #  - exist in doctor_availability
        #  - are marked as is_available = 1
        #  - are within [today, today+7 days]
        #  - have NO booked appointment at that doctor/date/time
        cur.execute(
            """
            SELECT da.date, da.time
            FROM doctor_availability da
            LEFT JOIN appointments a
              ON a.doctor_id = da.doctor_id
             AND a.date = da.date
             AND a.time = da.time
             AND a.status = 'Booked'
            WHERE da.doctor_id = ?
              AND da.is_available = 1
              AND date(da.date) >= date(?)
              AND date(da.date) <= date(?)
              AND a.id IS NULL
            ORDER BY da.date, da.time
            """,
            (doctor_id, today_str, next_week_str),
        )
        slots = cur.fetchall()

        # Current patient's existing appointments with this doctor (for display)
        patient = get_patient_profile_for_current_user()
        appointments = []
        if patient:
            cur.execute(
                """
                SELECT date, time, status
                FROM appointments
                WHERE patient_id = ? AND doctor_id = ?
                ORDER BY date, time
                """,
                (patient["id"], doctor_id),
            )
            appointments = cur.fetchall()

        conn.close()
        return render_template(
            "patient/doctor_availability.html",
            doctor=doctor,
            slots=slots,
            appointments=appointments,
        )

    # ==========================
    # BOOK FROM AVAILABILITY PAGE (POST ONLY)
    # ==========================
    @app.route("/patient/book", methods=["POST"])
    @role_required("patient")
    def patient_book_appointment():
        """Book an appointment from the doctor_availability page."""
        doctor_id = request.form.get("doctor_id")
        date_str = request.form.get("date")
        time_str = request.form.get("time")

        if not doctor_id or not date_str or not time_str:
            flash("Invalid booking request.", "danger")
            return redirect(url_for("patient_dashboard"))

        try:
            doctor_id = int(doctor_id)
        except ValueError:
            flash("Invalid doctor.", "danger")
            return redirect(url_for("patient_dashboard"))

        patient = get_patient_profile_for_current_user()
        if not patient:
            flash("Patient profile not found.", "danger")
            return redirect(url_for("logout"))

        conn = get_db()
        cur = conn.cursor()

        # 1) Verify that the requested slot is actually available:
        #    - Exists in doctor_availability
        #    - is_available = 1
        #    - No existing Booked appointment for that doctor/date/time
        cur.execute(
            """
            SELECT da.id
            FROM doctor_availability da
            LEFT JOIN appointments a
              ON a.doctor_id = da.doctor_id
             AND a.date = da.date
             AND a.time = da.time
             AND a.status = 'Booked'
            WHERE da.doctor_id = ?
              AND da.date = ?
              AND da.time = ?
              AND da.is_available = 1
              AND a.id IS NULL
            """,
            (doctor_id, date_str, time_str),
        )
        slot = cur.fetchone()
        if not slot:
            conn.close()
            flash("Selected slot is no longer available. Please choose another.", "warning")
            return redirect(url_for("patient_doctor_availability", doctor_id=doctor_id))

        # 2) Insert the appointment (UNIQUE(doctor_id, date, time) in schema still protects us)
        created_at = datetime.now().isoformat(timespec="seconds")

        cur.execute(
            """
            INSERT INTO appointments (patient_id, doctor_id, department_id, date, time, status, created_at)
            VALUES (
                ?, ?,
                (SELECT department_id FROM doctor_profiles WHERE id = ?),
                ?, ?, 'Booked', ?
            )
            """,
            (
                patient["id"],
                doctor_id,
                doctor_id,
                date_str,
                time_str,
                created_at,
            ),
        )

        conn.commit()
        conn.close()

        flash("Appointment booked successfully.", "success")
        return redirect(url_for("patient_dashboard"))

    # ==========================
    # OLD BOOK APPOINTMENT PAGE (OPTIONAL, STILL KEPT)
    # ==========================
    @app.route("/patient/appointments/book/<int:doctor_id>", methods=["GET", "POST"])
    @role_required("patient")
    def book_appointment(doctor_id):
        """Separate book page (if you still use it)."""
        patient = get_patient_profile_for_current_user()
        if not patient:
            flash("Patient profile not found.", "danger")
            return redirect(url_for("logout"))

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM doctor_profiles WHERE id = ?", (doctor_id,))
        doctor = cur.fetchone()
        if not doctor:
            conn.close()
            flash("Doctor not found.", "danger")
            return redirect(url_for("patient_doctors"))

        if request.method == "POST":
            date_str = request.form.get("date")
            time_str = request.form.get("time")

            if not date_str or not time_str:
                flash("Please select date and time.", "danger")
                conn.close()
                return redirect(url_for("book_appointment", doctor_id=doctor_id))

            # Check that slot is in availability
            cur.execute(
                """
                SELECT id FROM doctor_availability
                WHERE doctor_id = ? AND date = ? AND time = ? AND is_available = 1
                """,
                (doctor_id, date_str, time_str),
            )
            if not cur.fetchone():
                flash("Selected slot is not available.", "warning")
                conn.close()
                return redirect(url_for("book_appointment", doctor_id=doctor_id))

            # Check for double booking (same doctor/date/time)
            cur.execute(
                """
                SELECT id FROM appointments
                WHERE doctor_id = ? AND date = ? AND time = ?
                """,
                (doctor_id, date_str, time_str),
            )
            if cur.fetchone():
                flash("This slot is already booked. Please choose another.", "warning")
                conn.close()
                return redirect(url_for("book_appointment", doctor_id=doctor_id))

            created_at = datetime.now().isoformat(timespec="seconds")
            cur.execute(
                """
                INSERT INTO appointments (patient_id, doctor_id, department_id, date, time, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'Booked', ?)
                """,
                (patient["id"], doctor_id, doctor["department_id"], date_str, time_str, created_at),
            )
            conn.commit()
            conn.close()
            flash("Appointment booked successfully.", "success")
            return redirect(url_for("patient_dashboard"))

        conn.close()
        return render_template("patient/book_appointment.html", doctor=doctor)

    # ==========================
    # VIEW ALL APPOINTMENTS
    # ==========================
    @app.route("/patient/appointments")
    @role_required("patient")
    def patient_appointments():
        patient = get_patient_profile_for_current_user()
        if not patient:
            flash("Patient profile not found.", "danger")
            return redirect(url_for("logout"))

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT a.*, d.name AS doctor_name
            FROM appointments a
            JOIN doctor_profiles d ON a.doctor_id = d.id
            WHERE a.patient_id = ?
            ORDER BY a.date DESC, a.time DESC
            """,
            (patient["id"],),
        )
        appointments = cur.fetchall()
        conn.close()
        return render_template("patient/appointments.html", appointments=appointments)

    # ==========================
    # CANCEL APPOINTMENT
    # ==========================
    @app.route("/patient/appointments/<int:appointment_id>/cancel", methods=["POST"])
    @role_required("patient")
    def cancel_appointment(appointment_id):
        patient = get_patient_profile_for_current_user()
        if not patient:
            flash("Patient profile not found.", "danger")
            return redirect(url_for("logout"))

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, status FROM appointments
            WHERE id = ? AND patient_id = ?
            """,
            (appointment_id, patient["id"]),
        )
        appt = cur.fetchone()
        if not appt:
            conn.close()
            flash("Appointment not found.", "danger")
            return redirect(url_for("patient_appointments"))

        if appt["status"] == "Cancelled":
            flash("Appointment is already cancelled.", "info")
        else:
            cur.execute(
                "UPDATE appointments SET status = 'Cancelled' WHERE id = ?",
                (appointment_id,),
            )
            conn.commit()
            flash("Appointment cancelled.", "success")

        conn.close()
        return redirect(url_for("patient_appointments"))

    # ==========================
    # RESCHEDULE APPOINTMENT
    # ==========================
    @app.route("/patient/appointments/<int:appointment_id>/reschedule", methods=["GET", "POST"])
    @role_required("patient")
    def reschedule_appointment(appointment_id):
        patient = get_patient_profile_for_current_user()
        if not patient:
            flash("Patient profile not found.", "danger")
            return redirect(url_for("logout"))

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT a.*, d.name AS doctor_name
            FROM appointments a
            JOIN doctor_profiles d ON a.doctor_id = d.id
            WHERE a.id = ? AND a.patient_id = ?
            """,
            (appointment_id, patient["id"]),
        )
        appt = cur.fetchone()
        if not appt:
            conn.close()
            flash("Appointment not found.", "danger")
            return redirect(url_for("patient_appointments"))

        if request.method == "POST":
            date_str = request.form.get("date")
            time_str = request.form.get("time")

            if not date_str or not time_str:
                flash("Please select date and time.", "danger")
                conn.close()
                return redirect(url_for("reschedule_appointment", appointment_id=appointment_id))

            # Check availability table
            cur.execute(
                """
                SELECT id FROM doctor_availability
                WHERE doctor_id = ? AND date = ? AND time = ? AND is_available = 1
                """,
                (appt["doctor_id"], date_str, time_str),
            )
            if not cur.fetchone():
                flash("Selected slot is not available.", "warning")
                conn.close()
                return redirect(url_for("reschedule_appointment", appointment_id=appointment_id))

            # Check double booking (another appointment)
            cur.execute(
                """
                SELECT id FROM appointments
                WHERE doctor_id = ? AND date = ? AND time = ? AND id != ?
                """,
                (appt["doctor_id"], date_str, time_str, appointment_id),
            )
            if cur.fetchone():
                flash("This slot is already booked. Please choose another.", "warning")
                conn.close()
                return redirect(url_for("reschedule_appointment", appointment_id=appointment_id))

            cur.execute(
                """
                UPDATE appointments
                SET date = ?, time = ?, status = 'Booked'
                WHERE id = ?
                """,
                (date_str, time_str, appointment_id),
            )
            conn.commit()
            conn.close()
            flash("Appointment rescheduled.", "success")
            return redirect(url_for("patient_appointments"))

        conn.close()
        return render_template("patient/reschedule_appointment.html", appointment=appt)
