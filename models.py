from app import db
from flask_login import UserMixin
from datetime import datetime

# =========================
# HOSPITAL (MODEL)
# =========================

class Hospital(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    email = db.Column(db.String(120), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# =========================
# USER (Hospital Admin)
# =========================
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer,db.ForeignKey('hospital.id'))
    hospital_name = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(200))

    role = db.Column(db.String(50), default='admin')  # admin / pharmacist / lab

    logo = db.Column(db.String(200))  # hospital logo filename


# =========================
# PATIENT
# =========================
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer,db.ForeignKey('hospital.id'))
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))

    guardian_name = db.Column(db.String(150))

    email = db.Column(db.String(150))
    phone = db.Column(db.String(20))

    address = db.Column(db.Text)


# =========================
# DOCTOR 
# =========================
class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer,db.ForeignKey('hospital.id'))
    name = db.Column(db.String(100))
    specialization = db.Column(db.String(100))
    fee = db.Column(db.Float)


# =========================
# MEDICINE
# =========================
class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer,db.ForeignKey('hospital.id'))
    name = db.Column(db.String(100))
    description = db.Column(db.String(200))

    price = db.Column(db.Float)
    quantity = db.Column(db.Integer)


# =========================
# LAB REPORT
# =========================
class LabReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer,db.ForeignKey('hospital.id'))
    name = db.Column(db.String(100))
    description = db.Column(db.String(200))
    fee = db.Column(db.Float)

# =========================
# BILL (MAIN SYSTEM)
# =========================

from datetime import datetime   # ✅ IMPORTANT

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer,db.ForeignKey('hospital.id'))
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))
    medicines = db.Column(db.Text)
    reports = db.Column(db.Text)
    doctor_name = db.Column(db.String(100)) 
    doctor_fee = db.Column(db.Float, default=0)
    total = db.Column(db.Float)
    status = db.Column(db.String(50), default='draft')
    created_by = db.Column(db.String(50))
    combined = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)