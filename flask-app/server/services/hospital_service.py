import logging
from server.database import db
from server.models.user import User
from server.models.hospital_data import Hospital

logger = logging.getLogger(__name__)

class HospitalService:
    def add_hospital(self, user_id: int, data):
        """Add hospital with address duplication check."""
        logger.info("Method add_hospital started")
        message, status = User.check_user_type_required(user_id, "super_admin")
        if status != 200:
            return message, status

        # Get input data
        name = data.get("name")
        country = data.get("country")
        city = data.get("city")
        street = data.get("street")
        postal_code = data.get("postal_code")

        # Check required fields: all must be provided
        if not name or not country or not city or not street or not postal_code:
            error_message = "Missing required fields for hospital: name, country, city, street, or postal_code"
            logger.error(error_message)
            return {"error": error_message}, 400

        # Check if hospital with the same address already exists
        existing_hospital = Hospital.query.filter_by(city=city, street=street, postal_code=postal_code).first()
        if existing_hospital:
            error_message = "Hospital with this address already exists."
            logger.error(error_message)
            return {"error": error_message}, 400

        try:
            new_hospital = Hospital(
                name=name,
                country=country,
                city=city,
                street=street,
                postal_code=postal_code
            )
            db.session.add(new_hospital)
            db.session.commit()
            message = f"Hospital '{name}' was successfully added"
            logger.info(message)
            return {"message": message}, 201
        except Exception as e:
            db.session.rollback()
            error_message = f"Exception while adding hospital: {e}"
            logger.exception(error_message)
            return {"error": error_message}, 500

    def update_hospital(self, user_id: int, hospital_id: int, data):
        """Update hospital"""
        logger.info("Started update_hospital method for hospital_id: %s", hospital_id)
        message, status = User.check_user_type_required(user_id, "super_admin")
        if status != 200:
            return message, status

        try:
            hospital = Hospital.query.get(hospital_id)
        except Exception as e:
            logger.exception("Exception while getting hospital with id %s: %s", hospital_id, e)
            return {"error": "Internal server error"}, 500

        if not hospital:
            logger.error("Hospital with id %s not found", hospital_id)
            return {"error": "Hospital not found"}, 404

        try:
            # Update data if new values are provided, otherwise keep original values
            hospital.name = data.get("name", hospital.name)
            hospital.city = data.get("city", hospital.city)
            hospital.street = data.get("street", hospital.street)
            hospital.postal_code = data.get("postal_code", hospital.postal_code)
            hospital.country = data.get("country", hospital.country)

            db.session.commit()
            logger.info("Hospital with id %s successfully updated", hospital_id)
            return {"message": "Hospital updated successfully"}, 200
        except Exception as e:
            logger.exception("Exception while updating hospital with id %s: %s", hospital_id, e)
            db.session.rollback()
            return {"error": "Internal server error"}, 500

    def get_hospitals(self, user_id: int):
        """Get all hospitals"""
        logger.info("Started get_hospitals method")
        message, status = User.check_user_type_required(user_id, "super_admin")
        if status != 200:
            return message, status

        try:
            hospitals = Hospital.query.all()
            hospitals_data = [
                {
                    "id": h.id,
                    "name": h.name,
                    "city": h.city,
                    "street": h.street,
                    "postal_code": h.postal_code,
                    "country": h.country,
                } for h in hospitals
            ]
            logger.info("Hospital list loaded, count: %d", len(hospitals_data))
            return hospitals_data, 200
        except Exception as e:
            logger.exception("Exception while getting hospitals list: %s", e)
            return {"error": "Internal server error"}, 500

    def get_hospital(self, user_id: int, hospital_id: int):
        """Get specific hospital"""
        logger.info("Started get_hospital method")
        message, status = User.check_user_type_required(user_id, "super_admin")
        if status != 200:
            return message, status
        try:
            hospital = Hospital.query.get(hospital_id)
            hospital_data = {
                    "id": hospital.id,
                    "name": hospital.name,
                    "city": hospital.city,
                    "street": hospital.street,
                    "postal_code": hospital.postal_code,
                    "hospital_code": hospital.hospital_code,
                    "country": hospital.country,
                }
            logger.info("Hospital information loaded, data count: %d", len(hospital_data))
            return hospital_data, 200
        except Exception as e:
            logger.exception("Exception while getting hospital information: %s", e)
            return {"error": "Internal server error"}, 500


    def check_user_id(self, user_id: int):
        """Check if user has super_admin permission."""
        return User.check_user_type_required(user_id, "super_admin")
