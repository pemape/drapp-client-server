import logging
from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from server.services.doctors_service import DoctorsService

bp = Blueprint('doctors', __name__, url_prefix='/doctors')
doctor_service = DoctorsService()

logger = logging.getLogger(__name__)


@bp.route('/add', methods=['POST'])
@jwt_required()
def add_doctor():
    """Add doctor (only for super_admin)."""
    logger.info("add_doctor endpoint requested")
    user_id = get_jwt_identity()

    if not (request.is_json and request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']):
        logger.error("add_doctor: Invalid input or Accept header")
        return jsonify({'error': 'Invalid input or only JSON responses supported'}), 406

    data = request.get_json()
    logger.debug("add_doctor: Received data, keys: %s", list(data.keys()))

    try:
        response_data, status = doctor_service.add_doctor(user_id, data)
        logger.info("add_doctor: Doctor added with status %s", status)
    except Exception as e:
        logger.exception("add_doctor: Exception while adding doctor: %s", e)
        return jsonify({'error': 'Internal server error'}), 500

    return jsonify(response_data), status


@bp.route('/update/<int:doctor_id>', methods=['PUT'])
@jwt_required()
def update_doctor(doctor_id):
    """Update doctor (only for super_admin)."""
    logger.info("update_doctor endpoint requested for doctor_id: %s", doctor_id)
    user_id = get_jwt_identity()

    if not (request.is_json and request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']):
        logger.error("update_doctor: Invalid input or Accept header")
        return jsonify({'error': 'Invalid input or only JSON responses supported'}), 406

    data = request.get_json()
    logger.debug("update_doctor: Received data, keys: %s", list(data.keys()))

    try:
        response_data, status = doctor_service.update_doctor(user_id, doctor_id, data)
        logger.info("update_doctor: Doctor with id %s updated with status %s", doctor_id, status)
    except Exception as e:
        logger.exception("update_doctor: Exception while updating doctor: %s", e)
        return jsonify({'error': 'Internal server error'}), 500

    return jsonify(response_data), status


@bp.route('/list', methods=['GET'])
@jwt_required()
def list_doctors():
    """Get list of doctors (only for super_admin)."""
    logger.info("list_doctors endpoint requested")
    user_id = get_jwt_identity()

    if not (request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']):
        logger.error("list_doctors: Frontend does not require JSON response")
        return jsonify({'error': 'Only JSON responses supported'}), 406

    try:
        response_data, status = doctor_service.get_doctors(user_id)
        logger.info("list_doctors: Doctors list loaded with status %s", status)
    except Exception as e:
        logger.exception("list_doctors: Exception while getting doctors: %s", e)
        return jsonify({'error': 'Internal server error'}), 500

    return jsonify(response_data), status


@bp.route('/<int:doctor_id>', methods=['GET'])
@jwt_required()
def get_doctor(doctor_id):
    """Get information about specific doctor."""
    logger.info("get_doctor endpoint requested for doctor_id: %s", doctor_id)
    user_id = get_jwt_identity()

    try:
        response_data, status = doctor_service.get_doctor(user_id, doctor_id)
        logger.info("get_doctor: Doctor information loaded with status %s", status)
    except Exception as e:
        logger.exception("get_doctor: Exception while getting doctor: %s", e)
        if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
            return jsonify({'error': 'Internal server error'}), 500
        else:
            return render_template("error_500.html", error="Internal server error"), 500

    if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
        return jsonify(response_data), status
    else:
        return render_template("doctor_details.html", doctor=response_data), status


@bp.route('/', methods=['GET'])
@jwt_required()
def get_doctors_page():
    """Display main doctors page (only for super_admin)."""
    user_id = get_jwt_identity()
    try:
        user_id_int = int(user_id)
        message, status = doctor_service.check_user_id(user_id_int)
    except (ValueError, TypeError):
        if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
            return jsonify({'error': 'Internal server error'}), 500
        else:
            return render_template("error_500.html", error="Internal server error"), 500

    if status != 200:
        return render_template('error_404.html'), 404
    else:
        logger.info("User with id %s accessing doctors page", user_id_int)
        return render_template("doctors.html"), status
