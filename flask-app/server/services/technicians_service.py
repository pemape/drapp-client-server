import logging
from server.database import db
from server.models.user import User
from server.models.admin_data import AdminData
from server.models.hospital_data import Hospital
from server.models.doctor_data import DoctorData
from server.models.technician_data import TechnicianData
logger = logging.getLogger(__name__)

class TechniciansService:
    def add_technician(self, user_id: int, data):
        logger.info("Method add_technician started")
        user = User.query.get(int(user_id))
        try:
            if user.is_super_admin():
                hospital_code = data.get("hospital_code")
            elif user.is_admin():
                hospital_code = AdminData.query.filter_by(id=user_id).first().hospital.hospital_code
            elif user.is_doctor():
                hospital_code = DoctorData.query.filter_by(id=user_id).first().hospital.hospital_code
            else:
                return {"error": f"Unauthorized access for user_id {user_id}"}, 403
        except Exception as e:
            logger.exception("Error retrieving hospital for technician: %s", e)
            return {"error": "Internal server error"}, 500


        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        password = data.get("password")

        if User.query.filter_by(email=email).first():
            logger.error("Technician with email %s already exists", email)
            return {'error': 'Email already exists'}, 400

        if not all([first_name, last_name, hospital_code, email, password]):
            return {"error": "Missing required fields"}, 400

        hospital = Hospital.query.filter_by(hospital_code=hospital_code).first()
        if not hospital:
            return {"error": "Hospital does not exist"}, 404

        try:
            new_technician = TechnicianData(
                email=email,
                first_name=first_name,
                last_name=last_name,
                hospital_id=hospital.id
            )
            if (len(new_technician.validate_password(password)) > 0):
                logger.error("Technician registration failed: %s", new_technician.validate_password(password))
                return {"error": new_technician.validate_password(password)}, 400
            new_technician.set_password(password)

            db.session.add(new_technician)
            db.session.commit()
            logger.info("Technician '%s %s' was added", first_name, last_name)
            return {"message": "Technician was successfully added."}, 201

        except Exception as e:
            logger.exception("Error adding technician: %s", e)
            db.session.rollback()
            return {"error": "Internal server error"}, 500

    def update_technician(self, user_id: int, technician_id: int, data):
        logger.info("Method update_technician started for id %s", technician_id)
        user = User.query.get(int(user_id))

        technician = TechnicianData.query.get(technician_id)
        if not technician:
            return {"error": "Technician does not exist"}, 404

        if user.is_super_admin():
            pass
        elif user.is_admin() or user.is_doctor():
            if technician.hospital_id != user.hospital_id:
                return {"error": "You do not have permission to edit this technician"}, 403
        else:
            return {"error": "Unauthorized access"}, 403
        try:
            technician.first_name = data.get("first_name", technician.first_name)
            technician.last_name = data.get("last_name", technician.last_name)
            User.query.get(technician_id).email = data.get("email", User.query.get(technician_id).email)
            password = data.get("password", "")
            if password != "":
                if (len(technician.validate_password(password)) > 0):
                    logger.error("Technician update failed: %s", technician.validate_password(password))
                    return {"error": technician.validate_password(password)}, 400
                technician.set_password(password)

            if user.is_super_admin():
                new_code = data.get("hospital_code")
                if new_code and new_code != technician.hospital.hospital_code:
                    hospital = Hospital.query.filter_by(hospital_code=new_code).first()
                    if not hospital:
                        return {"error": "Hospital does not exist"}, 404
                    technician.hospital_id = hospital.id

            db.session.commit()
            return {"message": "Technician updated"}, 200

        except Exception as e:
            logger.exception("Error updating technician: %s", e)
            db.session.rollback()
            return {"error": "Internal server error"}, 500

    def get_technicians(self, user_id: int):
        logger.info("Method get_technicians started")
        user = User.query.get(int(user_id))

        try:
            if user.is_super_admin():
                technicians = TechnicianData.query.all()
            elif user.is_admin() or user.is_doctor():
                technicians = TechnicianData.query.filter_by(hospital_id=user.hospital_id).all()
            else:
                return {"error": "Unauthorized access"}, 403

            result = []
            for t in technicians:
                hospital = t.hospital
                result.append({
                    "id": t.id,
                    "first_name": t.first_name,
                    "last_name": t.last_name,
                    "email": t.email,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "hospital": {
                        "id": hospital.id,
                        "name": hospital.name,
                        "city": hospital.city,
                        "street": hospital.street,
                        "postal_code": hospital.postal_code,
                        "hospital_code": hospital.hospital_code
                    } if hospital else None
                })

            return result, 200

        except Exception as e:
            logger.exception("Error retrieving technicians: %s", e)
            return {"error": "Internal server error"}, 500

    def get_technician(self, user_id: int, technician_id: int):
        logger.info("Method get_technician started")
        user = User.query.get(int(user_id))
        technician = TechnicianData.query.get(technician_id)

        if not technician:
            return {"error": "Technician does not exist"}, 404

        if user.is_super_admin():
            pass
        elif user.is_admin() or user.is_doctor():
            if technician.hospital_id != user.hospital_id:
                return {"error": "You do not have access to this technician"}, 403
        else:
            return {"error": "Unauthorized access"}, 403

        hospital = technician.hospital
        return {
            "id": technician.id,
            "first_name": technician.first_name,
            "last_name": technician.last_name,
            "email": technician.email,
            "created_at": technician.created_at.isoformat() if technician.created_at else None,
            "hospital": {
                "id": hospital.id,
                "name": hospital.name,
                "city": hospital.city,
                "street": hospital.street,
                "postal_code": hospital.postal_code,
                "hospital_code": hospital.hospital_code
            } if hospital else None
        }, 200

    def check_user_id(self, user_id: int):
        message, status = User.check_user_type_required(user_id, "super_admin")
        if status != 200:
            message, status = User.check_user_type_required(user_id, "admin")
        if status != 200:
            message, status = User.check_user_type_required(user_id, "doctor")
        return message, status