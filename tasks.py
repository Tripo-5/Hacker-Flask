from celery import Celery
import requests
import re
import os
from app import db
from models import Proxy

# Initialize Celery
celery = Celery('tasks', broker='redis://localhost:6379/0')

# Path to the proxy sources file
PROXY_SOURCES_FILE = os.path.join(os.path.dirname(__file__), 'proxy_sources.txt')

# Function to load proxy sources from a file
def load_proxy_sources():
    """Loads proxy source URLs from the proxy_sources.txt file."""
    if not os.path.exists(PROXY_SOURCES_FILE):
        return []
    with open(PROXY_SOURCES_FILE, 'r') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

# Function to fetch proxies from a URL
def fetch_proxies(url):
    """Fetches proxies from a given URL, extracting valid IP:PORT pairs."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an error for failed requests
        proxies = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}:\d+\b', response.text)  # Extract IP:PORT format
        return proxies
    except requests.RequestException:
        return []

@celery.task
def scrape_proxies_task():
    """Scrapes proxies from predefined sources and stores them in the database."""
    proxy_sources = load_proxy_sources()  # Load sources dynamically
    scraped_proxies = set()  # Use a set to avoid duplicates

    for url in proxy_sources:
        proxies = fetch_proxies(url)
        scraped_proxies.update(proxies)

    with db.session.begin():  # Ensure session is handled correctly
        for proxy in scraped_proxies:
            ip, port = proxy.split(':')
            if not Proxy.query.filter_by(ip=ip, port=int(port)).first():  # Avoid duplicate entries
                new_proxy = Proxy(ip=ip, port=int(port))
                db.session.add(new_proxy)

    return f'Scraped {len(scraped_proxies)} proxies and added to database.'

@celery.task
def test_proxies_task():
    """Tests the scraped proxies to determine their connectivity and response time."""
    proxies = Proxy.query.all()
    valid_proxies = []

    for proxy in proxies:
        proxy_url = f'socks5://{proxy.ip}:{proxy.port}'
        try:
            response = requests.get('https://www.google.com', proxies={'http': proxy_url, 'https': proxy_url}, timeout=5)
            if response.status_code == 200:
                proxy.connectivity = 'Working'
                proxy.response_time = response.elapsed.total_seconds()
                valid_proxies.append(proxy)
        except requests.RequestException:
            proxy.connectivity = 'Dead'

    with db.session.begin():  # Update the database in bulk
        db.session.bulk_save_objects(valid_proxies)

    return f'Tested {len(proxies)} proxies. {len(valid_proxies)} are working.'

