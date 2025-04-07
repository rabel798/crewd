import os
import secrets
from flask import current_app

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension"""
    allowed_extensions = {'png', 'jpg', 'jpeg'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_upload_dir():
    """Get the upload directory path and create it if it doesn't exist"""
    upload_dir = os.path.join(current_app.static_folder, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir
