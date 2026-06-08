# Handoff: "Matchday Programme" visual direction — Fixtures + Score Picker

## Overview
This package defines a new visual direction for the World Cup predictor app, called **"The Matchday Programme."** It replaces the previous dark / rounded-corner / glassy-app-nav theme (which read as a generic app shell) with a printed **stadium-programme** aesthetic: warm cream paper, editorial display type, a pitch-green + lime accent system, sporty LED scoreboards, and **square corners throughout**. Subtle football motifs (pitch markings, mown-grass stripes, goal-net texture) tie it to the sport.

It is the blend between two earlier explorations — an ink-on-paper **Broadsheet** sports page and a **Broadcast** TV scoreboard — and ships in two interchangeable "leans" so you can dial the personality:
- **Editorial lean** (≈ closer to a newspaper) — serif accents, double-rule, quieter.
- **Broadcast lean** (≈ closer to TV) — green header band, mown-grass stripes, bigger LED boards, louder.

Both leans share the **same tokens, components, and motifs** — only the header treatment, a couple of font choices, and scoreboard size differ.

> ### ✅ Chosen direction: **Broadcast lean**
> The product default is the **broadcast lean** — green broadcast header band, mown-grass stripes, larger LED scoreboards, `Archivo`/`Rajdhani` throughout (no serif). Build every screen in this lean. The editorial lean is documented below **for reference only** (it shows the alternative header/serif treatment and the shared component anatomy) — do not ship it. Where a screen below lists both leans, implement the **broadcast** one.

## About the Design Files
The files in this bundle are **design references built in HTML/React-via-Babel** — runnable prototypes that show the intended look and behaviour. They are **not** production code to copy verbatim. The task is to **recreate these designs inside the predictor's existing codebase**, using its established framework, component library, routing, and state patterns. If a component system already exists (buttons, inputs, cards), build these screens from those primitives and apply the tokens below — don't paste the prototype's raw inline styles.

The prototypes use a few conveniences that are **presentation-only** and should NOT be reproduced:
- A "design canvas" wrapper (`design-canvas.jsx`) that lays out artboards side-by-side.
- A phone status bar / home indicator (`wc-ui.jsx` → `PhoneStatusBar`, `HomeBar`) — these fake iOS chrome for the mockup; your real app shell replaces them.
- Inline `<style>` injection and Babel-in-browser — your app has its own styling system (CSS modules / Tailwind / styled-components / etc.).

## Fidelity
**High-fidelity.** Colours, typography, spacing, motifs and interactions are final. Recreate pixel-faithfully using your codebase's libraries. Exact values are in **Design Tokens** below; the prototype source files (`programme-picker.jsx`, `hybrid-concepts.jsx`) are the source of truth for anything not spelled out.

**Default lean = Broadcast.** Implement the broadcast variant of every screen (`HybridBroadcast` for fixtures, `PickerProgBroadcast` + `PickerProgDesktop` for the picker). Use `#f3eee1` as the page paper and `#cdfa57` as the lime. The editorial frames (`HybridEditorial`, `PickerProgEditorial`) are kept only to document the shared anatomy.

---

## Screenshots
Reference captures of the **broadcast** (default) screens are in `screenshots/`:
- `01-fixtures-broadcast.png` — the fixtures list (desktop, broadcast lean).
- `02-picker-mobile-broadcast.png` — the score picker (mobile, broadcast lean).
- `03-picker-desktop.png` — the score picker (desktop, broadcast lean).

## Screens / Views

There are two screens in this handoff. Each is shown in both leans.

### 1. Fixtures (match list)
**File:** `Programme Concepts.html` → components `HybridEditorial` (E1, editorial) and `HybridBroadcast` (E2, broadcast) in `hybrid-concepts.jsx`.
**Purpose:** Browse the matchday's fixtures; see which you've already predicted; jump into the picker for any match.

**Layout — Editorial lean (E1):**
- Full-width **green strip** (the only chrome at the top): left = a lime status dot + `MATCHDAY 01 · GROUP STAGE`; right = the date. Height ~36px, padding `9px 40px`.
- **Masthead** on cream, padding `22px 40px 0`: an `Archivo Black` H1 (~62px, uppercase, line-height .88) e.g. "The Fixtures", then a `Spectral` **italic** dek (~16px, muted) under a **3px double bottom rule** (ink).
- **Two-column body** (`grid-template-columns: 1fr 268px`): left = the fixtures list (right border 1px ink); right = a "Standings" aside.
- **Fixture row:** `grid-template-columns: 60px 1fr 116px 80px`, align-items center, padding `14px 22px 14px 40px`, separated by 1px rules at ~45% ink opacity.
  - Col 1: group label `GRP C` in `Archivo Black` 12px, **green**.
  - Col 2: the match — home team (flag 32×22 + `Archivo` 800 19px uppercase name), an italic `Spectral` "v", away team mirrored (`flex-direction: row-reverse`, right-aligned).
  - Col 3 (the pick): if predicted → an **ink LED box** (`#15271d` bg, lime `#c6f24e` Rajdhani 700 22px, padding `2px 13px`) showing `2–1`, with a tiny `YOUR CALL` label under; if not → a green **PREDICT ▸** button (`Archivo` 800 11.5px uppercase, white on green, padding `8px 10px`).
  - Col 4: time in `Rajdhani` 700 22px, date under in `Archivo` 8.5px tracked muted.
- **Standings aside:** `Archivo Black` 12px heading over a 2px ink rule; rows of name (`Archivo` 600) + value (`Rajdhani` 700 18px), the current user's row tinted green/bold; a closing `Spectral` italic pull-quote with a green-emphasised word.

**Layout — Broadcast lean (E2):**
- A **green broadcast header band** (linear-gradient `100deg, #06532a → #0a7d3c`) with **mown-grass vertical stripes** (see motifs) and a **4px ink bottom border**. Contains: a translucent "live" chip (`MATCHDAY 1`), an `Archivo Black` 33px uppercase title ("Fixtures & Predictions"), and right-aligned points (`Rajdhani` 28px "247 PTS" + muted caps sub).
- **Fixture cards** on cream (`#fbf8ef`), 1px ink-tint border + **5px left border in the group colour**, `grid-template-columns: 122px 1fr 146px`:
  - Left cell: time (`Rajdhani` 700 24px), date (caps muted), a group badge (`GRP C`, white on group colour).
  - Middle: teams either side of a **broadcast LED board** (`#15271d` bg, lime digits, `2 : 1`, min-width 74px) or an empty dashed `– : –` board if unpredicted.
  - Right: `Edit pick` (green outline) or `Predict` (solid green) button, `Archivo` 800 12px uppercase.
- Cards stacked with 11px gap, list padding `20px 36px`.

### 2. Score Picker (set a scoreline)
**File:** `Programme Picker.html` → components `PickerProgEditorial`, `PickerProgBroadcast`, `PickerProgDesktop` in `programme-picker.jsx`.
**Purpose:** The core interaction — set the predicted scoreline for one match, optionally "boost" it, then lock it in.

**Common anatomy (all three frames):**
1. **Match context header** — group, date/time, venue, teams.
2. **Scoreline area** — the hero. Two **steppers** (home / away) with a colon between, sitting on a **pitch-marking watermark** (see motifs). Each stepper = a `+` button, an **ink LED digit box** with goal-net texture, a `−` button.
3. **Boost toggle** — double-or-nothing on an exact score.
4. **Rival note** — a competitor's call (social/trash-talk carry-over from earlier work).
5. **Primary CTA** — "Lock in {h}–{a} · +{pts}".

**Mobile · Editorial (`PickerProgEditorial`, 390×844):**
- Green strip → masthead (`PREDICT THE SCORE` green kicker, `Archivo Black` 30px "Brazil v Morocco", `Spectral` italic venue under double rule).
- Score row padding `24px 18px 18px`, `position: relative; overflow: hidden` to clip the pitch watermark. Teams are 92px columns (flag 50×34, `Archivo Black` 14px name, `Home`/`Away` micro-label — home green, away muted). Stepper size **md**. Colon `Rajdhani` 32px muted.
- Boost = full-width row, **green outline** when off / **solid green** when on; 32px icon box (ink bg + lime bolt → inverts when on), title `Archivo` 800 + sub (`Spectral` italic when off, `Archivo` when on), and a 42×24 square toggle switch.
- Rival = `Spectral` italic line over a 1px top rule: `RIVAL · KIKO` (green `Archivo` 800 caps) + "Called it **1–2 Morocco** — …".
- A flex spacer pushes the **CTA** to the bottom: solid green, `Archivo` 800 14px uppercase, with a `Rajdhani` pill showing the score and `+10 pts`.

**Mobile · Broadcast (`PickerProgBroadcast`, 390×844):**
- Replaces the strip+masthead with a **green broadcast band** (gradient + mown-grass stripes + 4px ink border): a "live picks open" chip + `GRP C · 22:00` (`Rajdhani`), then `Archivo Black` 23px "Brazil vs Morocco", then a caps venue line.
- Stepper size **lg** (bigger LED boards). Colon `Rajdhani` 40px.
- Rival becomes a **card** (`#fbf8ef`, 4px green left border) instead of an italic line. Everything else matches the editorial lean.

**Desktop · Programme (`PickerProgDesktop`, 1180×720):**
- **Green broadcast header band** (gradient + grass stripes + 4px ink border): live chip, `Archivo Black` 30px "Brazil v Morocco", right-aligned `247 PTS` / `Kiko · Rank 3`.
- **Body** `grid-template-columns: 1.18fr 1fr`:
  - **Left** (padding `24px 36px`, 1px right rule): a `Rajdhani` context line (`GROUP C · SAT 13 JUN · 22:00 · METLIFE STADIUM`) under a double rule; a centred **hero** (flags 74×50, `Archivo Black` 18px names, stepper size **lg**, colon 46px) over a large pitch watermark; the **boost** row beneath.
  - **Right** (padding `24px 36px`): three labelled sections, each with a `::before` 3px green tick — **At stake** (`Rajdhani` 46px green `+10` + caption), **Your rival** (the card), **League consensus** (horizontal bars).
- **Footer** (`16px 40px`, top rule, bg `#efe9da`), right-aligned: **Cancel** (green outline) + **Lock in {h}–{a} +{pts}** (solid green with `Rajdhani` pill).
- Consensus bar: 66px label + track (`#e3ddcd`, 18px tall, square) + fill (green for the leader, `#b9c2ad` for others) + `Rajdhani` 14px percentage.

---

## Football motifs (the "more football" layer)
Apply these three; they're what make it read as football rather than generic editorial. All are pure CSS — no SVG illustration.

1. **Pitch markings** behind the scoreline (component `PitchLines`): an absolutely-positioned layer with
   - **center circle** — a bordered circle, 130px (mobile) / 184px (desktop "big"), `border: 1.6px solid currentColor`, centered with `translate(-50%,-50%)`;
   - **center spot** — a 7px filled circle, same center;
   - **halfway line** — a 1.6px vertical bar from 6% to 94% height, centered.
   Set the layer's `color` to `rgba(10,125,60,.18–.20)` (faint pitch green). The score content sits above it via `position: relative; z-index: 1`; the pitch layer is `z-index: 0`. The parent needs `position: relative; overflow: hidden`.
2. **Mown-grass stripes** in every green header band: `background-image: repeating-linear-gradient(90deg, rgba(255,255,255,.06) 0 56–60px, rgba(0,0,0,.05) 56–60px 112–120px)` as a non-interactive `::after` overlay. Keep band content above it with `z-index: 1`.
3. **Goal-net weave** inside the LED digit boxes: two crosshatched gradients over the ink fill —
   `repeating-linear-gradient(45deg, rgba(198,242,78,.10) 0 1px, transparent 1px 9px)` + the same at `-45deg`. The digit itself is wrapped and raised (`position: relative; z-index: 1`) so the net never hurts legibility.

---

## Interactions & Behavior
- **Steppers:** `+` / `−` adjust the digit, clamped **0–20**. Buttons: cream face, 1.5px green border, green glyph; **hover fills green with white glyph** (120ms). The LED box value updates instantly.
- **Boost toggle:** click anywhere on the row to flip. Off = transparent with green border + green text + ink/lime icon + grey switch (knob left). On = solid green fill, white text, lime/ink icon, translucent-white track (knob right). The CTA's `+pts` doubles when boosted (`exact × 2`).
- **Predict / Edit (fixtures):** a predicted row shows the LED score + "Edit"; an unpredicted row shows the green "Predict" CTA. Tapping routes to the Score Picker for that match.
- **CTA "Lock in":** persists the scoreline (your existing predictions API), then returns to the fixtures list with that row now showing the LED score.
- **Cancel (desktop):** discard and return to fixtures.
- **Hover (desktop):** stepper buttons fill; primary/secondary buttons may darken ~6–8% — match your existing button hover convention.
- **Transitions:** keep them small — 120–200ms on stepper/boost/button states. No large decorative animation.
- **Reduced motion:** there are no essential animations; honour `prefers-reduced-motion` by disabling the hover/colour transitions.

## State Management
Per picker instance:
- `home: number` (0–20), `away: number` (0–20) — the scoreline.
- `boost: boolean` — double-or-nothing flag.
- Derived `points = boost ? exactPoints * 2 : exactPoints` where `exactPoints = 5` (see scoring model).
On the fixtures list:
- A map of `matchId → prediction | null` to decide LED-box-vs-Predict-button per row.
Data needed: matchday fixtures (teams, group, kickoff datetime, venue), the user's existing predictions, the user's points/rank, a rival's prediction, and (desktop) league consensus percentages. These mirror the seed data in `wc-data.jsx`.

## Design Tokens

### Colour
| Token | Hex | Use |
|---|---|---|
| Paper (editorial) | `#f5f0e4` | page background, editorial lean |
| Paper (broadcast) | `#f3eee1` | page background, broadcast lean |
| Card paper | `#fbf8ef` | fixture cards, rival card |
| Footer paper | `#efe9da` | desktop footer bar |
| Ink | `#15271d` | primary text, LED box fill, 4px band border |
| Green (accent) | `#0a7d3c` | CTAs, links, accents, section ticks, pitch lines |
| Green dark | `#075e2d` / `#06532a` | header-band gradient end |
| Lime (editorial) | `#c6f24e` | LED digits, highlights (editorial) |
| Lime (broadcast) | `#cdfa57` | LED digits, highlights (broadcast) |
| Muted | `#6c7268` | secondary text, away labels |
| Consensus track | `#e3ddcd` | bar background |
| Consensus sub-fill | `#b9c2ad` | non-leader bars |
| Switch off track | `#d8d2c2` | boost toggle, off state |
| Group colours | see `GROUP_COLORS` in `wc-data.jsx` | group badges, broadcast card left-rule |

`GROUP_COLORS`: A `#16a34a`, B `#7c3aed`, C `#ea580c`, D `#0891b2`, E `#db2777`, F `#ca8a04`, G `#dc2626`, H `#059669`, I `#6366f1`, J `#c2410c`, K `#0f766e`, L `#9333ea`.

### Typography (Google Fonts)
| Family | Weights | Role |
|---|---|---|
| **Archivo Black** | 400 | display — team names, mastheads, big H1s (uppercase, tight tracking ≈ -.02em) |
| **Archivo** | 400–800 | UI — kickers, labels, buttons, micro-caps (800 for emphasis, letter-spacing .04–.16em on caps) |
| **Spectral** | 400 / 400 italic / 600 | editorial body — venue lines, deks, rival notes (italic) |
| **Rajdhani** | 600 / 700 | numerals — LED scores, times, points, consensus % |

### Type scale (key sizes)
- Masthead H1: 62px (fixtures), 30px (mobile picker), 23–33px (broadcast bands).
- Section/kicker caps: 11px `Archivo` 800, tracking .14em.
- Team name: 19px (fixtures list), 14–18px (picker, by frame).
- LED digit: 40px (md box) / 54px (lg box).
- Time / values: 18–26px `Rajdhani` 700.
- Body / dek: 13–16px `Spectral`.

### Spacing & shape
- **Border radius: 0 everywhere.** Square corners are core to the direction — do not round buttons, cards, inputs, boxes, or toggles.
- Page gutters: 40px (desktop fixtures/picker), 18–22px (mobile).
- Rules: 1px solid ink at 18–50% opacity for separators; 3px **double** ink rule under mastheads/context lines; 4px solid ink border under green header bands; 5px solid group-colour left border on broadcast cards.
- Stepper boxes: md 54×62, lg 70×84. Stepper buttons: md 30×24, lg 38×30.
- Toggle switch: 42×24 (mobile) / 48×27 (desktop), 3px padding, square knob.

### Scoring model
`exact = 5 pts`, `result = 2 pts`. Boost doubles the exact value (→ 10) and zeroes a miss. (See `SCORING` in `wc-data.jsx`.)

## Assets
- **Flags:** loaded from **flagcdn.com** via `flagUrl(code, width)` (e.g. `https://flagcdn.com/w160/br.png`). The 3-letter-squad-code → ISO-2 mapping is in `wc-data.jsx` (`FLAG`). Replace with your own flag asset pipeline if you have one; otherwise flagcdn is fine.
- **Icons:** the only icon is a **lightning bolt** for Boost, hand-rolled as a tiny inline SVG (`PK_BOLT` in `programme-picker.jsx`). Swap for your icon set's "bolt"/"zap". No other icon assets.
- **Fonts:** Archivo, Archivo Black, Spectral, Rajdhani — all Google Fonts. Self-host or import per your setup.
- No raster images, no illustrations — all football motifs are CSS.

## Files
Runnable prototypes (open in a browser) and their component sources:
- **`Programme Picker.html`** — the score picker, all three frames (mobile editorial, mobile broadcast, desktop). **Primary reference for this handoff.** Build the **`PickerProgBroadcast`** (mobile) and **`PickerProgDesktop`** frames; `PickerProgEditorial` is reference-only.
- `programme-picker.jsx` — picker components, `ProgStep`, `PitchLines`, `PK_BOLT`, and all picker CSS (source of truth for exact values).
- **`Programme Concepts.html`** — the fixtures screen in both leans (plus the two original anchors for context). Build the **`HybridBroadcast`** lean; `HybridEditorial` is reference-only.
- `hybrid-concepts.jsx` — `HybridEditorial` / `HybridBroadcast` fixtures components + CSS.
- `style-concepts.jsx` — the four original explorations (Broadsheet/Terrace/Broadcast/Album); reference only, for where the direction came from.
- `wc-data.jsx` — tokens, team names, flag helper, `GROUP_COLORS`, `SCORING`, sample fixtures.
- `wc-ui.jsx` — `PhoneStatusBar` / `HomeBar` (mockup chrome — **do not port**); `VStepper` is the old dark stepper (superseded by `ProgStep`).
- `design-canvas.jsx` — presentation wrapper only (**do not port**).

> To run a prototype: serve this folder over a static server and open the `.html` file (the Babel scripts need an http origin, not `file://`).
