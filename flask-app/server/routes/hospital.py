import logging
from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from server.services.hospital_service import HospitalService

bp = Blueprint('hospitals', __name__, url_prefix='/hospitals')
hospital_service = HospitalService()

logger = logging.getLogger(__name__)

@bp.route('/add', methods=['POST'])
@jwt_required()
def add_hospital():
    """Add hospital (only for super_admin)."""
    logger.info("add_hospital endpoint requested")
    user_id = get_jwt_identity()

    # This endpoint requires JSON input and JSON response.
    if not (request.is_json and request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']):
        logger.error("add_hospital: Invalid input or Accept header")
        return jsonify({'error': 'Invalid input or only JSON responses supported'}), 406

    data = request.get_json()
    logger.debug("add_hospital: Received data, keys: %s", list(data.keys()))

    try:
        response_data, status = hospital_service.add_hospital(user_id, data)
        logger.info("add_hospital: Hospital added with status %s", status)
    except Exception as e:
        logger.exception("add_hospital: Exception while adding hospital: %s", e)
        return jsonify({'error': 'Internal server error'}), 500

    return jsonify(response_data), status


@bp.route('/update/<int:hospital_id>', methods=['PUT'])
@jwt_required()
def update_hospital(hospital_id):
    """Update hospital (only for super_admin)."""
    logger.info("update_hospital endpoint requested for hospital_id: %s", hospital_id)
    user_id = get_jwt_identity()
    if not (request.is_json and request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']):
        logger.error("update_hospital: Invalid input or Accept header")
        return jsonify({'error': 'Invalid input or only JSON responses supported'}), 406

    data = request.get_json()
    logger.debug("update_hospital: Received data, keys: %s", list(data.keys()))

    try:
        response_data, status = hospital_service.update_hospital(user_id, hospital_id, data)
        logger.info("update_hospital: Hospital with id %s updated with status %s", hospital_id, status)
    except Exception as e:
        logger.exception("update_hospital: Exception while updating hospital with id %s: %s", hospital_id, e)
        return jsonify({'error': 'Internal server error'}), 500

    return jsonify(response_data), status


@bp.route('/list', methods=['GET'])
@jwt_required()
def list_hospitals():
    """Get list of hospitals (only for super_admin)."""
    logger.info("list_hospitals endpoint requested")
    user_id = get_jwt_identity()

    if not (request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']):
        logger.error("list_hospitals: Frontend does not require JSON response")
        return jsonify({'error': 'Only JSON responses supported'}), 406

    try:
        response_data, status = hospital_service.get_hospitals(user_id)
        logger.info("list_hospitals: Hospitals list loaded with status %s", status)
    except Exception as e:
        logger.exception("list_hospitals: Exception while getting hospitals: %s", e)
        return jsonify({'error': 'Internal server error'}), 500

    return jsonify(response_data), status

@bp.route('/<int:hospital_id>', methods=['GET'])
@jwt_required()
def get_hospital(hospital_id):
    """Get information about specific hospital (only for super_admin).
       Returns JSON if client prefers it, otherwise renders HTML page.
    """
    logger.info("get_hospital endpoint requested for hospital_id: %s", hospital_id)
    user_id = get_jwt_identity()

    try:
        response_data, status = hospital_service.get_hospital(user_id, hospital_id)
        logger.info("get_hospital: Hospital information loaded with status %s", status)
    except Exception as e:
        logger.exception("get_hospital: Exception while getting hospital with id %s: %s", hospital_id, e)
        if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
            return jsonify({'error': 'Internal server error'}), 500
        else:
            return render_template("error_500.html", error="Internal server error"), 500

    if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
        return jsonify(response_data), status
    else:
        return render_template("hospital_details.html", hospital=response_data), status


@bp.route('/', methods=['GET'])
@jwt_required()
def get_hospitals():
    """
    Endpoint for displaying hospitals page.
    Requires user to be logged in and have super_admin role.
    If not, access is denied.
    """
    user_id = get_jwt_identity()
    try:
        user_id_int = int(user_id)
        message, status = hospital_service.check_user_id(user_id_int)
    except (ValueError, TypeError):
        if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
            return jsonify({'error': 'Internal server error'}), 500
        else:
            return render_template("error_500.html", error="Internal server error"), 500
    if status != 200:
        return render_template('error_404.html'), 404
    else:
        logger.info("User with id %s accessing hospitals page", user_id_int)
        return render_template("hospitals.html"), status
