import logging
from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from server.services.patients_service import PatientsService

bp = Blueprint('patients', __name__, url_prefix='/patients')
patient_service = PatientsService()

logger = logging.getLogger(__name__)


@bp.route('/add', methods=['POST'])
@jwt_required()
def add_patient():
    """Add patient."""
    logger.info("add_patient endpoint requested")
    user_id = get_jwt_identity()

    if not (request.is_json and request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']):
        logger.error("add_patient: Invalid input or Accept header")
        return jsonify({'error': 'Invalid input or only JSON responses supported'}), 406

    data = request.get_json()
    logger.debug("add_patient: Received data, keys: %s", list(data.keys()))

    try:
        response_data, status = patient_service.add_patient(user_id, data)
        logger.info("add_patient: Patient added with status %s", status)
    except Exception as e:
        logger.exception("add_patient: Exception while adding patient: %s", e)
        return jsonify({'error': 'Internal server error'}), 500

    return jsonify(response_data), status

@bp.route('/assign', methods=['POST'])
@jwt_required()
def assign_patient():
    """Assign patient."""
    logger.info("assign_patient endpoint requested")
    user_id = get_jwt_identity()

    if not (request.is_json and request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']):
        logger.error("assign_patient: Invalid input or Accept header")
        return jsonify({'error': 'Invalid input or only JSON responses supported'}), 406

    data = request.get_json()
    logger.debug("assign_patient: Received data, keys: %s", list(data.keys()))

    try:
        response_data, status = patient_service.assign_patient(user_id, data)
        logger.info("assign_patient: Patient assigned with status %s", status)
    except Exception as e:
        logger.exception("assign_patient: Exception while assigning patient: %s", e)
        return jsonify({'error': 'Internal server error'}), 500

    return jsonify(response_data), status


@bp.route('/update/<int:patient_id>', methods=['PUT'])
@jwt_required()
def update_patient(patient_id):
    """Update patient."""
    logger.info("update_patient endpoint requested for patient_id: %s", patient_id)
    user_id = get_jwt_identity()

    if not (request.is_json and request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']):
        logger.error("update_patient: Invalid input or Accept header")
        return jsonify({'error': 'Invalid input or only JSON responses supported'}), 406

    data = request.get_json()
    logger.debug("update_patient: Received data, keys: %s", list(data.keys()))

    try:
        response_data, status = patient_service.update_patient(user_id, patient_id, data)
        logger.info("update_patient: Patient with id %s updated with status %s", patient_id, status)
    except Exception as e:
        logger.exception("update_patient: Exception while updating patient: %s", e)
        return jsonify({'error': 'Internal server error'}), 500

    return jsonify(response_data), status


@bp.route('/list', methods=['GET'])
@jwt_required()
def list_patients():
    """Get list of patients."""
    logger.info("list_patients endpoint requested")
    user_id = get_jwt_identity()

    if not (request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']):
        logger.error("list_patients: Frontend does not require JSON response")
        return jsonify({'error': 'Only JSON responses supported'}), 406

    try:
        response_data, status = patient_service.get_patients(user_id)
        logger.info("list_patients: Patients list loaded with status %s", status)
    except Exception as e:
        logger.exception("list_patients: Exception while getting patients: %s", e)
        return jsonify({'error': 'Internal server error'}), 500

    return jsonify(response_data), status

@bp.route('/unassigned_list', methods=['GET'])
@jwt_required()
def unassigned_list_patients():
    """Get list of unassigned patients."""
    logger.info("unassigned_list_patients endpoint requested")
    user_id = get_jwt_identity()

    if not (request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']):
        logger.error("unassigned_list_patients: Frontend does not require JSON response")
        return jsonify({'error': 'Only JSON responses supported'}), 406

    try:
        response_data, status = patient_service.get_unassigned_patients(user_id)
        logger.info("unassigned_list_patients: Unassigned patients list loaded with status %s", status)
    except Exception as e:
        logger.exception("unassigned_list_patients: Exception while getting unassigned patients: %s", e)
        return jsonify({'error': 'Internal server error'}), 500

    return jsonify(response_data), status

@bp.route('/<int:patient_id>', methods=['GET'])
@jwt_required()
def get_patient(patient_id):
    """Get information about specific patient."""
    logger.info("get_patient endpoint requested for patient_id: %s", patient_id)
    user_id = get_jwt_identity()

    try:
        response_data, status = patient_service.get_patient(user_id, patient_id)
        logger.info("get_patient: Patient information loaded with status %s", status)
    except Exception as e:
        logger.exception("get_patient: Exception while getting patient: %s", e)
        if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
            return jsonify({'error': 'Internal server error'}), 500
        else:
            return render_template("error_500.html", error="Internal server error"), 500

    if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
        return jsonify(response_data), status
    else:
        return render_template("patient_details.html", patient=response_data), status


@bp.route('/', methods=['GET'])
@jwt_required()
def get_patients_page():
    """Display main patients page."""
    user_id = get_jwt_identity()
    try:
        user_id_int = int(user_id)
        message, status = patient_service.check_user_id(user_id_int)
    except (ValueError, TypeError):
        if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
            return jsonify({'error': 'Internal server error'}), 500
        else:
            return render_template("error_500.html", error="Internal server error"), 500

    if status != 200:
        return render_template('error_404.html'), 404
    else:
        logger.info("User with id %s accessing patients page", user_id_int)
        return render_template("patients.html"), status