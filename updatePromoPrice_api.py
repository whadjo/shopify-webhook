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
    print(f"✅ Prix mis à jour pour variant {variant_id} → {new_price}")
    
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    # Shopify peut envoyer soit un "inventory item", soit un produit/variant
    # On gère les variantes
    if "variants" in data:
        for variant in data["variants"]:
            compare_at = variant.get("compare_at_price")
            qty = variant.get("inventory_quantity")
            product_tags = [t.strip().lower() for t in data.get("tags","").split(",")]

            # Ignorer liquidation
            if "liquidation" in product_tags:
                continue

            if compare_at and qty is not None and qty <= 6:
                update_variant_price(variant["id"], compare_at)
                time.sleep(0.5)  # éviter 429
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
