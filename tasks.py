from celery import Celery
from app import create_app, db  # Import the Flask factory function and database
from models import Proxy
import requests
import re

# Create Flask App and Initialize Celery
flask_app = create_app()
celery = Celery(flask_app.name, broker=flask_app.config['CELERY_BROKER_URL'])
celery.conf.update(flask_app.config)

@celery.task
def scrape_proxies_task():
    """Scrapes proxy lists and adds them to the database."""
    with flask_app.app_context():  # FIX: Run Celery task inside Flask context
        proxy_sources = [
            "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
            "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt",
            "https://spys.me/socks.txt"
        ]
        
        stored_proxies = {(p.ip, str(p.port)) for p in db.session.query(Proxy).all()}  # Fetch existing proxies

        for url in proxy_sources:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    proxies = re.findall(r'(\d+\.\d+\.\d+\.\d+):(\d+)', response.text)
                    for ip, port in proxies:
                        if (ip, port) not in stored_proxies:
                            new_proxy = Proxy(ip=ip, port=int(port))
                            db.session.add(new_proxy)
            except Exception as e:
                print(f"Failed to fetch proxies from {url}: {e}")

        db.session.commit()
        return "Scraping Complete"


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
