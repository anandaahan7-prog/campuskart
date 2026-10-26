"""
CampusKart - AI-powered second-hand marketplace for college students.

Run:   python app.py      then open http://127.0.0.1:5000
Reset demo data:  python seed.py
"""

import os
import shutil
import sqlite3
import textwrap
from contextlib import contextmanager
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


@contextmanager
def tx():
    """One write transaction: COMMIT on success, ROLLBACK on any error.
    It also records which user is acting, so the audit triggers can log "who"."""
    db = get_db()
    with db:
        db.execute("UPDATE audit_context SET user_id = ? WHERE id = 1",
                   (g.user["user_id"] if g.user else None,))
        yield db


# Friendly messages for errors raised by triggers and constraints.
DB_ERRORS = {
    "no longer available": "Someone bought this item just before you, so it's no longer available.",
    "buy your own product": "You can't buy your own listing.",
    "offer on your own product": "You can't make an offer on your own listing.",
    "below the asking price": "Offer less than the asking price, or just buy it at the listed price.",
    "offers.product_id, offers.buyer_id": "You already have an open offer on this item. Withdraw it to make a new one.",
}


def friendly_error(e, default):
    msg = str(e)
    return next((text for key, text in DB_ERRORS.items() if key in msg), default)


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


@app.template_filter("clean")
def clean_value(v):
    """Show stored numbers nicely: '1100.0' -> '1100'."""
    try:
        f = float(v)
        return str(int(f)) if f.is_integer() else str(round(f, 2))
    except (TypeError, ValueError):
        return v


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
            with tx() as db:   # transaction: commit on success, rollback on error
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
    recs, personalised, recent_searches, finding, board = [], False, [], None, {}
    if g.user and g.user["role"] == "user":
        uid = g.user["user_id"]
        recs, personalised = recommender.recommend_for_user(get_db(), uid)
        recent_searches = query(
            """SELECT query, MAX(searched_at) AS t FROM search_history WHERE user_id = ?
               GROUP BY LOWER(query) ORDER BY t DESC LIMIT 6""", (uid,))
        finding = home_finding(uid)
        board = {
            "offers": query("""SELECT o.offer_id, o.status, o.amount, o.counter_amount, p.product_id, p.title,
                                      p.category_id, CASE WHEN o.buyer_id = ? THEN 'out' ELSE 'in' END AS side
                               FROM offers o JOIN products p ON p.product_id = o.product_id
                               WHERE (o.buyer_id = ? OR p.seller_id = ?) AND o.status IN ('pending', 'countered')
                               ORDER BY COALESCE(o.updated_at, o.created_at) DESC LIMIT 3""", (uid, uid, uid)),
            "notes": query("""SELECT message, created_at, is_read FROM notifications WHERE user_id = ?
                              ORDER BY created_at DESC, notif_id DESC LIMIT 3""", (uid,)),
            "searches": query("SELECT COUNT(*) AS n FROM search_history WHERE user_id = ?", (uid,), one=True)["n"],
        }
    else:
        recs = recommender.trending(get_db(), None)

    latest = query("""SELECT * FROM v_product_details WHERE status = 'available'
                      ORDER BY created_at DESC LIMIT 4""")
    cat_counts = {r["category_id"]: r["n"] for r in query(
        "SELECT category_id, COUNT(*) AS n FROM products WHERE status = 'available' GROUP BY category_id")}
    return render_template("index.html", recs=recs, personalised=personalised, finding=finding, board=board,
                           recent_searches=recent_searches, latest=latest, cat_counts=cat_counts)


def home_finding(uid):
    """The one thing on the board that most needs this student's attention, with the action it drives."""
    first = lambda name: name.split()[0]
    r = query("""SELECT o.counter_amount, o.amount, p.product_id, p.title, s.name AS seller
                 FROM offers o JOIN products p ON p.product_id = o.product_id JOIN users s ON s.user_id = p.seller_id
                 WHERE o.buyer_id = ? AND o.status = 'countered' ORDER BY o.updated_at DESC LIMIT 1""", (uid,), one=True)
    if r:
        return {"kind": "Counter-offer", "label": "Reply to the counter", "url": url_for("product", pid=r["product_id"]),
                "text": f"{first(r['seller'])} countered your ₹{inr(r['amount'])} offer on {r['title']} "
                        f"at ₹{inr(r['counter_amount'])}."}
    r = query("""SELECT COUNT(*) AS n, MAX(o.amount) AS amount, MAX(p.title) AS title, MAX(b.name) AS buyer
                 FROM offers o JOIN products p ON p.product_id = o.product_id JOIN users b ON b.user_id = o.buyer_id
                 WHERE p.seller_id = ? AND o.status = 'pending'""", (uid,), one=True)
    if r["n"]:
        text = (f"{first(r['buyer'])} offered ₹{inr(r['amount'])} for your {r['title']}." if r["n"] == 1
                else f"{r['n']} offers on your items are waiting for your reply.")
        return {"kind": "Offer received", "label": "Review offers", "url": url_for("orders", tab="offers"), "text": text}
    r = query("""SELECT p.product_id, p.title, a.old_value, a.new_value
                 FROM wishlist w JOIN products p ON p.product_id = w.product_id
                 JOIN audit_log a ON a.table_name = 'products' AND a.row_id = p.product_id AND a.field = 'price'
                 WHERE w.user_id = ? AND p.status = 'available'
                   AND CAST(a.new_value AS REAL) < CAST(a.old_value AS REAL)
                 ORDER BY a.audit_id DESC LIMIT 1""", (uid,), one=True)
    if r:
        return {"kind": "Price drop", "label": "See the item", "url": url_for("product", pid=r["product_id"]),
                "text": f"{r['title']} on your wishlist dropped to ₹{inr(float(r['new_value']))} "
                        f"(was ₹{inr(float(r['old_value']))})."}
    r = query("""SELECT p.product_id, p.title, s.name AS seller FROM orders o
                 JOIN products p ON p.product_id = o.product_id JOIN users s ON s.user_id = p.seller_id
                 WHERE o.buyer_id = ? AND o.status = 'placed' ORDER BY o.ordered_at DESC LIMIT 1""", (uid,), one=True)
    if r:
        return {"kind": "Ready for pickup", "label": "See pickup details", "url": url_for("product", pid=r["product_id"]),
                "text": f"Pick up {r['title']} from {first(r['seller'])}. Their number is on the slip."}
    r = query("""SELECT o.amount, p.product_id, p.title, s.name AS seller FROM offers o
                 JOIN products p ON p.product_id = o.product_id JOIN users s ON s.user_id = p.seller_id
                 WHERE o.buyer_id = ? AND o.status = 'pending' ORDER BY o.created_at DESC LIMIT 1""", (uid,), one=True)
    if r:
        return {"kind": "Offer sent", "label": "See your offer", "url": url_for("product", pid=r["product_id"]),
                "text": f"Your ₹{inr(r['amount'])} offer on {r['title']} is with {first(r['seller'])}."}
    return None


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
        with tx() as db:
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
    with tx() as db:
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
        with tx() as db:
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
    also = recommender.also_viewed(get_db(), pid, g.user["user_id"] if g.user else None)
    views = query("SELECT COUNT(*) AS n FROM product_views WHERE product_id = ?", (pid,), one=True)["n"]

    # Latest price change, read from the audit log (written by a trigger)
    change = query("""SELECT old_value, new_value, changed_at FROM audit_log
                      WHERE table_name = 'products' AND row_id = ? AND field = 'price'
                      ORDER BY audit_id DESC LIMIT 1""", (pid,), one=True)
    price_drop = None
    if change and float(change["new_value"]) < float(change["old_value"]):
        price_drop = {"was": float(change["old_value"]), "at": change["changed_at"]}

    my_order = None
    if g.user and not is_owner:
        my_order = query("""SELECT o.order_id, o.status, o.price, s.phone AS seller_phone FROM orders o
                            JOIN users s ON s.user_id = ? WHERE o.product_id = ? AND o.buyer_id = ?
                            AND o.status IN ('placed', 'completed') ORDER BY o.order_id DESC LIMIT 1""",
                         (p["seller_id"], pid, g.user["user_id"]), one=True)

    my_offer, open_offers, suggested_offer = None, 0, None
    if is_owner:
        open_offers = query("SELECT COUNT(*) AS n FROM offers WHERE product_id = ? AND status = 'pending'",
                            (pid,), one=True)["n"]
    elif g.user and g.user["role"] == "user" and p["status"] == "available":
        my_offer = query("""SELECT * FROM offers WHERE product_id = ? AND buyer_id = ?
                            AND status IN ('pending', 'countered')""", (pid, g.user["user_id"]), one=True)
        # AI: start the buyer near the price model's estimate, a little under the asking price.
        base = min(p["price"] * 0.92, verdict["estimate"]) if verdict else p["price"] * 0.9
        suggested_offer = max(10, min(int(round(base / 10.0)) * 10, int(p["price"]) - 10))
    return render_template("product.html", p=p, is_owner=is_owner, in_wishlist=in_wishlist,
                           reviews=reviews, verdict=verdict, similar=similar, views=views, also=also,
                           price_drop=price_drop, my_offer=my_offer, open_offers=open_offers,
                           suggested_offer=suggested_offer, my_order=my_order,
                           torn=request.args.get("torn") == "1")


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
    with tx() as db:
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
        with tx() as db:
            db.execute("INSERT INTO orders (product_id, buyer_id, price) VALUES (?, ?, ?)",
                       (pid, g.user["user_id"], p["price"]))
    except sqlite3.DatabaseError as e:
        flash(friendly_error(e, "We couldn't place your order. Please try again."), "danger")
        return redirect(url_for("product", pid=pid))
    flash("Order placed. Call the seller on the number from the slip to arrange a campus pickup.", "success")
    return redirect(url_for("product", pid=pid, torn=1))


# =====================================================================
#  Offers  (state machine + transaction)
# =====================================================================
@app.route("/offer/<int:pid>", methods=["POST"])
@login_required
def make_offer(pid):
    amount = request.form.get("amount", type=float)
    if not amount or amount <= 0:
        flash("Enter how much you'd like to offer.", "warning")
        return redirect(url_for("product", pid=pid))
    try:
        with tx() as db:   # trigger trg_offer_validate checks status, owner and amount
            db.execute("INSERT INTO offers (product_id, buyer_id, amount, message) VALUES (?, ?, ?, ?)",
                       (pid, g.user["user_id"], amount, request.form.get("message", "").strip() or None))
    except sqlite3.DatabaseError as e:
        flash(friendly_error(e, "We couldn't send your offer. Please try again."), "danger")
        return redirect(url_for("product", pid=pid))
    flash(f"Offer of ₹{inr(amount)} sent. We'll let you know when the seller replies.", "success")
    return redirect(url_for("product", pid=pid))


@app.route("/offers/<int:oid>/<action>", methods=["POST"])
@login_required
def offer_action(oid, action):
    o = query("""SELECT o.*, p.seller_id, p.title, p.price AS asking FROM offers o
                 JOIN products p ON p.product_id = o.product_id WHERE o.offer_id = ?""", (oid,), one=True)
    if o is None:
        abort(404)
    uid = g.user["user_id"]
    is_seller, is_buyer = uid == o["seller_id"], uid == o["buyer_id"]
    allowed = {("accept", "pending"): is_seller, ("reject", "pending"): is_seller,
               ("counter", "pending"): is_seller, ("withdraw", "pending"): is_buyer,
               ("withdraw", "countered"): is_buyer, ("accept_counter", "countered"): is_buyer}
    back = request.form.get("next") or url_for("orders", tab="offers")
    if not allowed.get((action, o["status"])):
        flash("This offer has already changed. Here's its latest status.", "info")
        return redirect(back)
    try:
        with tx() as db:
            if action in ("accept", "accept_counter"):
                price = o["amount"] if action == "accept" else o["counter_amount"]
                # One transaction: accept the offer, then create the order at the agreed price.
                # If the item was sold meanwhile, the order trigger aborts and BOTH steps roll back.
                db.execute("""UPDATE offers SET status = 'accepted', updated_at = datetime('now', 'localtime')
                              WHERE offer_id = ?""", (oid,))
                db.execute("INSERT INTO orders (product_id, buyer_id, price) VALUES (?, ?, ?)",
                           (o["product_id"], o["buyer_id"], price))
            elif action == "counter":
                counter = request.form.get("counter_amount", type=float)
                if not counter or not o["amount"] < counter < o["asking"]:
                    raise ValueError
                db.execute("""UPDATE offers SET status = 'countered', counter_amount = ?,
                              updated_at = datetime('now', 'localtime') WHERE offer_id = ?""", (counter, oid))
            else:
                db.execute("""UPDATE offers SET status = ?, updated_at = datetime('now', 'localtime')
                              WHERE offer_id = ?""", ({"reject": "rejected", "withdraw": "withdrawn"}[action], oid))
    except ValueError:
        flash(f"Counter with an amount between ₹{inr(o['amount'])} and ₹{inr(o['asking'])}.", "warning")
        return redirect(back)
    except sqlite3.DatabaseError as e:
        flash(friendly_error(e, "Something went wrong. Please try again."), "danger")
        return redirect(back)
    flash({"accept": f"Deal done at ₹{inr(o['amount'])}. The order is in your sales.",
           "accept_counter": f"Deal done at ₹{inr(o['counter_amount'] or 0)}. Call the seller to arrange pickup.",
           "counter": "Counter-offer sent.",
           "reject": "Offer declined. The buyer has been notified.",
           "withdraw": "Offer withdrawn."}[action], "success")
    if action == "accept":
        return redirect(url_for("orders", tab="sales"))
    if action == "accept_counter":
        return redirect(url_for("product", pid=o["product_id"], torn=1))
    return redirect(back)


@app.route("/orders")
@login_required
def orders():
    uid = g.user["user_id"]
    purchases = query("""SELECT o.*, d.title, d.category_id, d.category_icon, d.seller_name, d.seller_id,
                                s.phone AS seller_phone, r.rating
                         FROM orders o
                         JOIN v_product_details d ON d.product_id = o.product_id
                         JOIN users s ON s.user_id = d.seller_id
                         LEFT JOIN reviews r ON r.order_id = o.order_id
                         WHERE o.buyer_id = ? ORDER BY o.ordered_at DESC""", (uid,))
    sales = query("""SELECT o.*, p.title, p.category_id, c.icon AS category_icon, b.name AS buyer_name,
                            b.phone AS buyer_phone, r.rating
                     FROM orders o
                     JOIN products p   ON p.product_id = o.product_id
                     JOIN categories c ON c.category_id = p.category_id
                     JOIN users b      ON b.user_id = o.buyer_id
                     LEFT JOIN reviews r ON r.order_id = o.order_id
                     WHERE p.seller_id = ? ORDER BY o.ordered_at DESC""", (uid,))
    open_first = "CASE o.status WHEN 'pending' THEN 0 WHEN 'countered' THEN 1 ELSE 2 END, o.created_at DESC"
    offers_in = query(f"""SELECT o.*, p.title, p.category_id, p.price AS asking, c.icon AS category_icon, b.name AS buyer_name
                          FROM offers o
                          JOIN products p   ON p.product_id = o.product_id
                          JOIN categories c ON c.category_id = p.category_id
                          JOIN users b      ON b.user_id = o.buyer_id
                          WHERE p.seller_id = ? ORDER BY {open_first}""", (uid,))
    offers_out = query(f"""SELECT o.*, p.title, p.category_id, p.price AS asking, c.icon AS category_icon, s.name AS seller_name
                           FROM offers o
                           JOIN products p   ON p.product_id = o.product_id
                           JOIN categories c ON c.category_id = p.category_id
                           JOIN users s      ON s.user_id = p.seller_id
                           WHERE o.buyer_id = ? ORDER BY {open_first}""", (uid,))
    return render_template("orders.html", purchases=purchases, sales=sales, offers_in=offers_in,
                           offers_out=offers_out, tab=request.args.get("tab", "purchases"))


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
        with tx() as db:   # trigger trg_order_cancelled re-lists the product
            db.execute("UPDATE orders SET status = 'cancelled' WHERE order_id = ?", (oid,))
        flash("Order cancelled. The item is back on sale.", "info")
    return redirect(url_for("orders"))


@app.route("/orders/<int:oid>/complete", methods=["POST"])
@login_required
def complete_order(oid):
    if _own_order(oid)["status"] == "placed":
        with tx() as db:
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
        with tx() as db:
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
        with tx() as db:
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
        with tx() as db:
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
    with tx() as db:
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
        with tx() as db:
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
    with tx() as db:
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
    with tx() as db:   # trigger trg_listing_moderated notifies the seller
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
    with tx() as db:
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


def _sql(text):
    return textwrap.dedent(text).strip()


def _run(title, icon, sql, params=()):
    """Run a predefined, parameterised query and keep its SQL for the "Show SQL" panel."""
    cur = get_db().execute(sql, params)
    columns = [c[0] for c in cur.description or []]
    return {"title": title, "icon": icon, "sql": sql, "columns": columns, "rows": cur.fetchall(),
            "visible": [c for c in columns if not c.startswith("_")]}   # "_pid"/"_uid" are link targets


USER_PROFILE_SQL = _sql("""
    SELECT u.user_id, u.name, u.email, u.role, u.branch, u.year, u.phone, u.is_blocked, u.created_at,
           (SELECT COUNT(*) FROM products WHERE seller_id = u.user_id AND status = 'available') AS live_listings,
           (SELECT COUNT(*) FROM orders o JOIN products p ON p.product_id = o.product_id
             WHERE p.seller_id = u.user_id AND o.status <> 'cancelled') AS items_sold,
           (SELECT COUNT(*) FROM orders WHERE buyer_id = u.user_id AND status <> 'cancelled') AS items_bought,
           (SELECT COALESCE(SUM(o.price), 0) FROM orders o JOIN products p ON p.product_id = o.product_id
             WHERE p.seller_id = u.user_id AND o.status <> 'cancelled') AS earned,
           (SELECT COALESCE(SUM(price), 0) FROM orders
             WHERE buyer_id = u.user_id AND status <> 'cancelled') AS spent,
           COALESCE(sr.avg_rating, 0) AS rating, COALESCE(sr.review_count, 0) AS reviews
    FROM users u LEFT JOIN v_seller_ratings sr ON sr.seller_id = u.user_id
    WHERE u.user_id = ?""")

USER_SECTIONS = [
    ("Listings", "package", """
        SELECT p.product_id AS _pid, p.title, c.name AS category, p.price, p.status, p.created_at AS listed_at
        FROM products p JOIN categories c ON c.category_id = p.category_id
        WHERE p.seller_id = ? ORDER BY p.created_at DESC"""),
    ("Purchases", "bag", """
        SELECT p.product_id AS _pid, p.title, s.name AS seller, o.price, o.status, o.ordered_at
        FROM orders o JOIN products p ON p.product_id = o.product_id
                      JOIN users s    ON s.user_id = p.seller_id
        WHERE o.buyer_id = ? ORDER BY o.ordered_at DESC"""),
    ("Sales", "tag", """
        SELECT p.product_id AS _pid, p.title, b.name AS buyer, o.price, o.status, o.ordered_at
        FROM orders o JOIN products p ON p.product_id = o.product_id
                      JOIN users b    ON b.user_id = o.buyer_id
        WHERE p.seller_id = ? ORDER BY o.ordered_at DESC"""),
    ("Offers made", "receipt", """
        SELECT p.product_id AS _pid, p.title, p.price AS asking, o.amount, o.counter_amount AS counter,
               o.status, o.created_at AS offered_at
        FROM offers o JOIN products p ON p.product_id = o.product_id
        WHERE o.buyer_id = ? ORDER BY o.created_at DESC"""),
    ("Offers received", "inbox", """
        SELECT p.product_id AS _pid, p.title, b.name AS buyer, p.price AS asking, o.amount,
               o.counter_amount AS counter, o.status, o.created_at AS offered_at
        FROM offers o JOIN products p ON p.product_id = o.product_id
                      JOIN users b    ON b.user_id = o.buyer_id
        WHERE p.seller_id = ? ORDER BY o.created_at DESC"""),
    ("Reviews received", "star", """
        SELECT p.title, b.name AS buyer, r.rating, r.comment, r.created_at AS reviewed_at
        FROM reviews r JOIN orders o   ON o.order_id = r.order_id
                       JOIN products p ON p.product_id = o.product_id
                       JOIN users b    ON b.user_id = o.buyer_id
        WHERE p.seller_id = ? ORDER BY r.created_at DESC"""),
    ("Wishlist", "heart", """
        SELECT p.product_id AS _pid, p.title, p.price, p.status, w.added_at
        FROM wishlist w JOIN products p ON p.product_id = w.product_id
        WHERE w.user_id = ? ORDER BY w.added_at DESC"""),
    ("Search history", "search", """
        SELECT query AS search, searched_at FROM search_history
        WHERE user_id = ? ORDER BY searched_at DESC LIMIT 20"""),
    ("Recently viewed", "eye", """
        SELECT p.product_id AS _pid, p.title, COUNT(*) AS times, MAX(v.viewed_at) AS last_viewed_at
        FROM product_views v JOIN products p ON p.product_id = v.product_id
        WHERE v.user_id = ? GROUP BY v.product_id ORDER BY last_viewed_at DESC LIMIT 15"""),
    ("Notifications", "bell", """
        SELECT message, created_at FROM notifications
        WHERE user_id = ? ORDER BY notif_id DESC LIMIT 15"""),
    ("Activity (audit log)", "zap", """
        SELECT a.table_name, a.row_id, a.action, a.field, a.old_value AS old, a.new_value AS new, a.changed_at
        FROM audit_log a WHERE a.changed_by = ? ORDER BY a.audit_id DESC LIMIT 30"""),
]

PRODUCT_SECTIONS = [
    ("Price and status history", "clock", """
        SELECT a.field, a.old_value AS old, a.new_value AS new, u.user_id AS _uid, u.name AS changed_by, a.changed_at
        FROM audit_log a LEFT JOIN users u ON u.user_id = a.changed_by
        WHERE a.table_name = 'products' AND a.row_id = ? ORDER BY a.audit_id DESC"""),
    ("Offers", "receipt", """
        SELECT b.user_id AS _uid, b.name AS buyer, o.amount, o.counter_amount AS counter, o.status, o.created_at AS offered_at
        FROM offers o JOIN users b ON b.user_id = o.buyer_id
        WHERE o.product_id = ? ORDER BY o.created_at DESC"""),
    ("Orders", "bag", """
        SELECT b.user_id AS _uid, b.name AS buyer, o.price, o.status, o.ordered_at
        FROM orders o JOIN users b ON b.user_id = o.buyer_id
        WHERE o.product_id = ? ORDER BY o.ordered_at DESC"""),
    ("Saved to wishlist by", "heart", """
        SELECT u.user_id AS _uid, u.name AS student, w.added_at
        FROM wishlist w JOIN users u ON u.user_id = w.user_id WHERE w.product_id = ?"""),
    ("Viewed by", "eye", """
        SELECT u.user_id AS _uid, u.name AS student, COUNT(*) AS views, MAX(v.viewed_at) AS last_viewed_at
        FROM product_views v JOIN users u ON u.user_id = v.user_id
        WHERE v.product_id = ? GROUP BY u.user_id ORDER BY views DESC"""),
    ("Also viewed (collaborative filtering)", "sparkles", """
        SELECT d.product_id AS _pid, d.title, COUNT(DISTINCT v2.user_id) AS shared_viewers
        FROM product_views v1
        JOIN product_views v2    ON v2.user_id = v1.user_id AND v2.product_id <> v1.product_id
        JOIN v_product_details d ON d.product_id = v2.product_id
        WHERE v1.product_id = ? GROUP BY v2.product_id ORDER BY shared_viewers DESC LIMIT 6"""),
]

REPORTS = {
    "leaderboard": ("Seller leaderboard", "CTE + view", """
        WITH seller_sales AS (
          SELECT p.seller_id, COUNT(*) AS sold, SUM(o.price) AS revenue
          FROM orders o JOIN products p ON p.product_id = o.product_id
          WHERE o.status <> 'cancelled' GROUP BY p.seller_id
        )
        SELECT u.user_id AS _uid, u.name AS seller, ss.sold, ss.revenue, COALESCE(r.avg_rating, 0) AS rating
        FROM seller_sales ss JOIN users u ON u.user_id = ss.seller_id
        LEFT JOIN v_seller_ratings r ON r.seller_id = ss.seller_id
        ORDER BY ss.revenue DESC"""),
    "demand": ("Unmet demand", "Correlated subquery", """
        SELECT s.query AS search,
               (SELECT COUNT(*) FROM products p
                WHERE p.status = 'available' AND p.title LIKE '%' || s.query || '%') AS matching_items
        FROM (SELECT DISTINCT LOWER(query) AS query FROM search_history) s
        ORDER BY matching_items ASC, search"""),
    "price_rank": ("Price rank in each category", "Window function", """
        SELECT c.name AS category, p.product_id AS _pid, p.title, p.price,
               RANK() OVER (PARTITION BY p.category_id ORDER BY p.price DESC) AS price_rank
        FROM products p JOIN categories c ON c.category_id = p.category_id
        WHERE p.status = 'available' ORDER BY c.name, price_rank"""),
    "never_viewed": ("Listings nobody has viewed", "NOT EXISTS", """
        SELECT p.product_id AS _pid, p.title, p.price, p.created_at AS listed_at
        FROM products p
        WHERE p.status = 'available'
          AND NOT EXISTS (SELECT 1 FROM product_views v WHERE v.product_id = p.product_id)"""),
    "offers": ("Offer outcomes", "GROUP BY + aggregate", """
        SELECT o.status, COUNT(*) AS offers,
               ROUND(AVG(100.0 * (p.price - o.amount) / p.price)) AS avg_discount_asked_pct
        FROM offers o JOIN products p ON p.product_id = o.product_id
        GROUP BY o.status ORDER BY offers DESC"""),
    "price_drops": ("Price drops", "Audit log (trigger output)", """
        SELECT p.product_id AS _pid, p.title, a.old_value AS old, a.new_value AS new, u.name AS changed_by, a.changed_at
        FROM audit_log a JOIN products p ON p.product_id = a.row_id
        LEFT JOIN users u ON u.user_id = a.changed_by
        WHERE a.table_name = 'products' AND a.field = 'price'
          AND CAST(a.new_value AS REAL) < CAST(a.old_value AS REAL)
        ORDER BY a.audit_id DESC"""),
    "category_sales": ("Sales by category", "View", """
        SELECT name AS category, items_sold, revenue FROM v_category_sales ORDER BY revenue DESC"""),
    "condition": ("Value kept by condition", "GROUP BY + AVG", """
        SELECT condition, COUNT(*) AS items, ROUND(AVG(100.0 * price / original_price)) AS avg_pct_of_mrp
        FROM products WHERE status IN ('available', 'sold')
        GROUP BY condition ORDER BY avg_pct_of_mrp DESC"""),
    "buyers_sellers": ("Who buys, who sells", "UNION", """
        SELECT user_id AS _uid, name AS student, 'Seller' AS activity FROM users
        WHERE user_id IN (SELECT seller_id FROM products)
        UNION
        SELECT user_id, name, 'Buyer' FROM users
        WHERE user_id IN (SELECT buyer_id FROM orders)
        ORDER BY student"""),
}


@app.route("/admin/lookup")
@admin_required
def admin_lookup():
    """Look up any student or item by name: no SQL typing needed. Every panel can show
    the parameterised query that produced it, for explaining in a viva."""
    q = request.args.get("q", "").strip()
    uid = request.args.get("user", type=int)
    pid = request.args.get("product", type=int)
    report_key = request.args.get("report")
    ctx = {"q": q, "reports": REPORTS, "report_key": report_key}
    ctx["names"] = query("""SELECT name AS label, 'Student' AS kind FROM users
                            UNION ALL SELECT title, 'Item' FROM products ORDER BY 1""")

    if q and not uid and not pid:
        users = query("""SELECT user_id, name, email, branch, year, role FROM users
                         WHERE name LIKE ? OR email LIKE ? ORDER BY name""", (f"%{q}%", f"%{q}%"))
        items = query("""SELECT product_id, title, price, status, category_icon, category_id, seller_name
                         FROM v_product_details WHERE title LIKE ? ORDER BY title LIMIT 20""", (f"%{q}%",))
        if len(users) == 1 and not items:
            return redirect(url_for("admin_lookup", user=users[0]["user_id"]))
        if len(items) == 1 and not users:
            return redirect(url_for("admin_lookup", product=items[0]["product_id"]))
        ctx.update(match_users=users, match_items=items)

    if uid:
        person = query(USER_PROFILE_SQL, (uid,), one=True)
        if person is None:
            abort(404)
        ctx.update(person=person, profile_sql=USER_PROFILE_SQL,
                   sections=[_run(t, i, _sql(sql), (uid,)) for t, i, sql in USER_SECTIONS])
    elif pid:
        item = query("SELECT * FROM v_product_details WHERE product_id = ?", (pid,), one=True)
        if item is None:
            abort(404)
        ctx.update(item=item, sections=[_run(t, i, _sql(sql), (pid,)) for t, i, sql in PRODUCT_SECTIONS])

    if report_key in REPORTS:
        title, concept, sql = REPORTS[report_key]
        ctx["report"] = dict(_run(title, "chart", _sql(sql)), concept=concept)

    objects = query("""SELECT type, name, tbl_name, sql FROM sqlite_master
                       WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'
                       ORDER BY CASE type WHEN 'table' THEN 1 WHEN 'view' THEN 2
                                          WHEN 'trigger' THEN 3 ELSE 4 END, name""")
    ctx["objects"] = objects
    ctx["counts"] = {o["name"]: query(f'SELECT COUNT(*) AS n FROM "{o["name"]}"', one=True)["n"]
                     for o in objects if o["type"] == "table"}
    return render_template("admin/lookup.html", **ctx)


@app.route("/admin/database")
@admin_required
def admin_database():
    return redirect(url_for("admin_lookup"))


@app.route("/admin/audit")
@admin_required
def admin_audit():
    table = request.args.get("table", "")
    tables = ["products", "orders", "offers", "users", "reviews"]
    sql = """SELECT a.*, u.name AS actor, p.title AS product_title
             FROM audit_log a
             LEFT JOIN users u    ON u.user_id = a.changed_by
             LEFT JOIN products p ON a.table_name = 'products' AND p.product_id = a.row_id"""
    args = ()
    if table in tables:
        sql += " WHERE a.table_name = ?"
        args = (table,)
    rows = query(sql + " ORDER BY a.audit_id DESC LIMIT 200", args)
    counts = {r["table_name"]: r["n"] for r in query(
        "SELECT table_name, COUNT(*) AS n FROM audit_log GROUP BY table_name")}
    triggers = query("SELECT name, tbl_name FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'trg_audit%' ORDER BY name")
    return render_template("admin/audit.html", rows=rows, table=table, tables=tables, counts=counts,
                           total=sum(counts.values()), triggers=triggers)


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
