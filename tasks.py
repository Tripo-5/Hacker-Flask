from celery import Celery
from flask_sqlalchemy import SQLAlchemy
from models import Proxy  # Import only the necessary models

from config import CELERY_BROKER_URL

celery = Celery(__name__, broker=CELERY_BROKER_URL)

@celery.task
def scrape_proxies_task():
    import random
    from app import db  # Lazy import to avoid circular dependency

    urls = ['https://example.com/proxies']  # Replace with real sources
    scraped_proxies = [(f'192.168.1.{random.randint(1, 255)}', random.randint(1000, 9999)) for _ in range(50)]

    for ip, port in scraped_proxies:
        proxy = Proxy(ip=ip, port=port)
        db.session.add(proxy)

    db.session.commit()
    return 'Scraping complete'

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

