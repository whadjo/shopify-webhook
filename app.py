from flask import Flask, request, jsonify
import requests
import time
from datetime import datetime, timezone, timedelta
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

def find_variant_recent(inventory_item_id, minutes=10):
    """Cherche le variant correspondant à inventory_item_id parmi les produits mis à jour récemment"""
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/products.json?limit=250&updated_at_min={since_str}"

    while url:
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        products = r.json().get("products", [])
        for product in products:
            for variant in product.get("variants", []):
                if variant.get("inventory_item_id") == inventory_item_id:
                    return variant, product.get("tags","")
        # Pagination
        if "Link" in r.headers and 'rel="next"' in r.headers["Link"]:
            url = r.headers["Link"].split(";")[0].strip("<> ")
        else:
            url = None
    return None, None

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    log(f"⚡ Webhook reçu : {data}")

    inventory_item_id = data.get("inventory_item_id")
    if not inventory_item_id:
        log("⚠️ Pas d'inventory_item_id dans la payload")
        return jsonify({"status": "ok"}), 200

    variant, tags = find_variant_recent(inventory_item_id)
    if not variant:
        log(f"⚠️ Aucun variant récent trouvé pour inventory_item_id {inventory_item_id}")
        return jsonify({"status": "ok"}), 200

    compare_at = variant.get("compare_at_price")
    qty = data.get("available")  # stock actuel envoyé par le webhook
    product_tags = [t.strip().lower() for t in tags.split(",")]

    log(f" - Variant {variant['id']} : stock={qty}, compare_at_price={compare_at}, tags={product_tags}")

    if "liquidation" in product_tags:
        log(f" ⏩ Ignoré (tag liquidation)")
    elif compare_at and qty is not None and qty <= 6:
        log(f" ⚡ Stock faible, remise à prix original")
        update_variant_price(variant['id'], compare_at)
        time.sleep(0.5)  # éviter 429
    else:
        log(f" ✅ Aucun changement nécessaire")

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    log(f"🚀 Démarrage du serveur Flask sur le port {port}")
    app.run(host="0.0.0.0", port=port)
