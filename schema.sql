-- =====================================================================
--  CampusKart : AI-powered second-hand marketplace for students
--  Database schema (SQLite)  -  11 tables (+1 helper), 4 views, 21 triggers, indexes
--  All tables are in 3NF.
-- =====================================================================

PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS v_product_details;
DROP VIEW IF EXISTS v_seller_ratings;
DROP VIEW IF EXISTS v_category_sales;
DROP VIEW IF EXISTS v_admin_stats;

DROP TABLE IF EXISTS audit_context;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS offers;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS product_views;
DROP TABLE IF EXISTS search_history;
DROP TABLE IF EXISTS wishlist;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS users;

-- ---------------------------------------------------------------------
-- 1. USERS : students and admins
-- ---------------------------------------------------------------------
CREATE TABLE users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    branch        TEXT,
    year          INTEGER CHECK (year BETWEEN 1 AND 4),
    phone         TEXT,
    is_blocked    INTEGER NOT NULL DEFAULT 0 CHECK (is_blocked IN (0, 1)),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ---------------------------------------------------------------------
-- 2. CATEGORIES
-- ---------------------------------------------------------------------
CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    icon        TEXT NOT NULL            -- emoji shown on the website
);

-- ---------------------------------------------------------------------
-- 3. PRODUCTS : items listed for sale
-- ---------------------------------------------------------------------
CREATE TABLE products (
    product_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id      INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    category_id    INTEGER NOT NULL REFERENCES categories(category_id),
    title          TEXT    NOT NULL,
    description    TEXT    NOT NULL,
    original_price REAL    NOT NULL CHECK (original_price > 0),
    price          REAL    NOT NULL CHECK (price > 0),
    condition      TEXT    NOT NULL CHECK (condition IN ('New', 'Like New', 'Good', 'Fair')),
    age_months     INTEGER NOT NULL DEFAULT 0 CHECK (age_months >= 0),
    status         TEXT    NOT NULL DEFAULT 'available'
                   CHECK (status IN ('pending', 'available', 'sold', 'rejected', 'removed')),
    is_flagged     INTEGER NOT NULL DEFAULT 0 CHECK (is_flagged IN (0, 1)),
    spam_score     REAL    NOT NULL DEFAULT 0,      -- filled by AI spam detector
    flag_reason    TEXT,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ---------------------------------------------------------------------
-- 4. ORDERS : one row per purchase
-- ---------------------------------------------------------------------
CREATE TABLE orders (
    order_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    buyer_id   INTEGER NOT NULL REFERENCES users(user_id),
    price      REAL    NOT NULL CHECK (price > 0),
    status     TEXT    NOT NULL DEFAULT 'placed'
               CHECK (status IN ('placed', 'completed', 'cancelled')),
    ordered_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ---------------------------------------------------------------------
-- 5. REVIEWS : buyer rates the seller after a completed order
-- ---------------------------------------------------------------------
CREATE TABLE reviews (
    review_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id   INTEGER NOT NULL UNIQUE REFERENCES orders(order_id),  -- one review per order
    rating     INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment    TEXT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ---------------------------------------------------------------------
-- 6. WISHLIST : composite primary key (M:N between users and products)
-- ---------------------------------------------------------------------
CREATE TABLE wishlist (
    user_id    INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    added_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    PRIMARY KEY (user_id, product_id)
);

-- ---------------------------------------------------------------------
-- 7. SEARCH_HISTORY : input for the AI recommender
-- ---------------------------------------------------------------------
CREATE TABLE search_history (
    search_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    query       TEXT    NOT NULL,
    searched_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ---------------------------------------------------------------------
-- 8. PRODUCT_VIEWS : which products a user opened (input for recommender)
-- ---------------------------------------------------------------------
CREATE TABLE product_views (
    view_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    viewed_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ---------------------------------------------------------------------
-- 9. NOTIFICATIONS : mostly created automatically by triggers
-- ---------------------------------------------------------------------
CREATE TABLE notifications (
    notif_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    message    TEXT    NOT NULL,
    is_read    INTEGER NOT NULL DEFAULT 0 CHECK (is_read IN (0, 1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ---------------------------------------------------------------------
-- 10. OFFERS : bargaining. A buyer offers below the asking price; the seller
--     accepts, rejects or counters. Status moves through a small state machine:
--       pending   -> accepted | rejected | countered | withdrawn | expired
--       countered -> accepted | withdrawn | expired
-- ---------------------------------------------------------------------
CREATE TABLE offers (
    offer_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id     INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    buyer_id       INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    amount         REAL    NOT NULL CHECK (amount > 0),
    counter_amount REAL    CHECK (counter_amount IS NULL OR counter_amount > amount),
    message        TEXT,
    status         TEXT    NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending', 'countered', 'accepted', 'rejected', 'withdrawn', 'expired')),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT
);

-- ---------------------------------------------------------------------
-- 11. AUDIT_LOG : every important change, written only by triggers
-- ---------------------------------------------------------------------
CREATE TABLE audit_log (
    audit_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT    NOT NULL,
    row_id     INTEGER NOT NULL,
    action     TEXT    NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    field      TEXT,
    old_value  TEXT,
    new_value  TEXT,
    changed_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    changed_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Helper (one row): which user the application is acting for right now.
-- The app sets it at the start of every write transaction so triggers can
-- record "who" in audit_log (triggers cannot see the web session).
CREATE TABLE audit_context (
    id      INTEGER PRIMARY KEY CHECK (id = 1),
    user_id INTEGER
);
INSERT INTO audit_context (id, user_id) VALUES (1, NULL);

-- =====================================================================
--  INDEXES : speed up the most frequent queries
-- =====================================================================
CREATE INDEX idx_products_status_cat ON products(status, category_id);
CREATE INDEX idx_products_seller     ON products(seller_id);
CREATE INDEX idx_orders_buyer        ON orders(buyer_id);
CREATE INDEX idx_search_user         ON search_history(user_id, searched_at);
CREATE INDEX idx_views_user          ON product_views(user_id, viewed_at);
CREATE INDEX idx_notif_user          ON notifications(user_id, is_read);
CREATE INDEX idx_views_product       ON product_views(product_id, user_id);   -- "also viewed" self-join
CREATE INDEX idx_offers_product      ON offers(product_id, status);
CREATE INDEX idx_offers_buyer        ON offers(buyer_id);
CREATE INDEX idx_audit_row           ON audit_log(table_name, row_id);
CREATE INDEX idx_audit_time          ON audit_log(changed_at);
-- Partial unique index: a buyer can have only ONE open offer per product.
CREATE UNIQUE INDEX uq_open_offer    ON offers(product_id, buyer_id) WHERE status IN ('pending', 'countered');

-- =====================================================================
--  TRIGGERS : business rules enforced inside the database
-- =====================================================================

-- T1. Block buying an item that is not available, or buying your own item.
CREATE TRIGGER trg_order_validate
BEFORE INSERT ON orders
BEGIN
    SELECT RAISE(ABORT, 'This product is no longer available')
    WHERE (SELECT status FROM products WHERE product_id = NEW.product_id) <> 'available';

    SELECT RAISE(ABORT, 'You cannot buy your own product')
    WHERE (SELECT seller_id FROM products WHERE product_id = NEW.product_id) = NEW.buyer_id;
END;

-- T2. When an order is placed: mark product sold and notify the seller.
CREATE TRIGGER trg_order_placed
AFTER INSERT ON orders
BEGIN
    UPDATE products SET status = 'sold' WHERE product_id = NEW.product_id;

    INSERT INTO notifications (user_id, message)
    SELECT p.seller_id,
           'Your item "' || p.title || '" was bought by ' ||
           (SELECT name FROM users WHERE user_id = NEW.buyer_id) ||
           ' for Rs. ' || CAST(NEW.price AS INTEGER) || '.'
    FROM products p WHERE p.product_id = NEW.product_id;
END;

-- T3. When an order is cancelled: put the product back on sale and notify seller.
CREATE TRIGGER trg_order_cancelled
AFTER UPDATE OF status ON orders
WHEN NEW.status = 'cancelled' AND OLD.status = 'placed'
BEGIN
    UPDATE products SET status = 'available' WHERE product_id = NEW.product_id;

    INSERT INTO notifications (user_id, message)
    SELECT p.seller_id, 'Order for "' || p.title || '" was cancelled. It is listed again.'
    FROM products p WHERE p.product_id = NEW.product_id;
END;

-- T4. When a product is sold: tell everyone who had it in their wishlist.
CREATE TRIGGER trg_wishlist_sold_alert
AFTER UPDATE OF status ON products
WHEN NEW.status = 'sold' AND OLD.status = 'available'
BEGIN
    INSERT INTO notifications (user_id, message)
    SELECT w.user_id, 'An item in your wishlist, "' || NEW.title || '", has been sold.'
    FROM wishlist w
    WHERE w.product_id = NEW.product_id
      AND w.user_id <> (SELECT buyer_id FROM orders
                        WHERE product_id = NEW.product_id ORDER BY order_id DESC LIMIT 1);
END;

-- T5. When the AI flags a new listing: alert every admin.
CREATE TRIGGER trg_flagged_listing
AFTER INSERT ON products
WHEN NEW.is_flagged = 1
BEGIN
    INSERT INTO notifications (user_id, message)
    SELECT user_id, 'AI flagged a suspicious listing: "' || NEW.title || '". Please review.'
    FROM users WHERE role = 'admin';
END;

-- T6. When an admin approves/rejects a listing: notify the seller.
CREATE TRIGGER trg_listing_moderated
AFTER UPDATE OF status ON products
WHEN OLD.status = 'pending' AND NEW.status IN ('available', 'rejected')
BEGIN
    INSERT INTO notifications (user_id, message)
    VALUES (NEW.seller_id,
            CASE NEW.status
                WHEN 'available' THEN 'Your listing "' || NEW.title || '" was approved and is now live.'
                ELSE 'Your listing "' || NEW.title || '" was rejected by the admin.'
            END);
END;

-- T7. Price-drop alert: when a seller lowers the price, tell everyone who
--     wishlisted the item (compares OLD and NEW values).
CREATE TRIGGER trg_price_drop_alert
AFTER UPDATE OF price ON products
WHEN NEW.price < OLD.price AND NEW.status = 'available'
BEGIN
    INSERT INTO notifications (user_id, message)
    SELECT w.user_id,
           'Price drop: "' || NEW.title || '" is now Rs. ' || CAST(NEW.price AS INTEGER) ||
           ' (was Rs. ' || CAST(OLD.price AS INTEGER) || ').'
    FROM wishlist w
    WHERE w.product_id = NEW.product_id AND w.user_id <> NEW.seller_id;
END;

-- T8. Offers must be for an available item, by someone other than the seller,
--     and below the asking price.
CREATE TRIGGER trg_offer_validate
BEFORE INSERT ON offers
BEGIN
    SELECT RAISE(ABORT, 'This product is no longer available')
    WHERE (SELECT status FROM products WHERE product_id = NEW.product_id) <> 'available';

    SELECT RAISE(ABORT, 'You cannot make an offer on your own product')
    WHERE (SELECT seller_id FROM products WHERE product_id = NEW.product_id) = NEW.buyer_id;

    SELECT RAISE(ABORT, 'Offer must be below the asking price')
    WHERE NEW.amount >= (SELECT price FROM products WHERE product_id = NEW.product_id);
END;

-- T9. New offer: notify the seller.
CREATE TRIGGER trg_offer_created
AFTER INSERT ON offers
BEGIN
    INSERT INTO notifications (user_id, message)
    SELECT p.seller_id,
           (SELECT name FROM users WHERE user_id = NEW.buyer_id) || ' offered Rs. ' ||
           CAST(NEW.amount AS INTEGER) || ' for "' || p.title || '" (you asked Rs. ' ||
           CAST(p.price AS INTEGER) || ').'
    FROM products p WHERE p.product_id = NEW.product_id;
END;

-- T10. Offer status changed: tell the other side what happened.
CREATE TRIGGER trg_offer_updated
AFTER UPDATE OF status ON offers
WHEN NEW.status <> OLD.status
BEGIN
    INSERT INTO notifications (user_id, message)
    SELECT NEW.buyer_id,
           CASE NEW.status
             WHEN 'countered' THEN 'The seller countered your offer on "' || p.title || '": Rs. ' ||
                                   CAST(NEW.counter_amount AS INTEGER) || '.'
             WHEN 'rejected'  THEN 'Your offer of Rs. ' || CAST(NEW.amount AS INTEGER) ||
                                   ' on "' || p.title || '" was declined.'
             WHEN 'accepted'  THEN 'Deal! Your offer on "' || p.title || '" was accepted. Check your orders.'
             WHEN 'expired'   THEN '"' || p.title || '" is no longer available, so your offer expired.'
           END
    FROM products p
    WHERE p.product_id = NEW.product_id AND NEW.status IN ('countered', 'rejected', 'accepted', 'expired');

    INSERT INTO notifications (user_id, message)
    SELECT p.seller_id,
           (SELECT name FROM users WHERE user_id = NEW.buyer_id) || ' withdrew their offer on "' || p.title || '".'
    FROM products p
    WHERE p.product_id = NEW.product_id AND NEW.status = 'withdrawn';
END;

-- T11. When an item is sold, removed or rejected, close every open offer on it.
CREATE TRIGGER trg_offers_expire
AFTER UPDATE OF status ON products
WHEN NEW.status IN ('sold', 'removed', 'rejected') AND OLD.status IN ('available', 'pending')
BEGIN
    UPDATE offers SET status = 'expired', updated_at = datetime('now', 'localtime')
    WHERE product_id = NEW.product_id AND status IN ('pending', 'countered');
END;

-- ---------------------------------------------------------------------
-- A1-A10. AUDIT TRIGGERS: record every important change in audit_log.
-- changed_by comes from audit_context, which the app sets per transaction.
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_audit_user_insert AFTER INSERT ON users
BEGIN
    INSERT INTO audit_log (table_name, row_id, action, field, new_value, changed_by)
    VALUES ('users', NEW.user_id, 'INSERT', 'account', NEW.name || ' <' || NEW.email || '>',
            (SELECT user_id FROM audit_context WHERE id = 1));
END;

CREATE TRIGGER trg_audit_user_block AFTER UPDATE OF is_blocked ON users
WHEN NEW.is_blocked <> OLD.is_blocked
BEGIN
    INSERT INTO audit_log (table_name, row_id, action, field, old_value, new_value, changed_by)
    VALUES ('users', NEW.user_id, 'UPDATE', 'is_blocked', OLD.is_blocked, NEW.is_blocked,
            (SELECT user_id FROM audit_context WHERE id = 1));
END;

CREATE TRIGGER trg_audit_product_insert AFTER INSERT ON products
BEGIN
    INSERT INTO audit_log (table_name, row_id, action, field, new_value, changed_by)
    VALUES ('products', NEW.product_id, 'INSERT', 'listing', NEW.title,
            (SELECT user_id FROM audit_context WHERE id = 1));
END;

CREATE TRIGGER trg_audit_product_price AFTER UPDATE OF price ON products
WHEN NEW.price <> OLD.price
BEGIN
    INSERT INTO audit_log (table_name, row_id, action, field, old_value, new_value, changed_by)
    VALUES ('products', NEW.product_id, 'UPDATE', 'price', OLD.price, NEW.price,
            (SELECT user_id FROM audit_context WHERE id = 1));
END;

CREATE TRIGGER trg_audit_product_status AFTER UPDATE OF status ON products
WHEN NEW.status <> OLD.status
BEGIN
    INSERT INTO audit_log (table_name, row_id, action, field, old_value, new_value, changed_by)
    VALUES ('products', NEW.product_id, 'UPDATE', 'status', OLD.status, NEW.status,
            (SELECT user_id FROM audit_context WHERE id = 1));
END;

CREATE TRIGGER trg_audit_order_insert AFTER INSERT ON orders
BEGIN
    INSERT INTO audit_log (table_name, row_id, action, field, new_value, changed_by)
    VALUES ('orders', NEW.order_id, 'INSERT', 'order', 'product #' || NEW.product_id || ' for ' || NEW.price,
            (SELECT user_id FROM audit_context WHERE id = 1));
END;

CREATE TRIGGER trg_audit_order_status AFTER UPDATE OF status ON orders
WHEN NEW.status <> OLD.status
BEGIN
    INSERT INTO audit_log (table_name, row_id, action, field, old_value, new_value, changed_by)
    VALUES ('orders', NEW.order_id, 'UPDATE', 'status', OLD.status, NEW.status,
            (SELECT user_id FROM audit_context WHERE id = 1));
END;

CREATE TRIGGER trg_audit_offer_insert AFTER INSERT ON offers
BEGIN
    INSERT INTO audit_log (table_name, row_id, action, field, new_value, changed_by)
    VALUES ('offers', NEW.offer_id, 'INSERT', 'offer', 'product #' || NEW.product_id || ' for ' || NEW.amount,
            (SELECT user_id FROM audit_context WHERE id = 1));
END;

CREATE TRIGGER trg_audit_offer_status AFTER UPDATE OF status ON offers
WHEN NEW.status <> OLD.status
BEGIN
    INSERT INTO audit_log (table_name, row_id, action, field, old_value, new_value, changed_by)
    VALUES ('offers', NEW.offer_id, 'UPDATE', 'status', OLD.status, NEW.status,
            (SELECT user_id FROM audit_context WHERE id = 1));
END;

CREATE TRIGGER trg_audit_review_insert AFTER INSERT ON reviews
BEGIN
    INSERT INTO audit_log (table_name, row_id, action, field, new_value, changed_by)
    VALUES ('reviews', NEW.review_id, 'INSERT', 'rating', NEW.rating,
            (SELECT user_id FROM audit_context WHERE id = 1));
END;

-- =====================================================================
--  VIEWS : reusable read-only queries
-- =====================================================================

-- Average rating of every seller (via orders -> reviews).
CREATE VIEW v_seller_ratings AS
SELECT p.seller_id,
       ROUND(AVG(r.rating), 1) AS avg_rating,
       COUNT(r.review_id)      AS review_count
FROM reviews r
JOIN orders   o ON o.order_id   = r.order_id
JOIN products p ON p.product_id = o.product_id
GROUP BY p.seller_id;

-- Product joined with its category, seller and seller rating.
CREATE VIEW v_product_details AS
SELECT p.*,
       c.name  AS category_name,
       c.icon  AS category_icon,
       u.name  AS seller_name,
       u.branch AS seller_branch,
       u.year  AS seller_year,
       COALESCE(sr.avg_rating, 0)   AS seller_rating,
       COALESCE(sr.review_count, 0) AS seller_reviews
FROM products p
JOIN categories c ON c.category_id = p.category_id
JOIN users u      ON u.user_id     = p.seller_id
LEFT JOIN v_seller_ratings sr ON sr.seller_id = p.seller_id;

-- Items sold and revenue per category (used in admin dashboard).
CREATE VIEW v_category_sales AS
SELECT c.category_id, c.name, c.icon,
       COUNT(o.order_id)          AS items_sold,
       COALESCE(SUM(o.price), 0)  AS revenue
FROM categories c
LEFT JOIN products p ON p.category_id = c.category_id
LEFT JOIN orders   o ON o.product_id  = p.product_id AND o.status <> 'cancelled'
GROUP BY c.category_id;

-- One-row summary for the admin dashboard.
CREATE VIEW v_admin_stats AS
SELECT
    (SELECT COUNT(*) FROM users WHERE role = 'user')                     AS total_users,
    (SELECT COUNT(*) FROM products WHERE status = 'available')           AS live_listings,
    (SELECT COUNT(*) FROM products WHERE status = 'pending')             AS pending_listings,
    (SELECT COUNT(*) FROM orders WHERE status <> 'cancelled')            AS total_orders,
    (SELECT COALESCE(SUM(price), 0) FROM orders WHERE status <> 'cancelled') AS total_sales,
    (SELECT COUNT(*) FROM search_history)                                AS total_searches;
