from celery import Celery
from flask import Flask
from app import create_app, db
from models import Proxy
import requests
import re

# Initialize Flask app inside Celery
flask_app = create_app()
celery = Celery(flask_app.name, broker=flask_app.config['CELERY_BROKER_URL'])
celery.conf.update(flask_app.config)

@celery.task
def scrape_proxies_task():
    """ Scrape proxies from online sources and store in the database """
    with flask_app.app_context():  # Ensure Celery has the Flask context
        proxy_sources = [
            "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
            "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt"
        ]
        
        # Fetch already stored proxies to avoid duplicates
        stored_proxies = {(p.ip, str(p.port)) for p in db.session.query(Proxy).all()}
        
        new_proxies = []
        for url in proxy_sources:
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                proxies = re.findall(r"(\d+\.\d+\.\d+\.\d+):(\d+)", response.text)  # Extract IP:Port

                for ip, port in proxies:
                    if (ip, port) not in stored_proxies:
                        new_proxies.append(Proxy(ip=ip, port=int(port)))
                        stored_proxies.add((ip, port))  # Add to avoid duplicates
            except requests.RequestException as e:
                print(f"Error fetching proxies from {url}: {e}")

        # Insert new proxies into database
        if new_proxies:
            db.session.bulk_save_objects(new_proxies)
            db.session.commit()

        return f"Scraped and added {len(new_proxies)} new proxies."


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
