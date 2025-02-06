from celery import Celery
from app import app, db
from models import Proxy
import requests
import re
import time

celery = Celery(
    'tasks',
    broker=app.config['CELERY_BROKER_URL'],
    backend=app.config['CELERY_RESULT_BACKEND']
)

PROXY_SOURCES = [
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt"
]

@celery.task
def scrape_proxies_task():
    """Scrape proxies from external sources and store valid ones in the database."""
    valid_proxies = set()
    ip_port_regex = re.compile(r'(\d+\.\d+\.\d+\.\d+):(\d+)')

    for url in PROXY_SOURCES:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                for line in response.text.splitlines():
                    match = ip_port_regex.match(line)
                    if match:
                        ip, port = match.groups()
                        valid_proxies.add((ip, port))
        except Exception as e:
            print(f"Error fetching {url}: {e}")

    with app.app_context():
        stored_proxies = {(p.ip, str(p.port)) for p in Proxy.query.all()}  
        new_proxies = valid_proxies - stored_proxies 

        for ip, port in new_proxies:
            new_proxy = Proxy(ip=ip, port=int(port))
            db.session.add(new_proxy)

        db.session.commit()

    return f"Scraped {len(new_proxies)} new proxies."

@celery.task
def test_proxies_task():
    """Tests stored proxies for connectivity and response time."""
    with app.app_context():
        proxies = Proxy.query.all()

        for proxy in proxies:
            proxy_url = f"socks5://{proxy.ip}:{proxy.port}"
            try:
                start_time = time.time()
                response = requests.get("https://httpbin.org/ip", proxies={"http": proxy_url, "https": proxy_url}, timeout=5)
                end_time = time.time()

                if response.status_code == 200:
                    proxy.connectivity = True
                    proxy.response_time = round(end_time - start_time, 2)
                else:
                    proxy.connectivity = False
            except Exception:
                proxy.connectivity = False

        db.session.commit()

    return "Proxy testing complete."
