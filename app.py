from flask import Flask, request, jsonify
import requests
import time
from datetime import datetime, timezone
import os

app = Flask(__name__)

SHOPIFY_STORE = os.getenv("SHOP_URL")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
API_VERSION = "2025-01"
HEADERS = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

def log(msg):
    """Affiche un log avec timestamp"""
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}")

def update_variant_price(variant_id, new_price):
    url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/variants/{variant_id}.json"
    payload = {
        "variant": {
            "id": variant_id,
            "price": new_price,
            "compare_at_price": None
        }
    }
    r = requests.put(url, headers=HEADERS, json=payload)
    r.raise_for_status()
    log(f"✅ Prix mis à jour pour variant {variant_id} → {new_price}")

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    log(f"⚡ Webhook reçu : {data}")
    log(f"⚡ Webhook reçu : {data.get('title', 'Produit inconnu')}")

    if "variants" in data:
        for variant in data["variants"]:
            compare_at = variant.get("compare_at_price")
            qty = variant.get("inventory_quantity")
            product_tags = [t.strip().lower() for t in data.get("tags","").split(",")]

            log(f" - Variant {variant['id']} : stock={qty}, compare_at_price={compare_at}, tags={product_tags}")

            if "liquidation" in product_tags:
                log(f" ⏩ Ignoré (tag liquidation)")
                continue

            if compare_at and qty is not None and qty <= 6:
                log(f" ⚡ Stock faible, remise à prix original")
                update_variant_price(variant["id"], compare_at)
                time.sleep(0.5)  # éviter 429
            else:
                log(f" ✅ Aucun changement nécessaire")
    else:
        log(" ⚠️ Pas de variants dans la payload")

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    log("🚀 Démarrage du serveur Flask")
    app.run(host="0.0.0.0", port=5000)
