"""
Smoke tests: python test_app.py
Re-creates the demo database, then walks through every page and the main flows.
Run `python seed.py` again afterwards if you want untouched demo data.
"""

import sqlite3

from app import app
from seed import DB_PATH, seed


def login(client, email, password="demo123"):
    client.get("/logout")
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)


def check(resp, *texts, status=200):
    assert resp.status_code == status, f"{resp.request.path}: got {resp.status_code}"
    body = resp.get_data(as_text=True)
    for t in texts:
        assert t in body, f"{resp.request.path}: missing {t!r}"
    return body


def main():
    seed()
    app.config["TESTING"] = True
    c = app.test_client()

    # Guest pages
    check(c.get("/"), "Trending on campus")
    check(c.get("/login"), "Demo accounts")
    check(c.get("/search?q=calculator"), "Casio")
    check(c.get("/product/1"), "Log in to buy")
    check(c.get("/sell", follow_redirects=True), "Log in to continue")

    # Rahul: personalised recommendations
    check(login(c, "rahul@college.edu"), "Pinned for you, Rahul", "Because you searched", "Open offers")
    check(c.get("/search?q=arduno"), "Did you mean")       # typo -> AI fallback
    check(c.get("/product/1"), "Similar items", "Our price model estimates")
    check(c.get("/orders"), "Head First Java")
    check(c.get("/orders?tab=sales"))
    check(c.get("/wishlist"), "Dell Inspiron")
    check(c.get("/profile"), "Search history", "dbms book")
    check(c.get("/notifications"), "Welcome to CampusKart")
    check(c.get("/my-listings"))
    check(c.get("/admin"), status=403)

    # AI APIs
    r = c.post("/api/predict-price", json={"original_price": 1000, "condition": "Good",
                                           "age_months": 12, "category_id": 1})
    assert r.status_code == 200 and r.json["suggested"] > 0, r.json
    r = c.post("/api/spam-check", json={"title": "Earn money fast", "description": "whatsapp 9876543210",
                                        "price": 100, "original_price": 1000})
    assert r.json["is_spam"], r.json

    # Sell a normal item and a spam item
    item = {"title": "Casio fx-991ES calculator", "description": "Used for one year, works fine",
            "category_id": 3, "condition": "Good", "original_price": 1200, "age_months": 12, "price": 650}
    check(c.post("/sell", data=item, follow_redirects=True), "Your item is live")
    spam = dict(item, title="Free iPhone giveaway", description="click link and pay advance on gpay")
    check(c.post("/sell", data=spam, follow_redirects=True), "flagged")

    # Buy an item (trigger marks it sold), buying again must fail (trigger aborts)
    check(c.post("/buy/2", follow_redirects=True), "Order placed", "Your tab: call", "tear-now")   # lands on the slip
    check(login(c, "priya@college.edu"), "Pinned for you, Priya", "Reply to the counter")         # the one finding
    check(c.post("/buy/2", follow_redirects=True), "no longer available")

    # Rahul completes and reviews the order
    login(c, "rahul@college.edu")
    db = sqlite3.connect(DB_PATH)
    oid = db.execute("SELECT MAX(order_id) FROM orders").fetchone()[0]
    check(c.post(f"/orders/{oid}/complete", follow_redirects=True), "Mark")
    check(c.post(f"/orders/{oid}/review", data={"rating": 5, "comment": "great"}, follow_redirects=True),
          "Thanks for your review")

    # Neha: new user -> cold start
    check(login(c, "aisha@college.edu"), "Price drop", "on your wishlist dropped to")
    check(login(c, "neha@college.edu"), "Trending on campus")

    # ---- New features -------------------------------------------------------
    pid_of = lambda title: db.execute("SELECT product_id FROM products WHERE title LIKE ?",
                                      (title + "%",)).fetchone()[0]
    arduino, korth, lamp = pid_of("Arduino Uno"), pid_of("Database System Concepts"), pid_of("LED Study")

    # "Also viewed" (collaborative filtering) on the product page
    check(c.get(f"/product/{arduino}"), "Students who viewed this also viewed", "of the same student")

    # Offers: validation trigger rejects an offer at or above the asking price
    check(c.post(f"/offer/{lamp}", data={"amount": 99999}, follow_redirects=True), "Offer less than the asking price")
    check(c.post(f"/offer/{lamp}", data={"amount": 400, "message": "ok?"}, follow_redirects=True), "Offer of ₹400 sent")
    check(c.post(f"/offer/{lamp}", data={"amount": 390}, follow_redirects=True), "already have an open offer")
    neha_offer = db.execute("SELECT offer_id FROM offers WHERE product_id = ? AND status = 'pending'",
                            (lamp,)).fetchone()[0]

    # Seller (Vikram) counters, Neha accepts the counter -> order created at the counter price
    check(login(c, "vikram@college.edu"), "Pinned for you, Vikram", "Review offers")
    check(c.get("/orders?tab=offers"), "Offers on your items", "Neha Gupta", "Rahul Sharma")
    check(c.post(f"/offers/{neha_offer}/counter", data={"counter_amount": 10}, follow_redirects=True), "Counter with an amount")
    check(c.post(f"/offers/{neha_offer}/counter", data={"counter_amount": 440}, follow_redirects=True), "Counter-offer sent")
    check(login(c, "neha@college.edu"), "Pinned for you, Neha")
    check(c.get(f"/product/{lamp}"), "countered at ₹440")
    check(c.post(f"/offers/{neha_offer}/accept_counter", follow_redirects=True), "Deal done at ₹440")
    order = db.execute("SELECT price, status FROM orders WHERE product_id = ? ORDER BY order_id DESC", (lamp,)).fetchone()
    assert order == (440.0, "placed"), order

    # Seller accepts Rahul's seeded offer on Korth -> order at the offered price
    login(c, "vikram@college.edu")
    rahul_offer = db.execute("SELECT offer_id FROM offers WHERE product_id = ? AND status = 'pending'",
                             (korth,)).fetchone()[0]
    check(c.post(f"/offers/{rahul_offer}/accept", follow_redirects=True), "Deal done at ₹380")
    assert db.execute("SELECT status FROM products WHERE product_id = ?", (korth,)).fetchone()[0] == "sold"
    check(c.post(f"/offers/{rahul_offer}/accept", follow_redirects=True), "already changed")   # state machine

    # Price drop: Vikram lowers the laptop price -> Rahul (wishlisted it) is notified, audit records it
    laptop = pid_of("Dell Inspiron")
    form = {"title": "Dell Inspiron 15 Laptop - i5, 8GB RAM, 512GB SSD", "description": "Dell laptop, charger included.",
            "category_id": 2, "condition": "Good", "original_price": 52000, "age_months": 30, "price": 24000}
    check(c.post(f"/listing/{laptop}/edit", data=form, follow_redirects=True), "Listing updated")
    check(login(c, "rahul@college.edu"), "Pinned for you, Rahul", "dropped to ₹24,000")
    check(c.get("/notifications"), "Price drop", "now Rs. 24000")
    check(c.get(f"/product/{laptop}"), "Price dropped from")
    who = db.execute("""SELECT u.name FROM audit_log a JOIN users u ON u.user_id = a.changed_by
                        WHERE a.field = 'price' AND a.row_id = ? ORDER BY audit_id DESC""", (laptop,)).fetchone()[0]
    assert who == "Vikram Singh", who

    # Admin
    check(login(c, "admin@campuskart.com", "admin123"), "Admin dashboard", "Sales by category")
    check(c.get("/admin/listings"), "Flagged by AI", "iPhone 14 Pro")
    check(c.get("/admin/users"), "Rahul Sharma")
    check(c.get("/admin/orders"), "Head First Java")
    # Data lookup: name search, student profile, item profile, reports, schema browser
    check(c.get("/admin/database", follow_redirects=True), "trg_order_validate", "v_seller_ratings")
    check(c.get("/admin/lookup?q=rahul", follow_redirects=True), "Rahul Sharma", "Search history",
          "Offers made", "Show SQL", "dbms book")
    check(c.get("/admin/lookup?q=a"), "Students", "Items")                     # many matches -> list
    check(c.get("/admin/lookup?product=1"), "Price and status history", "Offers", "Viewed by")
    check(c.get("/admin/lookup?report=price_rank"), "Window function", "RANK() OVER")
    check(c.get("/admin/lookup?report=leaderboard"), "CTE + view")
    check(c.get("/admin/audit"), "Audit log", "trg_audit_product_price")
    check(c.get("/admin/audit?table=offers"), "offer")
    pid = db.execute("SELECT product_id FROM products WHERE status = 'pending' LIMIT 1").fetchone()[0]
    check(c.post(f"/admin/listings/{pid}/approve", follow_redirects=True), "Listing approved")

    # Block a user -> cannot log in
    c.post("/admin/users/6/toggle-block")
    check(login(c, "neha@college.edu"), "blocked by an admin")

    # Register a new user
    c.get("/logout")
    check(c.post("/register", data={"name": "Test User", "email": "test@college.edu", "branch": "Civil",
                                    "year": 2, "phone": "9999999999", "password": "secret1"},
                 follow_redirects=True), "Account created")

    db.close()
    print("All tests passed ✔")


if __name__ == "__main__":
    main()
