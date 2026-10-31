"""Generates the synthetic e-commerce dataset used by the Power BI report.

Two years (2024-2025) of an Indian online store: customers, a product catalogue, website sessions with the
purchase funnel (visit -> product view -> add to cart -> checkout -> purchase), the orders those sessions produced,
order lines and customer reviews. Patterns are built in on purpose (festive-season peaks, weekend traffic, channel
and device differences, slower delivery to the North-East, low review scores on late deliveries) so the report has
real insights to find. A fixed seed makes every run produce the same files.

Run:  python scripts/generate_data.py      (writes data/*.csv)
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)
OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)

START, END = date(2024, 1, 1), date(2025, 12, 31)
DAYS = (END - START).days + 1

# ---------------------------------------------------------------- reference data
CITIES = [  # city, state, region, weight, extra delivery days
    ("Mumbai", "Maharashtra", "West", 14, 0), ("Pune", "Maharashtra", "West", 7, 0),
    ("Ahmedabad", "Gujarat", "West", 5, 1), ("Delhi", "Delhi", "North", 14, 0),
    ("Jaipur", "Rajasthan", "North", 5, 1), ("Lucknow", "Uttar Pradesh", "North", 5, 1),
    ("Chandigarh", "Punjab", "North", 3, 1), ("Bengaluru", "Karnataka", "South", 13, 0),
    ("Chennai", "Tamil Nadu", "South", 8, 0), ("Hyderabad", "Telangana", "South", 9, 0),
    ("Vijayawada", "Andhra Pradesh", "South", 4, 1), ("Kochi", "Kerala", "South", 3, 1),
    ("Kolkata", "West Bengal", "East", 7, 1), ("Bhubaneswar", "Odisha", "East", 2, 2),
    ("Patna", "Bihar", "East", 2, 2), ("Guwahati", "Assam", "North-East", 2, 3),
]
CHANNELS = [  # channel, share of sessions, conversion multiplier
    ("Organic Search", 30, 1.0), ("Paid Search", 20, 1.15), ("Social Media", 18, 0.7),
    ("Email", 8, 1.6), ("Direct", 16, 1.25), ("Referral", 8, 0.9),
]
DEVICES = [("Mobile", 64, 0.85), ("Desktop", 28, 1.35), ("Tablet", 8, 1.0)]
PAYMENTS = [("UPI", 46), ("Credit Card", 18), ("Debit Card", 12), ("Cash on Delivery", 16), ("Net Banking", 5), ("Wallet", 3)]

CATALOGUE = {  # category: [(subcategory, [brands], price range)]
    "Electronics": [("Mobiles", ["Samsung", "Redmi", "OnePlus", "Realme"], (8000, 45000)),
                    ("Audio", ["boAt", "JBL", "Sony", "Noise"], (900, 12000)),
                    ("Accessories", ["Ambrane", "Portronics", "Mi"], (300, 3000))],
    "Fashion": [("Men's Clothing", ["Allen Solly", "Levi's", "Roadster"], (500, 3500)),
                ("Women's Clothing", ["Biba", "W", "Libas", "Zara"], (600, 4500)),
                ("Footwear", ["Bata", "Puma", "Campus", "Nike"], (700, 6500))],
    "Home & Kitchen": [("Kitchen Appliances", ["Prestige", "Philips", "Bajaj"], (900, 9000)),
                       ("Home Decor", ["HomeTown", "Urban Ladder"], (400, 5000)),
                       ("Cookware", ["Hawkins", "Pigeon", "Milton"], (300, 3500))],
    "Beauty": [("Skincare", ["Mamaearth", "Nivea", "Minimalist"], (200, 1500)),
               ("Makeup", ["Lakme", "Maybelline", "Sugar"], (250, 1800))],
    "Books": [("Fiction", ["Penguin", "HarperCollins"], (199, 699)),
              ("Exam Prep", ["Arihant", "McGraw Hill"], (299, 999))],
    "Sports": [("Fitness", ["Decathlon", "Boldfit", "Cockatoo"], (300, 8000)),
               ("Outdoor", ["Wildcraft", "Quechua"], (500, 6000))],
}
MARGIN = {"Electronics": 0.12, "Fashion": 0.45, "Home & Kitchen": 0.30, "Beauty": 0.50, "Books": 0.25, "Sports": 0.35}
FESTIVE = {10: 1.9, 11: 1.6, 3: 1.15, 8: 1.2, 12: 1.25, 1: 1.1}  # Diwali / Navratri, year-end, spring and Independence-Day sales


def pick(options):
    """Weighted choice from tuples whose second item is the weight."""
    return random.choices(options, weights=[o[1] for o in options])[0]


def write(name, header, rows):
    with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"{name}.csv: {len(rows):,} rows")


# ---------------------------------------------------------------- products
products = []
pid = 1
for category, subs in CATALOGUE.items():
    for sub, brands, (lo, hi) in subs:
        for brand in brands:
            for model in range(random.randint(2, 4)):
                price = round(random.uniform(lo, hi) / 10) * 10 - 1
                cost = round(price * (1 - MARGIN[category] * random.uniform(0.8, 1.2)), 2)
                products.append([f"P{pid:04d}", f"{brand} {sub} {chr(65 + model)}{random.randint(10, 99)}",
                                 category, sub, brand, price, cost])
                pid += 1
# cheaper products sell more often
product_weights = [1 / (p[5] ** 0.45) for p in products]

# ---------------------------------------------------------------- customers
customers = []
for i in range(1, 9001):
    city = random.choices(CITIES, weights=[c[3] for c in CITIES])[0]
    signup = START + timedelta(days=int(random.triangular(0, DAYS - 1, DAYS * 0.35)))
    customers.append([f"C{i:05d}", random.choices(["Female", "Male"], weights=[48, 52])[0],
                      random.choices(["18-24", "25-34", "35-44", "45-54", "55+"], weights=[24, 38, 21, 11, 6])[0],
                      city[0], city[1], city[2], signup.isoformat(), pick(CHANNELS)[0]])
customer_city = {c[0]: next(x for x in CITIES if x[0] == c[3]) for c in customers}
signup_of = {c[0]: date.fromisoformat(c[6]) for c in customers}
loyal = set(random.sample([c[0] for c in customers], 1400))  # repeat buyers

# ---------------------------------------------------------------- sessions, orders, items, reviews
sessions, orders, items, reviews = [], [], [], []
sid = oid = 0
for d in range(DAYS):
    day = START + timedelta(days=d)
    growth = 1 + 0.45 * d / DAYS  # the store grows over the two years
    season = FESTIVE.get(day.month, 1.0) * (1.25 if day.weekday() >= 5 else 1.0)
    for _ in range(int(random.gauss(85, 12) * growth * season)):
        sid += 1
        channel, _, ch_mult = pick(CHANNELS)
        device, _, dev_mult = pick(DEVICES)
        known = [c for c in random.sample(customers, 3) if signup_of[c[0]] <= day]
        cust = known[0][0] if known and random.random() < 0.7 else ""
        if cust in loyal:
            ch_mult *= 1.8
        conv = ch_mult * dev_mult * (1.1 if season > 1.3 else 1.0)
        viewed = random.random() < min(0.95, 0.62 * conv ** 0.3)
        carted = viewed and random.random() < min(0.9, 0.30 * conv ** 0.5)
        checkout = carted and random.random() < min(0.95, 0.58 * conv ** 0.4)
        purchased = checkout and bool(cust) and random.random() < min(0.97, 0.66 * conv ** 0.3)
        order_id = ""
        if purchased:
            oid += 1
            order_id = f"O{oid:06d}"
            city = customer_city[cust]
            promised = 4 + city[4]
            delivery = max(1, int(random.gauss(promised - 0.5, 1.6)) + (2 if season > 1.5 and random.random() < 0.3 else 0))
            payment = pick(PAYMENTS)[0]
            cancel_p = 0.09 if payment == "Cash on Delivery" else 0.035
            r = random.random()
            status = "Cancelled" if r < cancel_p else "Returned" if r < cancel_p + 0.06 else (
                "Shipped" if day > END - timedelta(days=6) else "Delivered")
            order_total = 0
            for line in range(1, random.choices([1, 2, 3, 4], weights=[62, 24, 10, 4])[0] + 1):
                p = random.choices(products, weights=product_weights)[0]
                qty = random.choices([1, 2, 3], weights=[82, 14, 4])[0]
                disc = random.choice([0, 0, 0, 5, 10, 15, 20]) + (10 if season > 1.5 else 0)
                revenue = round(p[5] * qty * (1 - disc / 100), 2)
                order_total += revenue
                items.append([order_id, line, p[0], qty, p[5], disc, revenue, round(p[6] * qty, 2)])
            shipping = 0 if order_total >= 499 else 49
            orders.append([order_id, cust, day.isoformat(), status, payment, channel, device,
                           promised, delivery if status in ("Delivered", "Returned") else "", shipping])
            if status in ("Delivered", "Returned") and random.random() < 0.55:
                late = delivery - promised
                base = 4.4 - 0.45 * max(0, late) - (1.8 if status == "Returned" else 0)
                score = max(1, min(5, round(random.gauss(base, 0.9))))
                reviews.append([order_id, score, (day + timedelta(days=delivery + random.randint(1, 6))).isoformat()])
        sessions.append([f"S{sid:07d}", day.isoformat(), cust, channel, device,
                         int(viewed), int(carted), int(checkout), int(purchased), order_id])

write("products", ["product_id", "product_name", "category", "subcategory", "brand", "unit_price", "unit_cost"], products)
write("customers", ["customer_id", "gender", "age_group", "city", "state", "region", "signup_date", "acquisition_channel"], customers)
write("sessions", ["session_id", "session_date", "customer_id", "channel", "device", "product_view", "add_to_cart",
                   "checkout", "purchase", "order_id"], sessions)
write("orders", ["order_id", "customer_id", "order_date", "order_status", "payment_method", "channel", "device",
                 "promised_days", "delivery_days", "shipping_fee"], orders)
write("order_items", ["order_id", "line_number", "product_id", "quantity", "unit_price", "discount_pct",
                      "line_revenue", "line_cost"], items)
write("reviews", ["order_id", "review_score", "review_date"], reviews)
