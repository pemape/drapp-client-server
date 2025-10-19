import logging

from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from server.services.technicians_service import TechniciansService

bp = Blueprint('technicians', __name__, url_prefix='/technicians')
technician_service = TechniciansService()

logger = logging.getLogger(__name__)


@bp.route('/add', methods=['POST'])
@jwt_required()
def add_technician():
    """Add technician (only for super_admin)."""
    logger.info("add_technician endpoint requested")
    user_id = get_jwt_identity()

    if not (request.is_json and request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']):
        logger.error("add_technician: Invalid input or Accept header")
        return jsonify({'error': 'Invalid input or only JSON responses supported'}), 406

    data = request.get_json()
    logger.debug("add_technician: Received data, keys: %s", list(data.keys()))

    try:
        response_data, status = technician_service.add_technician(user_id, data)
        logger.info("add_technician: Technician added with status %s", status)
    except Exception as e:
        logger.exception("add_technician: Exception while adding technician: %s", e)
        return jsonify({'error': 'Internal server error'}), 500

    return jsonify(response_data), status


@bp.route('/update/<int:technician_id>', methods=['PUT'])
@jwt_required()
def update_technician(technician_id):
    """Update technician (only for super_admin)."""
    logger.info("update_technician endpoint requested for technician_id: %s", technician_id)
    user_id = get_jwt_identity()

    if not (request.is_json and request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']):
        logger.error("update_technician: Invalid input or Accept header")
        return jsonify({'error': 'Invalid input or only JSON responses supported'}), 406

    data = request.get_json()
    logger.debug("update_technician: Received data, keys: %s", list(data.keys()))

    try:
        response_data, status = technician_service.update_technician(user_id, technician_id, data)
        logger.info("update_technician: Technician with id %s updated with status %s", technician_id, status)
    except Exception as e:
        logger.exception("update_technician: Exception while updating technician: %s", e)
        return jsonify({'error': 'Internal server error'}), 500

    return jsonify(response_data), status


@bp.route('/list', methods=['GET'])
@jwt_required()
def list_technicians():
    """Get list of technicians (only for super_admin)."""
    logger.info("list_technicians endpoint requested")
    user_id = get_jwt_identity()

    if not (request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']):
        logger.error("list_technicians: Frontend does not require JSON response")
        return jsonify({'error': 'Only JSON responses supported'}), 406

    try:
        response_data, status = technician_service.get_technicians(user_id)
        logger.info("list_technicians: Technicians list loaded with status %s", status)
    except Exception as e:
        logger.exception("list_technicians: Exception while getting technicians: %s", e)
        return jsonify({'error': 'Internal server error'}), 500

    return jsonify(response_data), status


@bp.route('/<int:technician_id>', methods=['GET'])
@jwt_required()
def get_technician(technician_id):
    """Get information about specific technician."""
    logger.info("get_technician endpoint requested for technician_id: %s", technician_id)
    user_id = get_jwt_identity()

    try:
        response_data, status = technician_service.get_technician(user_id, technician_id)
        logger.info("get_technician: Technician information loaded with status %s", status)
    except Exception as e:
        logger.exception("get_technician: Exception while getting technician: %s", e)
        if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
            return jsonify({'error': 'Internal server error'}), 500
        else:
            return render_template("error_500.html", error="Internal server error"), 500

    if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
        return jsonify(response_data), status
    else:
        return render_template("technician_details.html", technician=response_data), status


@bp.route('/', methods=['GET'])
@jwt_required()
def get_technicians_page():
    """Display main technicians page (requires super_admin role)."""
    user_id = get_jwt_identity()
    try:
        user_id_int = int(user_id)
        message, status = technician_service.check_user_id(user_id_int)
    except (ValueError, TypeError):
        if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
            return jsonify({'error': 'Internal server error'}), 500
        else:
            return render_template("error_500.html", error="Internal server error"), 500

    if status != 200:
        return render_template('error_404.html'), 404
    else:
        logger.info("User with id %s accessing technicians page", user_id_int)
        return render_template("technicians.html"), status
