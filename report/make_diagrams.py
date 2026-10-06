"""
Generates all report diagrams as 300-dpi PNGs in report/figures/.
    python make_diagrams.py
"""
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageChops
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle, Circle

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)
plt.rcParams["font.family"] = "Arial"

INK = "#1f2937"
ENT = "#dbeafe"
REL = "#fef3c7"
ATT = "#ffffff"
KEY = "#dcfce7"
AI = "#ede9fe"


def canvas(w, h, k=1.0):
    fig, ax = plt.subplots(figsize=(w * k, h * k))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.05, facecolor="white")
    plt.close(fig)
    # trim empty white margins
    im = Image.open(path).convert("RGB")
    bbox = ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox()
    if bbox:
        m = 40
        im.crop((max(bbox[0] - m, 0), max(bbox[1] - m, 0), min(bbox[2] + m, im.width),
                 min(bbox[3] + m, im.height))).save(path, dpi=(300, 300))
    print("saved", name)


def line(ax, a, b, lw=1.0, color=INK, ls="-", z=1):
    ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=lw, ls=ls, zorder=z)


def arrow(ax, a, b, text=None, lw=1.0, color=INK, rad=0.0, fs=7, ls="-", toff=(0, 0.12), both=False):
    style = "<|-|>" if both else "-|>"
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=9, lw=lw, color=color,
                                 connectionstyle=f"arc3,rad={rad}", linestyle=ls, zorder=2))
    if text:
        mx, my = (a[0] + b[0]) / 2 + toff[0], (a[1] + b[1]) / 2 + toff[1]
        ax.text(mx, my, text, ha="center", va="center", fontsize=fs, color=INK, zorder=5,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none"))


def box(ax, x, y, w, h, text, fc="#ffffff", fs=8, bold=False, round_=True, ec=INK, lw=1.0):
    style = "round,pad=0.02,rounding_size=0.12" if round_ else "square,pad=0"
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle=style, fc=fc, ec=ec, lw=lw, zorder=3))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal",
            zorder=4, color=INK, linespacing=1.25)


# ---------------------------------------------------------------------------
# Fig: ER diagram (Chen notation)
# ---------------------------------------------------------------------------
def er_diagram():
    fig, ax = canvas(27.6, 17, k=0.46)
    ax.set_xlim(-0.5, 27.6)
    ax.set_ylim(-0.2, 17)

    def rel(x, y, name, w=2.9, h=1.3):
        ax.add_patch(Polygon([(x - w / 2, y), (x, y + h / 2), (x + w / 2, y), (x, y - h / 2)],
                             closed=True, fc=REL, ec=INK, lw=1.3, zorder=3))
        ax.text(x, y, name, ha="center", va="center", fontsize=7.5, fontweight="bold", zorder=4)
        return (x, y)

    def attr(owner, x, y, name, pk=False, w=2.2, h=0.72):
        line(ax, owner, (x, y), lw=0.8)
        ax.add_patch(Ellipse((x, y), w, h, fc=KEY if pk else ATT, ec=INK, lw=0.9, zorder=3))
        t = ax.text(x, y, name, ha="center", va="center", fontsize=7.5, zorder=4)
        if pk:
            t.set_fontweight("bold")
            ax.plot([x - len(name) * 0.075, x + len(name) * 0.075], [y - 0.18, y - 0.18], color=INK, lw=0.8, zorder=4)

    ENT_HALF = {}

    def conn(a, b, ca=None, cb=None):
        line(ax, a, b, lw=1.1)
        for c, p, q in ((ca, a, b), (cb, b, a)):
            if not c:
                continue
            hw, hh = ENT_HALF[p]
            dx, dy = q[0] - p[0], q[1] - p[1]
            # distance along the line at which it leaves the entity box, plus margin
            t = min(hw / abs(dx) if dx else 9, hh / abs(dy) if dy else 9)
            t += 0.45 / (dx * dx + dy * dy) ** 0.5
            tx, ty = p[0] + dx * t, p[1] + dy * t
            nx, ny = -dy, dx
            n = (nx * nx + ny * ny) ** 0.5
            ax.text(tx + nx / n * 0.28, ty + ny / n * 0.28, c, ha="center", va="center", fontsize=9,
                    fontweight="bold", color="#b91c1c", zorder=6)

    U = (6, 9); P = (17.5, 9); C = (24.6, 9); O = (11.5, 2.4); R = (22.5, 2.4)
    S = (6, 15.6); N = (1.9, 3.0)
    names = [(U, "USER"), (P, "PRODUCT"), (C, "CATEGORY"), (O, "ORDER"), (R, "REVIEW"),
             (S, "SEARCH_HISTORY"), (N, "NOTIFICATION")]
    for pt, name in names:
        ENT_HALF[pt] = ((3.6 if len(name) > 10 else 2.8) / 2, 0.475)

    sells = rel(11.7, 12.1, "SELLS")
    wish = rel(11.7, 9.0, "WISHLISTS", w=3.1)
    views = rel(11.7, 6.2, "VIEWS")
    belongs = rel(21.2, 9.0, "BELONGS_TO", w=3.0)
    performs = rel(6, 12.9, "PERFORMS", w=2.8)
    receives = rel(1.9, 6.2, "RECEIVES", w=2.7)
    places = rel(6, 2.4, "PLACES", w=2.6)
    contains = rel(15.4, 4.6, "CONTAINS", w=2.8)
    has = rel(17.8, 2.4, "HAS", w=2.0)

    conn(U, sells, "1"); conn(sells, P, None, "N")
    conn(U, wish, "M"); conn(wish, P, None, "N")
    conn(U, views, "M"); conn(views, P, None, "N")
    conn(P, belongs, "N"); conn(belongs, C, None, "1")
    conn(U, performs, "1"); conn(performs, S, None, "N")
    conn(U, receives, "1"); conn(receives, N, None, "N")
    conn(U, places, "1"); conn(places, O, None, "N")
    conn(O, contains, "N"); conn(contains, P, None, "1")
    conn(O, has, "1"); conn(has, R, None, "1")

    uattrs = ["user_id", "name", "email", "password_hash", "role", "branch"]
    for i, n in enumerate(uattrs):
        ang = math.radians(108 + 16 * i)
        attr(U, U[0] + 5.2 * math.cos(ang), U[1] + 5.2 * math.sin(ang), n, i == 0,
             w=2.6 if n == "password_hash" else 2.0)
    attr(U, 8.7, 14.0, "year", w=1.8)
    attr(U, 7.6, 6.6, "phone", w=1.8)
    for (x, y, n, pk) in [(13.6, 14.8, "product_id", True), (16.0, 14.8, "title", False),
                          (18.4, 14.8, "description", False), (21.0, 14.8, "original_price", False),
                          (22.4, 12.6, "condition", False), (23.4, 11.3, "age_months", False),
                          (17.6, 6.2, "price", False), (21.0, 7.3, "status", False),
                          (19.9, 5.3, "spam_score", False)]:
        attr(P, x, y, n, pk, w=2.6 if n == "original_price" else (1.8 if n == "price" else 2.2))
    for (x, y, n, pk) in [(24.2, 6.9, "category_id", True), (26.5, 7.7, "name", False), (26.5, 10.6, "icon", False)]:
        attr(C, x, y, n, pk, w=2.2 if pk else 1.6)
    for (x, y, n, pk) in [(8.6, 0.7, "order_id", True), (11.5, 0.5, "price", False),
                          (14.2, 0.7, "status", False), (9.0, 4.3, "ordered_at", False)]:
        attr(O, x, y, n, pk)
    for (x, y, n, pk) in [(20.5, 0.6, "review_id", True), (23.2, 0.5, "rating", False), (25.2, 3.9, "comment", False)]:
        attr(R, x, y, n, pk)
    for (x, y, n, pk) in [(2.4, 16.2, "search_id", True), (9.6, 16.4, "query", False), (10.0, 15.3, "searched_at", False)]:
        attr(S, x, y, n, pk)
    for (x, y, n, pk) in [(0.9, 0.9, "notif_id", True), (3.4, 0.6, "message", False), (4.3, 4.3, "is_read", False)]:
        attr(N, x, y, n, pk, w=1.9)
    attr(wish, 11.7, 10.35, "added_at", w=2.0)
    attr(views, 11.7, 4.95, "viewed_at", w=2.0)

    for (x, y), name in names:
        w = 3.6 if len(name) > 10 else 2.8
        box(ax, x, y, w, 0.95, name, fc=ENT, fs=9, bold=True, round_=False, lw=1.4)

    lx, ly = 23.4, 16.6
    ax.add_patch(Rectangle((lx - 0.3, ly - 2.6), 4.4, 2.9, fc="white", ec="#9ca3af", lw=0.8, zorder=2))
    box(ax, lx + 0.5, ly - 0.15, 1.0, 0.42, "", fc=ENT, round_=False)
    ax.text(lx + 1.2, ly - 0.15, "Entity", fontsize=8, va="center")
    ax.add_patch(Polygon([(lx, ly - 0.8), (lx + 0.5, ly - 0.57), (lx + 1.0, ly - 0.8), (lx + 0.5, ly - 1.03)],
                         fc=REL, ec=INK, zorder=3))
    ax.text(lx + 1.2, ly - 0.8, "Relationship", fontsize=8, va="center")
    ax.add_patch(Ellipse((lx + 0.5, ly - 1.45), 1.0, 0.4, fc=KEY, ec=INK, zorder=3))
    ax.text(lx + 1.2, ly - 1.45, "Primary key (underlined)", fontsize=8, va="center")
    ax.add_patch(Ellipse((lx + 0.5, ly - 2.05), 1.0, 0.4, fc=ATT, ec=INK, zorder=3))
    ax.text(lx + 1.2, ly - 2.05, "Attribute", fontsize=8, va="center")
    ax.text(lx + 0.5, ly - 2.45, "1", fontsize=9, color="#b91c1c", fontweight="bold", va="center", ha="center")
    ax.text(lx + 1.2, ly - 2.45, "1 / N / M  cardinality", fontsize=8, va="center")
    save(fig, "er_diagram.png")


# ---------------------------------------------------------------------------
# Fig: Relational schema (tables with PK / FK)
# ---------------------------------------------------------------------------
TABLES = {
    "search_history": (["search_id PK", "user_id FK", "query", "searched_at"], (0.3, 15.5)),
    "notifications": (["notif_id PK", "user_id FK", "message", "is_read", "created_at"], (0.3, 11.6)),
    "users": (["user_id PK", "name", "email UQ", "password_hash", "role", "branch", "year", "phone",
               "is_blocked", "created_at"], (6.3, 15.5)),
    "wishlist": (["user_id PK FK", "product_id PK FK", "added_at"], (6.3, 8.0)),
    "products": (["product_id PK", "seller_id FK", "category_id FK", "title", "description", "original_price",
                  "price", "condition", "age_months", "status", "is_flagged", "spam_score", "flag_reason",
                  "created_at"], (12.3, 15.5)),
    "product_views": (["view_id PK", "user_id FK", "product_id FK", "viewed_at"], (12.3, 6.0)),
    "orders": (["order_id PK", "product_id FK", "buyer_id FK", "price", "status", "ordered_at"], (18.3, 15.5)),
    "reviews": (["review_id PK", "order_id FK UQ", "rating", "comment", "created_at"], (18.3, 10.6)),
    "categories": (["category_id PK", "name UQ", "icon"], (18.3, 5.6)),
}


def schema_diagram():
    fig, ax = canvas(23.2, 16.0, k=0.41)
    W, RH = 4.2, 0.5
    pos = {}
    for name, (cols, (x, y)) in TABLES.items():
        ax.add_patch(Rectangle((x, y - RH), W, RH, fc="#1e3a8a", ec=INK, lw=1, zorder=3))
        ax.text(x + W / 2, y - RH / 2, name, ha="center", va="center", color="white", fontsize=9.5,
                fontweight="bold", zorder=4)
        rows = {}
        for i, c in enumerate(cols):
            cy = y - RH * (i + 2)
            parts = c.split()
            col, tags = parts[0], parts[1:]
            fc = "#ecfdf5" if "PK" in tags else ("#eff6ff" if "FK" in tags else "white")
            ax.add_patch(Rectangle((x, cy), W, RH, fc=fc, ec="#9ca3af", lw=0.6, zorder=3))
            ax.text(x + 0.15, cy + RH / 2, col, va="center", fontsize=8,
                    fontweight="bold" if "PK" in tags else "normal", zorder=4)
            ax.text(x + W - 0.12, cy + RH / 2, " ".join(tags), va="center", ha="right", fontsize=7,
                    color="#047857" if "PK" in tags else "#1d4ed8", zorder=4)
            rows[col] = (x, cy + RH / 2)
        pos[name] = rows

    def edge(t, c, side):
        x, y = pos[t][c]
        return (x + W if side == "r" else x, y)

    def ortho(t1, c1, s1, t2, c2, s2, via_x, color="#2563eb"):
        """Orthogonal connector: FK row -> vertical channel at via_x -> PK row (arrow)."""
        a, b = edge(t1, c1, s1), edge(t2, c2, s2)
        ax.plot([a[0], via_x, via_x], [a[1], a[1], b[1]], color=color, lw=0.9, zorder=2)
        ax.add_patch(FancyArrowPatch((via_x, b[1]), b, arrowstyle="-|>", mutation_scale=10, lw=0.9,
                                     color=color, zorder=2, shrinkA=0, shrinkB=0))
        ax.plot(*a, marker="o", ms=3, color=color, zorder=4)

    ortho("search_history", "user_id", "r", "users", "user_id", "l", 5.1)
    ortho("notifications", "user_id", "r", "users", "user_id", "l", 5.1)
    ortho("wishlist", "user_id", "l", "users", "user_id", "l", 5.7, color="#0891b2")
    ortho("wishlist", "product_id", "r", "products", "product_id", "l", 11.5, color="#0891b2")
    ortho("products", "seller_id", "l", "users", "user_id", "r", 11.1)
    ortho("product_views", "user_id", "l", "users", "user_id", "r", 10.7, color="#7c3aed")
    ortho("product_views", "product_id", "l", "products", "product_id", "l", 11.9, color="#7c3aed")
    ortho("orders", "product_id", "l", "products", "product_id", "r", 17.0, color="#ea580c")
    ortho("orders", "buyer_id", "l", "users", "user_id", "r", 17.5, color="#ea580c")
    ortho("reviews", "order_id", "r", "orders", "order_id", "r", 22.9, color="#16a34a")
    ortho("products", "category_id", "r", "categories", "category_id", "l", 16.6, color="#db2777")

    lx, ly = 0.4, 6.4
    ax.text(lx, ly, "Legend", fontsize=9, fontweight="bold")
    for i, (fc, t) in enumerate([("#ecfdf5", "PK  primary key"), ("#eff6ff", "FK  foreign key"),
                                 ("white", "UQ  unique constraint")]):
        ax.add_patch(Rectangle((lx, ly - 0.8 - i * 0.6), 0.5, 0.4, fc=fc, ec="#9ca3af"))
        ax.text(lx + 0.7, ly - 0.6 - i * 0.6, t, fontsize=8, va="center")
    ax.plot([lx, lx + 0.5], [ly - 2.6, ly - 2.6], color="#2563eb", lw=0.9)
    ax.plot(lx, ly - 2.6, marker="o", ms=3, color="#2563eb")
    ax.annotate("", xy=(lx + 0.6, ly - 2.6), xytext=(lx + 0.4, ly - 2.6),
                arrowprops=dict(arrowstyle="-|>", color="#2563eb"))
    ax.text(lx + 0.8, ly - 2.6, "foreign key (dot) to referenced key (arrow)", fontsize=8, va="center")
    save(fig, "relational_schema.png")


# ---------------------------------------------------------------------------
# Fig: System architecture
# ---------------------------------------------------------------------------
def architecture():
    fig, ax = canvas(12, 8.4, k=0.52)
    # tiers
    for y, h, label, fc in [(6.6, 1.4, "Presentation tier", "#f8fafc"), (2.55, 3.6, "Application tier (Python Flask)", "#f8fafc"),
                            (0.05, 2.0, "Data tier", "#f8fafc")]:
        ax.add_patch(FancyBboxPatch((0.2, y), 11.6, h, boxstyle="round,pad=0,rounding_size=0.15",
                                    fc=fc, ec="#94a3b8", lw=0.9, ls="--", zorder=1))
        ax.text(0.4, y + h - 0.22, label, fontsize=8, color="#475569", fontweight="bold", va="center")
    box(ax, 3.2, 7.15, 3.8, 0.7, "Student browser\nHTML / CSS / JavaScript", fc=ENT, fs=8)
    box(ax, 8.8, 7.15, 3.8, 0.7, "Admin browser\nDashboard / SQL explorer", fc=ENT, fs=8)

    box(ax, 2.2, 5.2, 3.4, 0.75, "Routing & sessions\n(Flask, Jinja2 templates)", fs=7.5)
    box(ax, 6.0, 5.2, 3.6, 0.75, "Authentication\n(hashed passwords, roles)", fs=7.5)
    box(ax, 9.8, 5.2, 3.4, 0.75, "Business logic\nsearch, sell, buy, moderate", fs=7.5)
    box(ax, 2.2, 3.35, 3.4, 0.9, "AI 1: Recommender\nTF-IDF + cosine similarity", fc=AI, fs=7.5)
    box(ax, 6.0, 3.35, 3.6, 0.9, "AI 2: Price predictor\nLinear Regression", fc=AI, fs=7.5)
    box(ax, 9.8, 3.35, 3.4, 0.9, "AI 3: Spam detector\nMultinomial Naive Bayes", fc=AI, fs=7.5)

    box(ax, 3.4, 1.05, 5.4, 1.2, "SQLite database (campuskart.db)\n9 tables · 4 views · 6 triggers · 6 indexes",
        fc=REL, fs=8, bold=True)
    box(ax, 9.2, 1.05, 4.2, 1.2, "scikit-learn models\ntrained on-demand from DB rows", fc=AI, fs=7.5)

    arrow(ax, (3.2, 6.78), (3.0, 5.6), "HTTP request", both=True, fs=6.5, toff=(0.9, 0))
    arrow(ax, (8.8, 6.78), (9.2, 5.6), "HTTP request", both=True, fs=6.5, toff=(0.9, 0))
    for x in (2.2, 6.0, 9.8):
        arrow(ax, (x, 4.8), (x, 3.82))
    arrow(ax, (3.4, 2.9), (3.4, 1.67), "SQL (parameterised)", both=True, fs=6.5, toff=(1.1, 0))
    arrow(ax, (6.0, 2.9), (5.4, 1.67), both=True)
    arrow(ax, (9.8, 2.9), (9.4, 1.67), both=True)
    arrow(ax, (6.1, 1.05), (7.1, 1.05), "rows", fs=6.5, toff=(0, 0.2))
    save(fig, "architecture.png")


# ---------------------------------------------------------------------------
# DFD helpers
# ---------------------------------------------------------------------------
def process(ax, x, y, r, text, num):
    ax.add_patch(Circle((x, y), r, fc="#e0f2fe", ec=INK, lw=1.2, zorder=3))
    ax.text(x, y + r * 0.45, num, ha="center", va="center", fontsize=7.5, fontweight="bold", zorder=4)
    ax.text(x, y - 0.08, text, ha="center", va="center", fontsize=7.5, zorder=4, linespacing=1.15)


def store(ax, x, y, w, text, sid):
    ax.add_patch(Rectangle((x - w / 2, y - 0.25), w, 0.5, fc="#f8fafc", ec="none", zorder=3))
    line(ax, (x - w / 2, y + 0.25), (x + w / 2, y + 0.25), lw=1.1, z=4)
    line(ax, (x - w / 2, y - 0.25), (x + w / 2, y - 0.25), lw=1.1, z=4)
    line(ax, (x - w / 2, y - 0.25), (x - w / 2, y + 0.25), lw=1.1, z=4)
    line(ax, (x - w / 2 + 0.55, y - 0.25), (x - w / 2 + 0.55, y + 0.25), lw=0.8, z=4)
    ax.text(x - w / 2 + 0.27, y, sid, ha="center", va="center", fontsize=7, fontweight="bold", zorder=5)
    ax.text(x + 0.27, y, text, ha="center", va="center", fontsize=7.5, zorder=5)


def dfd0():
    fig, ax = canvas(11, 5.2, k=0.52)
    box(ax, 1.4, 2.6, 2.2, 0.9, "STUDENT\n(buyer / seller)", fc="#fee2e2", round_=False, bold=True, fs=8)
    box(ax, 9.6, 2.6, 2.0, 0.9, "ADMIN", fc="#fee2e2", round_=False, bold=True, fs=9)
    process(ax, 5.5, 2.6, 1.55, "CampusKart\nAI Marketplace\nSystem", "0")
    arrow(ax, (2.5, 3.1), (4.05, 3.3), "registration, login,\nsearch query, listing,\norder, review", rad=-0.15, fs=6.5, toff=(0, 0.55))
    arrow(ax, (4.05, 1.9), (2.5, 2.1), "recommendations, search\nresults, price suggestion,\nnotifications", rad=-0.15, fs=6.5, toff=(0, -0.55))
    arrow(ax, (8.6, 3.1), (6.95, 3.3), "approve / reject,\nblock user, SQL query", rad=0.15, fs=6.5, toff=(0, 0.45))
    arrow(ax, (6.95, 1.9), (8.6, 2.1), "flagged listings,\nstatistics, reports", rad=0.15, fs=6.5, toff=(0, -0.45))
    save(fig, "dfd_level0.png")


def dfd1():
    fig, ax = canvas(14, 12, k=0.74)
    box(ax, 1.3, 8.8, 1.9, 0.8, "STUDENT", fc="#fee2e2", round_=False, bold=True)
    box(ax, 12.8, 5.5, 1.9, 0.8, "ADMIN", fc="#fee2e2", round_=False, bold=True)
    procs = {"1.0": (4.0, 8.8, "Authenticate\nuser"), "2.0": (7.0, 8.8, "Search &\nbrowse"),
             "5.0": (10.2, 8.8, "Generate\nrecommend-\nations"), "3.0": (4.0, 5.5, "Manage\nlistings"),
             "4.0": (6.8, 5.5, "Process\norders"), "6.0": (9.6, 5.5, "Moderate\n& report")}
    for k, (x, y, t) in procs.items():
        process(ax, x, y, 0.95, t, k)
    stores = {"D1": (4.0, 11.1, "Users"), "D5": (1.7, 2.0, "Notifications"), "D2": (5.0, 2.0, "Products"),
              "D3": (8.6, 2.0, "Orders / Reviews"), "D4": (12.0, 2.0, "Search history / Views")}
    for k, (x, y, t) in stores.items():
        store(ax, x, y, 3.0 if k != "D4" else 3.5, t, k)

    fs = 7
    arrow(ax, (2.25, 8.95), (3.05, 8.95), "login", fs=fs, toff=(0, 0.2))
    arrow(ax, (4.0, 9.75), (4.0, 10.85), "verify", fs=fs, toff=(0.4, 0), both=True)
    arrow(ax, (2.2, 8.4), (6.2, 8.25), "query / results", fs=fs, rad=0.45, both=True, toff=(-1.2, -0.6))
    arrow(ax, (6.3, 8.15), (5.1, 2.25), "product data", fs=fs, toff=(0.05, -1.7))
    arrow(ax, (7.95, 9.05), (9.25, 9.05), "events", fs=fs, toff=(0, 0.2))
    arrow(ax, (9.25, 8.55), (7.95, 8.55), "picks", fs=fs, toff=(0, -0.22))
    arrow(ax, (10.6, 7.9), (11.6, 2.25), "history", fs=fs, toff=(0.35, -1.2), both=True)
    arrow(ax, (5.6, 2.25), (9.7, 7.85), "available products", fs=fs, ls="--", toff=(0.9, 1.4))
    arrow(ax, (1.7, 8.35), (3.35, 6.2), "listing", fs=fs, toff=(-0.3, 0.1))
    arrow(ax, (4.3, 4.6), (4.7, 2.25), "listing +\nspam score", fs=fs, toff=(0.25, 0.3))
    arrow(ax, (2.1, 8.35), (6.1, 6.15), "buy / cancel /\nreview", fs=fs, toff=(1.2, -0.45))
    arrow(ax, (7.2, 4.6), (8.2, 2.25), "orders", fs=fs, toff=(0.2, 0.1))
    arrow(ax, (6.5, 4.6), (5.9, 2.25), "sold\n(trigger)", fs=fs, toff=(-0.1, -0.3))
    arrow(ax, (6.0, 4.95), (3.0, 2.25), "alerts (trigger)", fs=fs, toff=(-1.0, -0.6))
    arrow(ax, (1.0, 2.25), (1.0, 8.35), "notifications", fs=fs, toff=(0, 0))
    arrow(ax, (11.85, 5.5), (10.55, 5.5), "decisions /\nreports", fs=fs, both=True, toff=(1.6, 0.8))
    arrow(ax, (9.0, 4.8), (6.4, 2.25), "approve /\nreject", fs=fs, toff=(0.5, 0.3))
    arrow(ax, (9.1, 2.25), (9.7, 4.55), "statistics", fs=fs, toff=(0.45, 0))
    save(fig, "dfd_level1.png")


# ---------------------------------------------------------------------------
# Use case diagram
# ---------------------------------------------------------------------------
def actor(ax, x, y, name):
    ax.add_patch(Circle((x, y + 0.75), 0.22, fc="white", ec=INK, lw=1.2, zorder=3))
    line(ax, (x, y + 0.53), (x, y - 0.1), lw=1.2)
    line(ax, (x - 0.35, y + 0.3), (x + 0.35, y + 0.3), lw=1.2)
    line(ax, (x, y - 0.1), (x - 0.3, y - 0.6), lw=1.2)
    line(ax, (x, y - 0.1), (x + 0.3, y - 0.6), lw=1.2)
    ax.text(x, y - 0.9, name, ha="center", fontsize=8.5, fontweight="bold")


def use_case():
    fig, ax = canvas(11, 9, k=0.62)
    ax.add_patch(Rectangle((2.2, 0.3), 6.6, 8.4, fc="#f8fafc", ec=INK, lw=1.1))
    ax.text(5.5, 8.4, "CampusKart System", ha="center", fontsize=9, fontweight="bold")
    actor(ax, 0.9, 5.2, "Student")
    actor(ax, 10.1, 5.2, "Admin")
    student = ["Register / Login", "Search & filter items", "View recommendations (AI)", "Sell item + price hint (AI)",
               "Buy / cancel order", "Rate seller", "Manage wishlist", "View notifications"]
    admin = ["Review AI-flagged listings", "Block / unblock users", "View dashboard & reports", "Run SQL queries"]
    for i, t in enumerate(student):
        y = 7.7 - i * 0.92
        ax.add_patch(Ellipse((3.85, y), 2.95, 0.68, fc=AI if "AI" in t else "white", ec=INK, lw=0.9, zorder=3))
        ax.text(3.85, y, t, ha="center", va="center", fontsize=7.3, zorder=4)
        line(ax, (1.3, 5.5), (2.38, y), lw=0.7)
    for i, t in enumerate(admin):
        y = 7.0 - i * 1.15
        ax.add_patch(Ellipse((7.4, y), 2.55, 0.68, fc="white", ec=INK, lw=0.9, zorder=3))
        ax.text(7.4, y, t, ha="center", va="center", fontsize=7.3, zorder=4)
        line(ax, (9.7, 5.5), (8.68, y), lw=0.7)
    ax.add_patch(Ellipse((7.4, 1.85), 2.55, 0.68, fc="white", ec=INK, lw=0.9, zorder=3))
    ax.text(7.4, 1.85, "Login", ha="center", va="center", fontsize=7.3, zorder=4)
    line(ax, (9.7, 5.5), (8.68, 1.85), lw=0.7)
    ax.text(5.5, 0.6, "Shaded use cases use the AI modules", fontsize=7, ha="center", color="#6d28d9")
    save(fig, "use_case.png")


# ---------------------------------------------------------------------------
# Recommendation flowchart
# ---------------------------------------------------------------------------
def rec_flow():
    fig, ax = canvas(7.8, 11.6, k=0.6)
    steps = [
        ("Student opens home page", "#fee2e2", 0.7),
        ("Fetch signals from DB:\nlast 10 searches, last 10 views,\nwishlist (newest first)", "white", 1.0),
        ("Any history?", REL, 0.8),
        ("Build TF-IDF vectors of all available\nproducts (title + category + description,\ncharacter 3-5 grams)", AI, 1.1),
        ("Weight each signal:\nw = base x 0.9^rank", AI, 0.8),
        ("For every product j:\nscore = max_i ( w_i x cos(signal_i, product_j) )\nignore matches with cos < 0.15", AI, 1.1),
        ("Sort by score, take top 8,\nattach strongest signal as reason", "white", 0.9),
        ("Show 'Recommended for you'\nwith 'Because you searched ...'", "#dcfce7", 0.9),
    ]
    X = 3.1
    y = 11.4
    centers = []
    for t, fc, h in steps:
        if t == "Any history?":
            ax.add_patch(Polygon([(X - 1.5, y - h / 2), (X, y), (X + 1.5, y - h / 2), (X, y - h)],
                                 fc=fc, ec=INK, lw=1, zorder=3))
            ax.text(X, y - h / 2, t, ha="center", va="center", fontsize=8, zorder=4)
        else:
            box(ax, X, y - h / 2, 4.8, h, t, fc=fc, fs=7.5)
        centers.append((y, y - h))
        y -= h + 0.42
    for (top, bot), (ntop, _) in zip(centers, centers[1:]):
        arrow(ax, (X, bot), (X, ntop))
    ax.text(X + 0.2, centers[2][1] - 0.2, "Yes", fontsize=7.5)
    dy = (centers[2][0] + centers[2][1]) / 2
    cx = 6.9
    line(ax, (X + 1.5, dy), (cx, dy))
    ax.text(X + 1.8, dy + 0.15, "No", fontsize=7.5)
    arrow(ax, (cx, dy), (cx, dy - 1.0), None)
    box(ax, cx, dy - 1.65, 1.4, 1.3, "Cold start:\nshow most\nviewed items\n(30 days)", fc="#fef3c7", fs=6.8)
    fy = (centers[-1][0] + centers[-1][1]) / 2
    line(ax, (cx, dy - 2.3), (cx, fy))
    arrow(ax, (cx, fy), (X + 2.4, fy), None)
    save(fig, "recommendation_flow.png")


# ---------------------------------------------------------------------------
# Sequence diagram: buying an item (transaction + triggers)
# ---------------------------------------------------------------------------
def buy_sequence():
    fig, ax = canvas(12, 7.6, k=0.58)
    cols = {"Buyer": 1.2, "Flask app": 4.0, "SQLite (orders)": 7.0, "Triggers": 10.4}
    for n, x in cols.items():
        box(ax, x, 7.1, 2.3, 0.6, n, fc=ENT if n != "Triggers" else REL, bold=True, fs=8)
        line(ax, (x, 6.8), (x, 1.2), lw=0.8, ls="--", color="#64748b")
    msgs = [
        ("Buyer", "Flask app", 6.3, "POST /buy/<id>"),
        ("Flask app", "SQLite (orders)", 5.7, "BEGIN; INSERT INTO orders"),
        ("SQLite (orders)", "Triggers", 5.1, "BEFORE INSERT: trg_order_validate"),
        ("Triggers", "SQLite (orders)", 4.5, "RAISE(ABORT) if already sold"),
        ("SQLite (orders)", "Triggers", 3.9, "AFTER INSERT: trg_order_placed"),
        ("Triggers", "Triggers", 3.3, "UPDATE product status='sold';\nnotify seller + wishlisters"),
        ("Flask app", "SQLite (orders)", 2.4, "COMMIT  (or ROLLBACK on error)"),
        ("Flask app", "Buyer", 1.7, "'Order placed' / 'No longer available'"),
    ]
    for a, b, y, t in msgs:
        xa, xb = cols[a], cols[b]
        if a == b:
            ax.add_patch(FancyArrowPatch((xa, y + 0.2), (xa, y - 0.3), arrowstyle="-|>", mutation_scale=9,
                                         connectionstyle="arc3,rad=-1.2", color=INK, lw=0.9))
            ax.text(xa - 0.5, y - 0.05, t, ha="right", va="center", fontsize=7)
        else:
            arrow(ax, (xa, y), (xb, y), t, fs=7, ls="--" if xb < xa else "-", toff=(0, 0.18))
    ax.add_patch(Rectangle((3.75, 1.95), 6.95, 4.05, fc="none", ec="#7c3aed", lw=1, ls="-."))
    ax.text(10.6, 6.12, "single atomic transaction", fontsize=7, color="#7c3aed", ha="right")
    save(fig, "buy_sequence.png")


if __name__ == "__main__":
    er_diagram()
    schema_diagram()
    architecture()
    dfd0()
    dfd1()
    use_case()
    rec_flow()
    buy_sequence()
