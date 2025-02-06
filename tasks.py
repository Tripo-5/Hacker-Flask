from celery import Celery
from flask_sqlalchemy import SQLAlchemy
from models import Proxy  # Import only the necessary models

from config import CELERY_BROKER_URL

celery = Celery(__name__, broker=CELERY_BROKER_URL)

from celery import Celery
import requests
import random
import os
from app import db  # Lazy import to avoid circular dependency
from models import Proxy  # Ensure correct import

@celery.task
def scrape_proxies_task():
    """
    Scrapes proxies from a list of URLs specified in 'proxy_sources.txt'.
    Saves proxies to the database.
    """
    file_path = os.path.join(os.path.dirname(__file__), 'proxy_sources.txt')

    # Check if the file exists
    if not os.path.exists(file_path):
        return "Error: 'proxy_sources.txt' not found in project directory."

    # Read URLs from the file
    try:
        with open(file_path, 'r') as file:
            urls = [line.strip() for line in file.readlines() if line.strip()]
    except Exception as e:
        return f"Error reading 'proxy_sources.txt': {str(e)}"

    if not urls:
        return "Error: No URLs found in 'proxy_sources.txt'."

    scraped_proxies = []

    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                lines = response.text.splitlines()
                for line in lines:
                    parts = line.strip().split(':')
                    if len(parts) == 2:  # Ensure it's in IP:PORT format
                        scraped_proxies.append((parts[0], parts[1]))
        except Exception as e:
            print(f"Failed to fetch from {url}: {e}")

    # If no proxies were scraped, return an error
    if not scraped_proxies:
        return "No valid proxies found from the sources."

    # Store scraped proxies in the database
    for ip, port in scraped_proxies:
        proxy = Proxy(ip=ip, port=int(port))
        db.session.add(proxy)

    db.session.commit()
    return f'Successfully scraped {len(scraped_proxies)} proxies.'


@celery.task
def test_proxies_task():
    import requests
    import time
    from app import db  # Lazy import to avoid circular dependency

    proxies = Proxy.query.all()
    for proxy in proxies:
        start = time.time()
        try:
            response = requests.get('http://8.8.8.8', proxies={"http": f"{proxy.ip}:{proxy.port}"}, timeout=5)
            proxy.connectivity = 'Yes' if response.status_code == 200 else 'No'
        except:
            proxy.connectivity = 'No'

        proxy.response_time = round(time.time() - start, 2)
        db.session.commit()

