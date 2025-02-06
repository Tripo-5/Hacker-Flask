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
    Scrapes proxies from a list of URLs in 'proxy_sources.txt',
    extracts only valid IP:PORT format, and stores them in the database.
    """
    file_path = os.path.join(os.path.dirname(__file__), 'proxy_sources.txt')

    # Check if file exists
    if not os.path.exists(file_path):
        print("❌ Error: 'proxy_sources.txt' not found.")
        return "Error: 'proxy_sources.txt' not found."

    # Read URLs from file
    try:
        with open(file_path, 'r') as file:
            urls = [line.strip() for line in file.readlines() if line.strip()]
    except Exception as e:
        print(f"❌ Error reading 'proxy_sources.txt': {e}")
        return f"Error reading 'proxy_sources.txt': {str(e)}"

    if not urls:
        print("❌ No URLs found in 'proxy_sources.txt'.")
        return "Error: No URLs found in 'proxy_sources.txt'."

    # Regular expression to match valid IP:PORT format
    proxy_regex = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{2,5})")

    scraped_proxies = set()  # Store unique proxies

    for url in urls:
        print(f"🔍 Fetching from {url}...")
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                matches = proxy_regex.findall(response.text)  # Extract valid IP:PORT
                for match in matches:
                    scraped_proxies.add(match)
                print(f"✅ Found {len(matches)} proxies from {url}")
            else:
                print(f"⚠️ Skipping {url}: Status {response.status_code}")
        except Exception as e:
            print(f"⚠️ Failed to fetch {url}: {e}")

    # If no proxies found, log it
    if not scraped_proxies:
        print("❌ No valid proxies found from any source.")
        return "No valid proxies found."

    # Store scraped proxies in database
    with app.app_context():
        for ip, port in scraped_proxies:
            if not Proxy.query.filter_by(ip=ip, port=int(port)).first():  # Avoid duplicates
                proxy = Proxy(ip=ip, port=int(port))
                db.session.add(proxy)

        db.session.commit()

    print(f"✅ Successfully scraped and saved {len(scraped_proxies)} proxies.")
    return f"Successfully scraped and saved {len(scraped_proxies)} proxies."
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

