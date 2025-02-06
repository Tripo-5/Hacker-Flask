from celery import Celery
from flask import Flask
from app import db, create_app  # Ensure you have create_app() function in app.py
from models import Proxy
import requests
import re

# Create Celery instance
celery = Celery(__name__, broker="redis://localhost:6379/0")

# Flask application initialization inside Celery worker
def make_celery():
    flask_app = create_app()  # Make sure create_app() is defined in app.py
    celery.conf.update(flask_app.config)
    return celery

celery = make_celery()
@celery.task
def scrape_proxies_task():
    """Scrapes proxies from predefined sources and saves to the database."""
    
    proxy_sources = [
        "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
        "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt"
    ]

    proxies = set()
    regex = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{2,5})")

    with create_app().app_context():  # Ensures SQLAlchemy works within Celery task
        for url in proxy_sources:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    new_proxies = regex.findall(response.text)
                    proxies.update(new_proxies)
            except requests.RequestException as e:
                print(f"Error fetching {url}: {e}")

        stored_proxies = {(p.ip, str(p.port)) for p in Proxy.query.all()}

        # Insert only new proxies
        new_entries = [Proxy(ip=ip, port=int(port)) for ip, port in proxies if (ip, port) not in stored_proxies]
        if new_entries:
            db.session.bulk_save_objects(new_entries)
            db.session.commit()
            print(f"✅ {len(new_entries)} new proxies added.")
        else:
            print("ℹ️ No new proxies found.")

    return f"Scraping completed. {len(new_entries)} new proxies added."

@celery.task
def test_proxies_task():
    """Tests the scraped proxies to determine their connectivity and response time."""
    with app.app_context():
        proxies = Proxy.query.all()
        for proxy in proxies:
            proxy_url = f'socks5://{proxy.ip}:{proxy.port}'
            try:
                response = requests.get('https://www.google.com', proxies={'http': proxy_url, 'https': proxy_url}, timeout=5)
                proxy.connectivity = 'Working' if response.status_code == 200 else 'Failed'
            except requests.RequestException:
                proxy.connectivity = 'Failed'
        db.session.commit()
    
    return "Proxy testing completed."
