"""
CampusKart - AI-powered second-hand marketplace for college students.

Run:   python app.py      then open http://127.0.0.1:5000
Reset demo data:  python seed.py
"""

import os
import shutil
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from ai import price_predictor, recommender, spam_detector
from seed import DB_PATH as SEED_DB_PATH, seed

if os.environ.get("VERCEL"):
    # Vercel's file system is read-only except /tmp, so each server instance works on a
    # fresh copy of the bundled demo database (changes reset when the instance restarts).
    DB_PATH = "/tmp/campuskart.db"
    if not os.path.exists(DB_PATH):
        shutil.copyfile(SEED_DB_PATH, DB_PATH)
else:
    DB_PATH = SEED_DB_PATH

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "campuskart-dev-secret-change-me")

CONDITIONS = ["New", "Like New", "Good", "Fair"]


# =====================================================================
#  Database helpers
# =====================================================================
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, args=(), one=False):
    rows = get_db().execute(sql, args).fetchall()
    return (rows[0] if rows else None) if one else rows


# =====================================================================
#  Auth helpers
# =====================================================================
@app.before_request
def load_user():
    g.user = None
    if "user_id" in session:
        g.user = query("SELECT * FROM users WHERE user_id = ?", (session["user_id"],), one=True)
        if g.user is None or g.user["is_blocked"]:
            session.clear()
            g.user = None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Log in to continue.", "info")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if g.user["role"] != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_globals():
    unread = 0
    if g.user:
        unread = query("SELECT COUNT(*) AS n FROM notifications WHERE user_id = ? AND is_read = 0",
                       (g.user["user_id"],), one=True)["n"]
    return {"categories": query("SELECT * FROM categories ORDER BY category_id"),
            "unread_count": unread, "conditions": CONDITIONS}


# =====================================================================
#  Template filters
# =====================================================================
@app.template_filter("inr")
def inr(value):
    """Indian number format: 125000 -> 1,25,000"""
    n = str(int(round(value or 0)))
    if len(n) <= 3:
        return n
    head, tail = n[:-3], n[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


@app.template_filter("ago")
def time_ago(ts):
    try:
        dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return ts
    secs = (datetime.now() - dt).total_seconds()
    for unit, size in (("day", 86400), ("hour", 3600), ("min", 60)):
        if secs >= size:
            n = int(secs // size)
            return f"{n} {unit}{'s' if n > 1 else ''} ago"
    return "just now"


# =====================================================================
#  Authentication
# =====================================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        user = query("SELECT * FROM users WHERE email = ?", (email,), one=True)
        if user is None or not check_password_hash(user["password_hash"], request.form["password"]):
            flash("That email and password don't match. Check them and try again.", "danger")
        elif user["is_blocked"]:
            flash("This account has been blocked by an admin. Contact the admin if you think this is a mistake.", "danger")
        else:
            session.clear()
            session["user_id"] = user["user_id"]
            flash(f"Welcome back, {user['name'].split()[0]}!", "success")
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(request.args.get("next") or url_for("index"))

    demo_users = query("""SELECT name, email, role, branch, year FROM users
                          WHERE email IN ('admin@campuskart.com', 'rahul@college.edu',
                                          'priya@college.edu', 'karan@college.edu',
                                          'aisha@college.edu', 'neha@college.edu')
                          ORDER BY user_id""")
    return render_template("login.html", demo_users=demo_users)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        if len(f["password"]) < 6:
            flash("Use at least 6 characters for your password.", "danger")
            return render_template("register.html", form=f)
        try:
            with get_db() as db:   # transaction: commit on success, rollback on error
                cur = db.execute(
                    """INSERT INTO users (name, email, password_hash, branch, year, phone)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (f["name"].strip(), f["email"].strip().lower(),
                     generate_password_hash(f["password"]), f["branch"], int(f["year"]),
                     f["phone"].strip()))
                db.execute("INSERT INTO notifications (user_id, message) VALUES (?, ?)",
                           (cur.lastrowid, "Welcome to CampusKart! Search for something to get "
                                           "AI recommendations."))
        except sqlite3.IntegrityError:
            flash("An account with this email already exists. Log in instead, or use a different email.", "danger")
            return render_template("register.html", form=f)
        session.clear()
        session["user_id"] = cur.lastrowid
        flash("Account created. Search for something you need and your recommendations will start adapting.", "success")
        return redirect(url_for("index"))
    return render_template("register.html", form={})


@app.route("/logout")
def logout():
    session.clear()
    flash("You've logged out. See you soon.", "info")
    return redirect(url_for("index"))


# =====================================================================
#  Home, search, product
# =====================================================================
@app.route("/")
def index():
    recs, personalised, recent_searches = [], False, []
    if g.user and g.user["role"] == "user":
        recs, personalised = recommender.recommend_for_user(get_db(), g.user["user_id"])
        recent_searches = query(
            """SELECT query, MAX(searched_at) AS t FROM search_history WHERE user_id = ?
               GROUP BY LOWER(query) ORDER BY t DESC LIMIT 6""", (g.user["user_id"],))
    else:
        recs = recommender.trending(get_db(), None)

    latest = query("""SELECT * FROM v_product_details WHERE status = 'available'
                      ORDER BY created_at DESC LIMIT 8""")
    cat_counts = {r["category_id"]: r["n"] for r in query(
        "SELECT category_id, COUNT(*) AS n FROM products WHERE status = 'available' GROUP BY category_id")}
    return render_template("index.html", recs=recs, personalised=personalised,
                           recent_searches=recent_searches, latest=latest, cat_counts=cat_counts)


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", type=int)
    condition = request.args.get("condition", "")
    max_price = request.args.get("max_price", type=float)
    sort = request.args.get("sort", "newest")

    sql = "SELECT * FROM v_product_details WHERE status = 'available'"
    args = []
    if q:
        sql += " AND (title LIKE ? OR description LIKE ? OR category_name LIKE ?)"
        args += [f"%{q}%"] * 3
    if category:
        sql += " AND category_id = ?"
        args.append(category)
    if condition in CONDITIONS:
        sql += " AND condition = ?"
        args.append(condition)
    if max_price:
        sql += " AND price <= ?"
        args.append(max_price)
    sql += {"price_low": " ORDER BY price ASC",
            "price_high": " ORDER BY price DESC",
            "rating": " ORDER BY seller_rating DESC, created_at DESC"}.get(sort, " ORDER BY created_at DESC")
    results = query(sql, args)

    # Save the search -> this is what powers AI recommendations
    if q and g.user and g.user["role"] == "user":
        with get_db() as db:
            db.execute("INSERT INTO search_history (user_id, query) VALUES (?, ?)",
                       (g.user["user_id"], q.lower()))

    # Nothing matched exactly -> use AI similarity to suggest close matches
    ai_suggestions = []
    if q and not results:
        ai_suggestions = _semantic_search(q)

    return render_template("search.html", results=results, q=q, category=category,
                           condition=condition, max_price=max_price, sort=sort,
                           ai_suggestions=ai_suggestions)


def _semantic_search(q, n=6):
    """Typo-tolerant fallback search using the recommender's TF-IDF index."""
    from sklearn.metrics.pairwise import cosine_similarity
    products = recommender._available_products(get_db())
    if not products:
        return []
    vectorizer, matrix = recommender._build_index(products)
    scores = cosine_similarity(vectorizer.transform([q.lower()]), matrix)[0]
    ranked = sorted(zip(products, scores), key=lambda x: x[1], reverse=True)
    return [p for p, s in ranked if s > 0.12][:n]


@app.route("/search/history/clear", methods=["POST"])
@login_required
def clear_search_history():
    with get_db() as db:
        db.execute("DELETE FROM search_history WHERE user_id = ?", (g.user["user_id"],))
    flash("Search history cleared. Your recommendations will start fresh.", "info")
    return redirect(request.referrer or url_for("index"))


@app.route("/product/<int:pid>")
def product(pid):
    p = query("SELECT * FROM v_product_details WHERE product_id = ?", (pid,), one=True)
    if p is None:
        abort(404)
    is_owner = g.user and g.user["user_id"] == p["seller_id"]
    is_admin = g.user and g.user["role"] == "admin"
    if p["status"] in ("pending", "rejected", "removed") and not (is_owner or is_admin):
        abort(404)

    in_wishlist = False
    if g.user and g.user["role"] == "user" and not is_owner:
        with get_db() as db:
            db.execute("INSERT INTO product_views (user_id, product_id) VALUES (?, ?)",
                       (g.user["user_id"], pid))
        in_wishlist = query("SELECT 1 FROM wishlist WHERE user_id = ? AND product_id = ?",
                            (g.user["user_id"], pid), one=True) is not None

    reviews = query("""SELECT r.rating, r.comment, r.created_at, u.name AS buyer_name, p.title
                       FROM reviews r
                       JOIN orders o   ON o.order_id = r.order_id
                       JOIN products p ON p.product_id = o.product_id
                       JOIN users u    ON u.user_id = o.buyer_id
                       WHERE p.seller_id = ? ORDER BY r.created_at DESC LIMIT 3""",
                    (p["seller_id"],))
    verdict = price_predictor.price_verdict(get_db(), p) if p["status"] == "available" else None
    similar = recommender.similar_products(get_db(), pid)
    views = query("SELECT COUNT(*) AS n FROM product_views WHERE product_id = ?", (pid,), one=True)["n"]
    return render_template("product.html", p=p, is_owner=is_owner, in_wishlist=in_wishlist,
                           reviews=reviews, verdict=verdict, similar=similar, views=views)


# =====================================================================
#  Wishlist
# =====================================================================
@app.route("/wishlist")
@login_required
def wishlist():
    items = query("""SELECT d.*, w.added_at FROM wishlist w
                     JOIN v_product_details d ON d.product_id = w.product_id
                     WHERE w.user_id = ? ORDER BY w.added_at DESC""", (g.user["user_id"],))
    return render_template("wishlist.html", items=items)


@app.route("/wishlist/toggle/<int:pid>", methods=["POST"])
@login_required
def toggle_wishlist(pid):
    uid = g.user["user_id"]
    with get_db() as db:
        removed = db.execute("DELETE FROM wishlist WHERE user_id = ? AND product_id = ?",
                             (uid, pid)).rowcount
        if not removed:
            db.execute("INSERT INTO wishlist (user_id, product_id) VALUES (?, ?)", (uid, pid))
    flash("Removed from your wishlist." if removed else "Saved to your wishlist. We'll tell you if it sells.",
          "info" if removed else "success")
    return redirect(request.referrer or url_for("product", pid=pid))


# =====================================================================
#  Orders  (transactions + triggers)
# =====================================================================
@app.route("/buy/<int:pid>", methods=["POST"])
@login_required
def buy(pid):
    p = query("SELECT * FROM products WHERE product_id = ?", (pid,), one=True)
    if p is None:
        abort(404)
    try:
        # One atomic transaction. Trigger trg_order_validate aborts it if the item
        # was already bought by someone else (prevents double selling).
        with get_db() as db:
            db.execute("INSERT INTO orders (product_id, buyer_id, price) VALUES (?, ?, ?)",
                       (pid, g.user["user_id"], p["price"]))
    except sqlite3.DatabaseError as e:
        msg = str(e)
        if "no longer available" in msg:
            msg = "Someone bought this item just before you, so it's no longer available."
        elif "own product" in msg:
            msg = "You can't buy your own listing."
        else:
            msg = "We couldn't place your order. Please try again."
        flash(msg, "danger")
        return redirect(url_for("product", pid=pid))
    flash("Order placed. Call the seller (number below) to arrange a campus pickup.", "success")
    return redirect(url_for("orders"))


@app.route("/orders")
@login_required
def orders():
    uid = g.user["user_id"]
    purchases = query("""SELECT o.*, d.title, d.category_icon, d.seller_name, d.seller_id,
                                s.phone AS seller_phone, r.rating
                         FROM orders o
                         JOIN v_product_details d ON d.product_id = o.product_id
                         JOIN users s ON s.user_id = d.seller_id
                         LEFT JOIN reviews r ON r.order_id = o.order_id
                         WHERE o.buyer_id = ? ORDER BY o.ordered_at DESC""", (uid,))
    sales = query("""SELECT o.*, p.title, c.icon AS category_icon, b.name AS buyer_name,
                            b.phone AS buyer_phone, r.rating
                     FROM orders o
                     JOIN products p   ON p.product_id = o.product_id
                     JOIN categories c ON c.category_id = p.category_id
                     JOIN users b      ON b.user_id = o.buyer_id
                     LEFT JOIN reviews r ON r.order_id = o.order_id
                     WHERE p.seller_id = ? ORDER BY o.ordered_at DESC""", (uid,))
    return render_template("orders.html", purchases=purchases, sales=sales,
                           tab=request.args.get("tab", "purchases"))


def _own_order(oid):
    o = query("SELECT * FROM orders WHERE order_id = ? AND buyer_id = ?",
              (oid, g.user["user_id"]), one=True)
    if o is None:
        abort(404)
    return o


@app.route("/orders/<int:oid>/cancel", methods=["POST"])
@login_required
def cancel_order(oid):
    if _own_order(oid)["status"] == "placed":
        with get_db() as db:   # trigger trg_order_cancelled re-lists the product
            db.execute("UPDATE orders SET status = 'cancelled' WHERE order_id = ?", (oid,))
        flash("Order cancelled. The item is back on sale.", "info")
    return redirect(url_for("orders"))


@app.route("/orders/<int:oid>/complete", methods=["POST"])
@login_required
def complete_order(oid):
    if _own_order(oid)["status"] == "placed":
        with get_db() as db:
            db.execute("UPDATE orders SET status = 'completed' WHERE order_id = ?", (oid,))
        flash("Marked as received. How was the seller? Leave a rating below.", "success")
    return redirect(url_for("orders"))


@app.route("/orders/<int:oid>/review", methods=["POST"])
@login_required
def review_order(oid):
    o = _own_order(oid)
    rating = request.form.get("rating", type=int)
    if o["status"] != "completed" or not rating:
        flash("You can rate the seller after you mark the order as received.", "warning")
        return redirect(url_for("orders"))
    try:
        with get_db() as db:
            db.execute("INSERT INTO reviews (order_id, rating, comment) VALUES (?, ?, ?)",
                       (oid, rating, request.form.get("comment", "").strip()))
        flash("Thanks for your review!", "success")
    except sqlite3.IntegrityError:
        flash("You've already rated this order.", "info")
    return redirect(url_for("orders"))


# =====================================================================
#  Selling (AI price suggestion + AI spam check)
# =====================================================================
def _listing_from_form(f):
    return {
        "title": f["title"].strip(),
        "description": f["description"].strip(),
        "category_id": int(f["category_id"]),
        "original_price": float(f["original_price"]),
        "price": float(f["price"]),
        "condition": f["condition"],
        "age_months": int(f["age_months"]),
    }


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if g.user["role"] == "admin":
        flash("Admin accounts can't create listings. Log in as a student to sell.", "warning")
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        d = _listing_from_form(request.form)
        check = spam_detector.check_listing(d["title"], d["description"], d["price"], d["original_price"])
        with get_db() as db:
            # Trigger trg_flagged_listing alerts admins when is_flagged = 1
            cur = db.execute(
                """INSERT INTO products (seller_id, category_id, title, description, original_price,
                                         price, condition, age_months, status, is_flagged,
                                         spam_score, flag_reason)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (g.user["user_id"], d["category_id"], d["title"], d["description"],
                 d["original_price"], d["price"], d["condition"], d["age_months"],
                 "pending" if check["is_spam"] else "available", int(check["is_spam"]),
                 check["score"], "; ".join(check["reasons"]) or None))
        if check["is_spam"]:
            flash("Your listing is waiting for review because our spam check flagged it ("
                  + "; ".join(check["reasons"]).lower() + "). An admin will check it soon.", "warning")
            return redirect(url_for("my_listings"))
        flash("Your item is live. Students searching for similar things will see it in their recommendations.", "success")
        return redirect(url_for("product", pid=cur.lastrowid))
    return render_template("sell.html", item=None)


@app.route("/listing/<int:pid>/edit", methods=["GET", "POST"])
@login_required
def edit_listing(pid):
    item = query("SELECT * FROM products WHERE product_id = ? AND seller_id = ?",
                 (pid, g.user["user_id"]), one=True)
    if item is None or item["status"] not in ("available", "pending"):
        abort(404)
    if request.method == "POST":
        d = _listing_from_form(request.form)
        check = spam_detector.check_listing(d["title"], d["description"], d["price"], d["original_price"])
        with get_db() as db:
            db.execute(
                """UPDATE products SET title = ?, description = ?, category_id = ?, original_price = ?,
                          price = ?, condition = ?, age_months = ?, spam_score = ?
                   WHERE product_id = ?""",
                (d["title"], d["description"], d["category_id"], d["original_price"], d["price"],
                 d["condition"], d["age_months"], check["score"], pid))
            if check["is_spam"] and item["status"] == "available":
                db.execute("""UPDATE products SET status = 'pending', is_flagged = 1, flag_reason = ?
                              WHERE product_id = ?""", ("; ".join(check["reasons"]), pid))
                db.execute("""INSERT INTO notifications (user_id, message)
                              SELECT user_id, ? FROM users WHERE role = 'admin'""",
                           (f'AI flagged an edited listing: "{d["title"]}". Please review.',))
        flash("Listing updated." if not check["is_spam"] else
              "Listing updated. Our spam check flagged it, so an admin will review it before it goes live.",
              "success" if not check["is_spam"] else "warning")
        return redirect(url_for("my_listings"))
    return render_template("sell.html", item=item)


@app.route("/listing/<int:pid>/remove", methods=["POST"])
@login_required
def remove_listing(pid):
    with get_db() as db:
        db.execute("""UPDATE products SET status = 'removed'
                      WHERE product_id = ? AND seller_id = ? AND status IN ('available', 'pending')""",
                   (pid, g.user["user_id"]))
    flash("Listing removed. Buyers can no longer see it.", "info")
    return redirect(url_for("my_listings"))


@app.route("/my-listings")
@login_required
def my_listings():
    items = query("""SELECT d.*, (SELECT COUNT(*) FROM product_views v WHERE v.product_id = d.product_id) AS views,
                            (SELECT COUNT(*) FROM wishlist w WHERE w.product_id = d.product_id) AS wishes
                     FROM v_product_details d WHERE d.seller_id = ? AND d.status <> 'removed'
                     ORDER BY d.created_at DESC""", (g.user["user_id"],))
    return render_template("my_listings.html", items=items)


@app.route("/api/predict-price", methods=["POST"])
@login_required
def api_predict_price():
    data = request.get_json(force=True)
    try:
        result = price_predictor.predict_price(
            get_db(), float(data["original_price"]), data["condition"],
            int(data.get("age_months") or 0), int(data["category_id"]))
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "Fill original price, category and condition first."}), 400
    if result is None:
        return jsonify({"error": "Not enough data to predict."}), 400
    return jsonify(result)


@app.route("/api/spam-check", methods=["POST"])
@login_required
def api_spam_check():
    data = request.get_json(force=True)
    try:
        return jsonify(spam_detector.check_listing(
            data.get("title", ""), data.get("description", ""),
            float(data.get("price") or 0), float(data.get("original_price") or 0)))
    except ValueError:
        return jsonify({"error": "Invalid price"}), 400


# =====================================================================
#  Profile & notifications
# =====================================================================
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    uid = g.user["user_id"]
    if request.method == "POST":
        f = request.form
        with get_db() as db:
            db.execute("UPDATE users SET name = ?, branch = ?, year = ?, phone = ? WHERE user_id = ?",
                       (f["name"].strip(), f["branch"], f.get("year", type=int), f["phone"].strip(), uid))
        flash("Profile saved.", "success")
        return redirect(url_for("profile"))

    stats = query("""SELECT
            (SELECT COUNT(*) FROM products WHERE seller_id = :u AND status = 'available') AS listed,
            (SELECT COUNT(*) FROM orders o JOIN products p ON p.product_id = o.product_id
              WHERE p.seller_id = :u AND o.status <> 'cancelled') AS sold,
            (SELECT COUNT(*) FROM orders WHERE buyer_id = :u AND status <> 'cancelled') AS bought,
            (SELECT COALESCE(SUM(o.price), 0) FROM orders o JOIN products p ON p.product_id = o.product_id
              WHERE p.seller_id = :u AND o.status <> 'cancelled') AS earned""", {"u": uid}, one=True)
    rating = query("SELECT * FROM v_seller_ratings WHERE seller_id = ?", (uid,), one=True)
    searches = query("""SELECT query, searched_at FROM search_history WHERE user_id = ?
                        ORDER BY searched_at DESC LIMIT 15""", (uid,))
    return render_template("profile.html", stats=stats, rating=rating, searches=searches)


@app.route("/notifications")
@login_required
def notifications():
    items = query("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC, notif_id DESC",
                  (g.user["user_id"],))
    with get_db() as db:
        db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (g.user["user_id"],))
    return render_template("notifications.html", items=items)


# =====================================================================
#  Admin panel
# =====================================================================
@app.route("/admin")
@admin_required
def admin_dashboard():
    stats = query("SELECT * FROM v_admin_stats", one=True)
    cat_sales = query("SELECT * FROM v_category_sales ORDER BY revenue DESC")
    max_rev = max([c["revenue"] for c in cat_sales] + [1])
    top_searches = query("""SELECT LOWER(query) AS query, COUNT(*) AS n FROM search_history
                            GROUP BY LOWER(query) ORDER BY n DESC, MAX(searched_at) DESC LIMIT 8""")
    recent_orders = query("""SELECT o.*, p.title, b.name AS buyer_name FROM orders o
                             JOIN products p ON p.product_id = o.product_id
                             JOIN users b ON b.user_id = o.buyer_id
                             ORDER BY o.ordered_at DESC LIMIT 6""")
    top_sellers = query("""SELECT u.name, u.branch, sr.avg_rating, sr.review_count
                           FROM v_seller_ratings sr JOIN users u ON u.user_id = sr.seller_id
                           ORDER BY sr.avg_rating DESC, sr.review_count DESC LIMIT 5""")
    return render_template("admin/dashboard.html", stats=stats, cat_sales=cat_sales, max_rev=max_rev,
                           top_searches=top_searches, recent_orders=recent_orders,
                           top_sellers=top_sellers)


@app.route("/admin/listings")
@admin_required
def admin_listings():
    pending = query("SELECT * FROM v_product_details WHERE status = 'pending' ORDER BY spam_score DESC")
    status = request.args.get("status", "available")
    listings = query("SELECT * FROM v_product_details WHERE status = ? ORDER BY created_at DESC",
                     (status,))
    return render_template("admin/listings.html", pending=pending, listings=listings, status=status)


@app.route("/admin/listings/<int:pid>/<action>", methods=["POST"])
@admin_required
def admin_listing_action(pid, action):
    new_status = {"approve": "available", "reject": "rejected", "remove": "removed"}.get(action)
    if new_status is None:
        abort(400)
    with get_db() as db:   # trigger trg_listing_moderated notifies the seller
        db.execute("UPDATE products SET status = ?, is_flagged = 0 WHERE product_id = ?",
                   (new_status, pid))
    flash({"available": "Listing approved. It's live now and the seller has been notified.",
           "rejected": "Listing rejected. The seller has been notified.",
           "removed": "Listing removed."}[new_status], "success")
    return redirect(request.referrer or url_for("admin_listings"))


@app.route("/admin/users")
@admin_required
def admin_users():
    users = query("""SELECT u.*,
                       (SELECT COUNT(*) FROM products p WHERE p.seller_id = u.user_id) AS listings,
                       (SELECT COUNT(*) FROM orders o WHERE o.buyer_id = u.user_id) AS purchases,
                       (SELECT COUNT(*) FROM search_history s WHERE s.user_id = u.user_id) AS searches,
                       COALESCE(sr.avg_rating, 0) AS rating
                     FROM users u LEFT JOIN v_seller_ratings sr ON sr.seller_id = u.user_id
                     ORDER BY u.role, u.user_id""")
    return render_template("admin/users.html", users=users)


@app.route("/admin/users/<int:uid>/toggle-block", methods=["POST"])
@admin_required
def admin_toggle_block(uid):
    with get_db() as db:
        db.execute("UPDATE users SET is_blocked = 1 - is_blocked WHERE user_id = ? AND role = 'user'",
                   (uid,))
    u = query("SELECT name, is_blocked FROM users WHERE user_id = ?", (uid,), one=True)
    if u:
        flash(f"{u['name']} is blocked and can't log in." if u["is_blocked"]
              else f"{u['name']} is unblocked and can log in again.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/orders")
@admin_required
def admin_orders():
    rows = query("""SELECT o.*, p.title, b.name AS buyer_name, s.name AS seller_name, r.rating
                    FROM orders o
                    JOIN products p ON p.product_id = o.product_id
                    JOIN users b ON b.user_id = o.buyer_id
                    JOIN users s ON s.user_id = p.seller_id
                    LEFT JOIN reviews r ON r.order_id = o.order_id
                    ORDER BY o.ordered_at DESC""")
    return render_template("admin/orders.html", orders=rows)


@app.route("/admin/database", methods=["GET", "POST"])
@admin_required
def admin_database():
    """Database explorer: shows schema objects and runs read-only SELECT queries."""
    objects = query("""SELECT type, name, tbl_name, sql FROM sqlite_master
                       WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'
                       ORDER BY CASE type WHEN 'table' THEN 1 WHEN 'view' THEN 2
                                          WHEN 'trigger' THEN 3 ELSE 4 END, name""")
    counts = {o["name"]: query(f'SELECT COUNT(*) AS n FROM "{o["name"]}"', one=True)["n"]
              for o in objects if o["type"] == "table"}

    sql = request.form.get("sql", "SELECT * FROM v_seller_ratings;").strip()
    columns, rows, error = [], [], None
    if request.method == "POST":
        if not sql.lower().lstrip("( ").startswith(("select", "with")):
            error = "Only SELECT queries are allowed here."
        else:
            try:
                # Separate read-only connection: even a tricky query cannot change data.
                ro = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
                cur = ro.execute(sql)
                columns = [c[0] for c in cur.description or []]
                rows = cur.fetchmany(200)
                ro.close()
            except sqlite3.Error as e:
                error = str(e)
    return render_template("admin/database.html", objects=objects, counts=counts, sql=sql,
                           columns=columns, rows=rows, error=error)


@app.errorhandler(403)
def forbidden(_e):
    return render_template("error.html", code=403, message="This page is only available to admins. Log in with an admin account to view it."), 403


@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", code=404, message="The page may have been removed, or the link might be wrong."), 404


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print("No database found - creating demo database...")
        seed()
    app.run(debug=True)
