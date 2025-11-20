# seed_demo_data.py
from datetime import datetime, date, timedelta

from werkzeug.security import generate_password_hash

from db import get_db


def seed_demo_data():
    conn = get_db()
    cur = conn.cursor()

    print("=== Seeding demo data ===")

    # -----------------------
    # 1) Departments
    # -----------------------
    dept_defs = [
        ("Cardiology", "Heart and blood vessel related issues."),
        ("Neurology", "Brain and nervous system."),
        ("Orthopedics", "Bones and joints."),
        ("Pediatrics", "Child health and development."),
        ("Dermatology", "Skin, hair and nails."),
    ]

    dept_ids = {}  # name -> id

    for name, desc in dept_defs:
        cur.execute("SELECT id FROM departments WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            dept_id = row["id"]
            print(f"[Dept] Exists: {name} (id={dept_id})")
        else:
            cur.execute(
                "INSERT INTO departments (name, description) VALUES (?, ?)",
                (name, desc),
            )
            dept_id = cur.lastrowid
            print(f"[Dept] Created: {name} (id={dept_id})")
        dept_ids[name] = dept_id

    # -----------------------
    # 2) Doctors (users + profiles)
    # -----------------------
    doctor_defs = [
        {
            "email": "dr.cardiac@hospital.com",
            "password": "doctor123",
            "name": "Dr. Alice Cardio",
            "department": "Cardiology",
            "specialization": "Interventional Cardiologist",
            "phone": "1111111111",
            "bio": "Specialist in heart failure and coronary interventions.",
        },
        {
            "email": "dr.neuro@hospital.com",
            "password": "doctor123",
            "name": "Dr. Brian Neuro",
            "department": "Neurology",
            "specialization": "Neurologist",
            "phone": "2222222222",
            "bio": "Focus on epilepsy and movement disorders.",
        },
        {
            "email": "dr.ortho@hospital.com",
            "password": "doctor123",
            "name": "Dr. Charlie Ortho",
            "department": "Orthopedics",
            "specialization": "Orthopedic Surgeon",
            "phone": "3333333333",
            "bio": "Joint replacement and sports injuries.",
        },
    ]

    doctor_profile_ids = {}  # email -> doctor_profiles.id

    for d in doctor_defs:
        email = d["email"]

        # Check if user already exists
        cur.execute("SELECT id FROM users WHERE email = ?", (email,))
        urow = cur.fetchone()
        if urow:
            user_id = urow["id"]
            print(f"[Doctor-User] Exists: {email} (id={user_id})")
        else:
            pwd_hash = generate_password_hash(d["password"])
            cur.execute(
                "INSERT INTO users (email, password_hash, role, status) "
                "VALUES (?, ?, 'doctor', 'active')",
                (email, pwd_hash),
            )
            user_id = cur.lastrowid
            print(f"[Doctor-User] Created: {email} (id={user_id})")

        # Check doctor_profile
        cur.execute("SELECT id FROM doctor_profiles WHERE user_id = ?", (user_id,))
        prow = cur.fetchone()
        if prow:
            doctor_id = prow["id"]
            print(f"[Doctor-Profile] Exists for {email} (id={doctor_id})")
        else:
            dept_id = dept_ids[d["department"]]
            cur.execute(
                """
                INSERT INTO doctor_profiles
                  (user_id, department_id, name, specialization, phone, bio)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    dept_id,
                    d["name"],
                    d["specialization"],
                    d["phone"],
                    d["bio"],
                ),
            )
            doctor_id = cur.lastrowid
            print(f"[Doctor-Profile] Created for {email} (id={doctor_id})")

        doctor_profile_ids[email] = doctor_id

    # -----------------------
    # 3) Demo patients
    # -----------------------
    patient_defs = [
        {
            "email": "john.doe@example.com",
            "password": "patient123",
            "name": "John Doe",
            "age": 35,
            "gender": "Male",
            "phone": "4444444444",
            "address": "123 Main Street",
            "emergency": "Jane Doe - 5555555555",
        },
        {
            "email": "jane.smith@example.com",
            "password": "patient123",
            "name": "Jane Smith",
            "age": 29,
            "gender": "Female",
            "phone": "6666666666",
            "address": "456 Park Lane",
            "emergency": "John Smith - 7777777777",
        },
    ]

    patient_profile_ids = {}  # email -> patient_profiles.id

    for p in patient_defs:
        email = p["email"]
        cur.execute("SELECT id FROM users WHERE email = ?", (email,))
        urow = cur.fetchone()
        if urow:
            user_id = urow["id"]
            print(f"[Patient-User] Exists: {email} (id={user_id})")
        else:
            pwd_hash = generate_password_hash(p["password"])
            cur.execute(
                "INSERT INTO users (email, password_hash, role, status) "
                "VALUES (?, ?, 'patient', 'active')",
                (email, pwd_hash),
            )
            user_id = cur.lastrowid
            print(f"[Patient-User] Created: {email} (id={user_id})")

        cur.execute("SELECT id FROM patient_profiles WHERE user_id = ?", (user_id,))
        prow = cur.fetchone()
        if prow:
            patient_id = prow["id"]
            print(f"[Patient-Profile] Exists for {email} (id={patient_id})")
        else:
            cur.execute(
                """
                INSERT INTO patient_profiles
                  (user_id, name, age, gender, phone, address, emergency_contact)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    p["name"],
                    p["age"],
                    p["gender"],
                    p["phone"],
                    p["address"],
                    p["emergency"],
                ),
            )
            patient_id = cur.lastrowid
            print(f"[Patient-Profile] Created for {email} (id={patient_id})")

        patient_profile_ids[email] = patient_id

    # -----------------------
    # 4) Doctor availability (next 3 days, 10:00 and 11:00)
    # -----------------------
    today = date.today()
    slot_times = ["10:00", "11:00"]

    for email, doctor_id in doctor_profile_ids.items():
        for offset in range(0, 3):
            d = today + timedelta(days=offset)
            d_str = d.isoformat()
            for t in slot_times:
                cur.execute(
                    """
                    SELECT id FROM doctor_availability
                    WHERE doctor_id = ? AND date = ? AND time = ?
                    """,
                    (doctor_id, d_str, t),
                )
                if cur.fetchone():
                    continue
                cur.execute(
                    """
                    INSERT INTO doctor_availability (doctor_id, date, time, is_available)
                    VALUES (?, ?, ?, 1)
                    """,
                    (doctor_id, d_str, t),
                )
        print(f"[Availability] Seeded next 3 days for {email}")

    # -----------------------
    # 5) A couple of appointments + treatments
    # -----------------------
    # Use: John Doe with Cardio doctor, Jane Smith with Neuro doctor
    created_at = datetime.now().isoformat(timespec="seconds")

    def ensure_appointment(patient_email, doctor_email, days_ago, status, diagnosis=None, prescription=None):
        patient_id = patient_profile_ids[patient_email]
        doctor_id = doctor_profile_ids[doctor_email]
        appt_date = (today - timedelta(days=days_ago)).isoformat()
        appt_time = "10:00"

        # Check if appointment already exists
        cur.execute(
            """
            SELECT id FROM appointments
            WHERE patient_id = ? AND doctor_id = ? AND date = ? AND time = ?
            """,
            (patient_id, doctor_id, appt_date, appt_time),
        )
        row = cur.fetchone()
        if row:
            appt_id = row["id"]
            print(f"[Appointment] Exists id={appt_id} ({patient_email} with {doctor_email} on {appt_date})")
        else:
            # Get department from doctor_profiles
            cur.execute("SELECT department_id FROM doctor_profiles WHERE id = ?", (doctor_id,))
            drow = cur.fetchone()
            dept_id = drow["department_id"] if drow else None

            cur.execute(
                """
                INSERT INTO appointments (patient_id, doctor_id, department_id, date, time, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (patient_id, doctor_id, dept_id, appt_date, appt_time, status, created_at),
            )
            appt_id = cur.lastrowid
            print(f"[Appointment] Created id={appt_id} ({patient_email} with {doctor_email} on {appt_date})")

        if status == "Completed":
            # Ensure treatment record
            cur.execute(
                "SELECT id FROM treatments WHERE appointment_id = ?",
                (appt_id,),
            )
            trow = cur.fetchone()
            if trow:
                print(f"[Treatment] Exists for appointment {appt_id}")
            else:
                cur.execute(
                    """
                    INSERT INTO treatments (appointment_id, diagnosis, prescription, notes)
                    VALUES (?, ?, ?, ?)
                    """,
                    (appt_id, diagnosis or "", prescription or "", "Follow-up in 2 weeks."),
                )
                print(f"[Treatment] Created for appointment {appt_id}")

    # John with Cardio doctor - completed 5 days ago
    ensure_appointment(
        "john.doe@example.com",
        "dr.cardiac@hospital.com",
        days_ago=5,
        status="Completed",
        diagnosis="Hypertension, well controlled",
        prescription="Amlodipine 5mg once daily",
    )

    # Jane with Neuro doctor - completed 2 days ago
    ensure_appointment(
        "jane.smith@example.com",
        "dr.neuro@hospital.com",
        days_ago=2,
        status="Completed",
        diagnosis="Migraine without aura",
        prescription="Paracetamol + lifestyle changes",
    )

    # John with Ortho doctor - booked for tomorrow
    ensure_appointment(
        "john.doe@example.com",
        "dr.ortho@hospital.com",
        days_ago=-1,  # -1 => future: tomorrow
        status="Booked",
    )

    conn.commit()
    conn.close()
    print("=== Demo data seeding completed ===")


if __name__ == "__main__":
    seed_demo_data()
