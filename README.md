# 🛒 CampusKart: AI-Powered Student Marketplace

A second-hand marketplace where college students buy and sell books, calculators, lab coats,
cycles and hostel items. It has three AI features: personalised recommendations from search
history, a fair-price predictor and a spam-listing detector.

**Tech stack:** Python · Flask · SQLite · scikit-learn · HTML/CSS/JS. It needs no internet
connection or database server.

**Live demo:** https://campuskart-delta-lilac.vercel.app (demo data resets periodically,
because Vercel gives each server instance a fresh copy of the database).

---

## 1. How to run

```bash
pip install -r requirements.txt
python seed.py        # creates campuskart.db with demo data (run again any time to reset)
python app.py         # open http://127.0.0.1:5000
```

Optional: `python test_app.py` runs automated tests of every page and flow. It resets the
database, so run `python seed.py` afterwards.

## 2. Demo accounts

On the login page you can **click any demo account** to log in instantly.

| User | Email | Password | What to show |
|---|---|---|---|
| Admin | admin@campuskart.com | admin123 | Dashboard, AI-flagged listings, users, SQL explorer |
| Rahul Sharma (CSE, 3rd yr) | rahul@college.edu | demo123 | Searched *dbms book, python, laptop…* → gets CS books and keyboard |
| Priya Patel (Mech, 2nd yr) | priya@college.edu | demo123 | Searched *engineering drawing, drafter…* → gets drawing tools and calculators |
| Karan Mehta (ECE, 3rd yr) | karan@college.edu | demo123 | Searched *arduino, multimeter…* → gets electronics |
| Aisha Khan (IT, 1st yr) | aisha@college.edu | demo123 | Searched *cycle, mattress, kettle…* → gets hostel items and cycles |
| Neha Gupta (Civil, 1st yr) | neha@college.edu | demo123 | **New user with no history** → sees "Trending" (cold-start problem) |

Seller accounts (vikram, sneha, arjun, meera, rohan, ravi @college.edu) also use `demo123`.

## 3. Suggested presentation flow (about 10 minutes)

1. **Login page:** explain the demo accounts and that every student has a different history.
2. **Rahul:** the home page shows *"Recommended for you"*, each card with a reason such as
   *"Because you searched 'python'"*.
3. **Log out, then Priya:** same website, completely different recommendations.
4. **Neha:** no history, so the site falls back to trending items. Search "cycle" and go back
   home: the feed is now personalised.
5. **Search a typo**, e.g. `arduno` or `calculatr`: there's no exact match, but AI shows
   *"Did you mean…"*.
6. **Product page:** AI price badge (*Great deal / Fair / Overpriced*) and *Similar items*.
7. **Sell page:** enter MRP, condition and age, then click **✨ Suggest price**. Type
   "whatsapp me" in the title to see the live spam warning.
8. **Buy an item:** it disappears from listings (trigger). Log in as the seller to see the
   notification (trigger).
9. **Admin:** dashboard stats come from views, there are flagged listings to approve or reject,
   you can block a user, and the **Database explorer** shows all tables, views and triggers and
   lets you run live SELECT queries.

---

## 4. Database design

### ER summary
```
USERS 1──N PRODUCTS N──1 CATEGORIES
USERS 1──N ORDERS N──1 PRODUCTS
ORDERS 1──1 REVIEWS
USERS M──N PRODUCTS  (via WISHLIST, composite PK)
USERS 1──N SEARCH_HISTORY
USERS 1──N PRODUCT_VIEWS N──1 PRODUCTS
USERS 1──N NOTIFICATIONS
```

### Tables (9)
| Table | Purpose | Key constraints |
|---|---|---|
| users | students and admins | PK, UNIQUE email, CHECK role/year |
| categories | 9 item categories | UNIQUE name |
| products | listings | FK seller/category, CHECK price > 0, CHECK condition/status |
| orders | purchases | FK product/buyer, CHECK status |
| reviews | rating of a seller per order | UNIQUE order_id (1:1), CHECK rating 1-5 |
| wishlist | saved items | **composite PK (user_id, product_id)** |
| search_history | every search (AI input) | FK user, ON DELETE CASCADE |
| product_views | every product opened (AI input) | FK user, product |
| notifications | alerts, mostly from triggers | FK user |

### Normalization (3NF)
- **1NF:** every column is atomic (no lists stored in one column; wishlist is a separate table).
- **2NF:** the only composite key is wishlist(user_id, product_id), and `added_at` depends on the whole key.
- **3NF:** no transitive dependencies. For example, `orders` does **not** store `seller_id`,
  because it can be derived through `products`, and seller rating is computed by a view
  instead of being stored.

### Triggers (6)
| Trigger | When | What it does |
|---|---|---|
| trg_order_validate | BEFORE INSERT on orders | Aborts if the item is already sold or the buyer is the seller (prevents double selling) |
| trg_order_placed | AFTER INSERT on orders | Marks product *sold* and notifies the seller |
| trg_order_cancelled | AFTER UPDATE on orders | Puts product back on sale and notifies the seller |
| trg_wishlist_sold_alert | AFTER UPDATE on products | Notifies users who wishlisted a product when it is sold |
| trg_flagged_listing | AFTER INSERT on products | Notifies admins when AI flags a listing |
| trg_listing_moderated | AFTER UPDATE on products | Tells the seller their listing was approved or rejected |

### Views (4)
`v_product_details` (4-table join), `v_seller_ratings` (AVG + GROUP BY), `v_category_sales`
(LEFT JOIN + SUM), `v_admin_stats` (scalar subqueries).

### Other DBMS concepts used
- **Transactions:** every write uses `with db:`, which commits on success and rolls back on error.
  Buying is atomic: the order insert, the product status change and the notification either all
  happen or none do.
- **Indexes:** on products(status, category_id), search_history(user_id, searched_at) and others.
- **Referential integrity:** foreign keys with `ON DELETE CASCADE`.
- **Security:** parameterised queries (no SQL injection), hashed passwords (Werkzeug PBKDF2),
  and a read-only connection for the SQL explorer.

---

## 5. AI features (all in `ai/`)

### AI 1: Recommendations (`ai/recommender.py`)
- **Technique:** content-based filtering with **TF-IDF + cosine similarity**.
- Each product becomes a TF-IDF vector of its title, category and description, using character
  n-grams so typos still match.
- User signals come from the **last 10 searches, last 10 viewed items and wishlist**. Newer signals
  get a higher weight (10% decay per step).
- A product's score is the best `weight × similarity` across all signals, and that signal becomes
  the explanation shown on the card.
- **Cold start:** a new user with no history sees the most-viewed items of the last 30 days.
- The same index powers **"Similar items"** and the **typo-tolerant "Did you mean"** search.

### AI 2: Fair-price prediction (`ai/price_predictor.py`)
- **Technique:** **Linear Regression** on the listings in the database.
- Predicts the *resale ratio* (price ÷ MRP) from condition (one-hot), age and category (one-hot).
- Suggested price = ratio × MRP, rounded, with a ±10% range.
- The same model labels listings for buyers: *Great deal / Fair price / Overpriced*.

### AI 3: Spam-listing detection (`ai/spam_detector.py`)
- **Technique:** **Multinomial Naive Bayes** on TF-IDF words and bigrams, trained on 38 labelled examples.
- Plus explainable rules: phone numbers or links, payment words (UPI, GPay, OTP), a price above MRP,
  and a price below 5% of MRP.
- A score ≥ 0.5 saves the listing as *pending*. A trigger alerts admins, who approve or reject it.

---

## 6. Likely viva questions

- **Why SQLite?** It's a full relational DBMS (ACID, triggers, views, FKs) with zero setup, which is
  ideal for a demo. The SQL is standard, so moving to MySQL needs only small changes (AUTOINCREMENT →
  AUTO_INCREMENT, `datetime('now')` → `NOW()`, and `RAISE` → `SIGNAL` in triggers).
- **How do you prevent two people buying the same item?** The BEFORE INSERT trigger checks the status
  inside the same transaction, so the second insert is aborted.
- **Why TF-IDF and not deep learning?** The data is small, TF-IDF is fast and explainable, and it
  needs no training time.
- **What is the cold-start problem?** A new user has no history to learn from, so we show trending items.
- **Why predict a ratio instead of the price?** Prices range from ₹100 to ₹50,000. A ratio is on the
  same scale for all items, so one simple model works for everything.
- **How is search history privacy handled?** Users can view and clear their history from the
  profile page.

## 7. Project report (IEEE format)

`report/CampusKart_IEEE_Report.docx` (editable) and `report/CampusKart_IEEE_Report.pdf` are
in IEEE two-column A4 conference format. Before submitting, replace the **yellow-highlighted
placeholders** (author names, department, college, guide) in the Word file and export it to PDF again.

All diagrams are in `report/figures/` as 300-dpi PNGs: ER diagram, relational schema,
architecture, DFD level 0 and level 1, use case, recommendation flowchart, purchase sequence
diagram, and website screenshots. To regenerate them:

```bash
python report/make_diagrams.py        # diagrams
python report/take_screenshots.py     # screenshots (app must be running; run seed.py afterwards)
```

## 8. Project structure
```
campuskart/
├── app.py              Flask routes (auth, search, products, orders, admin)
├── schema.sql          tables, indexes, triggers, views
├── seed.py             demo data (users, 58 products, histories, orders)
├── test_app.py         automated tests
├── ai/
│   ├── recommender.py  AI 1: TF-IDF recommendations
│   ├── price_predictor.py  AI 2: linear regression pricing
│   └── spam_detector.py    AI 3: Naive Bayes spam filter
├── templates/          HTML pages (Jinja2)
└── static/style.css    styling (no external CSS framework)
```
