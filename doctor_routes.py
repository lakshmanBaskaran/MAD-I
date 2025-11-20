# doctor_routes.py
from datetime import date, timedelta

from flask import render_template, request, redirect, url_for, flash

from db import get_db
from security import role_required, get_doctor_profile_for_current_user


def init_doctor_routes(app):

    @app.route("/doctor/dashboard", methods=["GET", "POST"])
    @role_required("doctor")
    def doctor_dashboard():
        doctor = get_doctor_profile_for_current_user()
        if not doctor:
            flash("No doctor profile found. Contact admin.", "danger")
            return redirect(url_for("index"))

        conn = get_db()
        cur = conn.cursor()

        # ---------------------------------------------------
        # Handle actions (POST): add slot, update appointment
        # ---------------------------------------------------
        if request.method == "POST":
            action = request.form.get("action")

            if action == "add_slot":
                d = request.form.get("date")
                t = request.form.get("time")

                if not d or not t:
                    flash("Please provide both date and time.", "warning")
                else:
                    try:
                        # Ensure date is within next 7 days (optional, but nice)
                        today = date.today()
                        slot_date = date.fromisoformat(d)
                        if slot_date < today or slot_date > today + timedelta(days=7):
                            flash("Availability must be within the next 7 days.", "warning")
                        else:
                            cur.execute(
                                """
                                SELECT id FROM doctor_availability
                                WHERE doctor_id = ? AND date = ? AND time = ?
                                """,
                                (doctor["id"], d, t),
                            )
                            if cur.fetchone():
                                flash("This slot already exists.", "info")
                            else:
                                cur.execute(
                                    """
                                    INSERT INTO doctor_availability (doctor_id, date, time, is_available)
                                    VALUES (?, ?, ?, 1)
                                    """,
                                    (doctor["id"], d, t),
                                )
                                conn.commit()
                                flash("Availability slot added.", "success")
                    except ValueError:
                        flash("Invalid date format.", "danger")

            elif action == "update_appointment":
                appt_id = request.form.get("appointment_id")
                status = request.form.get("status")
                diagnosis = request.form.get("diagnosis", "").strip()
                prescription = request.form.get("prescription", "").strip()
                notes = request.form.get("notes", "").strip()

                if not appt_id or not status:
                    flash("Invalid appointment update.", "danger")
                else:
                    # Make sure appointment belongs to this doctor
                    cur.execute(
                        "SELECT id FROM appointments WHERE id = ? AND doctor_id = ?",
                        (appt_id, doctor["id"]),
                    )
                    if not cur.fetchone():
                        flash("Appointment not found or not assigned to you.", "danger")
                    else:
                        cur.execute(
                            "UPDATE appointments SET status = ? WHERE id = ?",
                            (status, appt_id),
                        )

                        # If status is Completed, upsert treatment
                        if status == "Completed":
                            cur.execute(
                                "SELECT id FROM treatments WHERE appointment_id = ?",
                                (appt_id,),
                            )
                            trow = cur.fetchone()
                            if trow:
                                cur.execute(
                                    """
                                    UPDATE treatments
                                    SET diagnosis = ?, prescription = ?, notes = ?
                                    WHERE appointment_id = ?
                                    """,
                                    (diagnosis, prescription, notes, appt_id),
                                )
                            else:
                                cur.execute(
                                    """
                                    INSERT INTO treatments (appointment_id, diagnosis, prescription, notes)
                                    VALUES (?, ?, ?, ?)
                                    """,
                                    (appt_id, diagnosis, prescription, notes),
                                )

                        conn.commit()
                        flash("Appointment updated.", "success")

        # ---------------------------------------------------
        # Fetch data for dashboard
        # ---------------------------------------------------
        today = date.today()
        end_date = today + timedelta(days=7)
        today_str = today.isoformat()
        end_str = end_date.isoformat()

        # Upcoming appointments (next 7 days)
        cur.execute(
            """
            SELECT a.id,
                   a.date,
                   a.time,
                   a.status,
                   p.name AS patient_name,
                   t.diagnosis,
                   t.prescription,
                   t.notes
            FROM appointments a
            JOIN patient_profiles p ON a.patient_id = p.id
            LEFT JOIN treatments t ON t.appointment_id = a.id
            WHERE a.doctor_id = ?
              AND a.date >= ?
              AND a.date <= ?
            ORDER BY a.date, a.time
            """,
            (doctor["id"], today_str, end_str),
        )
        upcoming_appts = cur.fetchall()

        # Distinct patients assigned (any appointment with this doctor)
        cur.execute(
            """
            SELECT DISTINCT p.id, p.name
            FROM appointments a
            JOIN patient_profiles p ON a.patient_id = p.id
            WHERE a.doctor_id = ?
            ORDER BY p.name
            """,
            (doctor["id"],),
        )
        patients = cur.fetchall()

        # Doctor availability for next 7 days
        cur.execute(
            """
            SELECT id, date, time
            FROM doctor_availability
            WHERE doctor_id = ?
              AND date >= ?
              AND date <= ?
            ORDER BY date, time
            """,
            (doctor["id"], today_str, end_str),
        )
        slots = cur.fetchall()

        # Optional: patient history view (if a patient is selected via ?patient_id=)
        selected_patient = None
        history = []
        selected_patient_id = request.args.get("patient_id")

        if selected_patient_id:
            try:
                pid_int = int(selected_patient_id)
                cur.execute(
                    "SELECT * FROM patient_profiles WHERE id = ?",
                    (pid_int,),
                )
                selected_patient = cur.fetchone()

                if selected_patient:
                    cur.execute(
                        """
                        SELECT a.date,
                               a.time,
                               d.name AS doctor_name,
                               t.diagnosis,
                               t.prescription
                        FROM appointments a
                        JOIN doctor_profiles d ON a.doctor_id = d.id
                        LEFT JOIN treatments t ON t.appointment_id = a.id
                        WHERE a.patient_id = ?
                          AND a.status = 'Completed'
                        ORDER BY a.date DESC, a.time DESC
                        """,
                        (pid_int,),
                    )
                    history = cur.fetchall()
            except ValueError:
                selected_patient = None
                history = []

        conn.close()

        return render_template(
            "doctor/dashboard.html",
            doctor=doctor,
            upcoming_appts=upcoming_appts,
            patients=patients,
            slots=slots,
            selected_patient=selected_patient,
            history=history,
            selected_patient_id=selected_patient_id,
        )
