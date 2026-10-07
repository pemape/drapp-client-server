import os
import logging
from datetime import date

from server.database import db
from server.models.hospital_data import Hospital
from server.models.doctor_data import DoctorData
from server.models.patient_data import PatientData

logger = logging.getLogger(__name__)


def _seed_hospital() -> Hospital:
    hospital = Hospital.query.filter_by(name="Demo Hospital").first()
    if hospital:
        return hospital
    hospital = Hospital(
        name="Demo Hospital",
        country="Slovakia",
        city="Bratislava",
        street="Hlavna 1",
        postal_code="81101",
    )
    db.session.add(hospital)
    db.session.flush()
    logger.info("Seeded hospital: %s", hospital.name)
    return hospital


def _seed_doctor(hospital: Hospital) -> DoctorData:
    email = os.getenv("SEED_DOCTOR_EMAIL", "doctor@example.com")
    doctor = DoctorData.query.filter_by(email=email).first()
    if doctor:
        return doctor
    doctor = DoctorData(
        email=email,
        first_name="Demo",
        last_name="Doctor",
        phone_number="+421900000001",
        gender="male",
        title="MUDr.",
        hospital_id=hospital.id,
    )
    doctor.set_password(os.getenv("SEED_DOCTOR_PASSWORD", "Doctor123!"))
    db.session.add(doctor)
    db.session.flush()
    logger.info("Seeded doctor: %s", email)
    return doctor


def _seed_patient(doctor: DoctorData) -> PatientData:
    email = os.getenv("SEED_PATIENT_EMAIL", "patient@example.com")
    patient = PatientData.query.filter_by(email=email).first()
    if patient:
        return patient
    patient = PatientData(
        email=email,
        first_name="Demo",
        last_name="Patient",
        phone_number="+421900000002",
        birth_date=date(1980, 1, 1),
        birth_number="800101/1234",
        gender="female",
        doctor_id=doctor.id,
    )
    patient.set_password(os.getenv("SEED_PATIENT_PASSWORD", "Patient123!"))
    db.session.add(patient)
    db.session.flush()
    logger.info("Seeded patient: %s", email)
    return patient


def create_seed_data() -> None:
    """Idempotently create one hospital, one doctor and one patient."""
    try:
        hospital = _seed_hospital()
        doctor = _seed_doctor(hospital)
        _seed_patient(doctor)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Failed to create seed data")
