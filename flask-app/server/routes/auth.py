import logging

from flask import Blueprint, request, render_template, flash, redirect, url_for, jsonify
from flask_jwt_extended import jwt_required, set_access_cookies, unset_jwt_cookies, get_jwt_identity

from server import db
from server.models import User
from server.services.auth_service import AuthService
from server.extensions import limiter
from server.services.dashboard_service import DashboardService

bp = Blueprint('auth', __name__, url_prefix='/')
auth_service = AuthService()
dashboard_service = DashboardService()

logger = logging.getLogger(__name__)

@bp.route('/login', methods=['GET'], endpoint='login_get')
def login_get():
    """Endpoint to display the login form."""
    logger.info("GET /login endpoint accessed")
    if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
        logger.debug("Returning JSON response for login page")
        return jsonify({"msg": "Login page"}), 200
    else:
        logger.debug("Rendering login.html template")
        return render_template('login.html'), 200


@bp.route('/login', methods=['POST'], endpoint='login_post')
@limiter.limit("5 per 5 minutes", methods=['POST'])
def login_post():
    """
    Endpoint for user login.
    """
    logger.info("POST /login endpoint accessed")
    if request.is_json:
        data = request.get_json()
        logger.debug("Received JSON data: %s", data)
    else:
        data = request.form
        logger.debug("Received form data: %s", data)

    result, status = auth_service.login_user(data)
    logger.info("AuthService login_user result: %s, status: %d", result, status)

    if status == 200:
        logger.info("Login successful")
        if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
            response = jsonify(result)
        else:
            flash(result.get('message', 'Login successful'), 'success')
            response = redirect(url_for('auth.dashboard'))

        set_access_cookies(response, result.get('access_token'))
        return response, status
    else:
        logger.warning("Login failed with status: %d, result: %s", status, result)
        if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
            return jsonify(result), status
        else:
            flash(result.get('error', 'Login failed'), 'error')
            return render_template('login.html'), status


@bp.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    logger.info("GET /dashboard endpoint accessed")
    if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
        logger.debug("Returning JSON response for dashboard")
        return jsonify({"msg": "This endpoint returns HTML for dashboard"}), 200
    else:
        user_id = get_jwt_identity()
        logger.debug("JWT identity retrieved: %s", user_id)
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            logger.error("Invalid user identifier: %s", user_id)
            flash("Invalid user identifier", "error")
            return render_template('error_400.html'), 400

        user = db.session.get(User, user_id_int)
        if not user:
            logger.error("User not found for ID: %d", user_id_int)
            flash("User not found", "error")
            return render_template('error_404.html'), 404

        logger.info("Rendering dashboard for user: %s", user.user_type)
        return render_template('dashboard.html', user=user, current_page="dashboard")


@bp.route('/dashboard/info', methods=['GET'])
@jwt_required()
def dashboard_info():
    """
    Endpoint to fetch dashboard information as JSON.
    """
    logger.info("GET /dashboard/info endpoint accessed")
    user_id = get_jwt_identity()
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        logger.error("Invalid user identifier: %s", user_id)
        return jsonify({"error": "Invalid user identifier"}), 400

    message, status = dashboard_service.get_info(user_id_int)
    logger.info("DashboardService get_info result: %s, status: %d", message, status)
    return jsonify(message), status


@bp.route('/logout', methods=['GET'])
def logout():
    """
    Endpoint for user logout.
    """
    logger.info("GET /logout endpoint accessed")
    response = redirect(url_for('auth.login_get'))
    unset_jwt_cookies(response)
    logger.info("JWT cookies unset, redirecting to login page")
    return response


@bp.route('/', methods=['GET'])
def landing():
    logger.info("GET / endpoint accessed")
    if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
        logger.debug("Returning JSON response for landing page")
        return jsonify({"msg": "Landing page"}), 200
    else:
        logger.debug("Rendering landing.html template")
        return render_template('landing.html'), 200