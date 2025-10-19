import os
import logging
from server.database import db
from server.models.super_admin_data import SuperAdminData
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def create_super_admin() -> None:
    load_dotenv()  # Load environment variables from the .env file
    # Check if a super admin with user_type="super_admin" already exists
    super_admin = SuperAdminData.query.filter_by(user_type="super_admin").first()
    if super_admin:
        logger.info("Super admin already exists: %s", super_admin.email)
        return

    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")
    if not email or not password:
        logger.error("ADMIN_EMAIL or ADMIN_PASSWORD are not set in environment variables.")
        return

    new_super_admin = SuperAdminData(
        email=email,
        user_type="super_admin"
    )
    new_super_admin.set_password(password)

    try:
        db.session.add(new_super_admin)
        db.session.commit()
        logger.info("Super admin successfully created with email: %s", email)
    except Exception as e:
        logger.exception("Failed to create super admin: %s", e)
        db.session.rollback()
