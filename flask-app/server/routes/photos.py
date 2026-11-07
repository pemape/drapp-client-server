import logging
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from server.models.methods_data import MethodsData
from server.models.original_image_data import OriginalImageData
from server.models.processed_image_data import ProcessedImageData
from server.models.user import User
from server.models.doctor_data import DoctorData
from server.models.patient_data import PatientData
from server.services.patients_service import PatientsService
from server.services.photo_service import PhotoService
from server.database import db
from server.config import Config
import os

bp = Blueprint('photos', __name__, url_prefix='/photos')
logger = logging.getLogger(__name__)

# Create service instances
patient_service = PatientsService()
photo_service = PhotoService()


def get_process_types():
    process_types = MethodsData.query.all()
    return process_types


# Helper function to get current user ID
def get_current_user_id():
    user_id = get_jwt_identity()
    logger.info(f"JWT Identity: {user_id}")

    try:
        if user_id:
            user_id = int(user_id)
            user = User.query.get(user_id)
            if not user or user.user_type not in ['super_admin', 'admin', 'doctor', 'technician']:
                return {'error': 'Unauthorized'}, 403

            return user_id
        else:
            logger.error(f"Invalid user_id from token")
            return 1

    except (ValueError, TypeError) as e:
        logger.error(f"Invalid user_id from token: {user_id}, error: {str(e)}")
        return 1


# Helper function to get available patients
def get_available_patients(user_id):
    logger.info("Attempting to get patients data via service")
    patients = []

    # First try to get patients through the service (preferred method)
    try:
        logger.info(f"Using PatientsService to get patients for user ID: {user_id}")
        patients_data, status = patient_service.get_patients(user_id)

        logger.info(f"PatientsService returned status: {status}")

        if status == 200 and isinstance(patients_data, list):
            for patient in patients_data:
                logger.info(f"Service found patient: {patient.get('first_name', '')} {patient.get('last_name', '')}")
                patients.append({
                    "id": patient["id"],
                    "name": f"{patient['first_name']} {patient['last_name']}",
                    "eye": "right"  # Default value
                })
        else:
            logger.warning(f"PatientsService returned non-200 status or invalid data format: {status}")
    except Exception as e:
        logger.exception(f"Exception getting patients via PatientsService: {str(e)}")

    # Only use direct DB access as a fallback if service approach failed
    if not patients:
        logger.warning("PatientsService failed, falling back to direct database access")
        try:
            patients_query = PatientData.query.all()
            logger.info(f"Direct query found {len(patients_query) if patients_query else 0} patients")

            if patients_query:
                for patient in patients_query:
                    logger.info(f"Found patient: ID={patient.id}, Name={patient.first_name} {patient.last_name}")
                    patients.append({
                        "id": patient.id,
                        "name": f"{patient.first_name} {patient.last_name}",
                        "eye": "right"  # Default value
                    })
            else:
                logger.warning("No patients found in database")
        except Exception as db_error:
            logger.exception(f"Error in direct DB query: {str(db_error)}")

    logger.info(f"Retrieved {len(patients)} patients")
    return patients


@bp.route('/list', methods=['GET'])
@jwt_required(optional=True)
def photos_list():
    logger.info("==== Accessing photos list page ====")

    # Get the current user
    user_id = get_current_user_id()
    user = db.session.get(User, user_id) if user_id else None
    user_type = user.user_type if user else "guest"

    # Get photos for the current user
    photos, status, message = photo_service.get_user_photos(user_id)

    if status != 200:
        flash(message, 'error')
        photos = []

    # Extract unique values for doctors, patients, and device types
    doctors = set()
    patients = set()
    device_types = set()

    # Process photos to get unique values
    photos_data = []
    for photo in photos:
        # Get patient info
        patient = photo.patient
        patient_name = patient.get_full_name() if patient else "Unknown Patient"

        # Get doctor info
        doctor = patient.doctor if patient else None
        doctor_name = doctor.get_full_name() if doctor else "Unknown Doctor"

        # Get hospital info
        hospital = doctor.hospital if doctor else None
        hospital_name = hospital.name if hospital else "Unknown Hospital"

        # Get device info
        device_type = photo.device.device_type if hasattr(photo, "device") and photo.device else "Unknown Device"

        # Add to sets
        doctors.add(doctor_name)
        patients.add(patient_name)
        device_types.add(device_type)

        # Get relative path from the upload folder
        relative_path = os.path.relpath(photo.original_image_path, Config.UPLOAD_FOLDER)

        # Create photo data dictionary
        photo_data = {
            "id": photo.id,
            "name": os.path.basename(photo.original_image_path),
            "eye": "Pravé" if photo.eye_side == "right" else "Ľavé",
            "patient": patient_name,
            "doctor": doctor_name,
            "date": photo.created_at.strftime("%d.%m.%Y %H:%M:%S"),
            "url": url_for('photos.serve_photo', filepath=photo.original_image_path),
            "device_type": device_type
        }
        photos_data.append(photo_data)

    return render_template(
        'photos.html',
        photos=photos_data,
        doctors=sorted(doctors),
        patients=sorted(patients),
        device_types=sorted(device_types),
        user_type=user_type,
        user_data=user)


@bp.route('/detail/<photo_id>', methods=['GET'])
@jwt_required(optional=True)
def photo_detail(photo_id):
    logger.info(f"==== Accessing photo detail page for {photo_id} ====")

    # Get current user ID
    user_id = get_current_user_id()

    # Get the photo
    photo, status, message = photo_service.get_photo_by_id(photo_id)

    if status != 200:
        flash(message, 'error')
        return redirect(url_for('photos.photos_list'))

    # Get absolute path and verify file exists
    full_path = photo.original_image_path
    logger.info(f"Original image absolute path: {full_path}")

    if not os.path.exists(full_path):
        logger.error(f"Image file not found at path: {full_path}")
        flash("Image file not found", "error")
        return redirect(url_for('photos.photos_list'))

    # Get previous and next photo IDs
    prev_id, next_id = photo_service.get_adjacent_photo_ids(photo_id, user_id)

    # Create photo data dictionary
    photo_data = {
        "id": photo.id,
        "name": os.path.basename(photo.original_image_path),
        "eye": "Pravé" if photo.eye_side == "right" else "Ľavé",
        "patient": photo.patient.get_full_name() if photo.patient else "Unknown Patient",
        "doctor": photo.patient.doctor.get_full_name() if photo.patient and photo.patient.doctor else "Unknown Doctor",
        "date": photo.created_at.strftime("%d.%m.%Y %H:%M:%S"),
        "url": url_for('photos.serve_photo', filepath=os.path.relpath(full_path, Config.UPLOAD_FOLDER)),
        "patient_id": photo.patient.id if photo.patient else "",
        "diagnosis": photo.diagnosis if hasattr(photo, "diagnosis") else "",
        "device_name": photo.device.device_name if hasattr(photo, "device") and photo.device else "",
        "device_type": photo.device.device_type if hasattr(photo, "device") and photo.device else "",
        "camera_type": photo.device.camera_model if hasattr(photo, "device") and photo.device else "",
        "prev_id": prev_id,
        "next_id": next_id
    }

    # Prepare processed images for the table
    processed_images = []
    for img in getattr(photo, 'processed_images', []):
        if img.processed_image_path and os.path.exists(img.processed_image_path):
            processed_url = url_for('photos.serve_photo',
                                    filepath=os.path.relpath(img.processed_image_path, Config.UPLOAD_FOLDER))
            

            # Extract processing timestamp from filename if possible
            processed_at = ""
            try:
                # Get filename and split it
                filename = os.path.basename(img.processed_image_path)
                # Expected format: patient_id_original-id_eye_method_YYYYMMDD_HHMMSS.ext
                name_parts = os.path.splitext(filename)[0].split('_')
                if len(name_parts) >= 6:  # At least patient_id, orig_id, eye, method, date, time
                    # Try to extract date and time (the last two parts before extension)
                    date_part = name_parts[-2]
                    time_part = name_parts[-1]
                    if len(date_part) == 8 and len(time_part) == 6:  # YYYYMMDD and HHMMSS
                        # Format as readable date
                        year, month, day = date_part[:4], date_part[4:6], date_part[6:8]
                        hour, minute, second = time_part[:2], time_part[2:4], time_part[4:6]
                        processed_at = f"{day}.{month}.{year} {hour}:{minute}:{second}"
            except:
                # If any error occurs in parsing, just leave processed_at empty
                pass


        else:
            processed_url = ""
            processed_at = ""

        # Ensure created_at is always present and formatted
        created_at = ""
        if img.created_at:
            created_at = img.created_at.strftime("%d.%m.%Y %H:%M:%S")

                
        else:
            processed_url = ""
            processed_at = ""


        # Ensure created_at is always present and formatted
        created_at = ""
        if img.created_at:
            created_at = img.created_at.strftime("%d.%m.%Y %H:%M:%S")
            
        processed_images.append({
            "id": img.id,
            "method": getattr(img, 'process_type', ''),
            "status": getattr(img, 'status', ''),
            "created_at": created_at,
            "processed_at": processed_at,
            "url": processed_url,
            "name": os.path.basename(img.processed_image_path) if img.processed_image_path else ''
        })

    # Define available medical methods - pass the full method objects
    medical_methods = get_process_types()

    user_id = get_current_user_id()
    user = db.session.get(User, user_id) if user_id else None

    return render_template(
        'photo_detail.html',
        photo=photo_data,
        medical_methods=medical_methods,
        processed_images=processed_images,
        current_user=user
    )


@bp.route('/add_photo', methods=['GET'])
@jwt_required(optional=True)
def add_photo_get():
    logger.info("==== Accessing the add_photo page (GET) ====")

    # Get current user ID
    user_id = get_current_user_id()

    # Get available patients
    patients = get_available_patients(user_id)
    logger.info(f"Available patients: {patients}")

    # Get available methods
    method_names = [method.name for method in get_process_types()]

    logger.info(f"Rendering template with {len(patients)} patients")

    return render_template("add_photo.html", medical_methods=method_names, patients=patients)


@bp.route('/add_photo', methods=['POST'])
@jwt_required(optional=True)
def add_photo_post():
    logger.info("==== Processing add_photo form submission (POST) ====")

    try:
        # Get current user ID
        user_id = get_current_user_id()

        # Get form data
        patient_id = request.form.get('patient')
        eye_side = request.form.get('eye')
        quality = request.form.get('quality')
        device_name = request.form.get('typ_kamery')
        device_type = request.form.get('typ_zariadenia')
        camera_type = request.form.get('typ_kamery')
        photo_file = request.files.get('photo')
        methods_to_process = request.form.getlist('methods')

        # Log the received data
        logger.info(f"Received form data: patient_id={patient_id}, eye={eye_side}, quality={quality}, "
         f"device_name={device_name}, device_type={device_type}")
        logger.info(f"Methods to process: {methods_to_process}")


        

        # Save photo first
        photo_data, status, message = photo_service.save_photo(
            photo_file=photo_file,
            user_id=user_id,
            patient_id=patient_id,
            eye_side=eye_side,
            quality=quality,
            device_name=device_name,
            device_type=device_type,
            camera_type=camera_type
        )
        if status != 200:
            raise Exception(message)
            
        photo_id = int(photo_data.id)

        # If no methods, just save and redirect
        if not methods_to_process:
            flash('Photo uploaded successfully!', 'success')
            return redirect(url_for('photos.photos_list'))

        # If methods, check processing server
        server_available, server_message = photo_service.check_methods_availability(methods_to_process)
        if not server_available:
            flash('Photo uploaded successfully but processing server is unavailable: ' + server_message, 'warning')
            return redirect(url_for('photos.photo_detail', photo_id=photo_id))

        # Server is available, process the methods
        logger.info(f"Processing server is available, processing {len(methods_to_process)} methods")
        results = []
        success_count = 0
        method_objects = [method for method in get_process_types() if method.name in methods_to_process]

        for method in method_objects:
            success, status, message = photo_service.sent_image_to_processing(
                photo_id, method.name, method.parameters, user_id, int(patient_id),
                eye_side, quality, device_name, device_type, camera_type
            )

            results.append({
                "method_name": method.name,
                "success": success,
                "message": message
            })

            if success:
                success_count += 1
            else:
                logger.warning(f"Failed to process method {method.name}: {message}")

        # Show appropriate success/partial success message
        if success_count == len(method_objects):
            flash('Photo uploaded and all methods sent for processing successfully!', 'success')
        elif success_count > 0:

            flash(
                f'Photo uploaded but only {success_count} of {len(method_objects)} methods were processed successfully.',
                'warning')
        else:
            flash('Photo uploaded but no methods could be processed.', 'warning')


        return redirect(url_for('photos.photo_detail', photo_id=photo_id))

    except Exception as e:
        logger.exception(f"Error processing form: {str(e)}")
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('photos.add_photo_get'))


@bp.route('/delete/<photo_id>', methods=['POST'])
@jwt_required(optional=True)
def delete_photo(photo_id):
    logger.info(f"==== Deleting photo {photo_id} ====")

    try:
        # Get current user ID
        user_id = get_current_user_id()

        # Delete photo using PhotoService
        success, status, message = photo_service.delete_photo(photo_id, user_id)

        if not success:
            raise Exception(message)

        flash('Photo deleted successfully!', 'success')
        return redirect(url_for('photos.photos_list'))

    except Exception as e:
        logger.exception(f"Error deleting photo: {str(e)}")
        flash(str(e), 'error')
        return redirect(url_for('photos.photos_list'))


@bp.route('/uploads/<path:filepath>')
def serve_photo(filepath):
    """Serve photos using either absolute or relative filepath."""
    try:
        # Get the base directory (UPLOAD_FOLDER) and normalize paths
        base_dir = os.path.abspath(Config.UPLOAD_FOLDER)

        # Clean up the filepath to prevent directory traversal
        filepath = filepath.lstrip('/')

        # Construct the full path using the base directory
        full_path = os.path.join(base_dir, filepath)
        full_path = os.path.normpath(full_path)

        # Security check - ensure the path is within the base directory
        if not full_path.startswith(base_dir):
            logger.error(f"Invalid path - outside base directory: {filepath}")
            return "Invalid path", 400

        # Get directory and filename
        directory = os.path.dirname(full_path)
        filename = os.path.basename(full_path)

        logger.info(f"Serving photo from directory: {directory}, filename: {filename}")
        logger.info(f"Full path: {full_path}")

        if not os.path.exists(full_path):
            logger.error(f"File not found at path: {full_path}")
            return "Image not found", 404

        return send_from_directory(directory, filename)

    except Exception as e:
        logger.error(f"Error serving photo: {str(e)}")
        return "Error serving image", 500


@bp.route('/sent_to_processing', methods=['POST'])
@jwt_required(optional=True)
def sent_to_processing():
    data = request.json
    logger.info(f"Received data: {data}")

    # Extract data
    photo_id = data.get('photo_id')
    method_names = data.get('method_names', [])  # Changed to array of method names
    method_parameters_list = data.get('method_parameters_list', [])  # Array of parameter objects
    user_id = data.get('user_id')
    patient_id = data.get('patient_id')
    eye_side = data.get('eye_side')
    diagnosis = data.get('diagnosis')
    device_name = data.get('device_name')
    device_type = data.get('device_type')
    camera_type = data.get('camera_type')

    # Validate that we have method names
    if not method_names:
        return jsonify({"status": "error", "message": "No methods specified for processing"}), 400

    # Check if the servers needed by the requested methods are available first
    server_available, message = photo_service.check_methods_availability(method_names)
    if not server_available:
        logger.error(f"Processing server not available: {message}")
        return jsonify({
            "status": "error",
            "message": f"Processing server is not available: {message}"
        }), 503

    results = []
    overall_success = True

    # Process each method
    for i, method_name in enumerate(method_names):
        # Get parameters for this method (if available)
        method_parameters = {}
        if i < len(method_parameters_list):
            method_parameters = method_parameters_list[i]

        # Call the service for each method
        success, status, message = photo_service.sent_image_to_processing(
            photo_id, method_name, method_parameters, user_id, patient_id,
            eye_side, diagnosis, device_name, device_type, camera_type
        )

        results.append({
            "method_name": method_name,
            "success": success,
            "message": message
        })

        # If any method fails, set overall_success to False
        if not success:
            overall_success = False

    if overall_success:
        return jsonify({
            "status": "success",
            "message": "All methods sent to processing successfully",
            "results": results
        }), 200
    else:
        return jsonify({
            "status": "partial_error",
            "message": "Some methods could not be processed",
            "results": results
        }), 207  # 207 Multi-Status


@bp.route('/processed/recieve', methods=['POST'])
def recieve():
    logger.info("==== Processing receive form submission (POST) ====")
    data = request.json
    logger.info(
        f"Received data: status: {data.get('status')}, answer: {data.get('answer')}, file_id: {data.get('file', {}).get('id')}, file_extension: {data.get('file', {}).get('extension')}")

    try:
        # Extract data from the request
        status = data.get('status')
        answer = data.get('answer')
        processed_at = data.get('processed_at')  # Get the processed_at timestamp if available
        created_at = data.get('created_at')  # Get the created_at timestamp if available
        file_data = data.get('file', {})

        if not all([status, file_data]):
            return jsonify({"status": "error", "message": "Missing required data"}), 400

        # Process the received data
        success, message = photo_service.process_received_data(
            status=status,
            answer=answer,
            file_id=file_data.get('id'),
            file_data=file_data.get('data'),
            file_extension=file_data.get('extension'),
            processed_at=processed_at,  # Pass the processed_at timestamp
            created_at=created_at  # Pass the created_at timestamp
        )

        if success:
            return jsonify({"status": "success", "message": message}), 200
        else:
            return jsonify({"status": "error", "message": message}), 500

    except Exception as e:
        logger.exception("Error processing received data: %s", str(e))
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@bp.route('/processed/<int:processed_image_id>', methods=['GET'])
@jwt_required(optional=True)
def processed_image_detail(processed_image_id):
    logger.info("==== Accessing processed image detail %s ====", processed_image_id)

    processed = ProcessedImageData.query.get(processed_image_id)
    if not processed:
        flash("Processed image not found", "error")
        return redirect(url_for("photos.photos_list"))

    # ---------- pôvodný obrázok -------------------------------------------
    original_url = ""
    original_name = ""
    if processed.original_image and processed.original_image.original_image_path:
        original_path = processed.original_image.original_image_path
        try:
            original_name = os.path.basename(original_path)
            # Convert absolute path to relative path from UPLOAD_FOLDER
            rel_path = os.path.relpath(original_path, Config.UPLOAD_FOLDER)
            original_url = url_for('photos.serve_photo', filepath=rel_path)
            logger.info(f"Original image path: {original_path}")
            logger.info(f"Relative path: {rel_path}")
            logger.info(f"Original URL: {original_url}")
        except Exception as e:
            logger.error(f"Error creating URL for original image: {e}")
            flash("Error loading original image", "error")

    # ---------- spracovaný obrázok -----------------------------------------
    processed_url = ""
    processed_name = ""
    processed_at = ""
    if processed.processed_image_path:
        processed_path = processed.processed_image_path
        try:
            processed_name = os.path.basename(processed_path)
            # Convert absolute path to relative path from UPLOAD_FOLDER
            rel_path = os.path.relpath(processed_path, Config.UPLOAD_FOLDER)
            processed_url = url_for('photos.serve_photo', filepath=rel_path)
            logger.info(f"Processed image path: {processed_path}")
            logger.info(f"Relative path: {rel_path}")
            logger.info(f"Processed URL: {processed_url}")

            # Extract processing timestamp from filename if possible
            try:
                # Get filename and split it
                filename = os.path.basename(processed_path)
                # Expected format: patient_id_original-id_eye_method_YYYYMMDD_HHMMSS.ext
                name_parts = os.path.splitext(filename)[0].split('_')
                if len(name_parts) >= 6:  # At least patient_id, orig_id, eye, method, date, time
                    # Try to extract date and time (the last two parts before extension)
                    date_part = name_parts[-2]
                    time_part = name_parts[-1]
                    if len(date_part) == 8 and len(time_part) == 6:  # YYYYMMDD and HHMMSS
                        # Format as readable date
                        year, month, day = date_part[:4], date_part[4:6], date_part[6:8]
                        hour, minute, second = time_part[:2], time_part[2:4], time_part[4:6]
                        processed_at = f"{day}.{month}.{year} {hour}:{minute}:{second}"
            except:
                # If any error occurs in parsing, just leave processed_at empty
                pass

        except Exception as e:
            logger.error(f"Error creating URL for processed image: {e}")
            flash("Error loading processed image", "error")

    # ---------- XAI (Grad-CAM) obrázok -------------------------------------
    explanation_path = ""
    if processed.explanation_image_path and os.path.exists(processed.explanation_image_path):
        explanation_path = os.path.relpath(processed.explanation_image_path, Config.UPLOAD_FOLDER)

    # ---------- JSON pre šablónu -------------------------------------------
    # Get patient name
    patient_name = "-"
    if processed.original_image and hasattr(processed.original_image, 'patient') and processed.original_image.patient:
        patient_name = processed.original_image.patient.get_full_name()
    elif processed.original_image and hasattr(processed.original_image, 'patient_id'):
        patient_name = str(processed.original_image.patient_id)

    data = {
        "id": processed.id,
        "method": processed.process_type,
        "status": processed.status,
        "created_at": processed.created_at.strftime("%d.%m.%Y %H:%M:%S") if processed.created_at else "",
        "processed_at": processed_at,
        "answer": processed.answer,
        "url": processed_url,
        "patient_name": patient_name,
        "original_photo_id": processed.original_image_id,
        "original_image": {
            "url": original_url,
            "name": original_name,
        },
        "processed_image_path": rel_path if processed.processed_image_path else "",
        "explanation_image_path": explanation_path,
        "explanation": processed.explanation or {},
        "original_image_path": os.path.relpath(original_path, Config.UPLOAD_FOLDER) if original_path else ""
    }

    logger.info(f"Template data: {data}")
    return render_template("processed_image_details.html", processed_image=data)


@bp.route('/processed_images', methods=['GET'])
@jwt_required(optional=True)
def processed_images_list():
    user_id = get_current_user_id()
    # Get photos for the current user
    photos, status, message = photo_service.get_user_photos(user_id)

    processed_images = [
        proc
        for orig in photos
        for proc in (orig.processed_images or [])
    ]

    table_data = []
    for img in processed_images:
        original = img.original_image
        # Get patient name
        if original and hasattr(original, 'patient') and original.patient:
            patient_name = original.patient.get_full_name()
        else:
            patient_name = str(original.patient_id) if original and hasattr(original, 'patient_id') else "-"
        # Get doctor name (creator)
        if original and hasattr(original, 'creator') and original.creator:
            doctor_name = original.creator.get_full_name()
        else:
            doctor_name = str(original.creator_id) if original and hasattr(original, 'creator_id') else "-"

        # Extract processing timestamp from filename if possible
        processed_at = ""
        if img.processed_image_path:
            try:
                # Get filename and split it
                filename = os.path.basename(img.processed_image_path)
                # Expected format: patient_id_original-id_eye_method_YYYYMMDD_HHMMSS.ext
                name_parts = os.path.splitext(filename)[0].split('_')
                if len(name_parts) >= 6:  # At least patient_id, orig_id, eye, method, date, time
                    # Try to extract date and time (the last two parts before extension)
                    date_part = name_parts[-2]
                    time_part = name_parts[-1]
                    if len(date_part) == 8 and len(time_part) == 6:  # YYYYMMDD and HHMMSS
                        # Format as readable date
                        year, month, day = date_part[:4], date_part[4:6], date_part[6:8]
                        hour, minute, second = time_part[:2], time_part[2:4], time_part[4:6]
                        processed_at = f"{day}.{month}.{year} {hour}:{minute}:{second}"
            except:
                # If any error occurs in parsing, just leave processed_at empty
                pass

        table_data.append({
            "id": img.id,
            "name": os.path.basename(img.processed_image_path) if img.processed_image_path else "",
            "method": img.process_type,
            "status": img.status,
            "created_at": img.created_at.strftime("%d.%m.%Y %H:%M:%S") if img.created_at else "",
            "processed_at": processed_at,
            "patient_name": patient_name,
            "doctor_name": doctor_name,
            "answer": img.answer if hasattr(img, "answer") else "-",
            "url": url_for('photos.serve_photo', filepath=img.processed_image_path) if img.processed_image_path else "",
        })
    return render_template('processed_images.html', processed_images=table_data)


@bp.route('/update_diagnosis', methods=['POST'])
@jwt_required(optional=True)
def update_diagnosis():
    """Update the diagnosis for a photo."""
    try:
        data = request.json
        photo_id = data.get('photo_id')
        new_diagnosis = data.get('diagnosis')

        if not photo_id:
            return jsonify({"status": "error", "message": "Photo ID is required"}), 400

        # Get the photo using PhotoService
        photo, status, message = photo_service.get_photo_by_id(photo_id)

        if status != 200:
            return jsonify({"status": "error", "message": message}), status

        # Update the diagnosis using PhotoService
        success, status, message = photo_service.update_photo_diagnosis(photo_id, new_diagnosis)

        if not success:
            return jsonify({"status": "error", "message": message}), status

        return jsonify({"status": "success", "message": "Diagnosis updated successfully"}), 200

    except Exception as e:
        logger.exception("Error updating diagnosis: %s", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route('/get_processed_images/<photo_id>', methods=['GET'])
@jwt_required(optional=True)
def get_processed_images(photo_id):
    """Get processed images for a specific photo."""
    image_dir = os.path.join(os.path.dirname(__file__), 'images')
    try:
        photo = OriginalImageData.query.get(photo_id)
        if not photo:
            return jsonify({"error": "Photo not found"}), 404

        processed_images = []
        for img in photo.processed_images:
            # Format created_at timestamp
            created_at = img.created_at.strftime("%d.%m.%Y %H:%M:%S") if img.created_at else '-'

            # Extract processed_at from filename if it exists
            processed_at = "-"
            if img.processed_image_path:
                try:
                    # Try to extract timestamp from the filename
                    filename = os.path.basename(img.processed_image_path)
                    name_parts = os.path.splitext(filename)[0].split('_')
                    if len(name_parts) >= 6:  # At least patient_id, orig_id, eye, method, date, time
                        date_part = name_parts[-2]
                        time_part = name_parts[-1]
                        if len(date_part) == 8 and len(time_part) == 6:  # YYYYMMDD and HHMMSS
                            year, month, day = date_part[:4], date_part[4:6], date_part[6:8]
                            hour, minute, second = time_part[:2], time_part[2:4], time_part[4:6]
                            processed_at = f"{day}.{month}.{year} {hour}:{minute}:{second}"
                except:
                    # If any error in parsing, leave processed_at as default
                    pass


            processed_url = ""
            if img.processed_image_path and os.path.exists(img.processed_image_path):
                processed_url = url_for('photos.serve_photo',
                                        filepath=os.path.relpath(img.processed_image_path, Config.UPLOAD_FOLDER))


            processed_images.append({
                "id": img.id,
                "method": img.process_type,
                "status": img.status,
                "created_at": created_at,
                "processed_at": processed_at,
                "url": processed_url
            })

        return jsonify(processed_images), 200

    except Exception as e:
        logger.exception("Error getting processed images: %s", str(e))
        return jsonify({"error": str(e)}), 500


@bp.route('/check_server_health', methods=['GET'])
@jwt_required(optional=True)
def check_server_health():
    """Check if the processing server is available and return status"""
    logger.info("==== Checking processing server health ====")


    try:
        server_available, message = photo_service.check_processing_server_availability()


        # Always return 200 HTTP status to avoid client-side errors
        # The "available" field in the response indicates whether the processing server is up
        return jsonify({
            "available": server_available,
            "message": message
        }), 200
    except Exception as e:
        logger.exception("Error checking server health: %s", str(e))
        return jsonify({
            "available": False,
            "message": f"Error checking server health: {str(e)}"
        }), 200  # Return 200 even for errors to avoid client-side issues
