import logging
import os
import uuid
from flask import Blueprint, jsonify, send_from_directory, request
from datetime import datetime
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
# Assuming api.exceptions.FileTooLargeError is defined elsewhere
from api.exception import FileTooLargeError 
# Assuming models.Upload_Files and models.db are defined elsewhere
from models import Upload_Files, db

upload_bp = Blueprint("upload_files", __name__)

UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'pdf', 'jpeg', 'jpg', 'png', 'docx', 'txt'}

# Fallback value is 5 * 1024 * 1024 bytes (5MB)
MAX_FILE_SIZE = int(os.getenv("MAX_CONTENT_LENGTH", 5 * 1024 * 1024)) 


# --- Utility Functions (Copied/Adapted from Original Snippet) ---

# Function to check if a file has an allowed extension
def allowed_file(filename):
    """Checks if a file's extension is in the ALLOWED_EXTENSIONS set."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_file_size(file):
    """Checks if the file size exceeds MAX_FILE_SIZE and raises an error if it does."""
    # Seek to the end of the file to get its size
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    logging.info(f"The length of {file.filename} is {file_length} bytes")
    # Reset the file pointer to the beginning for later operations like file.save()
    file.seek(0)
    
    if file_length > MAX_FILE_SIZE:
        raise FileTooLargeError(file.filename, MAX_FILE_SIZE)

def delete_selected_files(file_ids):
    """Deletes files from disk and their records from the database based on a list of file_ids."""
    for file_id in file_ids:
        # Use .one_or_none() if using Flask-SQLAlchemy 3 or newer, or .first() as per original code
        file_record = db.session.query(Upload_Files).filter_by(file_id=file_id).first()
        if file_record:
            try:
                # Delete from disk
                if os.path.exists(file_record.file_path):
                    os.remove(file_record.file_path)
                    logging.info(f"Deleted file from disk: {file_record.file_path}")
                
                # Delete DB record
                db.session.delete(file_record)
                logging.info(f"Deleted DB record for file_id: {file_id}")

            except Exception as e:
                logging.exception(f"Failed to delete file {file_record.filename}: {str(e)}")
                # Re-raise to be caught by the calling update function's rollback logic
                raise e


# --- Folder Creation Functions (Provided in the User Prompt) ---

def create_pin_folder(pin_id):
    """
    Creates a dedicated upload folder for a specific Pin using its ID.
    """
    folder_path = os.path.join(
        UPLOAD_FOLDER, 
        "pin_uploads", 
        str(pin_id)
    )
    
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
        logging.info(f"Directory verified/created for Pin: {folder_path}")
    except Exception as e:
        logging.error(f"Failed to create directory {folder_path}: {e}")
        raise
        
    return folder_path

def create_space_folder(space_id):
    """
    Creates a dedicated upload folder for a specific Space using its ID.
    """
    folder_path = os.path.join(
        UPLOAD_FOLDER, 
        "space_uploads",
        str(space_id)
    )
    
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
        logging.info(f"Directory verified/created for Space: {folder_path}")
    except Exception as e:
        logging.error(f"Failed to create directory {folder_path}: {e}")
        raise
        
    return folder_path

def create_project_templates_folder(project_templates_id):
    """
    Creates a dedicated upload folder for Project Templates using the ID.
    Note: The path uses 'pin_uploads' which seems inconsistent with the ID name.
    Retaining original path logic from prompt.
    """
    folder_path = os.path.join(
        UPLOAD_FOLDER, 
        "pin_uploads",
        str(project_templates_id)
    )
    
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
        logging.info(f"Directory verified/created for Project Template: {folder_path}")
    except Exception as e:
        logging.error(f"Failed to create directory {folder_path}: {e}")
        raise
        
    return folder_path

def create_template_folder(template_id):
    """
    Creates a dedicated upload folder for a specific Template using its ID.
    Note: The path uses 'pin_uploads' which seems inconsistent with the ID name.
    Retaining original path logic from prompt.
    """
    folder_path = os.path.join(
        UPLOAD_FOLDER, 
        "pin_uploads",
        str(template_id)
    )
    
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
        logging.info(f"Directory verified/created for Template: {folder_path}")
    except Exception as e:
        logging.error(f"Failed to create directory {folder_path}: {e}")
        raise
        
    return folder_path

def create_document_folder(document_id):
    """
    Creates a dedicated upload folder for a specific Document using its ID.
    """
    folder_path = os.path.join(
        UPLOAD_FOLDER, 
        "document_uploads",
        str(document_id)
    )
    
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
        logging.info(f"Directory verified/created for Document: {folder_path}")
    except Exception as e:
        logging.error(f"Failed to create directory {folder_path}: {e}")
        raise
        
    return folder_path

def create_asset_folder(asset_id):
    """
    Creates a dedicated upload folder for a specific Asset using its ID.
    """
    folder_path = os.path.join(
        UPLOAD_FOLDER, 
        "asset_uploads",
        str(asset_id)
    )
    
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
        logging.info(f"Directory verified/created for Asset: {folder_path}")
    except Exception as e:
        logging.error(f"Failed to create directory {folder_path}: {e}")
        raise
        
    return folder_path

def create_drawing_folder(drawing_id):
    """
    Creates a dedicated upload folder for a specific Drawing using its ID.
    """
    folder_path = os.path.join(
        UPLOAD_FOLDER, 
        "drawing_uploads",
        str(drawing_id)
    )
    
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
        logging.info(f"Directory verified/created for Drawing: {folder_path}")
    except Exception as e:
        logging.error(f"Failed to create directory {folder_path}: {e}")
        raise
        
    return folder_path

def create_inspiration_folder(inspiration_id):
    """
    Creates a dedicated upload folder for a specific Inspiration using its ID.
    """
    folder_path = os.path.join(
        UPLOAD_FOLDER, 
        "inspiration_uploads",
        str(inspiration_id)
    )
    
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
        logging.info(f"Directory verified/created for Inspiration: {folder_path}")
    except Exception as e:
        logging.error(f"Failed to create directory {folder_path}: {e}")
        raise
        
    return folder_path

def create_task_folder(inspiration_id):
    """
    Creates a dedicated upload folder for a specific Inspiration using its ID.
    """
    folder_path = os.path.join(
        UPLOAD_FOLDER, 
        "task_uploads",
        str(inspiration_id)
    )
    
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
        logging.info(f"Directory verified/created for Inspiration: {folder_path}")
    except Exception as e:
        logging.error(f"Failed to create directory {folder_path}: {e}")
        raise
        
    return folder_path
# --- File Upload/Update Functions (New Logic) ---

def upload_pin_files(files, pin_id):
    """Handles the initial upload of multiple files for a Pin."""
    folder_path = create_pin_folder(pin_id)
    
    for file in files:
        if isinstance(file, FileStorage):
            original_filename = secure_filename(file.filename)
            try:
                validate_file_size(file)
            except ValueError as ve:
                logging.warning(f"Oversized file upload attempt for Pin: {str(ve)}")
                raise
            
            base, ext = os.path.splitext(original_filename)
            unique_filename = f"{base}{ext}"
            file_path = os.path.join(folder_path, unique_filename)

            try:
                file.save(file_path)
                file_id = str(uuid.uuid4())
                file_size_kb = os.path.getsize(file_path) / 1024

                upload_file = Upload_Files(
                    file_id=file_id,
                    pin_id=pin_id, # Use the correct foreign key
                    filename=unique_filename,
                    file_path=file_path,
                    file_size=file_size_kb,
                    # record_time_according_to_timezone=localized_time
                    )
                
                db.session.add(upload_file)
                                
            except Exception as e:
                logging.exception(f"Error uploading file for Pin {pin_id}: {str(e)}")
                # If you're handling multiple files, you might want to rollback after
                # the loop or commit after the loop, depending on atomicity requirements.
                # For consistency with the original `upload_blinding_files`: we raise immediately.
                raise e


def update_pin_files(files, pin_id, localized_time, files_to_delete):
    """Handles deletion of old files and upload of new files for a Pin."""
    try:
        folder_path = create_pin_folder(pin_id) 
        
        # 1. Delete files marked for deletion
        if files_to_delete:
            delete_selected_files(files_to_delete)
        
        # 2. Upload new files
        for file in files:
            if isinstance(file, FileStorage):
                try:
                    original_filename = secure_filename(file.filename)
                    validate_file_size(file)
                    base, ext = os.path.splitext(original_filename)
                    unique_filename = f"{base}{ext}"
                    file_path = os.path.join(folder_path, unique_filename)

                    file.save(file_path)

                    file_id = str(uuid.uuid4())
                    file_size_kb = os.path.getsize(file_path) / 1024

                    upload_file = Upload_Files(
                        file_id=file_id,
                        pin_id=pin_id,
                        filename=unique_filename,
                        file_path=file_path,
                        file_size=file_size_kb,
                        record_time_according_to_timezone=localized_time
                    )
                    db.session.add(upload_file)

                except Exception as e:
                    logging.exception(f"Error updating Pin file {original_filename}: {str(e)}")
                    db.session.rollback() 
                    raise e
        
        db.session.commit() # Commit all changes for this update operation

    except Exception as e:
        logging.exception(f"Failed to update Pin files for ID {pin_id}: {str(e)}")
        db.session.rollback()
        raise e

# The logic for space, project_templates, template, document, asset, drawing, and inspiration upload/update
# will follow the exact same pattern as the Pin functions, substituting the ID and folder creation function.

def upload_space_files(files, space_id):
    """Handles the initial upload of multiple files for a Space."""
    folder_path = create_space_folder(space_id)
    
    for file in files:
        if isinstance(file, FileStorage):
            original_filename = secure_filename(file.filename)
            try:
                validate_file_size(file)
            except ValueError as ve:
                logging.warning(f"Oversized file upload attempt for Space: {str(ve)}")
                raise
            
            base, ext = os.path.splitext(original_filename)
            unique_filename = f"{base}{ext}"
            file_path = os.path.join(folder_path, unique_filename)

            try:
                file.save(file_path)
                file_id = str(uuid.uuid4())
                file_size_kb = os.path.getsize(file_path) / 1024

                upload_file = Upload_Files(
                    file_id=file_id,
                    space_id=space_id, # Use the correct foreign key
                    filename=unique_filename,
                    file_path=file_path,
                    file_size=file_size_kb,
                    # record_time_according_to_timezone=localized_time
                    )
                
                db.session.add(upload_file)
                                
            except Exception as e:
                logging.exception(f"Error uploading file for Space {space_id}: {str(e)}")
                raise e

def update_space_files(files, space_id, localized_time, files_to_delete):
    """Handles deletion of old files and upload of new files for a Space."""
    try:
        folder_path = create_space_folder(space_id) 
        
        if files_to_delete:
            delete_selected_files(files_to_delete)
        
        for file in files:
            if isinstance(file, FileStorage):
                try:
                    original_filename = secure_filename(file.filename)
                    validate_file_size(file)
                    base, ext = os.path.splitext(original_filename)
                    unique_filename = f"{base}{ext}"
                    file_path = os.path.join(folder_path, unique_filename)

                    file.save(file_path)

                    file_id = str(uuid.uuid4())
                    file_size_kb = os.path.getsize(file_path) / 1024

                    upload_file = Upload_Files(
                        file_id=file_id,
                        space_id=space_id,
                        filename=unique_filename,
                        file_path=file_path,
                        file_size=file_size_kb,
                        record_time_according_to_timezone=localized_time
                    )
                    db.session.add(upload_file)

                except Exception as e:
                    logging.exception(f"Error updating Space file {original_filename}: {str(e)}")
                    db.session.rollback() 
                    raise e
        
        db.session.commit()

    except Exception as e:
        logging.exception(f"Failed to update Space files for ID {space_id}: {str(e)}")
        db.session.rollback()
        raise e

# ... Repeat upload/update functions for the other new models (Project Templates, Template, Document, Asset, Drawing, Inspiration)

def upload_project_templates_files(files, project_templates_id, localized_time):
    """Handles the initial upload of multiple files for Project Templates."""
    folder_path = create_project_templates_folder(project_templates_id)
    
    for file in files:
        if isinstance(file, FileStorage):
            original_filename = secure_filename(file.filename)
            try:
                validate_file_size(file)
            except ValueError as ve:
                logging.warning(f"Oversized file upload attempt for Project Template: {str(ve)}")
                raise
            
            base, ext = os.path.splitext(original_filename)
            unique_filename = f"{base}{ext}"
            file_path = os.path.join(folder_path, unique_filename)

            try:
                file.save(file_path)
                file_id = str(uuid.uuid4())
                file_size_kb = os.path.getsize(file_path) / 1024

                upload_file = Upload_Files(
                    file_id=file_id,
                    project_templates_id=project_templates_id, # Use the correct foreign key
                    filename=unique_filename,
                    file_path=file_path,
                    file_size=file_size_kb,
                    record_time_according_to_timezone=localized_time)
                
                db.session.add(upload_file)
                                
            except Exception as e:
                logging.exception(f"Error uploading file for Project Template {project_templates_id}: {str(e)}")
                raise e


def update_project_templates_files(files, project_templates_id, localized_time, files_to_delete):
    """Handles deletion of old files and upload of new files for Project Templates."""
    try:
        folder_path = create_project_templates_folder(project_templates_id) 
        
        if files_to_delete:
            delete_selected_files(files_to_delete)
        
        for file in files:
            if isinstance(file, FileStorage):
                try:
                    original_filename = secure_filename(file.filename)
                    validate_file_size(file)
                    base, ext = os.path.splitext(original_filename)
                    unique_filename = f"{base}{ext}"
                    file_path = os.path.join(folder_path, unique_filename)

                    file.save(file_path)

                    file_id = str(uuid.uuid4())
                    file_size_kb = os.path.getsize(file_path) / 1024

                    upload_file = Upload_Files(
                        file_id=file_id,
                        project_templates_id=project_templates_id,
                        filename=unique_filename,
                        file_path=file_path,
                        file_size=file_size_kb,
                        record_time_according_to_timezone=localized_time
                    )
                    db.session.add(upload_file)

                except Exception as e:
                    logging.exception(f"Error updating Project Template file {original_filename}: {str(e)}")
                    db.session.rollback() 
                    raise e
        
        db.session.commit()

    except Exception as e:
        logging.exception(f"Failed to update Project Template files for ID {project_templates_id}: {str(e)}")
        db.session.rollback()
        raise e


def upload_template_files(files, template_id, localized_time):
    """Handles the initial upload of multiple files for a Template."""
    folder_path = create_template_folder(template_id)
    
    for file in files:
        if isinstance(file, FileStorage):
            original_filename = secure_filename(file.filename)
            try:
                validate_file_size(file)
            except ValueError as ve:
                logging.warning(f"Oversized file upload attempt for Template: {str(ve)}")
                raise
            
            base, ext = os.path.splitext(original_filename)
            unique_filename = f"{base}{ext}"
            file_path = os.path.join(folder_path, unique_filename)

            try:
                file.save(file_path)
                file_id = str(uuid.uuid4())
                file_size_kb = os.path.getsize(file_path) / 1024

                upload_file = Upload_Files(
                    file_id=file_id,
                    template_id=template_id, # Use the correct foreign key
                    filename=unique_filename,
                    file_path=file_path,
                    file_size=file_size_kb,
                    record_time_according_to_timezone=localized_time)
                
                db.session.add(upload_file)
                                
            except Exception as e:
                logging.exception(f"Error uploading file for Template {template_id}: {str(e)}")
                raise e


def update_template_files(files, template_id, localized_time, files_to_delete):
    """Handles deletion of old files and upload of new files for a Template."""
    try:
        folder_path = create_template_folder(template_id) 
        
        if files_to_delete:
            delete_selected_files(files_to_delete)
        
        for file in files:
            if isinstance(file, FileStorage):
                try:
                    original_filename = secure_filename(file.filename)
                    validate_file_size(file)
                    base, ext = os.path.splitext(original_filename)
                    unique_filename = f"{base}{ext}"
                    file_path = os.path.join(folder_path, unique_filename)

                    file.save(file_path)

                    file_id = str(uuid.uuid4())
                    file_size_kb = os.path.getsize(file_path) / 1024

                    upload_file = Upload_Files(
                        file_id=file_id,
                        template_id=template_id,
                        filename=unique_filename,
                        file_path=file_path,
                        file_size=file_size_kb,
                        record_time_according_to_timezone=localized_time
                    )
                    db.session.add(upload_file)

                except Exception as e:
                    logging.exception(f"Error updating Template file {original_filename}: {str(e)}")
                    db.session.rollback() 
                    raise e
        
        db.session.commit()

    except Exception as e:
        logging.exception(f"Failed to update Template files for ID {template_id}: {str(e)}")
        db.session.rollback()
        raise e


def upload_document_files(files, document_id, localized_time):
    """Handles the initial upload of multiple files for a Document."""
    folder_path = create_document_folder(document_id)
    
    for file in files:
        if isinstance(file, FileStorage):
            original_filename = secure_filename(file.filename)
            try:
                validate_file_size(file)
            except ValueError as ve:
                logging.warning(f"Oversized file upload attempt for Document: {str(ve)}")
                raise
            
            base, ext = os.path.splitext(original_filename)
            unique_filename = f"{base}{ext}"
            file_path = os.path.join(folder_path, unique_filename)

            try:
                file.save(file_path)
                file_id = str(uuid.uuid4())
                file_size_kb = os.path.getsize(file_path) / 1024

                upload_file = Upload_Files(
                    file_id=file_id,
                    document_id=document_id, # Use the correct foreign key
                    filename=unique_filename,
                    file_path=file_path,
                    file_size=file_size_kb,
                    record_time_according_to_timezone=localized_time)
                
                db.session.add(upload_file)
                                
            except Exception as e:
                logging.exception(f"Error uploading file for Document {document_id}: {str(e)}")
                raise e


def update_document_files(files, document_id, localized_time, files_to_delete):
    """Handles deletion of old files and upload of new files for a Document."""
    try:
        folder_path = create_document_folder(document_id) 
        
        if files_to_delete:
            delete_selected_files(files_to_delete)
        
        for file in files:
            if isinstance(file, FileStorage):
                try:
                    original_filename = secure_filename(file.filename)
                    validate_file_size(file)
                    base, ext = os.path.splitext(original_filename)
                    unique_filename = f"{base}{ext}"
                    file_path = os.path.join(folder_path, unique_filename)

                    file.save(file_path)

                    file_id = str(uuid.uuid4())
                    file_size_kb = os.path.getsize(file_path) / 1024

                    upload_file = Upload_Files(
                        file_id=file_id,
                        document_id=document_id,
                        filename=unique_filename,
                        file_path=file_path,
                        file_size=file_size_kb,
                        record_time_according_to_timezone=localized_time
                    )
                    db.session.add(upload_file)

                except Exception as e:
                    logging.exception(f"Error updating Document file {original_filename}: {str(e)}")
                    db.session.rollback() 
                    raise e
        
        db.session.commit()

    except Exception as e:
        logging.exception(f"Failed to update Document files for ID {document_id}: {str(e)}")
        db.session.rollback()
        raise e


def upload_asset_files(files, asset_id, localized_time):
    """Handles the initial upload of multiple files for an Asset."""
    folder_path = create_asset_folder(asset_id)
    
    for file in files:
        if isinstance(file, FileStorage):
            original_filename = secure_filename(file.filename)
            try:
                validate_file_size(file)
            except ValueError as ve:
                logging.warning(f"Oversized file upload attempt for Asset: {str(ve)}")
                raise
            
            base, ext = os.path.splitext(original_filename)
            unique_filename = f"{base}{ext}"
            file_path = os.path.join(folder_path, unique_filename)

            try:
                file.save(file_path)
                file_id = str(uuid.uuid4())
                file_size_kb = os.path.getsize(file_path) / 1024

                upload_file = Upload_Files(
                    file_id=file_id,
                    asset_id=asset_id, # Use the correct foreign key
                    filename=unique_filename,
                    file_path=file_path,
                    file_size=file_size_kb,
                    record_time_according_to_timezone=localized_time)
                
                db.session.add(upload_file)
                                
            except Exception as e:
                logging.exception(f"Error uploading file for Asset {asset_id}: {str(e)}")
                raise e


def update_asset_files(files, asset_id, localized_time, files_to_delete):
    """Handles deletion of old files and upload of new files for an Asset."""
    try:
        folder_path = create_asset_folder(asset_id) 
        
        if files_to_delete:
            delete_selected_files(files_to_delete)
        
        for file in files:
            if isinstance(file, FileStorage):
                try:
                    original_filename = secure_filename(file.filename)
                    validate_file_size(file)
                    base, ext = os.path.splitext(original_filename)
                    unique_filename = f"{base}{ext}"
                    file_path = os.path.join(folder_path, unique_filename)

                    file.save(file_path)

                    file_id = str(uuid.uuid4())
                    file_size_kb = os.path.getsize(file_path) / 1024

                    upload_file = Upload_Files(
                        file_id=file_id,
                        asset_id=asset_id,
                        filename=unique_filename,
                        file_path=file_path,
                        file_size=file_size_kb,
                        record_time_according_to_timezone=localized_time
                    )
                    db.session.add(upload_file)

                except Exception as e:
                    logging.exception(f"Error updating Asset file {original_filename}: {str(e)}")
                    db.session.rollback() 
                    raise e
        
        db.session.commit()

    except Exception as e:
        logging.exception(f"Failed to update Asset files for ID {asset_id}: {str(e)}")
        db.session.rollback()
        raise e


def upload_drawing_files(files, drawing_id):
    """Handles the initial upload of multiple files for a Drawing."""
    folder_path = create_drawing_folder(drawing_id)
    
    for file in files:
        if isinstance(file, FileStorage):
            original_filename = secure_filename(file.filename)
            try:
                validate_file_size(file)
            except ValueError as ve:
                logging.warning(f"Oversized file upload attempt for Drawing: {str(ve)}")
                raise
            
            base, ext = os.path.splitext(original_filename)
            unique_filename = f"{base}{ext}"
            file_path = os.path.join(folder_path, unique_filename)

            try:
                file.save(file_path)
                file_id = str(uuid.uuid4())
                file_size_kb = os.path.getsize(file_path) / 1024

                upload_file = Upload_Files(
                    file_id=file_id,
                    drawing_id=drawing_id, # Use the correct foreign key
                    filename=unique_filename,
                    file_path=file_path,
                    file_size=file_size_kb,
                    # record_time_according_to_timezone=localized_time
                    )
                
                db.session.add(upload_file)
                # db.session.commit()
                                
            except Exception as e:
                logging.exception(f"Error uploading file for Drawing {drawing_id}: {str(e)}")
                raise e


# def update_drawing_files(files, drawing_id, localized_time, files_to_delete):
#     """Handles deletion of old files and upload of new files for a Drawing."""
#     try:
#         folder_path = create_drawing_folder(drawing_id) 
        
#         if files_to_delete:
#             delete_selected_files(files_to_delete)
        
#         for file in files:
#             if isinstance(file, FileStorage):
#                 try:
#                     original_filename = secure_filename(file.filename)
#                     validate_file_size(file)
#                     base, ext = os.path.splitext(original_filename)
#                     unique_filename = f"{base}{ext}"
#                     file_path = os.path.join(folder_path, unique_filename)

#                     file.save(file_path)

#                     file_id = str(uuid.uuid4())
#                     file_size_kb = os.path.getsize(file_path) / 1024

#                     upload_file = Upload_Files(
#                         file_id=file_id,
#                         drawing_id=drawing_id,
#                         filename=unique_filename,
#                         file_path=file_path,
#                         file_size=file_size_kb,
#                         record_time_according_to_timezone=localized_time
#                     )
#                     db.session.add(upload_file)

#                 except Exception as e:
#                     logging.exception(f"Error updating Drawing file {original_filename}: {str(e)}")
#                     db.session.rollback() 
#                     raise e
        
#         db.session.commit()

#     except Exception as e:
#         logging.exception(f"Failed to update Drawing files for ID {drawing_id}: {str(e)}")
#         db.session.rollback()
#         raise e

def update_drawing_files(files, drawing_id, localized_time, files_to_delete):
    """Handles deletion of old files and upload of new files for a Drawing."""
    try:
        # Create folder if it doesn't exist
        folder_path = create_drawing_folder(drawing_id) 
        
        # 1. Handle File Deletions
        if files_to_delete:
            # Assumes delete_selected_files also handles DB record deletion and file system deletion
            delete_selected_files(files_to_delete)
        
        # 2. Handle File Uploads
        for file in files:
            if file and isinstance(file, FileStorage): # Added 'file' check for robustness
                try:
                    original_filename = secure_filename(file.filename)
                    # Assuming validate_file_size raises an exception on failure
                    validate_file_size(file) 
                    
                    base, ext = os.path.splitext(original_filename)
                    # The original code uses a non-unique filename, which can overwrite existing files.
                    # A better practice is to ensure uniqueness, e.g., using a UUID prefix.
                    # unique_filename = f"{uuid.uuid4()}_{original_filename}"
                    # Keeping the original logic's filename for minimal change:
                    unique_filename = original_filename 
                    file_path = os.path.join(folder_path, unique_filename)

                    # Save the file to the file system
                    file.save(file_path)

                    file_id = str(uuid.uuid4())
                    # Check for file existence before getting size to prevent errors
                    file_size_bytes = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    file_size_kb = file_size_bytes / 1024

                    # Create and add the new database record for the uploaded file
                    upload_file = Upload_Files(
                        file_id=file_id,
                        drawing_id=drawing_id,
                        filename=unique_filename,
                        file_path=file_path,
                        file_size=file_size_kb,
                        # Use the passed-in localized_time
                        record_time_according_to_timezone=localized_time 
                    )
                    db.session.add(upload_file)

                except Exception as e:
                    # Log the error, rollback the session changes *within this function*
                    # and re-raise to be caught by the outer function's handler.
                    logging.exception(f"Error saving Drawing file {original_filename}: {str(e)}")
                    db.session.rollback() 
                    raise e
        
        # Note: We do NOT commit here because the outer function `update_drawing`
        # needs to commit both the Drawing metadata change (revision_number) AND
        # the file changes (uploads/deletions) together in a single transaction.
        # Removing the `db.session.commit()` from here prevents a premature commit.
        
    except Exception as e:
        logging.exception(f"Failed to process Drawing files for ID {drawing_id}: {str(e)}")
        # If an error happens outside the file loop (e.g., in create_drawing_folder or delete_selected_files),
        # we rollback and re-raise. The outer function will also catch this and rollback.
        db.session.rollback()
        raise e

def upload_inspiration_files(files, inspiration_id):
    """Handles the initial upload of multiple files for an Inspiration."""
    folder_path = create_inspiration_folder(inspiration_id)
    
    for file in files:
        if isinstance(file, FileStorage):
            original_filename = secure_filename(file.filename)
            try:
                validate_file_size(file)
            except ValueError as ve:
                logging.warning(f"Oversized file upload attempt for Inspiration: {str(ve)}")
                raise
            
            base, ext = os.path.splitext(original_filename)
            unique_filename = f"{base}{ext}"
            file_path = os.path.join(folder_path, unique_filename)

            try:
                file.save(file_path)
                file_id = str(uuid.uuid4())
                file_size_kb = os.path.getsize(file_path) / 1024

                upload_file = Upload_Files(
                    file_id=file_id,
                    inspiration_id=inspiration_id, # Use the correct foreign key
                    filename=unique_filename,
                    file_path=file_path,
                    file_size=file_size_kb
                    # record_time_according_to_timezone=localized_time
                    )
                
                db.session.add(upload_file)
                                
            except Exception as e:
                logging.exception(f"Error uploading file for Inspiration {inspiration_id}: {str(e)}")
                raise e

def upload_task_files(files, task_id):
    """Handles the initial upload of multiple files for an Inspiration."""
    folder_path = create_task_folder(task_id)
    
    for file in files:
        if isinstance(file, FileStorage):
            original_filename = secure_filename(file.filename)
            try:
                validate_file_size(file)
            except ValueError as ve:
                logging.warning(f"Oversized file upload attempt for task: {str(ve)}")
                raise
            
            base, ext = os.path.splitext(original_filename)
            unique_filename = f"{base}{ext}"
            file_path = os.path.join(folder_path, unique_filename)

            try:
                file.save(file_path)
                file_id = str(uuid.uuid4())
                file_size_kb = os.path.getsize(file_path) / 1024

                upload_file = Upload_Files(
                    file_id=file_id,
                    task_id=task_id, # Use the correct foreign key
                    filename=unique_filename,
                    file_path=file_path,
                    file_size=file_size_kb
                    # record_time_according_to_timezone=localized_time
                    )
                
                db.session.add(upload_file)
                                
            except Exception as e:
                logging.exception(f"Error uploading file for Inspiration {task_id}: {str(e)}")
                raise e

def update_inspiration_files(files, inspiration_id ,  files_to_delete):
    """Handles deletion of old files and upload of new files for an Inspiration."""
    try:
        folder_path = create_inspiration_folder(inspiration_id) 
        
        if files_to_delete:
            delete_selected_files(files_to_delete)
        
        for file in files:
            if isinstance(file, FileStorage):
                try:
                    original_filename = secure_filename(file.filename)
                    validate_file_size(file)
                    base, ext = os.path.splitext(original_filename)
                    unique_filename = f"{base}{ext}"
                    file_path = os.path.join(folder_path, unique_filename)

                    file.save(file_path)

                    file_id = str(uuid.uuid4())
                    file_size_kb = os.path.getsize(file_path) / 1024

                    upload_file = Upload_Files(
                        file_id=file_id,
                        inspiration_id=inspiration_id,
                        filename=unique_filename,
                        file_path=file_path,
                        file_size=file_size_kb,
                        # record_time_according_to_timezone=localized_time
                    )
                    db.session.add(upload_file)

                except Exception as e:
                    logging.exception(f"Error updating Inspiration file {original_filename}: {str(e)}")
                    db.session.rollback() 
                    raise e
        
        db.session.commit()

    except Exception as e:
        logging.exception(f"Failed to update Inspiration files for ID {inspiration_id}: {str(e)}")
        db.session.rollback()
        raise e


# --- Flask Route (Copied from Original Snippet) ---

@upload_bp.route('/uploads/<path:filename>')
def serve_file(filename):
    """Route to serve files from the 'uploads' directory."""
    try:
        # This will look for the file in the 'uploads' directory
        return send_from_directory(UPLOAD_FOLDER, filename)
    except FileNotFoundError:
        return "File not found", 404