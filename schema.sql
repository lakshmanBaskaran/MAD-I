PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'doctor', 'patient')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'blacklisted'))
);

CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS doctor_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    department_id INTEGER,
    name TEXT NOT NULL,
    specialization TEXT,
    phone TEXT,
    bio TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES departments (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS patient_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    age INTEGER,
    gender TEXT,
    phone TEXT,
    address TEXT,
    emergency_contact TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS doctor_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id INTEGER NOT NULL,
    date TEXT NOT NULL,         -- 'YYYY-MM-DD'
    time TEXT NOT NULL,         -- 'HH:MM'
    is_available INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (doctor_id) REFERENCES doctor_profiles (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    doctor_id INTEGER NOT NULL,
    department_id INTEGER,
    date TEXT NOT NULL,         -- 'YYYY-MM-DD'
    time TEXT NOT NULL,         -- 'HH:MM'
    status TEXT NOT NULL DEFAULT 'Booked'
        CHECK (status IN ('Booked', 'Completed', 'Cancelled')),
    created_at TEXT NOT NULL,   -- ISO datetime string
    FOREIGN KEY (patient_id) REFERENCES patient_profiles (id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctor_profiles (id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES departments (id) ON DELETE SET NULL,
    UNIQUE (doctor_id, date, time)
);

CREATE TABLE IF NOT EXISTS treatments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER NOT NULL UNIQUE,
    diagnosis TEXT,
    prescription TEXT,
    notes TEXT,
    FOREIGN KEY (appointment_id) REFERENCES appointments (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_appointments_patient_id
    ON appointments (patient_id);

CREATE INDEX IF NOT EXISTS idx_appointments_doctor_id
    ON appointments (doctor_id);

CREATE INDEX IF NOT EXISTS idx_doctor_availability_doctor_id
    ON doctor_availability (doctor_id);
