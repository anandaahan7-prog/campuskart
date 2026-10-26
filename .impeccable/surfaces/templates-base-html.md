---
version: 2
slug: "templates-base-html"
primary_target: "templates/base.html"
related_targets: ["static/style.css","templates/_macros.html"]
---

# Surface brief: CampusKart app shell (all student and admin screens)

Scope: every server-rendered screen (base layout, home, search, product, sell, orders/offers, wishlist, notifications, profile, auth, admin dashboard, listings, users, orders, audit log, data lookup). Visitor mode: Operate (the guest landing hero is the one Persuade moment inside the same world).

Audience and job: a professor watching a 10-minute live demo on a projector or laptop; simulated users are students buying and selling second-hand items on one campus. The demo path must be one or two clicks from each demo login, and AI and database machinery must be visible without narration.

Constraints: Flask/Jinja templates and one stylesheet; tests must pass; WCAG 2.1 AA in light and dark (axe 0); reduced motion; phone widths with bottom tab bar; no fabricated claims.

## Direction contract

THESIS: CampusKart is the department notice board, made searchable. Listings are the paper slips students already pin up, and the single tear-off tab at the bottom of every slip is how you get in touch: an item sells once, so there is one tab, torn off when it sells. It refuses the category default of a white e-commerce card grid with a blue search bar.

OWN-WORLD: a walnut frame (top bar and the 8px L around the page) holding one cork board sheet with soft 16px corners; listings on paper slips held by brass pins, whose paper colour codes the category (canary books, sky electronics, white calculators and clothing, pink drawing, mint lab, peach hostel, sage cycles, aqua sports); marker-black ink; pushpin red reserved for the screen's one next action (Buy, Accept, Reply to the counter, Review listings, Pin it to the board) and nothing else; AI notes handwritten in ballpoint blue as a senior's annotation, with "AI" circled in the same pen; states as outlined rubber-stamp marks in sentence case (green done, amber waiting, brick refused, ink neutral) and one big rotated "Sold" stamp. Type: two faces only. Archivo (condensed 82% at 800 for headings and prices, normal width for UI and body) and Caveat for hand annotations. Dark theme is the same board at night: near-black frame, dark cork, dim paper, chalk ink.

STORY: a visitor sees a campus board, recognises it in a second, reads why each slip was pinned for them, and acts with one red control.

FIRST VIEWPORT: walnut bar (logo pin, search, paper "Sell an item", nav). Board header: "Pinned for you, Rahul" in condensed black at 28px with a blue handwritten note "picked from your 6 searches, the items you viewed and your wishlist", recent searches as small paper tags. Left: six slips, three across: pin, condition and category, picture, title, price in condensed black, blue AI reason, seller line, one perforated tear-off tab. Right rail: the one finding as a canary sticky note with its red action (a counter to answer, offers to review, a wishlist price drop, a pickup, or an offer sent), then open offers and the latest notifications. The whole slip opens the item.

FORM: Campus Notice Board, my top-ranked grounded candidate (position 1 of 7), chosen as the pick over the assigned UPI Receipt world; seed:f7f0e95a085ff9e3. Shell from the taste app sheet: framed-sheet (seed 531504514), its tinted L-frame read as the board's wooden frame and its sheet as the cork. Signature interaction: the tear-off tab. Buying an item or accepting a counter lands on the item's slip, where its one tab tears off along the perforation and the seller's phone number lands under the slip (the real business rule: contact appears only after an order). Motion grammar, reconciled with the app-screen rules: no entrance animations; the tear-off is the one authored moment; toasts arrive as sticky notes; press feedback at 0.97; slips straighten and lift on hover (fine pointers only); the clicked slip's picture morphs into the product slip across the page change. All gated by prefers-reduced-motion (fades only).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Unresolved

- Real product photos do not exist; category artwork (Fluent 3D emoji via CDN, emoji fallback) is the printed picture on each slip.
- The walnut top bar is darker than the app-screen rule for a neutral shell; it is kept as the board's frame, the world's one brand face.
- The detector reads paper panels on the cork sheet as nested cards; in this world they are paper pinned to a board, by design.
