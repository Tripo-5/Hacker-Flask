from app import app, db
from models import User, Proxy

# Ensure database is created
with app.app_context():
    db.create_all()
    print("✅ Database initialized successfully.")
