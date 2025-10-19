import logging
from server.database import db
from server.models import User
from server.models.admin_data import AdminData
from server.models.hospital_data import Hospital

logger = logging.getLogger(__name__)

class AdminsService:
    def add_admin(self, user_id: int, data):
        logger.info("Method add_admin started")
        message, status = User.check_user_type_required(user_id, "super_admin")
        if status != 200:
            return message, status

        first_name = data.get("first_name")
        last_name = data.get("last_name")
        phone_number = data.get("phone_number")
        gender = data.get("gender")
        hospital_code = data.get("hospital_code")

        email = data.get("email")
        if User.query.filter_by(email=email).first():
            logger.error("Registration failed: Email %s already exists", email)
            return {'error': 'Email already exists'}, 400

        password = data.get("password")

        if not all([first_name, last_name, phone_number, gender, hospital_code, email, password]):
            logger.error("Missing required fields (including email/password)")
            return {"error": "Missing required fields including email and password"}, 400

        hospital = Hospital.query.filter_by(hospital_code=hospital_code).first()
        if not hospital:
            logger.error("Hospital with code '%s' does not exist", hospital_code)
            return {"error": "Nonexistent hospital with this code"}, 404

        try:
            new_admin = AdminData(
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                gender=gender,
                hospital_id=hospital.id
            )
            if (len(new_admin.validate_password(password)) > 0):
                logger.error("Admin registration failed: %s", new_admin.validate_password(password))
                return {"error": new_admin.validate_password(password)}, 400
            new_admin.set_password(password)
            db.session.add(new_admin)
            db.session.commit()
            logger.info("Admin '%s %s' was successfully added", first_name, last_name)
            return {"message": "Admin was successfully added."}, 201
        except Exception as e:
            logger.exception("Exception while adding admin: %s", e)
            db.session.rollback()
            return {"error": "Internal server error"}, 500

    def update_admin(self, user_id: int, admin_id: int, data):
        logger.info("Method update_admin started for admin_id: %s", admin_id)
        message, status = User.check_user_type_required(user_id, "super_admin")
        if status != 200:
            return message, status

        try:
            admin = AdminData.query.get(admin_id)
            if not admin:
                logger.warning("Admin with id %s does not exist", admin_id)
                return {"error": "Admin does not exist"}, 404

            admin.first_name = data.get("first_name", admin.first_name)
            admin.last_name = data.get("last_name", admin.last_name)
            admin.phone_number = data.get("phone_number", admin.phone_number)
            admin.gender = data.get("gender", admin.gender)
            User.query.get(admin_id).email = data.get("email", User.query.get(admin_id).email)

            password = data.get("password", "")
            if password != "":
                if (len(admin.validate_password(password)) > 0):
                    logger.error("Admin update failed: %s", admin.validate_password(password))
                    return {"error": admin.validate_password(password)}, 400
                admin.set_password(password)

            hospital_code = data.get("hospital_code")
            if hospital_code:
                hospital = Hospital.query.filter_by(hospital_code=hospital_code).first()
                if not hospital:
                    logger.warning("Nonexistent hospital with code '%s'", hospital_code)
                    return {"error": "Nonexistent hospital"}, 404
                admin.hospital_id = hospital.id
            db.session.commit()
            logger.info("Admin with id %s was updated", admin_id)
            return {"message": "Admin updated"}, 200
        except Exception as e:
            logger.exception("Exception while updating admin: %s", e)
            db.session.rollback()
            return {"error": "Internal server error"}, 500

    def get_admins(self, user_id: int):
        """Retrieve all admins (only for super_admin) with hospital details."""
        logger.info("Method get_admins started")
        message, status = User.check_user_type_required(user_id, "super_admin")
        if status != 200:
            return message, status

        try:
            admins = AdminData.query.all()
            admins_data = []
            for a in admins:
                hospital = a.hospital
                hospital_info = {
                    "id": hospital.id,
                    "name": hospital.name,
                    "city": hospital.city,
                    "street": hospital.street,
                    "postal_code": hospital.postal_code
                } if hospital else None

                admins_data.append({
                    "id": a.id,
                    "first_name": a.first_name,
                    "last_name": a.last_name,
                    "email": a.email,
                    "phone_number": a.phone_number,
                    "gender": a.gender,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    "hospital": hospital_info
                })
            logger.info("Loaded list of admins: %d", len(admins_data))
            return admins_data, 200
        except Exception as e:
            logger.exception("Error while loading admins: %s", e)
            return {"error": "Internal server error"}, 500

    def get_admin(self, user_id: int, admin_id: int):
        """Retrieve a specific admin with hospital details."""
        logger.info("Method get_admin started for admin_id: %s", admin_id)
        message, status = User.check_user_type_required(user_id, "super_admin")
        if status != 200:
            return message, status

        try:
            admin = AdminData.query.get(admin_id)
            if not admin:
                return {"error": "Admin does not exist"}, 404

            hospital = admin.hospital
            hospital_info = {
                "id": hospital.id,
                "name": hospital.name,
                "city": hospital.city,
                "street": hospital.street,
                "postal_code": hospital.postal_code,
                "hospital_code": hospital.hospital_code
            } if hospital else None

            admin_data = {
                "id": admin.id,
                "first_name": admin.first_name,
                "last_name": admin.last_name,
                "phone_number": admin.phone_number,
                "gender": admin.gender,
                "email": admin.email,
                "created_at": admin.created_at.isoformat() if admin.created_at else None,
                "hospital": hospital_info
            }
            logger.info("Admin loaded: %s %s", admin.first_name, admin.last_name)
            return admin_data, 200
        except Exception as e:
            logger.exception("Error while retrieving admin: %s", e)
            return {"error": "Internal server error"}, 500

    def check_user_id(self, user_id: int):
        """Verify if the user has super_admin privileges."""
        return User.check_user_type_required(user_id, "super_admin")
