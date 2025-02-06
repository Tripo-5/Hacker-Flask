import os

SECRET_KEY = 'your_secret_key'
SQLALCHEMY_DATABASE_URI = 'mysql://user:password@localhost/pentest_db'
SQLALCHEMY_TRACK_MODIFICATIONS = False

CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
