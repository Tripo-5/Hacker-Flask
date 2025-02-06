from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from celery import Celery
import os

# Initialize Extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'login'

def create_app():
    """Flask Application Factory Pattern"""
    app = Flask(__name__)
    app.config.from_object('config')

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()

    return app

# Create the app instance
app = create_app()

# Celery Setup
def make_celery(app):
    """Initialize Celery with Flask app context"""
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        """Ensure tasks run inside Flask context"""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

celery = make_celery(app)

@login_manager.user_loader
def load_user(user_id):
    """Fix for SQLAlchemy 2.0 - Use session.get() instead of query.get()"""
    with app.app_context():
        return db.session.get(User, int(user_id))

@app.route('/')
def home():
    return "Flask App is Running!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
