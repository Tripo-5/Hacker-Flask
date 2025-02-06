from celery import Celery
import requests
import re
from app import db
from models import Proxy

celery = Celery('tasks', broker='redis://localhost:6379/0')

PROXY_SOURCES = [
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt",
    "https://spys.me/socks.txt"
]

@celery.task
def scrape_proxies_task():
    """Fetch and store proxies from sources"""
    proxies_found = []

    for url in PROXY_SOURCES:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                raw_proxies = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}:\d+\b", response.text)
                for proxy in raw_proxies:
                    ip, port = proxy.split(':')
                    proxies_found.append((ip, port))
        except requests.RequestException:
            print(f"Failed to fetch from {url}")

    # Store in database
    with db.session.begin():
        for ip, port in proxies_found:
            existing_proxy = db.session.query(Proxy).filter_by(ip=ip, port=port).first()
            if not existing_proxy:  # Avoid duplicates
                new_proxy = Proxy(ip=ip, port=int(port))
                db.session.add(new_proxy)

    db.session.commit()
    return f"Scraped and stored {len(proxies_found)} proxies."

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

