"""Application configuration."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Flask
SECRET_KEY = "change-me-in-production"
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"pdf", "docx"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

# MySQL
MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "***********"           # <-- set your MySQL password
MYSQL_DB = "resume_screening"
MYSQL_PORT = 3306
