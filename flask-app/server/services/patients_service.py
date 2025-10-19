import logging
from datetime import date
import datetime
from server.database import db
from server.models.admin_data import AdminData
from server.models.user import User
from server.models.doctor_data import DoctorData
from server.models.patient_data import PatientData

logger = logging.getLogger(__name__)

class PatientsService:
    @staticmethod
    def register_patient(data):
        logger.info("Patient registration started")
        try:
            first_name = data.get('first_name')
            last_name = data.get('last_name')
            phone_number = data.get('phone_number')
            birth_date_str  = data.get('birth_date')
            birth_number = data.get('birth_number')
            gender = data.get('gender')
            email = data.get('email')
            password = data.get('password')

            if not all([first_name, last_name, birth_number, email, password]):
                logger.error("Missing required fields during patient registration")
                return {'error': 'Missing required fields'}, 400

            # --- DATE CONVERSION STARTS HERE ---
                    
            # 2. CONVERT STRING TO datetime.date OBJECT
            if birth_date_str:
                try:
                    # Assuming the format is 'YYYY-MM-DD' as seen in your error message
                    date_object = datetime.datetime.strptime(birth_date_str, '%Y-%m-%d').date()
                    birth_date = date_object # Use this converted object for the PatientData
                except ValueError:
                    # Handle cases where the date string is malformed
                    logger.error("Error converting birth date: invalid format")
                    return {'error': 'Invalid birth date format. Use YYYY-MM-DD.'}, 400
            else:
                birth_date = None # Set to None if it's an optional field
                
            # --- DATE CONVERSION ENDS HERE ---

            new_patient = PatientData(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone_number=phone_number,
                birth_date=birth_date,
                birth_number=birth_number,
                gender=gender,
            )
            if (len(new_patient.validate_password(password)) > 0):
                logger.error("Patient registration failed: %s", new_patient.validate_password(password))
                return {"error": new_patient.validate_password(password)}, 400
            new_patient.set_password(password)
            db.session.add(new_patient)
            db.session.commit()

            logger.info("Patient %s %s was successfully registered", first_name, last_name)
            return {'message': 'User registered successfully'}, 201

        except Exception as e:
            db.session.rollback()
            logger.exception("Exception during patient registration: %s", e)
            return {'error': str(e)}, 500

    def get_patients(self, user_id: int):
        user = User.query.get(user_id)
        if not user or not user.user_type in ['super_admin', 'admin', 'doctor']:
            return {'error': 'Unauthorized'}, 403

        if user.user_type == 'super_admin':
            patients = PatientData.query.all()
        elif user.user_type  == 'admin':
            admin = AdminData.query.get(user_id)
            if not admin or not admin.hospital:
                return {'error': 'Admin hospital not found'}, 404
            # Now access the hospital's doctors through the admin instance
            # In the get_patients method
            patients = []
            for doctor in admin.hospital.doctors:
                try:
                    doctor_patients = doctor.patients or []
                    patients.extend(doctor_patients)
                except Exception as e:
                    logger.exception(f"Error accessing patients for doctor {doctor.id}: {e}")
                    continue
        elif user.user_type == 'doctor':
            doctor = DoctorData.query.get(user_id)
            if doctor.super_doctor:
                patients = PatientData.query.all()
            else:
                patients = doctor.patients
        else:
            return {'error': 'Unauthorized'}, 403

        result = []
        for patient in patients:
            item = {
                "id": patient.id,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "email": patient.email,
                "gender": patient.gender,
                "phone_number": patient.phone_number,
                "created_at": patient.created_at.isoformat() if patient.created_at else None,
            }
            if user.user_type != 'technician':
                item["birth_number"] = patient.birth_number

            if patient.doctor_id:
                doctor = DoctorData.query.get(patient.doctor_id)
                if doctor:
                    item["doctor_id"] = doctor.id if doctor.id else None
                    item["doctor_name"] = f"{doctor.title + ' ' if doctor.title else ''}{doctor.first_name} {doctor.last_name}{' ' + doctor.suffix if doctor.suffix else ''}"
                    item["hospital_id"] = doctor.hospital.id if doctor.hospital else None
                    item["hospital_name"] = doctor.hospital.name if doctor.hospital else None

            result.append(item)

        return result, 200

    def get_unassigned_patients(self, user_id: int):
        user = User.query.get(user_id)
        if not user or not user.user_type in ['super_admin', 'admin', 'doctor']:
            return {'error': 'Unauthorized'}, 403
        patients = PatientData.query.all()
        unassigned_patients = [p for p in patients if p.doctor_id is None]

        result = [
            {
                "id": p.id,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "birth_number": p.birth_number,
            }
            for p in unassigned_patients
        ]

        return result, 200

    def add_patient(self, user_id: int, data):
        user = User.query.get(user_id)
        if not user or user.user_type not in ['super_admin', 'admin', 'doctor', 'technician']:
            return {'error': 'Unauthorized'}, 403

        try:
            first_name = data.get('first_name')
            last_name = data.get('last_name')
            email = data.get('email')
            phone_number = data.get('phone_number')
            birth_number = data.get('birth_number')
            password = data.get('password')
            doctor_id = None
            if user.user_type == 'doctor':
                doctor_id = user_id
            elif user.user_type == "admin":
                admin = AdminData.query.get(user_id)
                if not admin or not admin.hospital:
                    return {'error': 'Admin hospital not found'}, 404
                # Now access the hospital's doctors through the admin instance
                # In the get_patients method
                doctor_id = data.get('doctor_id')
                if doctor_id and doctor_id not in [doctor.id for doctor in admin.hospital.doctors]:
                    return {'error': 'Unauthorized to access this doctor'}, 403
            elif user.user_type == 'super_admin':
                doctor_id = data.get('doctor_id')
                if doctor_id:
                    doctor = DoctorData.query.get(doctor_id)
                    if not doctor:
                        return {'error': 'Doctor not found'}, 404


            if not all([first_name, last_name, birth_number, password]):
                return {'error': 'Missing required fields'}, 400

            birth_date, gender = self.calculate_birth_date_and_gender(birth_number)
            new_patient = PatientData(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone_number=phone_number,
                birth_date=birth_date,
                birth_number=birth_number,
                gender=gender,
                doctor_id=doctor_id
            )
            if (len(new_patient.validate_password(password)) > 0):
                logger.error("Patient registration failed: %s", new_patient.validate_password(password))
                return {"error": new_patient.validate_password(password)}, 400
            new_patient.set_password(password)
            db.session.add(new_patient)
            db.session.commit()

            return {'message': 'Patient added successfully'}, 201

        except Exception as e:
            db.session.rollback()
            logger.exception("Error adding patient: %s", e)
            return {'error': 'Internal server error'}, 500

    def get_patient(self, user_id: int, patient_id: int):
        user = User.query.get(user_id)
        if not user or user.user_type not in ['super_admin', 'admin', 'doctor']:
            return {'error': 'Unauthorized'}, 403

        # First get the patient data
        patient = PatientData.query.get(patient_id)
        if not patient:
            return {'error': 'Patient not found'}, 404

        # Check authorization based on user type
        if user.user_type == 'super_admin':
            # Super admin can access all patients
            pass
        elif user.user_type == 'admin':
            admin = AdminData.query.get(user_id)
            if not admin or not admin.hospital:
                return {'error': 'Admin hospital not found'}, 404

            if not patient.doctor_id or not any(
                    doctor.id == patient.doctor_id for doctor in admin.hospital.doctors
            ):
                return {'error': 'Unauthorized to access this patient'}, 403
        elif user.user_type == 'doctor':
            doctor = DoctorData.query.get(user_id)
            # Check if patient belongs to this doctor
            if not doctor or patient.doctor_id != doctor.id:
                # Also check if doctor is a super_doctor (can see all patients)
                if not doctor or not doctor.super_doctor:
                    return {'error': 'Unauthorized to access this patient'}, 403

        # Build response
        response = {
            "id": patient.id,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "email": patient.email,
            "gender": patient.gender,
            "phone_number": patient.phone_number,
            "created_at": patient.created_at.isoformat() if patient.created_at else None,
            "birth_date": patient.birth_date.isoformat() if patient.birth_date else None,
        }

        if user.user_type != 'technician':
            response["birth_number"] = patient.birth_number

        if patient.doctor_id:
            doctor = DoctorData.query.get(patient.doctor_id)
            if doctor:
                response["doctor_id"] = doctor.id
                response["doctor_name"] = f"{doctor.first_name} {doctor.last_name}"
                response["hospital_name"] = doctor.hospital.name if doctor.hospital else None

        return response, 200

    def update_patient(self, user_id: int, patient_id: int, data):
        user = User.query.get(user_id)
        if not user or user.user_type not in ['super_admin', 'admin', 'doctor']:
            return {'error': 'Unauthorized'}, 403

        patient = PatientData.query.get(patient_id)
        if not patient:
            return {'error': 'Patient not found'}, 404

        try:
            patient.first_name = data.get("first_name", patient.first_name)
            patient.last_name = data.get("last_name", patient.last_name)
            patient.email = data.get("email", patient.email)
            patient.phone_number = data.get("phone_number", patient.phone_number)
            patient.gender = data.get("gender", patient.gender)
            patient.birth_date = data.get("birth_date", patient.birth_date)
            password = data.get("password", "")
            if password != "":
                if (len(patient.validate_password(password)) > 0):
                    logger.error("Patient update failed: %s", patient.validate_password(password))
                    return {"error": patient.validate_password(password)}, 400
                patient.set_password(password)
            if user.user_type != 'technician':
                patient.birth_number = data.get("birth_number", patient.birth_number)

            # Add validation for doctor_id
            if "doctor_id" in data and data["doctor_id"] and user.user_type == 'super_admin':
                doctor = DoctorData.query.get(data["doctor_id"])
                if not doctor:
                    return {'error': f'Doctor with ID {data["doctor_id"]} not found'}, 400
                patient.doctor_id = data["doctor_id"]
            elif "doctor_id" in data and not data["doctor_id"]:
                patient.doctor_id = None  # Clear the doctor association

            db.session.commit()
            return {'message': 'Patient updated successfully'}, 200

        except Exception as e:
            db.session.rollback()
            logger.exception("Error updating patient: %s", e)
            return {'error': 'Internal server error'}, 500

    def assign_patient(self, user_id: int, data):
        try:
            user = User.query.get(user_id)
            logger.info("user_type = %s (%s)", user.user_type, type(user.user_type))

            if user.user_type not in ['super_admin', 'admin', 'doctor']:
                logger.error("Unauthorized access.")
                return {'error': 'Unauthorized access.'}, 403

            patient_id = data.get('id')
            if not patient_id:
                logger.error("Missing assignment id.")
                return {'error': 'Missing assignment id.'}, 400

            patient = PatientData.query.get(patient_id)
            if not patient:
                logger.error("Patient not found.")
                return {'error': 'Patient not found.'}, 404

            if patient.doctor_id is not None:
                logger.error("Patient already has an assigned doctor.")
                return {'error': 'Patient already has an assigned doctor.'}, 400

            if user.user_type == 'super_admin':
                doctor = DoctorData.query.get(data.get('doctor_id'))
                if not doctor:
                    logger.error("Doctor not found.")
                    return {'error': 'Doctor not found.'}, 404
                patient.doctor_id = doctor.id

            elif user.user_type == 'admin':
                admin = AdminData.query.get(user_id)
                if not admin or not admin.hospital:
                    logger.error("Admin hospital not found.")
                    return {'error': 'Admin hospital not found.'}, 404

                doctor = DoctorData.query.get(data.get('doctor_id'))
                if not doctor:
                    logger.error("Doctor not found.")
                    return {'error': 'Doctor not found.'}, 404

                if not doctor.hospital or doctor.hospital.id != admin.hospital.id:
                    logger.error("Doctor does not belong to your hospital.")
                    return {'error': 'Doctor does not belong to your hospital.'}, 403

                patient.doctor_id = doctor.id

            elif user.user_type == 'doctor':
                doctor = DoctorData.query.get(user_id)
                if not doctor:
                    logger.error("Doctor not found.")
                    return {'error': 'Doctor not found.'}, 404
                patient.doctor_id = doctor.id

            db.session.commit()
            logger.info("Patient was successfully assigned to a doctor.")
            return {'message': 'Patient was successfully assigned to a doctor.'}, 200

        except Exception as e:
            db.session.rollback()
            logger.exception("Error assigning patient: %s", e)
            return {'error': 'Internal server error.'}, 500

    def calculate_birth_date_and_gender(self, birth_number: str):
        """
        Získa dátum narodenia a pohlavie zo 6-ciferného rodného čísla (RRMMDD).
        """
        if len(birth_number) != 6 or not birth_number.isdigit():
            raise ValueError("Rodné číslo musí mať presne 6 číslic (RRMMDD).")

        rr = int(birth_number[:2])
        mm = int(birth_number[2:4])
        dd = int(birth_number[4:6])

        # Určenie pohlavia a reálneho mesiaca
        if mm > 50:
            gender = "Žena"
            mm -= 50
        else:
            gender = "Muž"

        current_year = date.today().year % 100
        century = 1900 if rr > current_year else 2000
        year = century + rr

        birthdate = date(year, mm, dd)
        return birthdate, gender

    def check_user_id(self, user_id: int):
        """Overenie, či používateľ má oprávnenie super_admin."""
        message, status = User.check_user_type_required(user_id, "super_admin")
        if status != 200:
            message, status = User.check_user_type_required(user_id, "admin")
        if status != 200:
            message, status = User.check_user_type_required(user_id, "doctor")
        if status != 200:
            message, status = User.check_user_type_required(user_id, "technician")
        return message, status
