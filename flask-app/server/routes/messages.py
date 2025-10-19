from server.models.messages_data import MessageData
from server.services.messages_service import MessageService
from server.models.doctor_data import DoctorData
from server.models.user import User
from server.models.patient_data import PatientData
from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from server.database import db
from flask import send_from_directory, current_app
import os
import logging

bp = Blueprint('messages_bp', __name__, url_prefix='/messages')
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "heic", "heif"}

logger = logging.getLogger(__name__)


@bp.route("/send", methods=["POST"])
@jwt_required()
def send_message():
    logger.info("send_message endpoint hit")

    user_id = get_jwt_identity()

    recipient_input = request.form.get("recipient")
    message = request.form.get("message")
    images = request.files.getlist("images")
    filtered_images = [img for img in images if img.filename and allowed_file(img.filename)]

    logger.info(f"Received {len(images)} images, filtered to {len(filtered_images)} allowed images")
    for i, f in enumerate(filtered_images):
        logger.info(f"Image {i}: filename={f.filename}")

    if len(filtered_images) > 10:
        return jsonify({"error": "Maximum 10 images allowed."}), 400

    logger.debug("Send message form data: sender=%s, recipient=%s, message length=%d", user_id, recipient_input,
                 len(message or ""))

    if not recipient_input or not message:
        return jsonify({"error": "Recipient and message are required fields."}), 400

    sender: User = db.session.get(User, user_id)
    if not sender:
        return jsonify({"error": "Sender does not exist."}), 404

    # Normalize recipient input and find user
    recipient = None
    if recipient_input.isdigit():
        recipient = db.session.get(User, int(recipient_input))
    else:
        recipient = db.session.query(User).filter_by(email=recipient_input.strip()).first()

    if not recipient:
        return jsonify({"error": "Recipient does not exist."}), 400

    if sender.id == recipient.id:
        return jsonify({"error": "You cannot send a message to yourself."}), 400

    # ===============================
    #     AUTHORIZATION RULES
    # ===============================

    def deny(reason="You are not authorized to send this message."):
        logger.warning(
            f"Unauthorized message attempt: sender={sender.id} ({sender.user_type}) -> recipient={recipient.id} ({recipient.user_type})")
        return jsonify({"error": reason}), 403

    s_type = sender.user_type
    r_type = recipient.user_type

    if r_type == "super_admin" and s_type != "admin":
        return deny("Only admin can send message to super-admin.")
    elif r_type == "admin" and s_type not in {"admin", "super_admin", "doctor"}:
        return deny("Only doctors or higher can send messages to admin.")
    elif s_type == "doctor" and r_type == "patient":
        sender_doctor: DoctorData = db.session.get(DoctorData, sender.id)
        if not sender_doctor or not any(p.id == recipient.id for p in sender_doctor.patients):
            return deny("You can only send messages to your patients.")
    elif s_type == "patient" and r_type == "doctor":
        sender_patient: PatientData = db.session.get(PatientData, sender.id)
        if not sender_patient or sender_patient.doctor_id != recipient.id:
            return deny("You can only send messages to your doctor.")

    try:
        result, status_code = MessageService.send_message({
            'sender_id': sender.id,
            'recipient_id': recipient.id,  # Always send email for resolution
            'content': message,
            'images': filtered_images,
        })

        return jsonify(result), status_code

    except Exception as e:
        logger.exception("send_message: Error")
        return jsonify({"error": "Internal server error."}), 500


@bp.route('/list', methods=['GET'])
@jwt_required()
def list_messages():
    logger.info("list_messages endpoint hit")
    user_id = int(get_jwt_identity())

    if not (request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']):
        logger.error("list_messages: Frontend does not accept JSON")
        return jsonify({'error': 'Only JSON responses supported'}), 406

    try:
        from server.models.messages_data import MessageData

        messages = MessageData.query.filter(
            (MessageData.sender_id == user_id) | (MessageData.recipient_id == user_id)
        ).order_by(MessageData.timestamp.desc()).all()

        response_data = [m.to_dict() for m in messages]

        logger.info("list_messages: Loaded %d messages", len(response_data))
        return jsonify({
            "user_id": user_id,
            "messages": response_data
        }), 200

    except Exception as e:
        logger.exception("list_messages: Exception occurred: %s", e)
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/uploads/message_images/<filename>')
def uploaded_file(filename):
    """Serve uploaded message images."""
    logger.info(f"Serving message image: {filename}")
    uploads_dir = os.path.join(current_app.root_path, '..', 'uploads', 'message_images')
    return send_from_directory(uploads_dir, filename)


@bp.route('/<int:message_id>', methods=['GET'])
@jwt_required()
def get_message(message_id):
    """Get detail of specific message."""
    logger.info("get_message endpoint requested for message_id: %s", message_id)
    user_id = get_jwt_identity()

    try:
        message = db.session.get(MessageData, message_id)
        if not message:
            return jsonify({"error": "Message does not exist"}), 404

        # Optional: check if user is authorized to view it
        # if user_id not in [message.sender_id, message.recipient_id]:
        #    return jsonify({"error": "You do not have access to this message"}), 403

        response_data = message.to_dict()
        logger.info("get_message: Successfully loaded message %s", message_id)

    except Exception as e:
        logger.exception("get_message: error")
        return jsonify({"error": "Server error"}), 500

    if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
        return jsonify(response_data), 200
    else:
        return render_template("message_details.html", message=response_data), 200


@bp.route('/<int:message_id>/mark_read', methods=['PUT'])
@jwt_required()
def mark_message_as_read(message_id):
    user_id = int(get_jwt_identity())
    logger.info("User %s is marking message %s as read", user_id, message_id)

    message = db.session.get(MessageData, message_id)
    if not message:
        return jsonify({"error": "Message does not exist"}), 404

    # only the recipient can mark message as is_read
    if user_id != message.recipient_id:
        return jsonify({"error": "You do not have permission to mark this message as read."}), 403

    try:
        if not message.is_read:
            message.is_read = True
            db.session.commit()
            logger.info("Message %s marked as read", message_id)
        return jsonify({"message": "Message marked as read"}), 200
    except Exception as e:
        logger.exception("Error while marking message as read")
        return jsonify({"error": "Server error"}), 500


@bp.route("/<int:message_id>/toggle_read", methods=["PUT"])
@jwt_required()
def toggle_read(message_id):
    user_id = int(get_jwt_identity())
    logger.info(f"User {user_id} is toggling read status for message {message_id}")

    try:
        message = db.session.get(MessageData, message_id)
        if not message:
            return jsonify({"error": "Message does not exist"}), 404

        # Only recipient can toggle read state
        if user_id != message.recipient_id:
            logger.info(f"User {user_id} is unauthorized to toggle is_read for recipient {message.recipient_id}")
            return jsonify({"error": "You do not have permission to change this message's status."}), 403

        message.is_read = not message.is_read
        db.session.commit()

        logger.info(f"Message {message_id} toggled to is_read={message.is_read}")
        return jsonify({"success": True, "is_read": message.is_read}), 200

    except Exception as e:
        logger.exception("Error while toggling message")
        return jsonify({"error": "Error updating message"}), 500


@bp.route('/', methods=['GET'])
@jwt_required()
def get_spravy_page():
    logger.debug("Entered get_spravy_page()")

    user_id = get_jwt_identity()
    logger.debug(f"User id from JWT: {user_id}")

    try:
        user_id_int = int(user_id)
        logger.debug(f"user_id_int successfully converted: {user_id_int}")
        # Example check if needed
        # message, status = some_check(user_id_int)
        status = 200  # temporarily hardcoded for debugging
    except (ValueError, TypeError) as e:
        logger.error(f"Error converting user_id: {e}")
        if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
            return jsonify({'error': 'Internal server error'}), 500
        else:
            return render_template("error_500.html", error="Internal server error"), 500

    if status != 200:
        logger.debug("Status not 200, returning 404 error page")
        return render_template('error_404.html'), 404
    else:
        logger.info(f"User with id {user_id_int} accessed messages page")
        return render_template("messages.html"), 200


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS