# api.py
import threading
import uuid
from collections import defaultdict
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required
from datetime import timedelta
from config import JWT_SECRET_KEY
from database import Database
from scraper import scrape_olx, scrape_item_by_url
from deal_selector import analyze_deals
from scheduler import start_scheduler  # opcjonalnie, jeśli chcesz używać harmonogramu
from auth import auth_bp


app = Flask(__name__)
# Konfiguracja CORS dla wszystkich ścieżek
CORS(app, supports_credentials=True, origins=["*"])
app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)
jwt = JWTManager(app)

# Rejestracja blueprinta autoryzacji
app.register_blueprint(auth_bp)
scraper_tasks = defaultdict(lambda: {"status": "unknown", "progress": 0, "total": 0, "completed": 0})


@app.route("/api/links", methods=["GET"])
@jwt_required()
def get_links():
    db = Database()
    links = db.get_search_links()
    return jsonify(links), 200

@app.route("/api/links", methods=["POST"])
@jwt_required()
def add_link():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"msg": "URL jest wymagany"}), 400
    db = Database()
    db.add_search_link(url)
    return jsonify({"msg": "Link dodany", "url": url}), 201

@app.route("/api/listings/<int:link_id>", methods=["GET"])
@jwt_required()
def get_listings(link_id):
    db = Database()
    listings = db.get_listings_for_search_link(link_id)
    if not listings:
        return jsonify({"msg": f"Brak listingów dla linku {link_id}"}), 404
    return jsonify(listings), 200

@app.route("/api/run_scraper", methods=["POST"])
@jwt_required()
def run_scraper():
    """
    Ręczne uruchomienie scrapera.
    Ewentualnie możesz przekazać w JSON "link_id", aby ograniczyć do jednego.
    """
    db = Database()
    link_id = int(request.json.get("link_id", 0))
    links = db.get_search_links()
    if link_id:
        links = [l for l in links if l["id"] == link_id]
    updated = {}
    for link in links:
        app.logger.info("Scraping dla: " + link["url"])
        ads = scrape_olx(link, db)
        updated[link["id"]] = len(ads)
    return jsonify({"msg": "Scraping zakończony", "updated_links": updated}), 200

@app.route("/api/best", methods=["GET"])
@jwt_required()
def best_deals():
    deals = analyze_deals()
    if not deals:
        return jsonify({"msg": "Brak ofert do analizy"}), 404
    limit = request.args.get("limit", 10, type=int)
    return jsonify(deals[:limit]), 200

if __name__ == "__main__":
    app.run(debug="true", host="0.0.0.0", port=3001)
