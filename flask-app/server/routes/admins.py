import logging
from os import abort

from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from server.services.admins_service import AdminsService

bp = Blueprint('admins', __name__, url_prefix='/admins')
admin_service = AdminsService()

logger = logging.getLogger(__name__)


@bp.route('/add', methods=['POST'])
@jwt_required()
def add_admin():
    """Add admin (only for super_admin)."""
    logger.info("add_admin endpoint requested")
    user_id = get_jwt_identity()

    if not (request.is_json and request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']):
        logger.error("add_admin: Invalid input or Accept header")
        return jsonify({'error': 'Invalid input or only JSON responses supported'}), 406

    data = request.get_json()
    logger.debug("add_admin: Received data, keys: %s", list(data.keys()))

    try:
        response_data, status = admin_service.add_admin(user_id, data)
        logger.info("add_admin: Admin added with status %s", status)
    except Exception as e:
        logger.exception("add_admin: Exception while adding admin: %s", e)
        return jsonify({'error': 'Internal server error'}), 500

    return jsonify(response_data), status


@bp.route('/update/<int:admin_id>', methods=['PUT'])
@jwt_required()
def update_admin(admin_id):
    """Update admin (only for super_admin)."""
    logger.info("update_admin endpoint requested for admin_id: %s", admin_id)
    user_id = get_jwt_identity()

    if not (request.is_json and request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']):
        logger.error("update_admin: Invalid input or Accept header")
        return jsonify({'error': 'Invalid input or only JSON responses supported'}), 406

    data = request.get_json()
    logger.debug("update_admin: Received data, keys: %s", list(data.keys()))

    try:
        response_data, status = admin_service.update_admin(user_id, admin_id, data)
        logger.info("update_admin: Admin with id %s updated with status %s", admin_id, status)
    except Exception as e:
        logger.exception("update_admin: Exception while updating admin: %s", e)
        return jsonify({'error': 'Internal server error'}), 500

    return jsonify(response_data), status


@bp.route('/list', methods=['GET'])
@jwt_required()
def list_admins():
    """Get list of admins (only for super_admin)."""
    logger.info("list_admins endpoint requested")
    user_id = get_jwt_identity()

    if not (request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']):
        logger.error("list_admins: Frontend does not require JSON response")
        return jsonify({'error': 'Only JSON responses supported'}), 406

    try:
        response_data, status = admin_service.get_admins(user_id)
        logger.info("list_admins: Admins list loaded with status %s", status)
    except Exception as e:
        logger.exception("list_admins: Exception while getting admins: %s", e)
        return jsonify({'error': 'Internal server error'}), 500

    return jsonify(response_data), status


@bp.route('/<int:admin_id>', methods=['GET'])
@jwt_required()
def get_admin(admin_id):
    """Get information about specific admin."""
    logger.info("get_admin endpoint requested for admin_id: %s", admin_id)
    user_id = get_jwt_identity()

    try:
        response_data, status = admin_service.get_admin(user_id, admin_id)
        logger.info("get_admin: Admin information loaded with status %s", status)
    except Exception as e:
        logger.exception("get_admin: Exception while getting admin: %s", e)
        if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
            return jsonify({'error': 'Internal server error'}), 500
        else:
            return render_template("error_500.html", error="Internal server error"), 500

    if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
        return jsonify(response_data), status
    else:
        return render_template("admin_details.html", admin=response_data), status


@bp.route('/', methods=['GET'])
@jwt_required()
def get_admins_page():
    """Display main admins page (requires super_admin role)."""
    user_id = get_jwt_identity()
    try:
        user_id_int = int(user_id)
        message, status = admin_service.check_user_id(user_id_int)
    except (ValueError, TypeError):
        if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
            return jsonify({'error': 'Internal server error'}), 500
        else:
            return render_template("error_500.html", error="Internal server error"), 500

    if status != 200:
        return render_template('error_404.html'), 404
    else:
        logger.info("User with id %s accessing admins page", user_id_int)
        return render_template("admins.html"), status
