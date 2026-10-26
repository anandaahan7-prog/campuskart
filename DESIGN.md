---
name: CampusKart
description: The department notice board, made searchable. Give your stuff a second semester.
colors:
  frame: "#36251a"
  frame-ink: "#f5ead9"
  frame-muted: "#cdb99d"
  cork: "#ead9bf"
  cork-ink: "#2b1e14"
  cork-muted: "#66503c"
  paper: "#fffdf8"
  paper-2: "#f6f0e4"
  line: "#e4d9c6"
  rule: "#efe7da"
  control: "#9b886d"
  ink: "#1f1711"
  ink-2: "#4a3d31"
  muted: "#6a5949"
  canary: "#fff3b0"
  sky: "#dfeffd"
  pink: "#ffe4ea"
  mint: "#dff4e6"
  peach: "#ffe7d3"
  sage: "#e9efd9"
  aqua: "#daf1f0"
  pin: "#cf2e26"
  pin-hover: "#b3241d"
  brass: "#b8892f"
  pen: "#1d4fc4"
  good: "#1a6b3c"
  warn: "#8a4b08"
  bad: "#a3261d"
  chart: "#7a4e2d"
  star: "#a8670a"
typography:
  title:
    fontFamily: "Archivo, Segoe UI, system-ui, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 800
    lineHeight: 1.12
    letterSpacing: "-0.01em"
  section:
    fontFamily: "Archivo, Segoe UI, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 800
    lineHeight: 1.12
  price:
    fontFamily: "Archivo, Segoe UI, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 800
    lineHeight: 1.2
  price-hero:
    fontFamily: "Archivo, Segoe UI, system-ui, sans-serif"
    fontSize: "2.5rem"
    fontWeight: 800
    lineHeight: 1
  body:
    fontFamily: "Archivo, Segoe UI, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  reading:
    fontFamily: "Archivo, Segoe UI, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Archivo, Segoe UI, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.4
  hand:
    fontFamily: "Caveat, Segoe Print, cursive"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.1
rounded:
  paper: "2px"
  panel: "4px"
  control: "6px"
  sheet: "16px"
  full: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  xxl: "48px"
components:
  button-pin:
    backgroundColor: "{colors.pin}"
    textColor: "#ffffff"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "40px"
  button-pin-hover:
    backgroundColor: "{colors.pin-hover}"
  button-ink:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "40px"
  button-outline:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "40px"
  button-paper:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    height: "32px"
  slip:
    backgroundColor: "{colors.canary}"
    textColor: "{colors.ink}"
    rounded: "{rounded.paper}"
    padding: "24px 16px 12px"
  panel:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "24px"
  sticky-note:
    backgroundColor: "{colors.canary}"
    textColor: "{colors.ink}"
    rounded: "{rounded.paper}"
    padding: "16px 20px 20px"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    height: "40px"
  chip:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.paper}"
    height: "32px"
---

# Design System: CampusKart

## Overview

CampusKart is the department notice board, made searchable. A walnut frame holds one cork board; every listing is a paper slip pinned to it with a brass pin, and the perforated tear-off tabs at the foot of each slip are how you get in touch. The world refuses the category default of a white card grid with a blue search bar: anyone who has walked past a college corridor recognises it in a second.

The screens are tools (Operate mode). Expression lives in the material (cork, paper, pins, stamps, handwriting) and in one authored moment; the layouts themselves stay quiet, scannable and conventional. The guest home is the one persuade moment, built from the same slips.

Key characteristics:
- A framed sheet: walnut top bar and an 8px walnut L around one cork sheet with 16px corners.
- Paper colour is the category, everywhere: slips, category tabs, swatches in tables.
- Red is the pushpin: the one next action on a screen, nothing else.
- The AI writes by hand in ballpoint blue, and circles "AI" in the same pen.
- States are rubber stamps; a sold item gets one big rotated "Sold".
- Buying tears a tab off the slip and puts the seller's number in your hand.

## Colors

The palette is the board's materials, with three inks that carry meaning: marker black for everything, pushpin red for the next action, ballpoint blue for the AI.

### Primary
- **Pushpin red** (`pin`, #cf2e26): the screen's one next action. Buy, Accept, Reply to the counter, Review listings, Pin it to the board, Create free account. Also the unread badge. White text holds 5.2:1.

### Secondary
- **Ballpoint blue** (`pen`, #1d4fc4): every AI output (recommendation reasons, fair-price verdicts, suggested offers, the spam-check hint) and the focus ring. 5.1:1 on cork, 5.7:1 on canary.

### Neutral
- **Walnut** (`frame`, #36251a) for the top bar, the L-frame and the phone tab bar, with `frame-ink` and `frame-muted` on it.
- **Cork** (`cork`, #ead9bf) with a speckle texture drawn in SVG; text on it uses `cork-ink` and `cork-muted` (5.4:1).
- **Paper** (`paper`, #fffdf8) for every working panel, `paper-2` for inset areas, `line` for paper edges and `rule` for row rules.
- **Marker ink** (`ink`, #1f1711), `ink-2`, and `muted` (#6a5949, 6.5:1 on paper, 5.4:1 on canary).

### Category papers
`canary` books, `sky` electronics, `paper` calculators and clothing, `pink` drawing instruments, `mint` lab equipment, `peach` hostel essentials, `sage` cycles, `aqua` sports. All are pale enough to stay off the colour budget.

### Named Rules
**The Pushpin Rule.** Red appears once per screen, on the action that moves the deal forward. The header's "Sell an item" is a blank paper slip, not red.
**The Pen Rule.** Blue means the AI said it. Nothing else is blue except the focus ring.
**The Paper Rule.** Category is told by paper colour, never by an emoji or an icon in a tinted box.

Dark theme is the same board at night: near-black frame #0e0a07, dark cork #2a2018, dim paper #322920, chalk ink #eee8de, papers dimmed to the same hues, pen lifted to #9db8ff.

## Typography

**Display and UI font:** Archivo (variable width and weight), Segoe UI fallback.
**Hand font:** Caveat, for annotations only.
**Code:** Cascadia Code or Consolas, for SQL and schema text only.

Headings and prices use Archivo at 82% width and weight 800: the condensed black of a marker on a slip. Body and UI use the normal width at 400 to 600.

### Hierarchy
- **Title** (800, 28px, 24px on phones): one h1 per screen. The guest headline is 32px.
- **Section** (800, 20px): section and card headings.
- **Price** (800 condensed, 20px on slips, 40px on the product slip): always tabular figures.
- **Reading** (400, 16px, 1.55): descriptions and page sublines.
- **Body** (400, 14px, 1.5): UI, table cells, lists.
- **Label** (500, 12-13px): table headers in sentence case, meta lines, stamps.
- **Hand** (Caveat 600, 20px): AI reasons, finding labels, the footer line.

### Named Rules
**Two Faces Rule.** Archivo and Caveat only. Monospace is for literal SQL.
**Tabular Rule.** Every price, count and KPI uses tabular figures.

## Layout

The page is a framed sheet: a 56px walnut top bar and an 8px walnut gutter around one cork sheet. Content sits in a 1240px container with 24px gutters (16px on phones). Sections are 48px apart; the space above a heading is always larger than below it.

- **Home (student):** board header (title, handwritten note, recent-search tags), then a two-column grid: six slips three across, and a 340px rail with the one finding on a sticky note, open offers and the latest notifications. Below: nine category tabs in one row, then four "Just pinned" slips.
- **Product:** the item as one large slip (left) beside the deal (right): the AI fair-price check, the red Buy, Make an offer, the seller and their reviews.
- **Tables** sit on paper panels; numbers right-aligned, identity column widest.
- **Breakpoints:** 1100px (rail moves above the slips, category tabs 3 across), 960px (two-column pages stack), 720px (phone: bottom walnut tab bar, slips two across, KPI strip two across, wide tables scroll inside their frame).

## Elevation & Depth

Depth is physical and shallow: paper resting on cork. Slips, chips, category tabs and report tiles cast a small drop-shadow filter that follows the paper's shape (so a torn tab's gap shows the cork); panels use a box shadow of the same strength. Nothing at rest exceeds about 10% opacity. Floating things (menus, toasts, the confirm dialog) take the one larger shadow.

### Shadow Vocabulary
- `shadow-slip`: `0 1px 1px rgb(54 37 26 / .08), 0 3px 8px -3px rgb(54 37 26 / .08)`, panels.
- `drop-slip`: `drop-shadow(0 1px 1px rgb(54 37 26 / .10)) drop-shadow(0 3px 5px rgb(54 37 26 / .07))`, slips and paper controls.
- `shadow-float`: `0 2px 6px rgb(30 20 12 / .10), 0 16px 36px -10px rgb(30 20 12 / .30)`, menus, toasts, dialogs.

### Named Rules
**Border or shadow, never both.** Paper has a shadow; inner strips on paper use a tone step instead.

## Shapes

Paper is nearly square: 2px on slips, notes and tabs, 4px on panels. Controls are 6px. The cork sheet is the only soft shape, at 16px. Pins and avatars are circles. Stamps are 3px rectangles with a 1.5px outline.

## Components

### Buttons
- **Pin (primary):** red fill, white label, 40px (46px large, 32px small), 6px radius. Once per screen.
- **Ink (default):** marker-black fill, paper label. Log in, Save changes, Apply filters, Approve.
- **Outline:** paper fill, `control` border. Save, Edit listing, Counter, View all.
- **Paper:** paper fill on the walnut bar (Sell an item, Sign up).
- **Ghost:** no fill; Withdraw, Decline, Cancel order.
- **AI outline:** pen-blue 1.5px outline and label ("Suggest a price").
- All buttons press to 0.97 over 140ms; hover changes colour only.

### Chips
Paper tags with a drop shadow for recent searches and quick picks; hover turns them canary.

### Cards / Containers
- **Panel:** paper, 4px radius, `shadow-slip`, 24px padding (16px on phones).
- **Sticky note:** canary (or mint, pink, sky by tone) square, slightly rotated, used for the home finding, toasts and callouts.

### Inputs / Fields
Paper fill, 1px `control` border (3.5:1), 6px radius, 40px tall, 16px text. Focus: pen-blue border and a 3px pen ring. Placeholders in `muted`.

### Navigation
Walnut top bar with frame-muted links; the current page gets frame-ink and a 2px underline. Sub-navigation and page tabs are underline tabs on a 1px rule. On phones a walnut bottom bar carries five destinations with Sell as a paper pill.

### Slip (signature)
Category paper, brass pin, condition and category, the printed picture, title (16px, two lines), condensed price with MRP and "% off", the AI reason in blue handwriting, seller and rating, then a perforated row of tear-off tabs (four on the grid, six on the product slip) carrying the seller's first name. Pinned a few tenths of a degree crooked; straightens and lifts 3px on hover.

### Tear-off (signature moment)
After an order, the product slip shows one tab missing, its ragged stub left at the perforation, and the tab "in hand" below with the seller's number as a `tel:` link. Arriving from Buy or Accept counter (`?torn=1`), the tab tugs, pivots from its top corner and falls away (820ms, ease-in) before the number lands (420ms, ease-out). Reduced motion: both simply fade.

### Stamps
Outlined, sentence case, 12px condensed bold: green Live, Completed, Accepted; amber Pending, Countered; brick Declined, Cancelled, Removed; ink Awaiting pickup, Sold; grey Withdrawn, Expired.

## Do's and Don'ts

### Do:
- **Do** put the screen's one finding first, with its red action beside it.
- **Do** write every AI output in the pen: Caveat for the note, "AI" circled.
- **Do** use the category paper colour for a listing wherever it appears.
- **Do** keep prices, counts and KPIs in tabular figures, right-aligned in tables.
- **Do** keep the tear-off the only authored animation; everything else is feedback.

### Don't:
- **Don't** use red for anything that isn't the next action (no red headers, links or decoration).
- **Don't** use emoji or icons in tinted boxes for categories; use the paper swatch.
- **Don't** add eyebrows above headings, gradients, glass or glowing buttons.
- **Don't** animate content in on page load.
- **Don't** set titles above 32px or figures above 40px on working screens.
- **Don't** put a border and a shadow on the same surface.
