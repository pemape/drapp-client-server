import logging
from server.database import db
from server.models.messages_data import MessageData
from server.models.user import User
import os
from werkzeug.utils import secure_filename
from server.models.messages_images_data import MessageImage
from pathlib import Path
from server.config import Config

logger = logging.getLogger(__name__)
# Removed hardcoded setLevel - now uses configurable LOG_LEVEL from environment

UPLOAD_FOLDER = "uploads/message_images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class MessageService:
    @staticmethod
    def send_message(data):
        logger.info("Starting message saving process")

        try:
            sender_id = data.get('sender_id')
            recipient_id = data.get('recipient_id')
            content = data.get('content')
            images = data.get('images', [])

            if not all([sender_id, recipient_id, content]):
                logger.error("Missing required fields")
                return {'error': 'Missing required fields'}, 400

            if not recipient_id:
                return {'error': 'Príjemca neexistuje'}, 404

            message = MessageData(
                sender_id=sender_id,
                recipient_id=recipient_id,
                content=content
            )

            db.session.add(message)
            db.session.flush()  # so message.id is available

            saved_images = []
            for img_file in images[:10]:
                if img_file.filename == "":
                    continue
                filename = secure_filename(img_file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, f"{message.id}_{filename}")
                img_file.save(filepath)

                # Store just the filename for frontend to use with the route
                filename_only = f"{message.id}_{filename}"

                image_entry = MessageImage(
                    message_id=message.id,
                    image_path=filename_only
                )
                saved_images.append(image_entry)

            db.session.add_all(saved_images)
            db.session.commit()

            logger.info("Message with images saved successfully")
            return {'message': 'Správa bola úspešne odoslaná.'}, 201

        except Exception as e:
            db.session.rollback()
            logger.exception("Exception while sending message")
            return {'error': 'Nepodarilo sa odoslať správu.'}, 500
