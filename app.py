from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from celery import Celery

# Initialize Flask extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

def create_app():
    """ Application Factory for Flask """
    app = Flask(__name__)
    app.config.from_object('config')

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()  # Ensure tables exist

    return app

app = create_app()

@login_manager.user_loader
def load_user(user_id):
    """ Load user session """
    return db.session.get(User, int(user_id))

# Import models AFTER initializing db to prevent circular imports
from models import User, Proxy

# ✅ **Routes**
@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """ User Registration """
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    """ User Login """
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
    """ Logout User """
    logout_user()
    return redirect(url_for('login'))

@app.route('/recon_management')
@login_required
def recon_management():
    return render_template('recon.html')

@app.route('/scrape_proxies', methods=['POST'])
@login_required
def scrape_proxies():
    """ Start proxy scraping task """
    from tasks import scrape_proxies_task  # Import inside route to avoid circular import
    with app.app_context():  # Ensure Celery tasks have Flask context
        scrape_proxies_task.delay()
    return jsonify({'message': 'Scraping started'})

@app.route('/test_proxies', methods=['POST'])
@login_required
def test_proxies():
    """ Start proxy testing task """
    from tasks import test_proxies_task  
    with app.app_context():
        test_proxies_task.delay()
    return jsonify({'message': 'Testing started'})

@app.route('/get_proxies')
@login_required
def get_proxies():
    """ Retrieve proxies from database """
    proxies = Proxy.query.limit(30).all()
    return jsonify([
        {'ip': p.ip, 'port': p.port, 'connectivity': p.connectivity, 'response_time': p.response_time, 'location': p.location}
        for p in proxies
    ])

# Start Flask App
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
