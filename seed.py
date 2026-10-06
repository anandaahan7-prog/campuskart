"""
Creates a fresh campuskart.db with demo data.

    python seed.py

Run this before your presentation to reset everything to a clean demo state.
All demo accounts and passwords are listed in README.md.
"""

import os
import random
import sqlite3

from werkzeug.security import generate_password_hash

from ai.spam_detector import check_listing

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "campuskart.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

ADMIN_PASSWORD = "admin123"
DEMO_PASSWORD = "demo123"

CATEGORIES = [
    ("Books", "📚"), ("Electronics", "💻"), ("Calculators", "🧮"),
    ("Drawing Instruments", "📐"), ("Lab Equipment", "🥼"), ("Hostel Essentials", "🛏️"),
    ("Cycles", "🚲"), ("Sports", "🏏"), ("Clothing", "👕"),
]

# (email, name, role, branch, year, phone)
USERS = [
    ("admin@campuskart.com", "Admin", "admin", None, None, None),
    # --- demo students with search history (show these to your professor) ---
    ("rahul@college.edu", "Rahul Sharma", "user", "Computer Science", 3, "9800000001"),
    ("priya@college.edu", "Priya Patel", "user", "Mechanical", 2, "9800000002"),
    ("karan@college.edu", "Karan Mehta", "user", "Electronics", 3, "9800000003"),
    ("aisha@college.edu", "Aisha Khan", "user", "Information Technology", 1, "9800000004"),
    ("neha@college.edu", "Neha Gupta", "user", "Civil", 1, "9800000005"),   # brand-new user
    # --- sellers who own most listings ---
    ("vikram@college.edu", "Vikram Singh", "user", "Computer Science", 4, "9800000006"),
    ("sneha@college.edu", "Sneha Reddy", "user", "Electronics", 4, "9800000007"),
    ("arjun@college.edu", "Arjun Nair", "user", "Mechanical", 4, "9800000008"),
    ("meera@college.edu", "Meera Joshi", "user", "Information Technology", 3, "9800000009"),
    ("rohan@college.edu", "Rohan Das", "user", "Civil", 2, "9800000010"),
    ("ravi@college.edu", "Ravi Kumar", "user", "Civil", 1, "9800000011"),   # posts spam
]

# key, seller, category, title, description, original_price, price, condition, age_months, days_ago
PRODUCTS = [
    # Books
    ("korth", "vikram", "Books", "Database System Concepts - Korth (6th Ed)",
     "Standard DBMS textbook by Korth, Silberschatz and Sudarshan. Some pencil highlights, all pages intact.", 950, 450, "Good", 24, 3),
    ("galvin", "vikram", "Books", "Operating System Concepts - Galvin",
     "Galvin OS book, 9th edition. Covers processes, scheduling, memory management. Good condition.", 850, 420, "Good", 20, 5),
    ("ds", "meera", "Books", "Data Structures Using C - Reema Thareja",
     "Data structures book with solved examples on linked lists, trees and graphs. Almost new.", 550, 340, "Like New", 12, 2),
    ("python", "meera", "Books", "Let Us Python - Yashavant Kanetkar",
     "Beginner friendly Python programming book. No markings.", 450, 290, "Like New", 8, 6),
    ("cn", "vikram", "Books", "Computer Networks - Tanenbaum",
     "Computer networks textbook, 5th edition. Cover slightly worn.", 900, 400, "Good", 30, 12),
    ("grewal", "arjun", "Books", "Higher Engineering Mathematics - B S Grewal",
     "Maths for all engineering branches. Useful for M1, M2, M3.", 1100, 520, "Good", 24, 8),
    ("nag", "arjun", "Books", "Engineering Thermodynamics - P K Nag",
     "Thermodynamics textbook for mechanical students, with steam tables.", 750, 380, "Good", 18, 4),
    ("bansal", "arjun", "Books", "Strength of Materials - R K Bansal",
     "SOM textbook, some pages folded, fully readable.", 700, 260, "Fair", 30, 20),
    ("boylestad", "sneha", "Books", "Electronic Devices and Circuit Theory - Boylestad",
     "EDC textbook for electronics branch, diodes, BJT, FET, op-amps.", 800, 420, "Good", 20, 9),
    ("oppenheim", "sneha", "Books", "Signals and Systems - Oppenheim",
     "Signals and systems book, clean copy.", 900, 520, "Like New", 12, 11),
    ("dbmsnotes", "meera", "Books", "DBMS and SQL handwritten notes + previous year papers",
     "Complete DBMS notes: ER model, normalization, SQL queries, transactions. With PYQs.", 300, 150, "Good", 6, 1),
    ("bhatt", "arjun", "Books", "Engineering Drawing - N D Bhatt",
     "Engineering drawing book for first year, projections and isometric views.", 600, 320, "Good", 14, 7),
    ("java", "vikram", "Books", "Head First Java (2nd Ed)",
     "Fun way to learn Java and OOP concepts.", 1200, 700, "Like New", 10, 25),

    # Electronics
    ("laptop", "vikram", "Electronics", "Dell Inspiron 15 Laptop - i5, 8GB RAM, 512GB SSD",
     "Dell laptop, 10th gen i5, 8GB RAM, SSD. Battery backup 3 hours. Charger included.", 52000, 26000, "Good", 30, 2),
    ("mouse", "meera", "Electronics", "Logitech M235 Wireless Mouse",
     "Wireless mouse with USB receiver, smooth tracking.", 900, 480, "Like New", 10, 3),
    ("keyboard", "vikram", "Electronics", "Cosmic Byte Mechanical Keyboard (RGB)",
     "Mechanical keyboard with blue switches and RGB lights. Great for coding.", 2200, 1250, "Like New", 8, 4),
    ("arduino", "sneha", "Electronics", "Arduino Uno R3 with USB Cable",
     "Arduino Uno microcontroller board, used in one mini project. Works perfectly.", 750, 470, "Like New", 6, 1),
    ("rpi", "sneha", "Electronics", "Raspberry Pi 4 (2GB) with Case and Adapter",
     "Raspberry Pi 4 model B, official case and 5V power adapter.", 4500, 3100, "Like New", 10, 6),
    ("multimeter", "sneha", "Electronics", "Digital Multimeter DT830D",
     "Multimeter for electronics lab, measures voltage, current, resistance. With probes.", 450, 250, "Good", 12, 8),
    ("solder", "sneha", "Electronics", "Soldering Iron Kit 60W with Stand",
     "Soldering iron with stand, solder wire and flux. For circuits and projects.", 650, 350, "Good", 14, 10),
    ("breadboard", "sneha", "Electronics", "Breadboard + Jumper Wires Kit",
     "Full size breadboard with 65 jumper wires for circuits lab.", 350, 190, "Good", 8, 13),
    ("headphones", "rohan", "Electronics", "boAt Rockerz 450 Bluetooth Headphones",
     "Wireless headphones, 15 hours battery.", 1500, 700, "Good", 18, 15),
    ("powerbank", "meera", "Electronics", "Mi Power Bank 10000 mAh",
     "Power bank with fast charging, comes with cable.", 1200, 600, "Good", 18, 16),
    ("pendrive", "rohan", "Electronics", "SanDisk 64GB USB Pen Drive",
     "64GB USB 3.0 pen drive.", 600, 360, "Like New", 6, 9),

    # Calculators
    ("fx991es", "arjun", "Calculators", "Casio fx-991ES Plus Scientific Calculator",
     "Scientific calculator allowed in university exams. Used for 2 semesters.", 1150, 650, "Good", 20, 3),
    ("fx82", "meera", "Calculators", "Casio fx-82MS Scientific Calculator",
     "Basic scientific calculator, works fine.", 650, 330, "Good", 24, 14),
    ("classwiz", "vikram", "Calculators", "Casio fx-991EX Classwiz Calculator",
     "Advanced scientific calculator with spreadsheet mode.", 1600, 1150, "Like New", 6, 22),

    # Drawing Instruments
    ("drafter", "arjun", "Drawing Instruments", "Omega Mini Drafter",
     "Mini drafter for engineering drawing, all scales and screws included.", 700, 400, "Good", 12, 2),
    ("board", "arjun", "Drawing Instruments", "Drawing Board A1 Size with Clips",
     "Wooden drawing board A1 for engineering graphics.", 600, 300, "Good", 18, 5),
    ("drawkit", "rohan", "Drawing Instruments", "Engineering Drawing Kit (Compass, Set Squares, Scale)",
     "Complete geometry and drawing instrument kit.", 400, 210, "Good", 12, 10),
    ("roller", "priya", "Drawing Instruments", "Roller Scale and Protractor Set",
     "Roller scale for parallel lines plus protractor.", 250, 110, "Fair", 24, 18),

    # Lab Equipment
    ("coatm", "meera", "Lab Equipment", "Chemistry Lab Coat (Size M)",
     "White cotton lab coat, washed and clean.", 450, 220, "Good", 12, 4),
    ("coatl", "rohan", "Lab Equipment", "Lab Coat (Size L)",
     "Lab coat, used only for one semester.", 450, 270, "Like New", 6, 7),
    ("goggles", "sneha", "Lab Equipment", "Safety Goggles for Lab",
     "Clear safety goggles, scratch free.", 200, 110, "Good", 10, 12),
    ("apron", "arjun", "Lab Equipment", "Workshop Apron and Gloves",
     "Heavy apron and gloves for workshop practicals.", 350, 140, "Fair", 18, 17),

    # Hostel Essentials
    ("mattress", "arjun", "Hostel Essentials", "Single Bed Mattress (4 inch)",
     "Clean foam mattress for hostel bed. Leaving hostel so selling.", 2500, 1100, "Good", 24, 1),
    ("kettle", "meera", "Hostel Essentials", "Prestige Electric Kettle 1.5L",
     "Electric kettle for tea, coffee and maggi in hostel.", 1100, 560, "Good", 14, 3),
    ("lamp", "vikram", "Hostel Essentials", "LED Study Table Lamp",
     "Table lamp with 3 brightness levels, USB charging.", 800, 470, "Like New", 6, 6),
    ("bucket", "rohan", "Hostel Essentials", "Bucket and Mug Set",
     "Plastic bucket and mug for hostel bathroom.", 350, 160, "Good", 12, 8),
    ("bedsheet", "meera", "Hostel Essentials", "Pillow and Bedsheet Set",
     "Single bedsheet with pillow and cover.", 900, 420, "Good", 12, 11),
    ("extension", "karan", "Hostel Essentials", "Extension Board 4 Socket",
     "Extension board with surge protection and 2m wire.", 500, 260, "Good", 12, 5),
    ("stand", "rohan", "Hostel Essentials", "Clothes Drying Stand",
     "Foldable steel drying stand.", 1200, 600, "Good", 18, 19),

    # Cycles
    ("hero", "arjun", "Cycles", "Hero Sprint 26T Cycle with Lock",
     "Hero bicycle, new tyres last month, lock and basket included.", 7500, 3400, "Good", 24, 2),
    ("btwin", "vikram", "Cycles", "Btwin Rockrider Gear Cycle",
     "Geared bicycle, 7 speed, very smooth ride.", 12000, 7000, "Like New", 14, 9),
    ("cyclelock", "rohan", "Cycles", "Cycle Lock with 2 Keys",
     "Strong cable lock for bicycle.", 400, 190, "Good", 12, 14),

    # Sports
    ("bat", "rohan", "Sports", "SG Cricket Bat (English Willow)",
     "English willow bat with cover, light use.", 3500, 1800, "Good", 18, 6),
    ("racket", "meera", "Sports", "Yonex Badminton Racket (Pair)",
     "Two badminton rackets with cover and shuttle box.", 2200, 1150, "Good", 14, 10),
    ("football", "rohan", "Sports", "Nivia Football Size 5",
     "Football, good grip.", 900, 460, "Good", 10, 15),
    ("yoga", "priya", "Sports", "Yoga Mat 6mm",
     "Anti-slip yoga mat with carry strap.", 600, 330, "Like New", 6, 7),

    # Clothing
    ("blazer", "vikram", "Clothing", "Formal Blazer Size 40",
     "Navy blue blazer, worn twice for placement interviews.", 3500, 1700, "Like New", 12, 4),
    ("shoes", "arjun", "Clothing", "Formal Shoes Size 9",
     "Black formal shoes for interviews and presentations.", 2500, 1150, "Good", 12, 8),
    ("hoodie", "meera", "Clothing", "College Fest Hoodie (Size L)",
     "Official college fest hoodie.", 1200, 520, "Good", 12, 13),

    # Extra items that get sold in the seed (for sales stats & reviews)
    ("earphones", "rohan", "Electronics", "Sony Wired Earphones",
     "Sony earphones with mic.", 1500, 700, "Good", 12, 26),
    ("labmanual", "meera", "Books", "Physics Lab Manual + Record",
     "Completed physics lab manual for reference.", 300, 130, "Good", 12, 24),
    ("cooler", "arjun", "Hostel Essentials", "Small Room Cooler",
     "Personal air cooler for hostel room.", 5000, 2500, "Good", 24, 28),
    ("fx991ms", "meera", "Calculators", "Casio fx-991MS Calculator",
     "Older scientific calculator model, fully working.", 900, 450, "Good", 30, 27),
]

# Listings posted by the "spam" account -> go through the AI spam detector.
SPAM_PRODUCTS = [
    ("ravi", "Electronics", "iPhone 14 Pro only Rs 3000 urgent sale!!!",
     "Brand new iPhone, pay advance on gpay and get delivery. Whatsapp 9876543210 now, limited offer.",
     80000, 3000, "New", 0),
    ("ravi", "Books", "Upcoming semester exam answers - guaranteed pass",
     "Selling answers of upcoming semester exam paper. Join telegram, pay now.",
     500, 499, "New", 0),
]

# Search history: user -> [(query, hours_ago)]
SEARCHES = {
    "rahul": [("dbms book", 2), ("python", 5), ("operating system", 26),
              ("mechanical keyboard", 30), ("data structures", 50), ("laptop", 72)],
    "priya": [("engineering drawing", 1), ("mini drafter", 3), ("scientific calculator", 20),
              ("thermodynamics", 28), ("drawing board", 48)],
    "karan": [("arduino", 1), ("multimeter", 4), ("raspberry pi", 22),
              ("soldering", 30), ("breadboard", 40)],
    "aisha": [("cycle", 2), ("mattress", 6), ("kettle", 24), ("table lamp", 30), ("bucket", 50)],
}

# Product views: user -> [(product_key, hours_ago)]
VIEWS = {
    "rahul": [("korth", 2), ("ds", 6), ("keyboard", 31)],
    "priya": [("drafter", 3), ("fx991es", 21), ("nag", 29)],
    "karan": [("arduino", 1), ("multimeter", 5)],
    "aisha": [("hero", 2), ("kettle", 25)],
}

WISHLIST = {
    "rahul": ["laptop"],
    "priya": ["grewal"],
    "karan": ["rpi"],
    "aisha": ["mattress"],
}

# Completed / placed / cancelled orders: (product_key, buyer, final_status, rating, comment)
ORDERS = [
    ("java", "rahul", "completed", 5, "Book was exactly as described. Smooth deal!"),
    ("classwiz", "priya", "completed", 4, "Calculator works great, seller was on time."),
    ("earphones", "karan", "completed", 4, "Good sound, minor scratches."),
    ("labmanual", "aisha", "placed", None, None),
    ("cooler", "rahul", "completed", 3, "Works fine but a bit noisy."),
    ("fx991ms", "karan", "completed", 5, "Very helpful senior, thanks!"),
    ("bedsheet", "priya", "cancelled", None, None),
]


def ago(unit_value, unit):
    return f"-{unit_value} {unit}"


def seed(db_path=DB_PATH):
    if os.path.exists(db_path):
        os.remove(db_path)

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        db.executescript(f.read())

    # Categories
    db.executemany("INSERT INTO categories (name, icon) VALUES (?, ?)", CATEGORIES)
    cat_id = {r["name"]: r["category_id"] for r in db.execute("SELECT * FROM categories")}

    # Users
    user_id = {}
    for email, name, role, branch, year, phone in USERS:
        pw = ADMIN_PASSWORD if role == "admin" else DEMO_PASSWORD
        cur = db.execute(
            """INSERT INTO users (name, email, password_hash, role, branch, year, phone, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime', '-40 days'))""",
            (name, email, generate_password_hash(pw), role, branch, year, phone),
        )
        user_id[email.split("@")[0]] = cur.lastrowid

    # Products
    product_id = {}
    for key, seller, cat, title, desc, orig, price, cond, age, days in PRODUCTS:
        cur = db.execute(
            """INSERT INTO products (seller_id, category_id, title, description, original_price,
                                     price, condition, age_months, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime', ?))""",
            (user_id[seller], cat_id[cat], title, desc, orig, price, cond, age, ago(days, "days")),
        )
        product_id[key] = cur.lastrowid

    # Spam listings checked by the real AI model (trigger notifies the admin)
    for seller, cat, title, desc, orig, price, cond, age in SPAM_PRODUCTS:
        result = check_listing(title, desc, price, orig)
        db.execute(
            """INSERT INTO products (seller_id, category_id, title, description, original_price,
                                     price, condition, age_months, status, is_flagged,
                                     spam_score, flag_reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id[seller], cat_id[cat], title, desc, orig, price, cond, age,
             "pending" if result["is_spam"] else "available", int(result["is_spam"]),
             result["score"], "; ".join(result["reasons"])),
        )

    # Orders (triggers mark products sold and create notifications)
    for i, (pkey, buyer, status, rating, comment) in enumerate(ORDERS):
        price = db.execute("SELECT price FROM products WHERE product_id = ?",
                           (product_id[pkey],)).fetchone()["price"]
        cur = db.execute(
            """INSERT INTO orders (product_id, buyer_id, price, ordered_at)
               VALUES (?, ?, ?, datetime('now', 'localtime', ?))""",
            (product_id[pkey], user_id[buyer], price, ago(20 - i * 2, "days")),
        )
        if status != "placed":
            db.execute("UPDATE orders SET status = ? WHERE order_id = ?", (status, cur.lastrowid))
        if rating:
            db.execute("INSERT INTO reviews (order_id, rating, comment) VALUES (?, ?, ?)",
                       (cur.lastrowid, rating, comment))

    # Search history, views and wishlist for demo users
    for user, searches in SEARCHES.items():
        for query, hours in searches:
            db.execute(
                """INSERT INTO search_history (user_id, query, searched_at)
                   VALUES (?, ?, datetime('now', 'localtime', ?))""",
                (user_id[user], query, ago(hours, "hours")),
            )
    for user, views in VIEWS.items():
        for pkey, hours in views:
            db.execute(
                """INSERT INTO product_views (user_id, product_id, viewed_at)
                   VALUES (?, ?, datetime('now', 'localtime', ?))""",
                (user_id[user], product_id[pkey], ago(hours, "hours")),
            )
    for user, keys in WISHLIST.items():
        for pkey in keys:
            db.execute("INSERT INTO wishlist (user_id, product_id) VALUES (?, ?)",
                       (user_id[user], product_id[pkey]))

    # Random background views from sellers -> powers "Trending on campus"
    random.seed(7)
    viewers = ["vikram", "sneha", "arjun", "meera", "rohan"]
    popular = ["laptop", "hero", "fx991es", "mattress", "arduino", "korth", "btwin", "keyboard"]
    for _ in range(60):
        pkey = random.choice(popular + list(product_id))
        db.execute(
            """INSERT INTO product_views (user_id, product_id, viewed_at)
               VALUES (?, ?, datetime('now', 'localtime', ?))""",
            (user_id[random.choice(viewers)], product_id[pkey], ago(random.randint(1, 600), "hours")),
        )

    # Welcome notification for everyone
    db.execute("""INSERT INTO notifications (user_id, message)
                  SELECT user_id, 'Welcome to CampusKart! Buy and sell within your campus.' FROM users""")

    db.commit()
    counts = {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ["users", "categories", "products", "orders", "reviews", "wishlist",
                        "search_history", "product_views", "notifications"]}
    db.close()
    return counts


if __name__ == "__main__":
    for table, n in seed().items():
        print(f"{table:<15} {n:>4} rows")
    print("\nDatabase created: campuskart.db")
