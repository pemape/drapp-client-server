import logging
from server.database import db
from server.models.user import User
from flask_jwt_extended import create_access_token
from datetime import timedelta

logger = logging.getLogger(__name__)

class AuthService:
    def login_user(self, data):
        """Prihlásenie používateľa a vygenerovanie JWT tokenu."""
        logger.info("Login method started")
        try:
            email = data.get('email')
            password = data.get('password')

            if not email or not password:
                logger.error("Login failed: email or password not provided")
                return {'error': 'Email and password are required'}, 400

            # Vyhľadanie používateľa podľa emailu
            user = User.query.filter_by(email=email).first()
            if not user:
                logger.warning("User with email %s not found", email)
                return {'error': 'Invalid email or password'}, 401

            logger.debug("User with email %s found", email)
            if user.check_password(password):
                access_token = create_access_token(identity=str(user.id), expires_delta=timedelta(hours=1))
                logger.info("Login successful for user with id %s", user.id)
                return {
                    "access_token": access_token,
                    "message": "Login successful"
                }, 200

            logger.error("Invalid login credentials for email %s", email)
            return {'error': 'Invalid email or password'}, 401

        except Exception as e:
            logger.exception("Exception in login_user: %s", e)
            return {'error': str(e)}, 500

    def logout(self):
        logger.info("Logout method started")
        try:
            # Pri JWT autentifikácii obvykle stačí odstrániť token (ak sa používajú HTTP-only cookies)
            return {'message': 'Logout successful'}, 200
        except Exception as e:
            logger.exception("Exception in logout: %s", e)
            return {'error': str(e)}, 500
