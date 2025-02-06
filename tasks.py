from celery import Celery
import requests
import re
from app import app, db
from models import Proxy

celery = Celery('tasks', broker='redis://localhost:6379/0')

# List of proxy sources
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt",
    "https://spys.me/socks.txt"
]

@celery.task
def scrape_proxies_task():
    """Fetch and store proxies from sources"""
    proxies_found = set()

    for url in PROXY_SOURCES:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Raises error for bad responses
            raw_proxies = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}:\d+\b", response.text)
            for proxy in raw_proxies:
                proxies_found.add(proxy)  # Use set to avoid duplicates
        except requests.RequestException as e:
            print(f"Error fetching proxies from {url}: {e}")

    with app.app_context():
        stored_proxies = {(p.ip, str(p.port)) for p in Proxy.query.all()}  # Fetch existing proxies
        new_proxies = [Proxy(ip=ip, port=int(port)) for ip, port in 
                       (proxy.split(":") for proxy in proxies_found)
                       if (ip, port) not in stored_proxies]

        if new_proxies:
            db.session.bulk_save_objects(new_proxies)
            db.session.commit()
        
    return f"Scraped {len(new_proxies)} new proxies."

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
