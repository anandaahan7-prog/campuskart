"""
AI Feature 1 : Personalised recommendations
-------------------------------------------
Content-based filtering using TF-IDF + cosine similarity.

1. Every available product is turned into a TF-IDF vector built from its
   title, category and description (character n-grams, so even misspelled
   searches like "arduno" or "calcu" still match).
2. A user's "interest signals" are collected from the database:
      - recent search queries           (search_history table)
      - recently viewed products        (product_views table)
      - products in the wishlist        (wishlist table)
   Newer signals get a higher weight (recency decay).
3. Each product's score = the strongest  weight * cosine_similarity(signal, product)
   over all signals (matches below MIN_SCORE are ignored).
4. That strongest signal becomes the explanation shown to the user,
   e.g.  "Because you searched 'dbms book'".

If the user has no history (new user) we fall back to trending products
(most viewed in the last 30 days) - this is the classic "cold start" problem.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SEARCH_WEIGHT = 1.0
VIEW_WEIGHT = 0.8
WISHLIST_WEIGHT = 1.0
DECAY = 0.9           # every older signal counts 10% less than the previous one
MIN_SCORE = 0.15      # ignore weak matches (cosine similarity below this)


def _product_text(p):
    # Title is repeated so it matters more than the long description.
    return f"{p['title']} {p['title']} {p['category_name']} {p['description']}".lower()


def _build_index(products):
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
    matrix = vectorizer.fit_transform([_product_text(p) for p in products])
    return vectorizer, matrix


def _available_products(db):
    return db.execute(
        "SELECT * FROM v_product_details WHERE status = 'available'"
    ).fetchall()


def _user_signals(db, user_id):
    """Returns a list of (text, weight, reason, source_product_id) tuples, newest first."""
    signals = []

    searches = db.execute(
        """SELECT query, MAX(searched_at) AS t FROM search_history
           WHERE user_id = ? GROUP BY LOWER(query) ORDER BY t DESC LIMIT 10""",
        (user_id,),
    ).fetchall()
    for i, s in enumerate(searches):
        signals.append((s["query"].lower(), SEARCH_WEIGHT * DECAY ** i,
                        f"Because you searched “{s['query']}”", None))

    views = db.execute(
        """SELECT p.product_id, p.title, p.description, c.name AS category_name,
                  MAX(v.viewed_at) AS t
           FROM product_views v
           JOIN products p   ON p.product_id = v.product_id
           JOIN categories c ON c.category_id = p.category_id
           WHERE v.user_id = ? GROUP BY v.product_id ORDER BY t DESC LIMIT 10""",
        (user_id,),
    ).fetchall()
    for i, v in enumerate(views):
        signals.append((_product_text(v), VIEW_WEIGHT * DECAY ** i,
                        f"Similar to “{v['title']}” you viewed", v["product_id"]))

    wish = db.execute(
        """SELECT p.product_id, p.title, p.description, c.name AS category_name
           FROM wishlist w
           JOIN products p   ON p.product_id = w.product_id
           JOIN categories c ON c.category_id = p.category_id
           WHERE w.user_id = ? ORDER BY w.added_at DESC LIMIT 5""",
        (user_id,),
    ).fetchall()
    for i, w in enumerate(wish):
        signals.append((_product_text(w), WISHLIST_WEIGHT * DECAY ** i,
                        f"Similar to “{w['title']}” in your wishlist", w["product_id"]))

    return signals


def trending(db, user_id=None, n=8):
    """Cold-start fallback: most viewed available products in last 30 days."""
    rows = db.execute(
        """SELECT d.*, COUNT(v.view_id) AS views
           FROM v_product_details d
           LEFT JOIN product_views v ON v.product_id = d.product_id
                AND v.viewed_at >= datetime('now', 'localtime', '-30 days')
           WHERE d.status = 'available' AND d.seller_id <> COALESCE(?, -1)
           GROUP BY d.product_id
           ORDER BY views DESC, d.created_at DESC
           LIMIT ?""",
        (user_id, n),
    ).fetchall()
    return [{"product": r, "score": None, "reason": "Trending on campus"} for r in rows]


def recommend_for_user(db, user_id, n=8):
    """Main entry point. Returns (list_of_recommendations, is_personalised)."""
    signals = _user_signals(db, user_id)
    products = [p for p in _available_products(db) if p["seller_id"] != user_id]
    if not signals or not products:
        return trending(db, user_id, n), False

    # Items already in the wishlist are not recommended again.
    wishlisted = {r["product_id"] for r in db.execute(
        "SELECT product_id FROM wishlist WHERE user_id = ?", (user_id,))}
    products = [p for p in products if p["product_id"] not in wishlisted]
    if not products:
        return trending(db, user_id, n), False

    vectorizer, product_matrix = _build_index(products)
    signal_matrix = vectorizer.transform([s[0] for s in signals])

    # similarity[i][j] = how similar signal i is to product j
    similarity = cosine_similarity(signal_matrix, product_matrix)

    results = []
    for j, product in enumerate(products):
        best_score, best_i = 0.0, None
        for i, (_, weight, _, source_id) in enumerate(signals):
            if source_id == product["product_id"]:
                continue        # don't say "similar to X" for X itself
            if similarity[i][j] < MIN_SCORE:
                continue        # too weak to count as a real match
            contribution = weight * similarity[i][j]
            if contribution > best_score:
                best_score, best_i = contribution, i
        if best_i is not None:
            results.append({"product": product, "score": round(float(best_score), 3),
                            "reason": signals[best_i][2]})

    results.sort(key=lambda r: r["score"], reverse=True)
    results = results[:n]
    if not results:
        return trending(db, user_id, n), False
    return results, True


def similar_products(db, product_id, n=4):
    """'You may also like' on the product page."""
    products = _available_products(db)
    ids = [p["product_id"] for p in products]
    target = db.execute(
        "SELECT * FROM v_product_details WHERE product_id = ?", (product_id,)
    ).fetchone()
    if target is None or not products:
        return []

    vectorizer, matrix = _build_index(products)
    target_vec = vectorizer.transform([_product_text(target)])
    scores = cosine_similarity(target_vec, matrix)[0]

    ranked = sorted(zip(products, scores), key=lambda x: x[1], reverse=True)
    return [{"product": p, "score": round(float(s), 3)}
            for p, s in ranked if p["product_id"] != product_id and s > MIN_SCORE][:n]
