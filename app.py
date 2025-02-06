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

# Initialize Flask App and Celery
app = create_app()
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

@login_manager.user_loader
def load_user(user_id):
    """Fix for SQLAlchemy 2.0 - Use session.get() instead of query.get()"""
    with app.app_context():
        return db.session.get(User, int(user_id))

# Route: User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        with app.app_context():
            if db.session.query(User).filter_by(username=username).first():
                return "User already exists!"

            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = User(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
        
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Route: Scrape Proxies
@app.route('/scrape_proxies', methods=['POST'])
@login_required
def scrape_proxies():
    scrape_proxies_task.delay()
    return jsonify({'message': 'Scraping started'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
