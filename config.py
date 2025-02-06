import os

# Database credentials (default values, change as needed)
DB_USER = "pentest_user"
DB_PASSWORD = "pentestpassword"
DB_HOST = "localhost"
DB_NAME = "pentest_db"

# Create MySQL database if it doesn't exist
SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# Celery Configuration
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"

SECRET_KEY = os.urandom(24)  # Generates a random secret key
SQLALCHEMY_TRACK_MODIFICATIONS = False
