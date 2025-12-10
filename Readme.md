# MAD-I – Hospital Management System 

A simple role-based **Hospital Management System** built with **Python (Flask)** and **SQLite**.

The application supports three types of users:

- **Admin**
- **Doctor**
- **Patient**

The SQLite database is **created programmatically when you run `app.py`** – no manual SQL commands are required.

---

## Features

###  Admin

- Secure admin login
- Manage **doctors**
  - Add, edit, delete doctor records
- Manage **patients**
  - Add, edit, delete patient records
- View overall hospital data

###  Doctor

- Doctor login
- View assigned patients
- View patient details and history
- Add / update:
  - Diagnosis
  - Notes
  - Prescriptions
- View upcoming appointments

###  Patient

- Patient login
- View personal profile
- View appointments
- View medical records shared by doctors

---

## Tech Stack

- **Language:** Python 3.x
- **Framework:** Flask
- **Database:** SQLite (`hms.db`, created automatically)
- **Templates:** HTML + Jinja2 (in `templates/`)
- **Modules:**
  - `admin_routes.py` – admin-related routes
  - `doctor_routes.py` – doctor-related routes
  - `patient_routes.py` – patient-related routes
  - `db.py` – database connection and helper functions
  - `security.py` – authentication / security helpers

---

## Project Structure


MAD-I/
├── __pycache__/          
├── templates/          
├── .gitignore            
├── LICENSE              
├── admin_routes.py       
├── app.py                
├── db.py                 
├── demo.py              
├── doctor_routes.py     
├── hms.db                
├── patient_routes.py     
├── schema.sql            
└── security.py           

Installation & Setup

git clone https://github.com/lakshmanBaskaran/MAD-I.git
cd MAD-I

python -m venv venv

venv\Scripts\activate

source venv/bin/activate

pip install flask

python app.py
