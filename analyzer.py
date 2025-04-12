# analyzer.py

def verify_ad(ad, keywords):
    """
    Funkcja sprawdza, czy ogłoszenie (tytuł oraz opis) zawiera wszystkie wymagane słowa kluczowe.
    """
    text = (ad.get('title', '') + " " + ad.get('description', '')).lower()
    for keyword in keywords:
        if keyword.lower() not in text:
            return False
    return True

def rate_ad(ad, previous_price=None):
    """
    Funkcja ocenia ogłoszenie na podstawie spadku ceny.
    Jeśli wcześniejsza cena była wyższa, zwraca procentowy spadek; w przeciwnym razie zwraca 0.
    """
    price = ad.get('price', 0)
    if previous_price and previous_price > price:
        drop_percentage = ((previous_price - price) / previous_price) * 100
        return round(drop_percentage, 2)
    return 0
