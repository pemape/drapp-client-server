import base64
import mimetypes
import os
import uuid
from datetime import datetime
import requests
from werkzeug.utils import secure_filename
from server.database import db
from server.models.admin_data import AdminData
from server.models.doctor_data import DoctorData
from server.models.original_image_data import OriginalImageData
from server.models.user import User
from server.models.patient_data import PatientData
from server.models.device_data import DeviceData
from server.models.processed_image_data import ProcessedImageData, ProcessingStatus
import logging
from server.config import Config
from pathlib import Path
from server.services.methods_service import MethodsService

logger = logging.getLogger(__name__)
methods_service = MethodsService()

# Canonical DR grade names used across the app. Some services return abbreviated names
# such as "Moderate NPDR", but the classifier uses the longer wording.
DR_CLASS_LABELS = {
    0: "No DR",
    1: "Mild Non-Proliferative DR",
    2: "Moderate Non-Proliferative DR",
    3: "Severe Non-Proliferative DR",
    4: "Proliferative DR",
}

DR_CLASS_ALIASES = {
    "no dr": "No DR",
    "no diabetic retinopathy": "No DR",
    "mild npdr": "Mild Non-Proliferative DR",
    "mild non-proliferative dr": "Mild Non-Proliferative DR",
    "mild diabetic retinopathy": "Mild Non-Proliferative DR",
    "moderate npdr": "Moderate Non-Proliferative DR",
    "moderate non-proliferative dr": "Moderate Non-Proliferative DR",
    "moderate diabetic retinopathy": "Moderate Non-Proliferative DR",
    "severe npdr": "Severe Non-Proliferative DR",
    "severe non-proliferative dr": "Severe Non-Proliferative DR",
    "severe diabetic retinopathy": "Severe Non-Proliferative DR",
    "proliferative dr": "Proliferative DR",
    "proliferative diabetic retinopathy": "Proliferative DR",
}

class PhotoService:
    def __init__(self, base_upload_path=Config.UPLOAD_FOLDER):      
        self.base_upload_path = os.path.abspath(base_upload_path)

    def _create_user_directory(self, user_id):
        """Create a directory for the user if it doesn't exist."""
        user_dir = os.path.join(self.base_upload_path, str(user_id))
        os.makedirs(user_dir, exist_ok=True)

        # Create original and processed subdirectories
        original_dir = os.path.join(user_dir, "original")
        processed_dir = os.path.join(user_dir, "processed")
        os.makedirs(original_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)

        return os.path.abspath(user_dir)

    def _get_image_sequence_number(self, patient_id):
        """Get the next sequence number for a patient's images."""
        # Count existing images for this patient and add 1
        existing_count = OriginalImageData.query.filter_by(patient_id=patient_id).count()
        return existing_count + 1

    def _generate_image_filename(self, patient_id, eye_side, device_type, original_filename):
        """Generate a filename based on the new naming convention."""
        # Get sequence number for this patient
        seq_num = self._get_image_sequence_number(patient_id)


        # Normalize eye_side to L/R
        eye_code = "P" if eye_side.lower() == "right" else "L"

        # Normalize device_type (remove spaces, special chars)
        device_code = device_type.replace(" ", "_").lower() if device_type else "unknown"

        # Get file extension
        ext = os.path.splitext(original_filename)[1]

        # Create filename: patient_id_sequence_eye_device.ext
        return f"{patient_id}_{seq_num}_{eye_code}_{device_code}{ext}"


    def save_file_for_user(self, user_id, file_storage, is_processed=False):
        """
        Save a file (original or processed) in a user-specific folder.

        Args:
            user_id: The ID of the user (or patient) to associate the file with.
            file_storage: The FileStorage object (from Flask's request.files).
            is_processed: Whether this is a processed image (True) or original (False)

        Returns:
            The full path to the saved file.
        """
        # Ensure the user directory exists with the new structure
        user_dir = self._create_user_directory(user_id)

        # Choose the appropriate subfolder
        subfolder = "processed" if is_processed else "original"
        target_dir = os.path.join(user_dir, subfolder)

        # Generate a unique filename
        original_filename = secure_filename(file_storage.filename)
        ext = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{ext}"

        # Full file path
        file_path = os.path.join(target_dir, unique_filename)

        # Save the file
        file_storage.save(file_path)

        return file_path

    def save_photo(self, photo_file, user_id, patient_id, eye_side, diagnosis=None, device_name=None, device_type=None,
                   camera_type=None, quality=None):
        """
        Save a photo file and create database entry.

        Args:
            photo_file: FileStorage object from request.files
            user_id: ID of the user uploading the photo
            patient_id: ID of the patient the photo is for
            eye_side: 'right' or 'left'
            diagnosis: Optional diagnosis text
            device_id: Optional ID of the device used to take the photo
            quality: Quality of the image (default: 'good')

        Returns:
            tuple: (OriginalImageData object, status code, message)
        """
        try:
            # Validate inputs
            if not photo_file:
                return None, 400, "No photo file provided"

            if not photo_file.filename:
                return None, 400, "Invalid filename"

            # Create user directory and get absolute path
            user_dir = self._create_user_directory(patient_id)

            # Get original images directory
            original_dir = os.path.join(user_dir, "original")

            # Generate filename based on the new naming convention
            filename = self._generate_image_filename(

                patient_id,
                eye_side,
                device_type,
                secure_filename(photo_file.filename)
            )

            abs_file_path = os.path.join(original_dir, filename)

            # Save the file
            photo_file.save(abs_file_path)

            # Create device entry
            new_device = DeviceData(
                device_name=device_name,
                device_type=device_type,
                camera_model=camera_type,
                camera_resolution="1080p"
            )
            db.session.add(new_device)
            db.session.commit()
            device_id = new_device.id

            # Create database entry with absolute path
            photo_data = OriginalImageData(
                original_image_path=abs_file_path,
                quality=quality,
                eye_side=eye_side,
                diagnosis=diagnosis,
                device_id=device_id,
                creator_id=user_id,
                patient_id=patient_id
            )

            db.session.add(photo_data)
            db.session.commit()
            logger.info(f"Photo saved successfully: {photo_data.id} at absolute path: {abs_file_path}")

            return photo_data, 200, "Photo saved successfully"

        except Exception as e:
            logger.error(f"Error saving photo: {str(e)}")
            db.session.rollback()
            return None, 500, f"Error saving photo: {str(e)}"

    def get_user_photos(self, user_id):
        """Get all photos created by a specific user."""
        user = User.query.get(int(user_id))
        try:
            if user.is_super_admin():
                photos = OriginalImageData.query.all()
            elif user.is_admin():
                admin = AdminData.query.get(user_id)

                if not admin or not admin.hospital:
                    return {'error': 'Admin hospital not found'}, 404
                # Now access the hospital's doctors through the admin instance
                # In the get_patients method
                photos = (
                    OriginalImageData.query
                    .join(OriginalImageData.patient)  # spojenie na PatientData
                    .join(PatientData.doctor)  # spojenie na DoctorData
                    .filter(DoctorData.hospital_id == admin.hospital.id)
                    .all()
                )
            elif user.is_doctor():
                doctor = DoctorData.query.get(user_id)
                if doctor.super_doctor:
                    photos = OriginalImageData.query.all()
                else:
                    photos = (
                        OriginalImageData.query
                        .join(OriginalImageData.patient)  # spojenie na PatientData
                        .join(PatientData.doctor)  # spojenie na DoctorData
                        .filter(DoctorData.id == doctor.id)  # len pre tohto doktora
                        .all()
                    )

            elif user.is_technician():
                photos = OriginalImageData.query.filter_by(creator_id=user_id).all()
            elif user.is_patient():
                photos = OriginalImageData.query.filter_by(patient_id=user_id).all()

            else:
                return {'error': 'Unauthorized'}, 403
            return photos, 200, "Photos retrieved successfully"
        except Exception as e:
            logger.error(f"Error retrieving photos: {str(e)}")
            return None, 500, f"Error retrieving photos: {str(e)}"

    def get_patient_photos(self, patient_id):
        """Get all photos for a specific patient."""
        try:
            photos = OriginalImageData.query.filter_by(patient_id=patient_id).all()
            return photos, 200, "Photos retrieved successfully"
        except Exception as e:
            logger.error(f"Error retrieving patient photos: {str(e)}")
            return None, 500, f"Error retrieving patient photos: {str(e)}"

    def delete_photo(self, photo_id, user_id):
        """Delete a photo and its file."""
        try:
            photo = OriginalImageData.query.get(photo_id)

            if not photo:
                return False, 404, "Photo not found"

            # Check if user has permission (creator or admin)
            if photo.creator_id != user_id:
                user = User.query.get(user_id)
                if not user or not (user.is_admin() or user.is_super_admin()):
                    return False, 403, "Permission denied"

            # Delete file
            file_path = os.path.join(self.base_upload_path, photo.original_image_path)
            if os.path.exists(file_path):
                os.remove(file_path)

            # Delete database entry
            db.session.delete(photo)
            db.session.commit()

            return True, 200, "Photo deleted successfully"

        except Exception as e:
            logger.error(f"Error deleting photo: {str(e)}")
            db.session.rollback()
            return False, 500, f"Error deleting photo: {str(e)}"

    def get_photo_by_id(self, photo_id):
        """Get a specific photo by ID."""
        try:
            photo = OriginalImageData.query.get(photo_id)
            if not photo:
                return None, 404, "Photo not found"
            return photo, 200, "Photo retrieved successfully"
        except Exception as e:
            logger.error(f"Error retrieving photo: {str(e)}")
            return None, 500, f"Error retrieving photo: {str(e)}"

    def get_adjacent_photo_ids(self, photo_id, user_id):
        """
        Get the IDs of the previous and next photos based on creation date.

        Args:
            photo_id: The ID of the current photo
            user_id: The ID of the current user

        Returns:
            tuple: (prev_id, next_id) - The IDs of the previous and next photos,
                  or None if there is no previous or next photo
        """
        try:
            # Get the current photo
            current_photo = OriginalImageData.query.get(photo_id)
            if not current_photo:
                return None, None

            # Get all photos accessible to the user, ordered by creation date
            user_photos, _, _ = self.get_user_photos(user_id)
            if not user_photos:
                return None, None

            # Sort photos by creation date
            sorted_photos = sorted(user_photos, key=lambda p: p.created_at)

            # Find the index of the current photo
            current_index = next((i for i, p in enumerate(sorted_photos) if p.id == int(photo_id)), -1)

            if current_index == -1:
                return None, None

            # Get previous and next photo IDs
            prev_id = sorted_photos[current_index - 1].id if current_index > 0 else None
            next_id = sorted_photos[current_index + 1].id if current_index < len(sorted_photos) - 1 else None

            return prev_id, next_id

        except Exception as e:
            logger.error(f"Error getting adjacent photo IDs: {str(e)}")
            return None, None

    def check_processing_server_availability(self):
        """
        Check if the processing server is available.

        Returns:
            tuple: (available (bool), message (str))
        """
        try:
            url = f"{Config.PROCESSING_SERVICE_URL}/health"
            logger.info(f"Checking processing server health at: {url}")
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                return True, "Processing server is available"
            else:
                logger.warning(f"Processing server returned status code: {response.status_code}")
                return False, f"Processing server is not available (status code: {response.status_code})"
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            return False, "Processing server is not running or unreachable"
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to processing server: {str(e)}")
            return False, "Cannot connect to the processing server"
        except Exception as e:
            logger.error(f"Unexpected error checking processing server: {str(e)}")
            return False, f"Error checking processing server: {str(e)}"

    @staticmethod
    def is_detection_method(method_name):
        """The 'Detekcia' method is served by the fundus-dr-inference service."""
        return (method_name or "").strip().lower() == Config.DETECTION_METHOD_NAME.strip().lower()

    def check_detection_server_availability(self):
        """Check if the fundus-dr-inference service is available."""
        try:
            response = requests.get(f"{Config.FUNDUS_INFERENCE_URL}/health", timeout=3)
            if response.status_code == 200:
                return True, "Detection server is available"
            logger.warning(f"Detection server returned status code: {response.status_code}")
            return False, f"Detection server is not available (status code: {response.status_code})"
        except requests.exceptions.RequestException as e:
            logger.error(f"Cannot connect to the detection server: {str(e)}")
            return False, "Detection server is not running or unreachable"

    def check_methods_availability(self, method_names):
        """Check only the servers needed by the requested methods."""
        names = list(method_names or [])
        if any(not self.is_detection_method(n) for n in names):
            available, message = self.check_processing_server_availability()
            if not available:
                return False, message
        if any(self.is_detection_method(n) for n in names):
            available, message = self.check_detection_server_availability()
            if not available:
                return False, message
        return True, "Servers are available"

    @staticmethod
    def _normalize_dr_label(label):
        """Normalize DR labels from different services to the same canonical wording."""
        if label is None:
            return None
        normalized = str(label).strip()
        normalized_lower = normalized.lower()
        if normalized_lower in DR_CLASS_ALIASES:
            return DR_CLASS_ALIASES[normalized_lower]
        for alias, canonical in DR_CLASS_ALIASES.items():
            if alias in normalized_lower:
                return canonical
        return normalized

    @staticmethod
    def _map_class_probabilities(prediction):
        """Map the per-class probabilities to class labels and flag the final (predicted) class."""
        predicted_id = int(prediction["predicted_class"])
        mapped = []
        for key, value in (prediction.get("probabilities") or {}).items():
            class_id = int(key)
            label = DR_CLASS_LABELS.get(class_id, f"Trieda {class_id}")
            if class_id == predicted_id:
                candidate = prediction.get("class_name")
                if candidate:
                    label = PhotoService._normalize_dr_label(candidate)
                else:
                    label = DR_CLASS_LABELS.get(class_id, label)
            mapped.append({
                "class_id": class_id,
                "label": label,
                "probability": float(value),
                "predicted": class_id == predicted_id,
            })
        return sorted(mapped, key=lambda item: item["class_id"])

    def _relative_upload_path(self, abs_path):
        return os.path.relpath(abs_path, self.base_upload_path).replace(os.sep, "/")

    @staticmethod
    def _image_extension(data):
        return "png" if data[:8] == b"\x89PNG\r\n\x1a\n" else "jpg"

    def _process_detection(self, processed_photo, photo):
        """
        Send the photo to fundus-dr-inference and store DR grade, class probabilities
        and the per-concept (MA, HE, SE, EX) heatmaps with the preprocessed image they refer to.
        """
        headers = {}
        if Config.FUNDUS_INFERENCE_AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {Config.FUNDUS_INFERENCE_AUTH_TOKEN}"

        mime_type = mimetypes.guess_type(photo.original_image_path)[0] or "image/jpeg"
        try:
            with open(photo.original_image_path, "rb") as image_file:
                response = requests.post(
                    f"{Config.FUNDUS_INFERENCE_URL}/inference",
                    params={"heatmaps": "true", "n_steps": Config.FUNDUS_INFERENCE_N_STEPS},
                    files={"file": (os.path.basename(photo.original_image_path), image_file, mime_type)},
                    headers=headers,
                    timeout=Config.FUNDUS_INFERENCE_TIMEOUT_S,
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending image to detection server: {str(e)}")
            processed_photo.set_status(ProcessingStatus.ERROR)
            db.session.commit()
            return False, 500, f"Network error sending image to detection server: {str(e)}"

        if response.status_code != 200:
            try:
                error_detail = response.json().get("detail", "")
            except ValueError:
                error_detail = response.text
            processed_photo.set_status(ProcessingStatus.ERROR)
            db.session.commit()
            return False, response.status_code, f"Detection request failed ({response.status_code}): {error_detail}"

        try:
            data = response.json()
            prediction = data["prediction"]
            probabilities = self._map_class_probabilities(prediction)
            final_class = next(p for p in probabilities if p["predicted"])

            processed_dir = os.path.join(self._create_user_directory(photo.patient_id), "processed")
            file_prefix = f"{photo.patient_id}_{photo.id}_{processed_photo.id}_{uuid.uuid4().hex[:8]}"

            def save_b64(b64_data, suffix):
                raw = base64.b64decode(b64_data)
                path = os.path.join(processed_dir, f"{file_prefix}_{suffix}.{self._image_extension(raw)}")
                with open(path, "wb") as f:
                    f.write(raw)
                return path

            preprocessed_path = None
            if data.get("preprocessed_image_b64"):
                preprocessed_path = save_b64(data["preprocessed_image_b64"], "preprocessed")

            concepts = []
            for key, concept in (data.get("concepts") or {}).items():
                heatmap_path = None
                # Heatmaps are only meaningful on top of the preprocessed image (different geometry than the original)
                if preprocessed_path and concept.get("heatmap_b64"):
                    heatmap_path = self._relative_upload_path(save_b64(concept["heatmap_b64"], f"concept_{key}"))
                concepts.append({
                    "key": key,
                    "label": concept.get("label") or key.upper(),
                    "density_score": concept.get("density_score"),
                    "heatmap_path": heatmap_path,
                })

            processed_photo.answer = f"{final_class['label']} ({final_class['probability']:.2f})"
            if preprocessed_path:
                processed_photo.explanation_image_path = preprocessed_path
            processed_photo.explanation = {
                "type": "concepts",
                "method": "Concept heatmaps",
                "framework": "fundus-dr-inference",
                "target_class_id": final_class["class_id"],
                "target_class_label": final_class["label"],
                "probabilities": probabilities,
                "concepts": concepts,
                "preprocessed_image_path": self._relative_upload_path(preprocessed_path) if preprocessed_path else None,
                "cached": bool(data.get("cached")),
                "sha256": data.get("sha256"),
                "explanation_time_ms": round(float(data.get("computation_time_s") or 0) * 1000),
            }
            processed_photo.set_status(ProcessingStatus.COMPLETED)
            db.session.commit()
            return True, 200, "Image evaluated successfully"
        except Exception as e:
            logger.exception(f"Error processing detection response: {str(e)}")
            db.session.rollback()
            processed_photo.set_status(ProcessingStatus.ERROR)
            db.session.commit()
            return False, 500, f"Error processing detection response: {str(e)}"

    def _store_explanation(self, processed_photo, photo, explanation):
        """
        Persist the Grad-CAM overlay returned by the inference server.

        The base64 image is written to the patient's processed folder (the DB only keeps
        the path plus lightweight metadata). Failures never affect the classification result.
        """
        if not explanation or explanation.get("status") != "SUCCESS":
            if explanation:
                logger.warning(f"Explanation not available: {explanation.get('error')}")
            return

        overlay_b64 = explanation.get("heatmap_overlay")
        if not overlay_b64:
            return

        try:
            processed_dir = os.path.join(self._create_user_directory(photo.patient_id), "processed")
            filename = f"{photo.patient_id}_{photo.id}_{processed_photo.id}_xai_{uuid.uuid4().hex[:8]}.jpg"
            abs_path = os.path.join(processed_dir, filename)

            with open(abs_path, "wb") as f:
                f.write(base64.b64decode(overlay_b64))

            processed_photo.explanation_image_path = abs_path
            processed_photo.explanation = {
                "method": explanation.get("method"),
                "framework": explanation.get("framework"),
                "target_class_id": explanation.get("target_class_id"),
                "target_class_label": explanation.get("target_class_label"),
                "explanation_time_ms": explanation.get("explanation_time_ms"),
            }
        except Exception as e:
            logger.error(f"Error saving explanation image: {str(e)}")

    def sent_image_to_processing(self,
                                 photo_id,
                                 method_name,
                                 method_parameters,
                                 user_id, patient_id,
                                 eye_side, diagnosis,
                                 device_name, device_type,
                                 camera_type):
        """Send a photo to processing."""
        try:
            # First, check if the server needed for this method is available
            if self.is_detection_method(method_name):
                server_available, message = self.check_detection_server_availability()
            else:
                server_available, message = self.check_processing_server_availability()
            if not server_available:
                logger.error(f"Processing server not available: {message}")
                return False, 503, f"Processing server is not available: {message}"

            photo = OriginalImageData.query.get(photo_id)
            if not photo:
                return False, 404, "Photo not found"
            file_extension = os.path.splitext(photo.original_image_path)[1].lstrip('.')
            method = methods_service.get_method_by_name(method_name)
            if not method:
                return False, 404, "Method not found"
            method_parameters = method.parameters

            # Create a new ProcessedImageData instance
            processed_photo = ProcessedImageData(
                created_at=datetime.now(),
                status=ProcessingStatus.PENDING.value,
                process_type=method_name,
                original_image_id=photo_id,
            )

            # Add and commit to the database
            db.session.add(processed_photo)
            db.session.commit()

            if self.is_detection_method(method_name):
                logger.info(f"Sending image to detection server: {photo.original_image_path}")
                return self._process_detection(processed_photo, photo)

            logger.info(f"Sending image to inference server: {photo.original_image_path}")

            # Send image as multipart/form-data to /process endpoint.
            try:
                with open(photo.original_image_path, 'rb') as image_file:
                    files = {
                        "image": (
                            os.path.basename(photo.original_image_path),
                            image_file,
                            f"image/{file_extension if file_extension else 'jpeg'}"
                        )
                    }

                    response = requests.post(
                        f"{Config.PROCESSING_SERVICE_URL}/process",
                        params={"explain": "true"},
                        files=files,
                        timeout=60
                    )

                if response.status_code != 200:
                    error_detail = ""
                    try:
                        error_detail = response.json().get("error", "")
                    except ValueError:
                        error_detail = response.text

                    processed_photo.set_status(ProcessingStatus.ERROR)
                    db.session.commit()
                    return False, response.status_code, (
                        f"Inference request failed ({response.status_code}): {error_detail}"
                    )

                response_data = response.json()
                process_result = response_data.get("process_result", {})
                classification = process_result.get("classification", {})

                predicted_label = classification.get("predicted_class_label")
                confidence_score = classification.get("confidence_score")

                if predicted_label is None:
                    predicted_label = classification.get("predicted_class")

                if isinstance(predicted_label, (int, float)):
                    predicted_label = DR_CLASS_LABELS.get(int(predicted_label), str(predicted_label))
                else:
                    predicted_label = self._normalize_dr_label(predicted_label)

                if predicted_label is None:
                    predicted_label = "Unknown"

                if confidence_score is not None:
                    processed_photo.answer = f"{predicted_label} ({float(confidence_score):.2f})"
                else:
                    processed_photo.answer = str(predicted_label)

                self._store_explanation(processed_photo, photo, process_result.get("explanation"))

                processed_photo.set_status(ProcessingStatus.COMPLETED)
                db.session.commit()

                return True, 200, "Image evaluated successfully"

            except requests.exceptions.RequestException as e:
                logger.error(f"Network error sending image to inference server: {str(e)}")
                processed_photo.set_status(ProcessingStatus.ERROR)
                db.session.commit()
                return False, 500, f"Network error sending image to inference server: {str(e)}"
        except Exception as e:
            logger.error(f"Error sending image to processing: {str(e)}")
            return False, 500, f"Error sending image to processing: {str(e)}"

    def process_received_data(self, status, answer, file_id, file_data, file_extension, processed_at=None,
                              created_at=None):

        """Process the received data from the processing service."""
        try:
            # Find the processed image by ID
            processed_image = ProcessedImageData.query.get(file_id)
            if not processed_image:
                return False, "Processed image not found"

            # Get the patient ID from the original image
            patient_id = processed_image.original_image.patient_id
            original_photo_id = processed_image.original_image.id

            # Create directory for the patient if it doesn't exist and get absolute path
            user_dir = self._create_user_directory(patient_id)

            # Get processed images directory
            processed_dir = os.path.join(user_dir, "processed")

            # Generate unique filename with new naming convention
            original_image = processed_image.original_image
            eye_code = "P" if original_image.eye_side.lower() == "right" else "L"
            method_name = processed_image.process_type.replace(" ", "_").lower()

            # Create filename: patient_id_original-id_eye_method_timestamp.extension
            # Use processed_at if provided, otherwise use current time
            if processed_at:
                try:
                    # Try to parse the timestamp from string if provided
                    processing_time = datetime.fromisoformat(processed_at)
                except (ValueError, TypeError):
                    # Use current time if parsing fails
                    processing_time = datetime.now()
            else:
                processing_time = datetime.now()


            timestamp = processing_time.strftime("%Y%m%d_%H%M%S")
            filename = f"{patient_id}_{original_photo_id}_{eye_code}_{method_name}_{timestamp}.{file_extension}"


            abs_file_path = os.path.join(processed_dir, filename)

            # Save the received base64 image data
            try:
                with open(abs_file_path, "wb") as f:
                    f.write(base64.b64decode(file_data))
            except Exception as e:
                logger.error(f"Error saving image file: {str(e)}")
                return False, f"Error saving image file: {str(e)}"

            # Update the processed image with the received data
            processed_image.set_status(ProcessingStatus.COMPLETED)
            processed_image.answer = answer
            processed_image.processed_image_path = abs_file_path  # Store absolute path

            # If created_at is provided, update the created_at timestamp
            if created_at:
                try:
                    # Only update if the existing created_at is None or very recent

                    if not processed_image.created_at or (
                            datetime.now() - processed_image.created_at).total_seconds() < 60:

                        processed_image.created_at = datetime.fromisoformat(created_at)
                except (ValueError, TypeError):
                    # If parsing fails, keep the existing created_at
                    pass

            logger.info(f"Saving processed image with absolute path: {abs_file_path}")

            db.session.commit()

            logger.info(f"Processed image saved: {abs_file_path}")
            return True, "Processed image updated successfully"
        except Exception as e:
            logger.error(f"Error processing received data: {str(e)}")
            return False, f"Error processing received data: {str(e)}"

    def save_base64_file_for_user(self, user_id, base64_data, extension, is_processed=False):
        """
        Save a base64-encoded file in a user-specific folder.
        Returns the full file path.
        """
        import base64
        import uuid
        # Ensure the user directory exists
        user_dir = self._create_user_directory(user_id)


        # Choose the appropriate subfolder
        subfolder = "processed" if is_processed else "original"
        target_dir = os.path.join(user_dir, subfolder)

        # Generate a unique filename
        unique_filename = f"{uuid.uuid4().hex}.{extension}"
        file_path = os.path.join(target_dir, unique_filename)


        # Decode and save the file
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(base64_data))
        return file_path

    def update_photo_diagnosis(self, photo_id, new_diagnosis):
        """Update the diagnosis for a specific photo.

        Args:
            photo_id: ID of the photo to update
            new_diagnosis: New diagnosis text

        Returns:
            tuple: (success (bool), status code (int), message (str))
        """
        try:
            photo = OriginalImageData.query.get(photo_id)

            if not photo:
                return False, 404, "Photo not found"

            photo.diagnosis = new_diagnosis
            db.session.commit()

            logger.info(f"Updated diagnosis for photo {photo_id}")
            return True, 200, "Diagnosis updated successfully"

        except Exception as e:
            logger.error(f"Error updating diagnosis: {str(e)}")
            db.session.rollback()
            return False, 500, f"Error updating diagnosis: {str(e)}"

