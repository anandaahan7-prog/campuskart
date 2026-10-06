// Builds CampusKart_IEEE_Report.docx in IEEE conference (A4, two-column) format.
//   node build_report.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, AlignmentType,
  HeadingLevel, WidthType, BorderStyle, ShadingType, SectionType, TabStopType, LevelFormat,
  VerticalAlign,
} = require("docx");

const FIG = path.join(__dirname, "figures");
const FONT = "Times New Roman";
const PAGE = {
  size: { width: 11906, height: 16838 },                                  // A4
  margin: { top: 1080, bottom: 2438, left: 812, right: 812 },            // IEEE A4 margins
};
const COL = 5018;      // single column width (3.48 in)
const FULL = 10282;    // both columns (7.14 in)
const GAP = 246;       // column gap (0.17 in)

// ------------------------------------------------------------------ text helpers
// Inline markup: **bold**, *italic*, `code`, [[placeholder]] (highlighted for the student to fill)
function runs(text, base = {}) {
  const out = [];
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[\[[^\]]+\]\])/);
  for (const part of parts) {
    if (!part) continue;
    if (part.startsWith("**")) out.push(new TextRun({ ...base, text: part.slice(2, -2), bold: true }));
    else if (part.startsWith("[[")) out.push(new TextRun({ ...base, text: part.slice(2, -2), highlight: "yellow" }));
    else if (part.startsWith("*")) out.push(new TextRun({ ...base, text: part.slice(1, -1), italics: true }));
    else if (part.startsWith("`")) out.push(new TextRun({ ...base, text: part.slice(1, -1), font: "Courier New", size: (base.size || 20) - 2 }));
    else out.push(new TextRun({ ...base, text: part }));
  }
  return out;
}

const P = (text, o = {}) => new Paragraph({
  children: runs(text, { font: FONT, size: o.size || 20 }),
  alignment: o.align || AlignmentType.JUSTIFIED,
  indent: o.noIndent ? undefined : { firstLine: 288 },
  spacing: { before: o.before || 0, after: o.after || 0, line: 240 },
  keepNext: o.keepNext,
});

const H1 = (num, text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text: `${num}. ${text}`, font: FONT, size: 20, smallCaps: true })],
});

const H1u = (text) => new Paragraph({          // unnumbered (Acknowledgment, References)
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text, font: FONT, size: 20, smallCaps: true })],
});

const H2 = (letter, text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  children: [new TextRun({ text: `${letter}. ${text}`, font: FONT, size: 20, italics: true })],
});

const bullet = (text) => new Paragraph({
  numbering: { reference: "bullets", level: 0 },
  children: runs(text, { font: FONT, size: 20 }),
  alignment: AlignmentType.JUSTIFIED,
  spacing: { after: 0, line: 240 },
});

// Equation centred in the column with a right-aligned number, e.g.  "  w = ...      (1)"
// parts: array of [text, "sub" | "sup" | undefined]
function EQ(parts, num) {
  const children = [new TextRun({ text: "\t", font: FONT, size: 20 })];
  for (const [t, kind] of parts) {
    children.push(new TextRun({ text: t, font: FONT, size: 20, italics: true,
      subScript: kind === "sub", superScript: kind === "sup" }));
  }
  children.push(new TextRun({ text: `\t(${num})`, font: FONT, size: 20 }));
  return new Paragraph({
    children,
    tabStops: [{ type: TabStopType.CENTER, position: COL / 2 }, { type: TabStopType.RIGHT, position: COL }],
    spacing: { before: 80, after: 80 },
  });
}

function code(lines) {
  return lines.map((l, i) => new Paragraph({
    children: [new TextRun({ text: l || " ", font: "Courier New", size: 14 })],
    shading: { type: ShadingType.CLEAR, color: "auto", fill: "F2F2F2" },
    spacing: { before: i === 0 ? 80 : 0, after: i === lines.length - 1 ? 80 : 0, line: 220 },
    indent: { left: 72, right: 72 },
  }));
}

// ------------------------------------------------------------------ figures & tables
function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}

let figNo = 0;
const figRef = {};
function FIGURE(key, file, caption, full = false, width = null) {
  figNo += 1;
  figRef[key] = figNo;
  const f = path.join(FIG, file);
  const { w, h } = pngSize(f);
  const widthPx = width || (full ? 680 : 330);             // 96 px per inch
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 120, after: 40 },
      keepNext: true,
      children: [new ImageRun({ type: "png", data: fs.readFileSync(f),
        transformation: { width: widthPx, height: Math.round(widthPx * h / w) },
        altText: { title: caption, description: caption, name: file } })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 160 },
      children: runs(`Fig. ${figNo}. ${caption}`, { font: FONT, size: 16 }),
    }),
  ];
}

const ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"];
let tabNo = 0;
const border = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
const borders = { top: border, bottom: border, left: border, right: border };

function TABLE(title, header, rows, widths) {
  tabNo += 1;
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (text, i, isHead) => new TableCell({
    borders,
    width: { size: widths[i], type: WidthType.DXA },
    margins: { top: 30, bottom: 30, left: 60, right: 60 },
    verticalAlign: VerticalAlign.CENTER,
    shading: isHead ? { type: ShadingType.CLEAR, color: "auto", fill: "E7E6E6" } : undefined,
    children: [new Paragraph({
      alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
      children: runs(text, { font: FONT, size: 16, bold: isHead }),
    })],
  });
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 160 }, keepNext: true,
      children: [new TextRun({ text: `TABLE ${ROMAN[tabNo - 1]}.`, font: FONT, size: 16 })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, keepNext: true,
      children: [new TextRun({ text: title, font: FONT, size: 16, smallCaps: true })] }),
    new Table({
      width: { size: total, type: WidthType.DXA },
      columnWidths: widths,
      alignment: AlignmentType.CENTER,
      rows: [
        new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, i, true)) }),
        ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, i, false)) })),
      ],
    }),
    new Paragraph({ spacing: { after: 120 }, children: [] }),
  ];
}

// ------------------------------------------------------------------ title block (single column)
const titleBlock = [
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 240 },
    children: [new TextRun({ text: "CampusKart: An AI-Enabled Database System for a Peer-to-Peer Student Marketplace",
      font: FONT, size: 48 })],
  }),
];

function authorCell(lines) {
  return new TableCell({
    borders: { top: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, bottom: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
      left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" } },
    width: { size: FULL / 3, type: WidthType.DXA },
    children: lines.map((l, i) => new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: l, font: FONT, size: i === 0 ? 22 : 20, italics: i === 1 || i === 2, highlight: "yellow" })],
    })),
  });
}
const author = (n) => [`[Author Name ${n}]`, "[Dept. of Computer Engineering]", "[College / University Name]", "[City], India", "[email address]"];
titleBlock.push(new Table({
  width: { size: FULL, type: WidthType.DXA },
  columnWidths: [FULL / 3, FULL / 3, FULL / 3],
  rows: [new TableRow({ children: [authorCell(author(1)), authorCell(author(2)), authorCell(author(3))] })],
}));
titleBlock.push(new Paragraph({ spacing: { after: 200 }, children: [] }));

// ------------------------------------------------------------------ body content
const A = [];   // two-column part 1
A.push(new Paragraph({
  alignment: AlignmentType.JUSTIFIED,
  children: [
    new TextRun({ text: "Abstract", font: FONT, size: 18, bold: true, italics: true }),
    new TextRun({ text: "—Students in colleges regularly buy expensive textbooks, calculators, drawing instruments and hostel items that their seniors sell or throw away a year later. This paper presents CampusKart, a campus-only second-hand marketplace built around a normalized relational database and three lightweight machine learning modules. The database, implemented in SQLite with nine tables in third normal form, enforces business rules through six triggers, four views, foreign keys and CHECK constraints, and runs every purchase as a single atomic transaction so that an item can never be sold twice. Using the stored search history, product views and wishlists, a content-based recommender based on TF-IDF and cosine similarity produces personalised and explainable suggestions. A linear regression model trained on existing listings suggests a fair resale price, and a Multinomial Naive Bayes classifier combined with simple rules flags spam or fraudulent listings for administrator review. On the demonstration dataset the recommender achieved a precision at five of 1.00 for all four test profiles, the price model reached a mean absolute percentage error of 7.2 percent under five-fold cross validation, and all 56 genuine listings passed the spam filter while both spam listings were caught. Every AI response completes in under 10 ms.", font: FONT, size: 18, bold: true }),
  ],
}));
A.push(new Paragraph({
  alignment: AlignmentType.JUSTIFIED,
  spacing: { before: 120, after: 120 },
  children: [
    new TextRun({ text: "Keywords", font: FONT, size: 18, bold: true, italics: true }),
    new TextRun({ text: "—database management system, relational schema, triggers, transactions, recommender system, TF-IDF, Naive Bayes, linear regression", font: FONT, size: 18, bold: true }),
  ],
}));

// I. Introduction
A.push(H1("I", "Introduction"));
A.push(P("Every academic year, students buy new textbooks, scientific calculators, lab coats, drafters and hostel essentials, while graduating seniors discard the same items or sell them informally through messaging groups. Such groups have no search, no price reference, no record of who sold what, and no protection against fraudulent posts. General marketplaces such as OLX or Facebook Marketplace are open to the public, which makes meeting strangers and paying in advance risky for students."));
A.push(P("A database-backed campus marketplace solves most of these problems. Listings become structured records, every purchase becomes a transaction, and the history of searches and views becomes data that can help each student find what they need. The aim of this project is to design such a system on sound database principles first, and then add a small number of explainable AI features that run directly on the stored data."));
A.push(P("The main contributions of this work are:", { keepNext: true }));
A.push(bullet("A normalized relational schema (3NF and BCNF) of nine tables derived from an ER model, with integrity enforced by keys, CHECK constraints, six triggers and four views."));
A.push(bullet("A transaction design that prevents an item from being sold twice, even when two buyers act at the same moment."));
A.push(bullet("Three AI modules that use the database as their training data: a TF-IDF recommender driven by search history, a regression-based price suggester and a Naive Bayes spam detector."));
A.push(bullet("A complete web application with student and administrator roles, including a read-only SQL explorer that demonstrates the database live."));
A.push(P("Section II reviews related work and Section III lists the requirements. Section IV presents the system and database design, Section V the AI modules, Section VI the implementation and Section VII the results. Section VIII concludes the paper."));

// II. Literature survey
A.push(H1("II", "Literature Survey"));
A.push(H2("A", "Relational Databases and ER Modelling"));
A.push(P("Codd’s relational model [3] and Chen’s entity-relationship model [4] remain the foundation of database design, and standard textbooks [1], [2] describe how an ER model is mapped to relations and normalized. Triggers and views [1] allow business rules to be enforced inside the DBMS instead of in application code, and ACID transactions [12] keep data consistent under concurrent access."));
A.push(H2("B", "Recommender Systems"));
A.push(P("Collaborative filtering, popularised by Amazon’s item-to-item approach [13], needs many users with overlapping purchases, which a single campus does not have at launch. Content-based filtering [6] instead compares item descriptions with a profile built from the user’s own behaviour, usually with TF-IDF weighting [5] and cosine similarity. Users without any history form the well-known cold-start problem [9], commonly handled with a popularity-based fallback."));
A.push(H2("C", "Spam Detection and Price Estimation"));
A.push(P("Naive Bayes classifiers have been used for junk e-mail filtering since [7], and the multinomial variant performs well on short texts [14]. Linear regression is the standard, interpretable baseline for price estimation. The scikit-learn library [8] provides tested implementations of all three techniques."));
A.push(H2("D", "Existing Platforms"));
A.push(P("Table I compares CampusKart with the platforms students use today. None of the existing options combines a campus-only audience with structured data, price guidance and fraud screening."));
A.push(...TABLE("Comparison With Existing Platforms",
  ["Feature", "OLX / FB", "Chat groups", "CampusKart"],
  [
    ["Restricted to campus", "No", "Yes", "Yes"],
    ["Search and filters", "Yes", "No", "Yes"],
    ["Personal recommendations", "Opaque", "No", "Explained"],
    ["Fair price suggestion", "No", "No", "Yes"],
    ["Spam / fraud screening", "Partial", "No", "AI + admin"],
    ["Seller ratings", "Partial", "No", "Yes"],
    ["Double-sale prevention", "No", "No", "Trigger"],
  ], [1918, 1000, 1000, 1100]));

// III. Requirements
A.push(H1("III", "Requirement Analysis"));
A.push(H2("A", "Functional Requirements"));
A.push(bullet("Registration and login with two roles: student and administrator."));
A.push(bullet("Listing an item with category, condition, MRP, age and price."));
A.push(bullet("Search with filters (category, condition, maximum price) and sorting."));
A.push(bullet("Wishlist, purchase, cancellation, receipt confirmation and seller rating."));
A.push(bullet("Notifications for sales, cancellations, wishlist items and moderation."));
A.push(bullet("AI recommendations, price suggestion and spam screening."));
A.push(bullet("Admin dashboard, listing moderation, user blocking and SQL explorer."));
A.push(H2("B", "Non-Functional Requirements"));
A.push(P("The system must never sell an item twice (consistency), store only hashed passwords and use parameterised queries (security), work on phones and laptops (usability), answer every request in under 100 ms (performance), and run on any laptop without installing a database server (portability)."));
A.push(H2("C", "Hardware and Software Requirements"));
A.push(P("Any PC with 4 GB RAM and a modern browser is sufficient. The software stack is Python 3.12, Flask 3.1, SQLite 3, scikit-learn 1.8 and NumPy, with HTML5, CSS3 and JavaScript on the client."));
A.push(H2("D", "Use Case Model"));
A.push(P(`Fig. 2 shows the two actors. A student registers, searches, receives recommendations, sells with a price hint, buys, cancels, rates sellers, manages a wishlist and reads notifications. An administrator reviews AI-flagged listings, blocks users, views reports and runs read-only SQL queries.`));

// IV. Design
A.push(H1("IV", "System Design"));
A.push(H2("A", "System Architecture"));
A.push(P("CampusKart follows a three-tier architecture (Fig. 1). The presentation tier is a server-rendered web interface. The application tier, written in Flask, handles routing, sessions, authentication and business logic, and calls the three AI modules. The data tier is a single SQLite database that also serves as the training data for the AI models, so no separate data pipeline is needed."));
A.push(...FIGURE("arch", "architecture.png", "Three-tier architecture of CampusKart."));
A.push(...FIGURE("uc", "use_case.png", "Use case diagram."));
A.push(H2("B", "Data Flow Diagrams"));
A.push(P("The context diagram (Fig. 3) treats the whole system as one process exchanging data with the two external entities. The level-1 DFD (Fig. 4) decomposes it into six processes: authenticate user, search and browse, manage listings, process orders, generate recommendations, and moderate and report. These processes use five data stores: Users, Products, Orders and Reviews, Search History and Views, and Notifications. The flows marked as triggers are produced by the DBMS itself, not by the application."));
A.push(...FIGURE("dfd0", "dfd_level0.png", "Level-0 (context) data flow diagram."));

const dfd1Fig = FIGURE("dfd1", "dfd_level1.png", "Level-1 data flow diagram.", true);

const B = [];   // two-column part 2 (after full-width DFD level 1)
B.push(H2("C", "Entity-Relationship Model"));
B.push(P("The ER diagram in Fig. 5 uses Chen notation and contains seven entity sets: USER, PRODUCT, CATEGORY, ORDER, REVIEW, SEARCH_HISTORY and NOTIFICATION. The relationships and their cardinalities are:"));
B.push(bullet("SELLS (USER 1 : N PRODUCT) and BELONGS_TO (PRODUCT N : 1 CATEGORY), both with total participation of PRODUCT."));
B.push(bullet("PLACES (USER 1 : N ORDER), CONTAINS (ORDER N : 1 PRODUCT) and HAS (ORDER 1 : 1 REVIEW)."));
B.push(bullet("WISHLISTS and VIEWS (USER M : N PRODUCT), with descriptive attributes added_at and viewed_at."));
B.push(bullet("PERFORMS (USER 1 : N SEARCH_HISTORY) and RECEIVES (USER 1 : N NOTIFICATION)."));
B.push(P("A product can appear in several orders over time because a cancelled order puts it back on sale, which is why CONTAINS is N : 1 and not 1 : 1."));

const erFig = FIGURE("er", "er_diagram.png", "Entity-relationship diagram of CampusKart (Chen notation).", true);

const C = [];   // after full-width ER
C.push(H2("D", "Relational Schema"));
C.push(P("The ER model was mapped to relations with the standard rules [2]. Each strong entity set became a table with a surrogate integer primary key. Each 1 : N relationship became a foreign key on the N side, and the 1 : 1 HAS relationship became a foreign key with a UNIQUE constraint in reviews. The M : N WISHLISTS relationship became the table wishlist with the composite primary key (user_id, product_id). VIEWS uses a surrogate key view_id instead, because the recommender needs every repeated view with its timestamp. The resulting schema is shown in Fig. 6 and summarised in Table II."));

const schemaFig = FIGURE("schema", "relational_schema.png", "Relational schema with primary keys, foreign keys and unique constraints.", true);

const D = [];   // after full-width schema
D.push(...TABLE("Tables in the Database",
  ["Table", "Primary key", "Foreign keys", "Rows"],
  [
    ["users", "user_id", "–", "12"],
    ["categories", "category_id", "–", "9"],
    ["products", "product_id", "seller_id, category_id", "58"],
    ["orders", "order_id", "product_id, buyer_id", "7"],
    ["reviews", "review_id", "order_id (unique)", "5"],
    ["wishlist", "(user_id, product_id)", "user_id, product_id", "4"],
    ["search_history", "search_id", "user_id", "21"],
    ["product_views", "view_id", "user_id, product_id", "70"],
    ["notifications", "notif_id", "user_id", "22"],
  ], [1250, 1450, 1718, 600]));
D.push(P("The demonstration database holds 208 rows and occupies only 108 KB, which keeps it small enough to inspect during a viva while still exercising every relationship."));
D.push(H2("E", "Normalization"));
D.push(P("**First normal form:** every attribute is atomic. A student’s wishlist, for example, is stored as rows of a separate table and not as a list inside users."));
D.push(P("**Second normal form:** the only composite key is (user_id, product_id) in wishlist, and its single non-key attribute added_at depends on the whole key. All other tables have single-attribute keys, so partial dependencies cannot occur."));
D.push(P("**Third normal form:** transitive dependencies were removed during design. Storing seller_name in products would create product_id → seller_id → seller_name, so only seller_id is kept. Likewise, orders does not store seller_id, because order_id → product_id → seller_id. Derived values such as a seller’s average rating are computed by views instead of being stored, which avoids update anomalies."));
D.push(P("In every table each determinant is a candidate key (for example, email is a candidate key of users), so the schema also satisfies Boyce-Codd normal form."));
D.push(H2("F", "Constraints, Triggers, Views and Indexes"));
D.push(P("Domain rules are declared as CHECK constraints: price > 0, rating between 1 and 5, year between 1 and 4, and enumerated values for role, condition and status. Referential integrity uses foreign keys with ON DELETE CASCADE where child rows have no meaning on their own. Table III lists the six triggers that move business logic into the DBMS."));
D.push(...TABLE("Database Triggers",
  ["Trigger", "Event", "Action"],
  [
    ["trg_order_validate", "BEFORE INSERT orders", "Abort if item not available or buyer is seller"],
    ["trg_order_placed", "AFTER INSERT orders", "Mark product sold, notify seller"],
    ["trg_order_cancelled", "AFTER UPDATE orders", "Re-list product, notify seller"],
    ["trg_wishlist_sold_alert", "AFTER UPDATE products", "Notify users who wishlisted it"],
    ["trg_flagged_listing", "AFTER INSERT products", "Alert admins about AI-flagged listing"],
    ["trg_listing_moderated", "AFTER UPDATE products", "Tell seller approved / rejected"],
  ], [1550, 1300, 2168]));
D.push(P("The validation trigger is the key safeguard against double selling:", { keepNext: true }));
D.push(...code([
  "CREATE TRIGGER trg_order_validate",
  "BEFORE INSERT ON orders",
  "BEGIN",
  "  SELECT RAISE(ABORT,",
  "         'This product is no longer available')",
  "  WHERE (SELECT status FROM products",
  "         WHERE product_id = NEW.product_id)",
  "        <> 'available';",
  "  SELECT RAISE(ABORT,",
  "         'You cannot buy your own product')",
  "  WHERE (SELECT seller_id FROM products",
  "         WHERE product_id = NEW.product_id)",
  "        = NEW.buyer_id;",
  "END;",
]));
D.push(P("Four views provide reusable read-only queries: v_product_details (a four-table join used by every listing page), v_seller_ratings (AVG with GROUP BY), v_category_sales (LEFT JOIN with SUM) and v_admin_stats (scalar subqueries for the dashboard). Six indexes, such as products(status, category_id) and search_history(user_id, searched_at), support the most frequent queries."));
D.push(H2("G", "Transaction Management"));
D.push(P(`Every write runs inside a transaction: the application opens it with BEGIN and ends with COMMIT on success or ROLLBACK on any error. Fig. 7 shows a purchase. Inserting the order fires the validation trigger, then the after-insert trigger marks the product sold and creates notifications. All of these steps commit together or not at all (atomicity). SQLite serialises writers with a database-level lock, so if two students press Buy at the same moment the second insert runs after the first, sees the status sold, and is aborted by the trigger (isolation). The rollback journal provides durability.`));
D.push(...FIGURE("seq", "buy_sequence.png", "Sequence of a purchase: one atomic transaction with triggers."));

// V. AI modules
D.push(H1("V", "AI Modules"));
D.push(H2("A", "Recommendations From Search History"));
D.push(P("Each available product is converted into a TF-IDF vector built from its title (weighted twice), category and description. Character n-grams of length 3 to 5 are used instead of whole words, so partial or misspelled searches such as “arduno” still match “Arduino”. With sublinear term frequency and smoothed inverse document frequency, the weight of n-gram t in product d is"));
D.push(EQ([["w(t, d) = (1 + ln tf(t, d)) · [ln((1 + N) / (1 + df(t))) + 1]"]], 1));
D.push(P("where N is the number of products and df(t) the number of products containing t. Similarity between two vectors is the cosine", { noIndent: true }));
D.push(EQ([["cos(a, b) = (a · b) / (‖a‖ ‖b‖)"]], 2));
D.push(P("The user profile consists of signals read from the database: the last ten distinct searches, the last ten viewed products and the wishlist. A signal of rank r (0 for the newest) receives the weight β · 0.9^r, where β is 1.0 for searches and wishlist items and 0.8 for views. The score of product p is the strongest weighted match"));
D.push(EQ([["score(p) = max"], ["i", "sub"], [" w"], ["i", "sub"], [" · cos(s"], ["i", "sub"], [", p)"]], 3));
D.push(P("and matches with a cosine below 0.15 are ignored. The signal that produced the maximum becomes the explanation shown on the card, for example “Because you searched ‘python’”. Products already in the wishlist or sold by the user are excluded, and the top eight are displayed. When a user has no history (the cold-start case), the system shows the items viewed most in the last 30 days instead. The complete pipeline is shown in Fig. 8. The same TF-IDF index also powers the “Similar items” panel and a typo-tolerant “Did you mean” search.", { noIndent: true }));
D.push(...FIGURE("flow", "recommendation_flow.png", "Recommendation pipeline with cold-start fallback.", false, 270));
D.push(H2("B", "Fair Price Prediction"));
D.push(P("Prices range from about Rs. 100 to Rs. 52,000, so instead of predicting the price directly the model predicts the resale ratio r = price / MRP, which lies on the same scale for every item. The features are a one-hot encoding of the condition (New, Like New, Good, Fair), the age in years capped at five, and a one-hot encoding of the nine categories. An ordinary least-squares linear regression is trained on all approved listings each time a prediction is requested:"));
D.push(EQ([["r̂ = θ"], ["0", "sub"], [" + Σ"], ["k", "sub"], [" θ"], ["k", "sub"], [" x"], ["k", "sub"], [",   price = clip(r̂, 0.10, 0.95) · MRP"]], 4));
D.push(P("The suggestion is rounded and shown with a ±10% range. On the demonstration data the model learned that Like New items keep about 8 percentage points more of their MRP than Good items, Fair items about 8 points less, and every year of age costs about 3 points. The same model labels each product page for buyers as Great deal (at least 10% below the estimate), Fair price or Overpriced (more than 12% above)."));
D.push(H2("C", "Spam and Fraud Detection"));
D.push(P("A Multinomial Naive Bayes classifier with TF-IDF word and bigram features is trained on 38 labelled genuine and spam listings. For a listing d it estimates"));
D.push(EQ([["P(spam | d) ∝ P(spam) · Π"], ["t", "sub"], [" P(t | spam)"]], 5));
D.push(P("Three explainable rules complement the model: a phone number, link or off-platform payment word (UPI, GPay, OTP), a price above the MRP, and a price below 5% of the MRP. Each rule raises the score to at least 0.55 to 0.6, and a listing whose final score reaches 0.5 is stored with status pending. The insert fires trg_flagged_listing, which notifies every administrator, and the admin’s decision fires trg_listing_moderated, which informs the seller. The sell page also calls the detector while the student types, so problems are visible before the listing is published."));

// VI. Implementation
D.push(H1("VI", "Implementation"));
D.push(H2("A", "Technology and Structure"));
D.push(P("The application consists of schema.sql (tables, indexes, triggers and views), seed.py (demonstration data), app.py (about 40 Flask routes), the ai package (recommender.py, price_predictor.py and spam_detector.py), 18 Jinja2 templates and one stylesheet with no external dependencies. SQL is written by hand rather than through an ORM so that every query is visible. A typical query, used for the profile page, is:"));
D.push(...code([
  "SELECT p.seller_id,",
  "       ROUND(AVG(r.rating), 1) AS avg_rating,",
  "       COUNT(r.review_id)      AS review_count",
  "FROM reviews r",
  "JOIN orders   o ON o.order_id   = r.order_id",
  "JOIN products p ON p.product_id = o.product_id",
  "GROUP BY p.seller_id;",
]));
D.push(H2("B", "Security"));
D.push(P("Passwords are stored as salted PBKDF2 hashes. Every query uses parameter binding, which prevents SQL injection. Role checks protect all admin routes, blocked users are logged out on their next request, and the SQL explorer accepts only SELECT or WITH statements and runs them over a separate read-only connection (mode=ro), so even a crafted query cannot modify data. Users can view and clear their own search history, which controls what the recommender knows about them."));
D.push(H2("C", "Demonstration Data"));
D.push(P("The seed script creates an administrator and eleven students. Four demonstration students have distinct search histories: computer science (DBMS, Python, laptop), mechanical (engineering drawing, drafter, calculator), electronics (Arduino, multimeter) and hostel items (cycle, mattress, kettle). A fifth, new student has no history, which demonstrates the cold-start case. The database contains 58 products in nine categories, seven orders including one cancellation, five reviews and two spam listings that wait for moderation."));

// VII. Results
D.push(H1("VII", "Results and Discussion"));
D.push(H2("A", "Functional Testing"));
D.push(P("An automated test script drives the application through every page and flow. Table IV lists the most important cases, all of which pass."));
D.push(...TABLE("Selected Test Cases",
  ["Test case", "Expected result", "Status"],
  [
    ["Login with wrong password", "Error message, no session", "Pass"],
    ["Blocked user logs in", "Access denied", "Pass"],
    ["Buy an available item", "Order placed, item sold, seller notified", "Pass"],
    ["Second buyer, same item", "Aborted by trigger", "Pass"],
    ["Cancel an order", "Item listed again", "Pass"],
    ["Review same order twice", "Rejected by UNIQUE", "Pass"],
    ["Post a spam listing", "Pending, admins notified", "Pass"],
    ["Admin approves listing", "Live, seller notified", "Pass"],
    ["DELETE in SQL explorer", "Rejected (read-only)", "Pass"],
    ["Search for “arduno”", "AI suggests Arduino items", "Pass"],
  ], [1800, 2518, 700]));
D.push(H2("B", "Evaluation of the AI Modules"));
D.push(P("Table V summarises the measured results. Recommendation quality was measured as precision at five: the share of the top five suggestions that belong to the categories each demonstration profile is interested in. The price model was evaluated with five-fold cross validation on 56 listings, and the Naive Bayes model with leave-one-out validation on its 38 training examples. Response times are averages on a standard laptop."));
D.push(...TABLE("Evaluation of AI Modules",
  ["Module", "Metric", "Result"],
  [
    ["Recommender", "Precision@5 (4 profiles)", "1.00"],
    ["Recommender", "Average response time", "7.9 ms"],
    ["Price model", "MAPE (5-fold CV)", "7.2%"],
    ["Price model", "R² on resale ratio", "0.55"],
    ["Price model", "Average response time", "0.7 ms"],
    ["Spam detector", "Accuracy / F1 (LOO)", "1.00 / 1.00"],
    ["Spam detector", "False alarms on 56 genuine listings", "0"],
  ], [1400, 2618, 1000]));
D.push(P("These scores come from a small, clean demonstration dataset and should not be read as general accuracy; a real deployment would need more listings and labelled spam to confirm them. The character n-gram matching occasionally links unrelated words (for example “breadboard” and “drawing board”), and the 0.15 similarity threshold removes most of these weak matches."));

const recsFig = FIGURE("recs", "fig_recs_compare.png", "Home pages of two students with different search histories: the same database gives each a different, explained recommendation list.", true);

const E = [];   // after full-width screenshot figure
E.push(H2("C", "User Interface"));
E.push(P("Fig. 9 shows the home pages of two demonstration students. With the same database, the mechanical student sees drawing instruments and calculators, while the computer science student sees programming books and a keyboard, each with the search that caused it. Fig. 10 shows the sell page: the AI suggests Rs. 690 for a calculator with an MRP of Rs. 1,200, and the spam checker reacts to the words “whatsapp me” before the listing is published. Fig. 11 shows the price badge on a product page, Fig. 12 the typo-tolerant search, Fig. 13 the moderation queue with the reasons for each flag, and Fig. 14 the SQL explorer running a join with GROUP BY."));
E.push(...FIGURE("sell", "ss_sell_ai.png", "Sell page with AI price suggestion and live spam check."));
E.push(...FIGURE("product", "ss_product.png", "Product page with the AI fair-price badge."));
E.push(...FIGURE("typo", "ss_typo_search.png", "No exact match for “arduno”: the AI suggests close matches."));
E.push(...FIGURE("flag", "ss_admin_flagged.png", "Admin queue of listings flagged by the spam detector."));
E.push(...FIGURE("sql", "ss_sql_explorer.png", "Read-only SQL explorer in the admin panel."));

// VIII. Conclusion
E.push(H1("VIII", "Conclusion and Future Scope"));
E.push(P("CampusKart shows that a carefully normalized database can serve both as the core of a transactional application and as the training data for useful AI features. Triggers, views and transactions keep the data consistent without extra application code, while TF-IDF recommendations, regression-based pricing and Naive Bayes screening make the marketplace easier and safer to use. All three AI modules are simple enough to explain step by step, and each of their outputs carries a reason that the user can see."));
E.push(P("Future work includes migrating to MySQL or PostgreSQL for multi-campus use, adding collaborative filtering once enough purchase history exists, uploading product photographs with image-based duplicate detection, in-app chat between buyer and seller, and retraining the spam model on listings rejected by administrators."));

E.push(H1u("Acknowledgment"));
E.push(P("The authors thank [[Guide Name]], [[Department]], [[College Name]], for guidance and support throughout this project.", { noIndent: false }));

E.push(H1u("References"));
const REFS = [
  "A. Silberschatz, H. F. Korth, and S. Sudarshan, *Database System Concepts*, 7th ed. New York: McGraw-Hill, 2019.",
  "R. Elmasri and S. B. Navathe, *Fundamentals of Database Systems*, 7th ed. Boston: Pearson, 2016.",
  "E. F. Codd, “A relational model of data for large shared data banks,” *Commun. ACM*, vol. 13, no. 6, pp. 377–387, 1970.",
  "P. P. Chen, “The entity-relationship model—toward a unified view of data,” *ACM Trans. Database Syst.*, vol. 1, no. 1, pp. 9–36, 1976.",
  "G. Salton and C. Buckley, “Term-weighting approaches in automatic text retrieval,” *Inf. Process. Manage.*, vol. 24, no. 5, pp. 513–523, 1988.",
  "P. Lops, M. de Gemmis, and G. Semeraro, “Content-based recommender systems: State of the art and trends,” in *Recommender Systems Handbook*, F. Ricci, L. Rokach, B. Shapira, and P. B. Kantor, Eds. Boston: Springer, 2011, pp. 73–105.",
  "M. Sahami, S. Dumais, D. Heckerman, and E. Horvitz, “A Bayesian approach to filtering junk e-mail,” in *Proc. AAAI Workshop on Learning for Text Categorization*, 1998, pp. 55–62.",
  "F. Pedregosa *et al.*, “Scikit-learn: Machine learning in Python,” *J. Mach. Learn. Res.*, vol. 12, pp. 2825–2830, 2011.",
  "A. I. Schein, A. Popescul, L. H. Ungar, and D. M. Pennock, “Methods and metrics for cold-start recommendations,” in *Proc. 25th Annu. Int. ACM SIGIR Conf.*, 2002, pp. 253–260.",
  "SQLite Consortium, “SQLite documentation,” 2024. [Online]. Available: https://www.sqlite.org/docs.html",
  "M. Grinberg, *Flask Web Development*, 2nd ed. Sebastopol, CA: O’Reilly, 2018.",
  "J. Gray and A. Reuter, *Transaction Processing: Concepts and Techniques*. San Mateo, CA: Morgan Kaufmann, 1993.",
  "G. Linden, B. Smith, and J. York, “Amazon.com recommendations: Item-to-item collaborative filtering,” *IEEE Internet Comput.*, vol. 7, no. 1, pp. 76–80, 2003.",
  "V. Metsis, I. Androutsopoulos, and G. Paliouras, “Spam filtering with naive Bayes—Which naive Bayes?” in *Proc. 3rd Conf. Email and Anti-Spam (CEAS)*, 2006.",
];
REFS.forEach((r, i) => E.push(new Paragraph({
  alignment: AlignmentType.JUSTIFIED,
  indent: { left: 360, hanging: 360 },
  spacing: { after: 20 },
  children: [new TextRun({ text: `[${i + 1}]\t`, font: FONT, size: 16 }), ...runs(r, { font: FONT, size: 16 })],
  tabStops: [{ type: TabStopType.LEFT, position: 360 }],
})));

// ------------------------------------------------------------------ assemble sections
// Full-width figures sit in single-column continuous sections between two-column sections.
const twoCol = { column: { count: 2, space: GAP, equalWidth: true } };
const oneCol = { column: { count: 1 } };
const sec = (children, cols, first = false) => ({
  properties: { ...(first ? {} : { type: SectionType.CONTINUOUS }), page: PAGE, ...cols },
  children,
});

const doc = new Document({
  creator: "CampusKart project team",
  title: "CampusKart: An AI-Enabled Database System for a Peer-to-Peer Student Marketplace",
  styles: {
    default: { document: { run: { font: FONT, size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 20, smallCaps: true, color: "000000" },
        paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 160, after: 80 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 20, italics: true, color: "000000" },
        paragraph: { spacing: { before: 120, after: 60 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: {
    config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022",
      alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 216 } } } }] }],
  },
  sections: [
    sec(titleBlock, oneCol, true),
    sec(A, twoCol),
    sec(dfd1Fig, oneCol),
    sec(B, twoCol),
    sec(erFig, oneCol),
    sec(C, twoCol),
    sec(schemaFig, oneCol),
    sec(D, twoCol),
    sec(recsFig, oneCol),
    sec(E, twoCol),
  ],
});

const out = path.join(__dirname, "CampusKart_IEEE_Report.docx");
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(out, buf); console.log("written", out); });
