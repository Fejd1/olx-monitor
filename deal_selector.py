# deal_selector.py

import statistics
import requests
from database import Database
from PIL import Image





def normalize(value, min_val, max_val):
    if max_val == min_val:
        return 1.0  # aby uniknąć dzielenia przez 0
    return (value - min_val) / (max_val - min_val)


def get_condition_factor(condition):
    """
    Zamienia opis stanu na wartość numeryczną:
      - "Stan: Nowe"      → 1.5
      - "Stan: Używane"   → 1.0
      - "Stan: Uszkodzone"→ 0.1
      - Inne              → 0.7
    """
    if not condition:
        return 0.7
    condition_l = condition.lower()
    if "nowe" in condition_l:
        return 1.5
    elif "używane" in condition_l:
        return 1.0
    elif "uszkodzone" in condition_l:
        return 0.1
    else:
        return 0.7


def analyze_deals():
    db = Database()
    best_deals = []
    links = db.get_search_links()
    for link in links:
        listings = db.get_listings_for_search_link(link['id'])
        if not listings:
            continue
        prices = [float(l['price']) for l in listings if float(l['price']) > 0]
        if not prices:
            continue
        avg_price = statistics.mean(prices)
        enriched_listings = []
        for listing in listings:
            current_price = float(listing['price'])
            previous_price = float(listing['previous_price']) if listing.get(
                'previous_price') else None
            potential_profit = max(avg_price - current_price, 0)
            search_link_id = listing['search_link_id']
            profit_ratio = potential_profit / avg_price if avg_price else 0
            if previous_price and previous_price > current_price:
                price_drop_pct = (
                    (previous_price - current_price) / previous_price) * 100
            else:
                price_drop_pct = 0
            condition_factor = get_condition_factor(
                listing.get('item_condition'))
            enriched_listings.append({
                'listing': listing,
                'potential_profit': potential_profit,
                'price_drop_pct': price_drop_pct,
                'condition_factor': condition_factor,
                'profit_ratio': profit_ratio,
                'avg_price': avg_price,
                'search_link_id': search_link_id
            })
        # Normalizacja
        max_profit = max(l['potential_profit'] for l in enriched_listings)
        max_drop = max(l['price_drop_pct'] for l in enriched_listings)
        min_drop = min(l['price_drop_pct'] for l in enriched_listings)
        min_profit = min(l['potential_profit'] for l in enriched_listings)
        not_matching = []
        for enriched in enriched_listings:
            norm_profit = normalize(
                enriched['potential_profit'], min_profit, max_profit)
            norm_drop = normalize(
                enriched['price_drop_pct'], min_drop, max_drop)
            norm_condition = enriched['condition_factor']  # już w skali
            raw_score = (0.5 * norm_profit + 0.3 *
                         (norm_drop) + 0.2 * norm_condition)
            scaled_score = 1 + raw_score * 9
            listing = enriched['listing']
            listing['avg_price'] = enriched['avg_price']
            listing['potential_profit'] = enriched['potential_profit']
            listing['price_drop_pct'] = enriched['price_drop_pct']
            listing['score'] = round(scaled_score, 2)
            best_deals.append(listing)
    
    best_deals.sort(key=lambda x: x['score'], reverse=True)
    return best_deals


def display_best_deals(n=10):
    best_deals = analyze_deals()
    if not best_deals:
        print("Nie znaleziono ofert do analizy.")
        return
    print(f"Top {n} najlepszych okazji:")
    for deal in best_deals[:n]:
        print("-" * 40)
        print(f"ID: {deal['olx_id']}")
        print(f"Tytuł: {deal['title']}")
        print(
            f"Cena: {deal['price']} zł  (średnia: {deal['avg_price']:.2f} zł)")
        print(f"Potencjalny zarobek: {deal['potential_profit']:.2f} zł")
        print(f"Spadek ceny: {deal['price_drop_pct']:.2f}%")
        print(f"Stan: {deal['item_condition']}")
        print(f"Score: {deal['score']:.2f}")
        print(f"Link: {deal['url']}")

