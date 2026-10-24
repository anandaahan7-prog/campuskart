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
    check(login(c, "rahul@college.edu"), "Recommended for you", "Because you searched")
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
    check(c.post("/buy/2", follow_redirects=True), "Order placed")
    check(login(c, "priya@college.edu"), "Recommended for you")
    check(c.post("/buy/2", follow_redirects=True), "no longer available")

    # Rahul completes and reviews the order
    login(c, "rahul@college.edu")
    db = sqlite3.connect(DB_PATH)
    oid = db.execute("SELECT MAX(order_id) FROM orders").fetchone()[0]
    check(c.post(f"/orders/{oid}/complete", follow_redirects=True), "Mark")
    check(c.post(f"/orders/{oid}/review", data={"rating": 5, "comment": "great"}, follow_redirects=True),
          "Thanks for your review")

    # Neha: new user -> cold start
    check(login(c, "neha@college.edu"), "Trending on campus")

    # Admin
    check(login(c, "admin@campuskart.com", "admin123"), "Admin dashboard", "Sales by category")
    check(c.get("/admin/listings"), "Flagged by AI", "iPhone 14 Pro")
    check(c.get("/admin/users"), "Rahul Sharma")
    check(c.get("/admin/orders"), "Head First Java")
    check(c.get("/admin/database"), "trg_order_validate", "v_seller_ratings")
    check(c.post("/admin/database", data={"sql": "SELECT name FROM users"}), "Rahul Sharma")
    check(c.post("/admin/database", data={"sql": "DELETE FROM users"}), "Only SELECT")
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
