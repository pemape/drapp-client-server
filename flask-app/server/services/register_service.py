import logging
from server.database import db
from server.models.user import User
from server.services.technicians_service import TechniciansService
from server.services.patients_service import PatientsService
from server.services.doctors_service import DoctorsService
from server.services.admins_service import AdminsService

logger = logging.getLogger(__name__)

class RegisterService:
    def register_user(self, data, user_type):
        """Register a new user with duplicate check and logging."""
        logger.info("User registration started. user_type: %s, data keys: %s", user_type, list(data.keys()))
        try:
            email = data.get('email')
            if not email:
                logger.error("Registration failed: email is not provided")
                return {'error': 'Email is required'}, 400

            # Check if the email already exists
            if User.query.filter_by(email=email).first():
                logger.error("Registration failed: Email %s already exists", email)
                return {'error': 'Email already exists'}, 400

            # Check if user type is provided
            if not user_type:
                logger.error("Registration failed: user_type is not provided")
                return {'error': 'Missing required fields: user type'}, 400

            # Call the appropriate registration method based on user type
            if user_type == 'patient':
                logger.info("Calling registration method for patient")
                return PatientsService().register_patient(data)
            elif user_type == 'technician':
                logger.info("Calling registration method for technician")
                return TechniciansService().add_technician(1, data)
            elif user_type == 'doctor':
                logger.info("Calling registration method for doctor")
                return DoctorsService().register_doctor(data)
            elif user_type == 'admin':
                logger.info("Calling registration method for admin")
                return AdminsService().add_admin(1, data)
            else:
                logger.error("Registration failed: Invalid user_type: %s", user_type)
                return {'error': 'Invalid user type'}, 400

        except Exception as e:
            db.session.rollback()
            logger.exception("Exception during user registration: %s", e)
            return {'error': str(e)}, 500
