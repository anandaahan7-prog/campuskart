"""
AI Feature 2 : Fair price suggestion (+ "Great deal / Overpriced" badge)
-----------------------------------------------------------------------
Linear Regression trained on the existing listings in the database.

Instead of predicting the price directly, the model predicts the
RESALE RATIO = price / original_price  (e.g. 0.55 means 55% of MRP).
This keeps the model simple and works for a Rs.200 book and a Rs.40,000
laptop alike.

Features used:
  - condition      (one-hot: New, Like New, Good, Fair)
  - age_months     (how old the item is)
  - category       (one-hot: Books, Electronics, ...)

suggested_price = predicted_ratio * original_price

The same model is reused on the product page to tell buyers whether a
listed price is a great deal, fair, or overpriced.
"""

import numpy as np
from sklearn.linear_model import LinearRegression

CONDITIONS = ["New", "Like New", "Good", "Fair"]


def _features(condition, age_months, category_id, category_ids):
    row = [1.0 if condition == c else 0.0 for c in CONDITIONS]
    row.append(min(age_months, 60) / 12.0)          # age in years, capped at 5
    row += [1.0 if category_id == cid else 0.0 for cid in category_ids]
    return row


def _train(db):
    category_ids = [r["category_id"] for r in
                    db.execute("SELECT category_id FROM categories ORDER BY category_id")]
    rows = db.execute(
        """SELECT price, original_price, condition, age_months, category_id
           FROM products WHERE status IN ('available', 'sold') AND is_flagged = 0"""
    ).fetchall()
    if len(rows) < 10:
        return None, category_ids

    X = np.array([_features(r["condition"], r["age_months"], r["category_id"], category_ids)
                  for r in rows])
    y = np.array([min(r["price"] / r["original_price"], 1.0) for r in rows])
    model = LinearRegression().fit(X, y)
    return model, category_ids


def predict_price(db, original_price, condition, age_months, category_id):
    """Returns dict with suggested price and a min-max range, or None."""
    model, category_ids = _train(db)
    if model is None or original_price <= 0:
        return None

    x = np.array([_features(condition, age_months, category_id, category_ids)])
    ratio = float(model.predict(x)[0])
    ratio = max(0.10, min(ratio, 0.95))              # keep inside a sane range
    price = original_price * ratio

    return {
        "suggested": _round_price(price),
        "low": _round_price(price * 0.9),
        "high": _round_price(price * 1.1),
        "ratio_percent": round(ratio * 100),
        "trained_on": len(db.execute(
            "SELECT 1 FROM products WHERE status IN ('available','sold') AND is_flagged = 0"
        ).fetchall()),
    }


def price_verdict(db, product):
    """Compares a listing's price with the AI estimate -> badge for buyers."""
    pred = predict_price(db, product["original_price"], product["condition"],
                         product["age_months"], product["category_id"])
    if pred is None:
        return None
    diff = (product["price"] - pred["suggested"]) / pred["suggested"] * 100
    if diff <= -10:
        label, css = "Great deal", "good"
    elif diff <= 12:
        label, css = "Fair price", "fair"
    else:
        label, css = "Overpriced", "bad"
    return {"label": label, "css": css, "estimate": pred["suggested"], "diff": round(diff)}


def _round_price(value):
    # Round to a "nice" number: nearest 10 below 1000, nearest 50 above.
    step = 10 if value < 1000 else 50
    return int(max(step, round(value / step) * step))
