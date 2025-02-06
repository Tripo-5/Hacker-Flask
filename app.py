from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from celery import Celery
import os

# Initialize Extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = "login"

# Flask Application Factory
def create_app():
    """Flask Application Factory Pattern"""
    app = Flask(__name__)
    app.config.from_object('config')  # Ensure your config.py has SQLALCHEMY_DATABASE_URI

    # Initialize extensions with the app
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    # Import models AFTER initializing db
    from models import User, Proxy

    @login_manager.user_loader
    def load_user(user_id):
        """Fix for SQLAlchemy 2.0 - Use session.get() instead of query.get()"""
        return db.session.get(User, int(user_id))

    with app.app_context():
        db.create_all()  # Ensure DB is created once

    # Flask Routes

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            if db.session.query(User).filter_by(username=username).first():
                return "User already exists!"

            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = User(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()

            return redirect(url_for('login'))

        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            user = db.session.query(User).filter_by(username=username).first()

            if user and bcrypt.check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('dashboard'))

        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    @app.route('/')
    @login_required
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/recon_management')
    @login_required
    def recon_management():
        return render_template('recon.html')

    @app.route('/scrape_proxies', methods=['POST'])
    @login_required
    def scrape_proxies():
        from tasks import scrape_proxies_task  # Lazy import
        scrape_proxies_task.delay()
        return jsonify({'message': 'Scraping started'})

    @app.route('/test_proxies', methods=['POST'])
    @login_required
    def test_proxies():
        from tasks import test_proxies_task  # Lazy import
        test_proxies_task.delay()
        return jsonify({'message': 'Testing started'})

    @app.route('/get_proxies')
    @login_required
    def get_proxies():
        """Fix: Ensure correct context and valid DB queries"""
        proxies = db.session.query(Proxy).limit(30).all()
        return jsonify([
            {'ip': p.ip, 'port': p.port, 'connectivity': p.connectivity, 'response_time': p.response_time, 'location': p.location}
            for p in proxies
        ])

    return app  # Return app instance

# Run App
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
