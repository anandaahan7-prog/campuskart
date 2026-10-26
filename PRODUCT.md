# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primary: the evaluating professor / viva panel.** CampusKart is a 3rd-year engineering DBMS final project (50% of the grade). The UI is judged in a ~10-minute live demo: the presenter logs in as prepared demo accounts and walks through AI and database features on a laptop/projector, and sometimes on a phone.
- **Simulated users the product is built for:** college students on one campus buying and selling second-hand study and hostel items (textbooks, calculators, drawing instruments, lab coats, electronics, cycles, hostel essentials), and one admin who moderates.

## Product Purpose

A campus-only second-hand marketplace backed by a normalised SQLite database. Success = the professor immediately understands what the app does, sees the AI features working on real data, and sees non-trivial database work (triggers, views, transactions, audit log) without the presenter needing to type SQL.

## Positioning

Unlike OLX/Facebook groups: campus-only, structured data, and every listing flows through visible AI (personalised recommendations from search history, fair-price prediction, spam detection, "also viewed" collaborative filtering) and visible DBMS mechanics (triggers that notify, a trigger-written audit log, transactional offers/orders). AI and database depth carry equal weight: AI on the student side, database depth on the admin side.

## Operating Context

- Flask + Jinja2 server-rendered pages, one stylesheet (`static/style.css`), no front-end framework. SQLite file DB; deployed on Vercel (demo data resets per instance) and run locally with `python app.py`.
- Demo accounts: Rahul, Priya, Karan, Aisha (different search histories), Neha (no history / cold start), sellers (Vikram, Sneha, Arjun, Meera, Rohan), Admin.
- Prices in Indian rupees (₹, Indian digit grouping).

## Capabilities and Constraints

- Student: search/filter, AI recommendations with reasons, typo-tolerant search, product page with AI fair-price verdict, similar items, "also viewed", wishlist, buy (transaction), make/counter/accept offers, orders, ratings, notifications, sell with AI price suggestion and live spam check, profile with clearable search history.
- Admin: dashboard (view-backed stats), AI-flagged moderation queue, users (block), orders, audit log (trigger-written), data lookup by name with one-click reports and "Show SQL".
- Must keep: automated tests passing (`python test_app.py`), WCAG 2.1 AA (axe: 0 violations in light and dark), reduced-motion support.
- Product imagery is category artwork (Fluent 3D emoji via CDN with emoji fallback); there are no real product photos.

## Brand Commitments

- Name: **CampusKart** (keep).
- Story: **"Give your stuff a second semester"** — reuse/sustainability on campus (keep).
- **Dark mode** with a user toggle (keep).
- Everything else about the visual identity is open.

## Evidence on Hand

- Real demo data in `seed.py` (58 listings, 12 users, orders, reviews, offers, searches).
- Measured AI results in the project report (precision@5 1.00, price MAPE 7.2%, spam 0 false alarms) — demo-dataset numbers only; never present them as real-world accuracy.
- No testimonials, user counts beyond the seed data, or press. Do not fabricate any.

## Product Principles

1. The demo path is the product: every key feature must be reachable in one or two clicks from a demo login and understandable without narration.
2. Show the machinery: AI decisions carry reasons; database work shows its SQL or trigger on request.
3. Believable student app first, showcase second — no fake metrics or marketing claims.
4. Accessible by default: AA contrast, keyboard paths, reduced motion, both themes.

## Accessibility & Inclusion

WCAG 2.1 AA in light and dark themes; prefers-reduced-motion honoured; works on phone widths (bottom tab bar).
