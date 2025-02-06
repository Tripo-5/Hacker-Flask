from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from celery import Celery
import requests
import time
import random

app = Flask(__name__)
app.config.from_object('config')

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Celery Configuration
celery = Celery(app.name, broker=app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'))
celery.conf.update(app.config)

from models import User, Proxy

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Ensure Database is Created on Startup
with app.app_context():
    db.create_all()

# Route: User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            return "User already exists!"

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Route: User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Route: Dashboard
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
    proxies = Proxy.query.limit(30).all()
    return jsonify([{'ip': p.ip, 'port': p.port, 'connectivity': p.connectivity, 'response_time': p.response_time, 'location': p.location} for p in proxies])

# Database setup (for first-time use)
def create_database():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    create_database()  # Ensure DB is created
    app.run(host='0.0.0.0', port=5000, debug=True)
