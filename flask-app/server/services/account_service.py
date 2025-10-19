import logging
from server import db
from server.models.user import User

logger = logging.getLogger(__name__)


class AccountService:
    @staticmethod
    def get_account_info(user_id):
        logger.info("Retrieving account information for user_id: %s", user_id)

        # Check if user_id was provided
        if not user_id:
            logger.error("No user_id provided.")
            return {'error': 'Missing user identifier'}, 400

        # Attempt to convert user_id to int
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError) as e:
            logger.exception("Invalid user_id format %s: %s", user_id, e)
            return {'error': 'Invalid user identifier'}, 400

        # Load user from database
        try:
            user = db.session.get(User, user_id_int)
        except Exception as e:
            logger.exception("Error retrieving user with id %s: %s", user_id_int, e)
            return {'error': 'Internal error'}, 500

        if not user:
            logger.error("User with id %s not found", user_id_int)
            return {'error': 'User not found'}, 404

        # Retrieve user information
        try:
            response = user.get_info()
            # Verify that the result is in the appropriate format
            if not isinstance(response, dict):
                logger.error("Invalid format of data retrieved from user.get_info() for user_id %s", user_id_int)
                return {'error': 'Invalid user info format'}, 500
        except Exception as e:
            logger.exception("Error retrieving user info for user_id %s: %s", user_id_int, e)
            return {'error': 'Error retrieving user info'}, 500

        logger.info("Account data successfully retrieved for user %s", user_id_int)
        return response, 200
