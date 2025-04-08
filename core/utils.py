import os

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension"""
    allowed_extensions = {'png', 'jpg', 'jpeg'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions
