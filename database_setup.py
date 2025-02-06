import pymysql
from app import db
from models import User
from config import DB_USER, DB_PASSWORD, DB_HOST, DB_NAME

# Connect to MySQL and Create the Database If It Doesn't Exist
connection = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD)
cursor = connection.cursor()
cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
connection.commit()
cursor.close()
connection.close()

# Initialize Flask Database Tables
def initialize_database():
    with db.engine.connect() as connection:
        db.create_all()

    # Ensure at least one user exists
    if not User.query.first():
        print("No users found. Please register an admin user via the web interface.")

if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully.")
