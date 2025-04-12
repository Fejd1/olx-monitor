# scraper.py

import time
import random
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By 
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Lista User-Agentów do rotacji
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/91.0.4472.101 Safari/537.36'
]

MAX_REQUESTS_PER_MINUTE = 10
request_timestamps = []

def can_make_request():
    """Sprawdza i respektuje limit żądań."""
    global request_timestamps
    now = time.time()
    request_timestamps = [ts for ts in request_timestamps if now - ts < 60]
    if len(request_timestamps) >= MAX_REQUESTS_PER_MINUTE:
        wait_time = 60 - (now - request_timestamps[0]) + 1
        print(f"Osiągnięto limit żądań ({MAX_REQUESTS_PER_MINUTE}/min). Czekam {int(wait_time)} s...")
        time.sleep(wait_time)
        return can_make_request()
    else:
        request_timestamps.append(now)
        return True

def extract_price(price_text):
    """Ekstrakcja ceny przy użyciu regex."""
    match = re.search(r'[\d\s,]+', price_text)
    if match:
        cleaned = match.group(0).replace(" ", "").replace("zł", "").replace(",", ".")
        try:
            return float(cleaned)
        except:
            return 0
    return 0

def extract_listing_details(html_content):
    """
    Ekstrakcja danych szczegółowych z ogłoszenia przy użyciu selektorów.
    Przeszukujemy paragrafy z selektorem '.css-1los5bp' i wybieramy pierwszy pasujący warunek:
    "Stan: Używane", "Stan: Uszkodzone" lub "Stan: Nowe".
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    try:
        description_element = soup.select_one('.css-19duwlz')
        paragraphs = soup.select('.css-1los5bp')
        # Dla debugowania wyświetlamy znalezione paragrafy
        print("Paragraphs found:", len(paragraphs))
        for p in paragraphs:
            print("-", p.get_text(strip=True))
        conditions = ["Stan: Używane", "Stan: Uszkodzone", "Stan: Nowe"]
        used_condition_paragraph = None
        for p in paragraphs:
            txt = p.get_text(strip=True)
            if any(cond in txt for cond in conditions):
                used_condition_paragraph = txt
                break
        print("Stan:", used_condition_paragraph)
        title_element = soup.select_one('.css-10ofhqw')
        price_element = soup.select_one('.css-fqcbii')
        location_element = soup.select_one('.css-7wnksb')
        image_element = soup.select_one('.css-1bmvjcs')
        image_url = image_element['src'] if image_element and image_element.has_attr('src') else None

        details = {
            'description': description_element.get_text().strip() if description_element else 'error',
            'item_condition': used_condition_paragraph if used_condition_paragraph else 'error',
            'title': title_element.get_text().strip() if title_element else 'error',
            'price': extract_price(price_element.get_text().strip()) if price_element else 0,
            'location': location_element.get_text().strip() if location_element else 'error',
            'image_url': image_url
        }
        return details
    except Exception as e:
        print("Błąd podczas ekstrakcji szczegółów ogłoszenia:", e)
        return {
            'description': 'error',
            'item_condition': 'error',
            'title': 'error',
            'price': 0,
            'location': 'error',
            'image_url': None
        }

def scrape_olx(search_link, db, keywords=None, progress_callback=None):
    """
    Scrapuje ogłoszenia dla zadanego linku wyszukiwania.
    search_link – słownik zawierający co najmniej 'id' i 'url'
    db – instancja Database
    keywords – lista słów kluczowych (jeśli nie podane, zostaną wyciągnięte z URL)
    """
    # Jeżeli nie podano, domyślne słowa (możesz zastąpić później dynamicznym wyciąganiem)
    if not keywords:
        keywords = []
    url = search_link['url']
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-setuid-sandbox")
    random_user_agent = random.choice(USER_AGENTS)
    chrome_options.add_argument(f"user-agent={random_user_agent}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        can_make_request()
        driver.get(url)
        time.sleep(2)
        
        has_captcha = driver.execute_script(
            "return (document.querySelector('.g-recaptcha') !== null || "
            "document.querySelector('[data-sitekey]') !== null || "
            "document.body.textContent.toLowerCase().includes('captcha'));"
        )
        if has_captcha:
            print("Wykryto CAPTCHA lub blokadę scraper'a! Zapisuję screenshot i przerywam.")
            driver.save_screenshot(f"captcha-{int(time.time())}.png")
            return []
        
        # Pobranie liczby stron wyników
        pagination_elements = driver.find_elements(By.CSS_SELECTOR, '.pagination-list .pagination-item')
        max_page = 1
        for elem in pagination_elements:
            try:
                num = int(elem.text.strip())
                if num > max_page:
                    max_page = num
            except:
                continue
        total_pages = max_page
        print(f"Liczba stron: {total_pages}")

        listing_selector = '.css-qfzx1y'
        all_listings = []
        for page_index in range(1, total_pages + 1):
            page_url = f"{url}?page={page_index}" if '?' not in url else f"{url}&page={page_index}"
            print(f"Pobieram stronę {page_index}: {page_url}")
            can_make_request()
            driver.get(page_url)
            time.sleep(2)
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            listings_elems = soup.select(listing_selector)
            print(f"Na stronie {page_index} znaleziono {len(listings_elems)} ogłoszeń.")
            for elem in listings_elems:
                all_listings.append({
                    "text": elem.get_text(strip=True),
                    "html": str(elem)
                })
            if progress_callback:
                progress_callback(page_index, total_pages, 0, len(all_listings))
        print(f"Zebrano {len(all_listings)} ogłoszeń ze wszystkich stron")
        results = []
        for i, listing in enumerate(all_listings):
            progress = int((i / len(all_listings)) * 100)
            print(f"Przetwarzanie ogłoszenia {i+1} z {len(all_listings)} ({progress}% ukończone)")
            soup_listing = BeautifulSoup(listing['html'], 'html.parser')
            a_tag = soup_listing.select_one('a.css-1tqlkj0')
            if not a_tag or not a_tag.has_attr('href'):
                continue
            href = "https://olx.pl" + a_tag['href']
            parts = href.split('-')
            olx_id = '-'.join(parts[-2:]).replace('.html', '')
            existing_listing = db.get_listing_by_olx_id(search_link['id'], olx_id)
            if not existing_listing:
                # Dynamiczne wyciągnięcie keywordów z URL wyszukiwania
                parsed_url = urlparse(url)
                match = re.search(r'q-([^/]+)/', parsed_url.path)
                if match:
                    raw_keywords = match.group(1)
                    cleaned = re.split(r'-CID', raw_keywords)[0]
                    keywords = cleaned.split('-')
                else:
                    keywords = []
                can_make_request()
                driver.get(href)
                time.sleep(2)
                print(f"Pobrano stronę szczegółów dla ogłoszenia: {olx_id}")
                details = extract_listing_details(driver.page_source)
                details['olx_id'] = olx_id
                details['url'] = href
                text = (details['title'] + " " + details['description']).lower()
                print("Treść ogłoszenia:", details['title'])
                print("Wymagane słowa kluczowe:", keywords)
                # Prosta metoda fuzzy match'owania (możesz rozwinąć)
                matched = all(kw.lower() in text for kw in keywords) if keywords else True
                if matched:
                    results.append(details)
                    db.insert_or_update_listing(search_link['id'], details)
                else:
                    print(f"Ogłoszenie {olx_id} nie spełnia kryteriów filtracji.")
                if progress_callback:
                    progress_callback(total_pages, total_pages, i, len(all_listings))
            else:
                db.update_listing_timestamp(existing_listing['id'])
        return results
    finally:
        driver.quit()

def scrape_item_by_url(db, item):
    """
    Scrapuje ogłoszenie dla danego przedmiotu (item) na podstawie item['olx_url'].
    Jeśli nie przekazano słów kluczowych, dynamicznie wyciąga je z URL.
    """
    print(f"Rozpoczynam scrapowanie URL: {item.get('olx_url')}")
    url = item.get('olx_url')
    if not url or not url.startswith('https://www.olx.pl/'):
        print(f"Nieprawidłowy URL dla przedmiotu {item.get('name', '')}: {url}")
        return
    parsed_url = urlparse(url)
    print("Parametry URL:", parsed_url.query)
    keywords = item.get('keywords')
    if not keywords:
        m = re.search(r'q-([^/]+)/', url)
        if m:
            keywords = m.group(1).split('-')
        else:
            keywords = []
    return scrape_olx(item, db, keywords)
