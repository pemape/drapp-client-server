import logging
import os  # <-- ADD THIS IMPORT
from flask import Blueprint, request, jsonify, abort, render_template, session, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from server.models import User
from server.services.account_service import AccountService
from server.database import db
from server.extensions import limiter

bp = Blueprint('settings', __name__, url_prefix='/settings')
account_service = AccountService()

logger = logging.getLogger(__name__)

# --- LOG LEVEL SEVERITY LOGIC ---
# Get logging level from environment (default INFO)
log_level_str = os.environ.get('LOG_LEVEL', 'INFO').upper()

# Convert text level to logging module constant
# Use .get() with INFO default for invalid values
log_level = getattr(logging, log_level_str, logging.INFO)

# Set logging level for this logger
logger.setLevel(log_level)
# --- END LOG LEVEL SEVERITY LOGIC ---


@bp.route('/', methods=['GET'], endpoint='account_page')
@jwt_required()
def account_page():
    # Simple display of account page
    return render_template("account.html")


@bp.route('/info', methods=['GET'], endpoint='account_info')
@jwt_required()
def account_info():
    # Input validation: validate user_id from token
    user_id = get_jwt_identity()
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        logger.error("Invalid user_id obtained from token: %s", user_id)
        if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
            return jsonify({'error': 'Invalid token data'}), 400
        else:
            flash("Invalid token data", "error")
            return render_template("error_400.html"), 400

    # Get account data using service layer
    response, status = AccountService.get_account_info(user_id_int)
    logger.debug("Account data successfully retrieved for user %s", user_id_int)

    # Output control: return JSON or HTML based on Accept header
    if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
        return jsonify(response), status
    else:
        return render_template("account.html", user=response), status


@bp.route('/edit', methods=['POST'], endpoint='edit_current_account_post')
@jwt_required()
def edit_current_account_post():
    logger.info("Started account edit request")

    # Input validation: check if it's JSON or form data
    if request.is_json:
        data = request.get_json()
        # Example validation: check if JSON contains required field "some_required_field"
        if not data or 'some_required_field' not in data:
            logger.error("Missing required field in JSON inputs")
            if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
                return jsonify({'error': 'Missing required field'}), 400
            else:
                flash("Missing required field", "error")
                return render_template("error_400.html"), 400
    else:
        data = request.form
        # Example validation for forms
        if not data or 'some_required_field' not in data:
            logger.error("Missing required field in form data")
            flash("Missing required field", "error")
            return render_template("error_400.html"), 400

    # Here would follow the logic for account update (e.g. account_service.update_account(data))
    # For demo purposes, we'll just call account_info() to return current data
    logger.info("Account edit data: %s", data)
    return account_info()


def _get_current_user():
    """Common logic for getting logged-in user data."""
    user_id = get_jwt_identity()
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        logger.error("Invalid user_id for getting current user: %s", user_id)
        flash('Invalid user', 'error')
        return render_template('error_400.html'), 400

    user = db.session.get(User, user_id_int)
    if not user:
        logger.error("User with id %s not found", user_id_int)
        flash('User not found', 'error')
        return render_template('error_404.html'), 404

    logger.info("User %s successfully loaded", user_id_int)
    return render_template("account.html", user=user)