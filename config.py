import os

# Database credentials (default values, change as needed)
DB_USER = "pentest_user"
DB_PASSWORD = "pentestpassword"
DB_HOST = "localhost"
DB_NAME = "pentest_db"

# Flask Secret Key
SECRET_KEY = os.environ.get('SECRET_KEY', 'mysecretkey')

# SQLAlchemy Database URI
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://pentest_user:pentestpassword@localhost/pentest_db'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

