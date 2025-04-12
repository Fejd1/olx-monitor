# scheduler.py

from apscheduler.schedulers.blocking import BlockingScheduler
from database import Database
from scraper import scrape_olx
from analyzer import verify_ad, rate_ad

def scheduled_job():
    db = Database()
    print("Rozpoczęcie zaplanowanego scrapingu...")
    links = db.get_search_links()
    for link in links:
        print("Scraping dla:", link['url'])
        ads = scrape_olx(link, db)
        print(f"Zaktualizowano {len(ads)} ogłoszeń dla linku id {link['id']}.")
    print("Zakończono scraping i aktualizację danych.")

def start_scheduler():
    scheduler = BlockingScheduler()
    scheduler.add_job(scheduled_job, 'interval', minutes=30)
    print("Harmonogram rozpoczęty. Aby zakończyć, naciśnij Ctrl+C.")
    scheduler.start()
