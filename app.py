from flask import Flask, render_template, request, redirect, url_for, session
from markupsafe import escape
from datetime import datetime

app = Flask(__name__)
app.secret_key = "change-this-secret-key"  # TODO: ganti dengan key rahasia Anda

WHATSAPP_NUMBER = "6281234567890"  # TODO: ganti dengan nomor WA bisnis (tanpa +)

PRODUCTS = [
    {
        "id": "arabica-gayo",
        "name": "Arabica Gayo",
        "origin": "Aceh Tengah",
        "roast": "Medium",
        "price": 120_000,  # base price for 250g
        "weights": [250, 500, 1000],
        "tasting": ["Cokelat", "Caramel", "Citrus"],
        "image": "https://images.unsplash.com/photo-1517705008128-361805f42e86?q=80&w=1200&auto=format&fit=crop",
        "description": "Single origin body medium, acidity seimbang. Cocok untuk pour over & espresso."
    },
    {
        "id": "robusta-lampung",
        "name": "Robusta Lampung",
        "origin": "Lampung Barat",
        "roast": "Medium-Dark",
        "price": 85_000,
        "weights": [250, 500, 1000],
        "tasting": ["Kakao", "Spice", "Nutty"],
        "image": "https://images.unsplash.com/photo-1447933601403-0c6688de566e?q=80&w=1200&auto=format&fit=crop",
        "description": "Bold & pahit nikmat, crema tebal. Ideal untuk kopi susu & tubruk."
    },
    {
        "id": "house-blend",
        "name": "House Blend 70/30",
        "origin": "Blend (Arabica/Robusta)",
        "roast": "Medium",
        "price": 99_000,
        "weights": [250, 500, 1000],
        "tasting": ["Caramel", "Toffee", "Dark Chocolate"],
        "image": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?q=80&w=1200&auto=format&fit=crop",
        "description": "Racikan andalan seimbang: wangi arabica, body robusta — ramah untuk semua metode."
    },
    {
        "id": "toraja-arabica",
        "name": "Toraja Arabica",
        "origin": "Tana Toraja",
        "roast": "Light-Medium",
        "price": 135_000,
        "weights": [250, 500, 1000],
        "tasting": ["Floral", "Herbal", "Stonefruit"],
        "image": "https://images.unsplash.com/photo-1432107294469-414527cb5c65?q=80&w=1200&auto=format&fit=crop",
        "description": "Profil kompleks, aroma floral & aftertaste bersih."
    }
]

def weight_price(base, grams):
    if grams == 250: return base
    if grams == 500: return round(base * 1.9)
    if grams == 1000: return round(base * 3.6)
    return base

def cart_total(cart):
    return sum(weight_price(item["price"], item["weight"]) * item["qty"] for item in cart)

@app.context_processor
def inject_globals():
    return {"now_year": datetime.now().year, "format_idr": lambda n: f"Rp{n:,.0f}".replace(",",".")}

@app.route("/")
def index():
    q = (request.args.get("q") or "").lower()
    roast = request.args.get("roast") or "Semua"
    origin = request.args.get("origin") or "Semua"
    sort = request.args.get("sort") or "popular"

    products = PRODUCTS.copy()
    if q:
        def match(p):
            blob = " ".join([p["name"], p["origin"], p["roast"], " ".join(p["tasting"]), p["description"]]).lower()
            return q in blob
        products = [p for p in products if match(p)]
    if roast != "Semua":
        products = [p for p in products if roast.lower() in p["roast"].lower()]
    if origin != "Semua":
        products = [p for p in products if p["origin"] == origin]

    if sort == "price-asc":
        products.sort(key=lambda p: p["price"])
    elif sort == "price-desc":
        products.sort(key=lambda p: -p["price"])
    elif sort == "name":
        products.sort(key=lambda p: p["name"])

    # origins list for filter
    origins = ["Semua"] + sorted(list({p["origin"] for p in PRODUCTS}))

    cart = session.get("cart", [])
    return render_template("index.html", products=products, origins=origins, q=q, roast=roast, origin=origin, sort=sort, cart_count=sum(i["qty"] for i in cart))

@app.post("/add")
def add_to_cart():
    product_id = request.form.get("product_id")
    weight = int(request.form.get("weight", "250"))
    qty = max(1, int(request.form.get("qty", "1")))
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        return redirect(url_for("index"))
    cart = session.get("cart", [])
    # merge same product+weight
    for item in cart:
        if item["id"] == product_id and item["weight"] == weight:
            item["qty"] += qty
            break
    else:
        cart.append({
            "id": product["id"],
            "name": product["name"],
            "roast": product["roast"],
            "weight": weight,
            "qty": qty,
            "price": product["price"],
            "image": product["image"]
        })
    session["cart"] = cart
    session.modified = True
    return redirect(url_for("cart"))

@app.get("/cart")
def cart():
    cart = session.get("cart", [])
    total = cart_total(cart)
    return render_template("cart.html", cart=cart, total=total)

@app.post("/cart/update")
def cart_update():
    cart = session.get("cart", [])
    for idx, item in enumerate(cart):
        field = f"qty_{idx}"
        if field in request.form:
            try:
                qty = max(0, int(request.form.get(field, "1")))
            except ValueError:
                qty = 1
            if qty == 0:
                continue
            item["qty"] = qty
    # remove zero qty
    cart = [i for i in cart if i["qty"] > 0]
    session["cart"] = cart
    session.modified = True
    return redirect(url_for("cart"))

@app.post("/cart/remove")
def cart_remove():
    idx = int(request.form.get("idx", "-1"))
    cart = session.get("cart", [])
    if 0 <= idx < len(cart):
        del cart[idx]
    session["cart"] = cart
    session.modified = True
    return redirect(url_for("cart"))

@app.post("/checkout")
def checkout():
    buyer = request.form.get("buyer","").strip()
    notes = request.form.get("notes","").strip()
    cart = session.get("cart", [])
    if not cart:
        return redirect(url_for("index"))
    lines = ["Halo, saya ingin pesan kopi:"]
    for it in cart:
        subtotal = weight_price(it["price"], it["weight"]) * it["qty"]
        lines.append(f"• {it['name']} {it['weight']}g x{it['qty']} — Rp{subtotal:,.0f}".replace(",", "."))
    total = cart_total(cart)
    lines.append(f"Total: Rp{total:,.0f}".replace(",", "."))
    if buyer:
        lines.append(f"Nama: {buyer}")
    if notes:
        lines.append(f"Catatan: {notes}")
    lines.append("Metode: COD/Transfer (sebutkan preferensi)")
    msg = "%0A".join(lines)
    wa_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={msg}"
    # Optionally, clear cart after redirect by choice; we keep it until user clears
    return redirect(wa_url)

@app.post("/cart/clear")
def cart_clear():
    session["cart"] = []
    session.modified = True
    return redirect(url_for("cart"))

if __name__ == "__main__":
    app.run(debug=True)
