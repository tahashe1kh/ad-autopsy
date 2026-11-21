# Ad Autopsy — Kill Switch + Ad Spy for DTC brands

Built for **Neluna** (Taha Sheikh's neck-stretcher brand). One tool, two jobs:

1. **Kill Switch** — paste in a Meta ad test's numbers and get a verdict with the math shown: **KILL / FIX_LANDER / SCALE / NEED_MORE_DATA**. It diagnoses *where* the funnel breaks instead of just saying a test failed.
2. **Ad Spy** — a manual tracker for competitor ads found in the Meta Ad Library: brand, format, start date, country, source (brand search vs problem-word search), and a 90+ day "Winner" longevity badge, plus per-brand summaries.

**Stack:** React + TypeScript (Vite) · Python FastAPI · SQLite via SQLAlchemy (file-based — no Docker or Postgres needed to run).

## Demo data — read this first

- **Neluna Test 1 is real.** Nov 14–15, 2026: spend $123.66 CAD, 4,114 impressions, 139 link clicks, 121 landing-page views, 1 add-to-cart, 0 purchases. Price $44.95, COGS $11 CAD, stop loss $300 USD. Verdict: **FIX_LANDER** — CTR 3.38% (ads fine), landing-page-to-add-to-cart 0.83% (page broken). It is seeded as the first saved test.
- **Competitor ads are SAMPLE data, not verified results.** The 9 seeded rows across Cevera, CerviTrax, Neck Cloud and FurTherapy exist so the Ad Spy UI has something to show and filter. Their dates, formats and counts are invented for demo purposes. **Do not present them as live-verified Ad Library counts or run dates.**

## Ad Library limitation

Meta Ad Library has **no official API**, so this app has no live Ad Library feed. The workflow is manual by design:

1. Open https://www.facebook.com/ads/library/ in your browser.
2. Search a brand name (e.g. Cevera) or a problem word (e.g. "neck pain", "tech neck", "neck hump", "stiff neck"), separately for CA and US.
3. Log the ads you find in the Ad Spy tab — start date, format, active status, destination.

Longevity is the signal: an ad still running after 90+ days is probably working. A discount-led ad on its own does not pass the native-story gate.

## Quick start

### Backend (FastAPI, port 8000)

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --port 8000
```

API docs: http://localhost:8000/docs — first run seeds the Neluna Test 1 demo test and the 9 sample ads into `backend/ad_autopsy.db` (created automatically; gitignored).

### Frontend (React + Vite, port 5173)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The frontend calls the backend at `http://localhost:8000` (override with `VITE_API_URL`).

### Production build

```bash
cd frontend
npm run build        # outputs to frontend/dist/
npm run preview      # serves the build on http://localhost:4173
```

### Tests

```bash
cd backend
.venv/bin/python -m pytest test_calculate.py -v
```

## How to use it with real Neluna data

1. **Kill Switch tab** — the form is prefilled with Test 1. Change the numbers for a new test (or load a saved test), and the verdict updates live as you type.
2. **Save** a test to keep a history of verdicts across tests.
3. **Import CSV** — export a report from Meta Ads Manager and paste it (or upload the file). Expected columns: `spend, impressions, clicks, lp_views, atc, purchases, ad_name`. Missing columns default to 0 and are reported as warnings. Price / COGS are taken from the form above the import box.
4. **Ad Spy tab** — log competitor ads you find in the Ad Library, filter by brand / country / format / source, and watch the per-brand summary cards for long-running winners.

## Formulas (shown in every `/api/calculate` response)

| Metric | Formula |
|---|---|
| CTR % | clicks / impressions × 100 |
| CPC | spend / clicks |
| Click → LP % | lp_views / clicks × 100 |
| LP → ATC % | atc / lp_views × 100 |
| ATC → purchase % | purchases / atc × 100 |
| CPA | spend / purchases (null when 0 purchases) |
| Break-even CPA | price − COGS − (price × fees_pct / 100) |
| Revenue | purchases × price |
| Profit / loss | revenue − spend − purchases × (COGS + fees per order) |
| ROAS | revenue / spend |
| Stop-loss used % | spend / stop_loss × 100 |

For Neluna at $44.95 with $11 COGS and no fees: break-even CPA = **$33.95**.

## Verdict rules (in order)

1. **NEED_MORE_DATA** — spend < $50 and 0 purchases. Sample too small to judge.
2. **KILL** — CTR < 1.5%. The ad is the problem; people are not clicking.
3. **SCALE** — 3+ purchases and CPA < break-even CPA. Profitable and proven.
4. **FIX_LANDER** — CTR ≥ 1.5% but LP → ATC < 2%. Ads work, page does not.
5. **KILL** — CPA > break-even CPA. Every order loses money.
6. **NEED_MORE_DATA** — profitable so far but fewer than 3 purchases, or funnel healthy but not enough data.

If spend reaches the stop loss ($300 USD in Taha's words — the app does not convert currencies, it reports spend vs stop loss as entered), the reasoning flags it regardless of verdict.

## API overview

| Endpoint | Description |
|---|---|
| `GET /api/health` | Status + counts |
| `POST /api/calculate` | Verdict + all metrics for one set of inputs |
| `POST /api/tests` · `GET /api/tests` · `GET /api/tests/{id}` · `DELETE /api/tests/{id}` | Saved tests (each response includes its calculation) |
| `POST /api/tests/import-csv` | Multipart file upload or JSON `{"csv_text": "..."}` |
| `POST /api/ads` · `GET /api/ads` · `GET /api/ads/{id}` · `DELETE /api/ads/{id}` | Competitor ads; list filters: `brand, country, format, source, q, active, longevity_threshold` (default 90) |
| `GET /api/competitors/summary` | Per-brand totals, long-running count, oldest ad, format + country breakdown |

## Project layout

```
ad-autopsy/
├── README.md
├── backend/
│   ├── main.py           # FastAPI app: calculate, tests, ads, CSV import, summary
│   ├── calculator.py     # Pure verdict/math logic (unit-tested)
│   ├── database.py       # SQLAlchemy models (SQLite file)
│   ├── seed.py           # Neluna Test 1 + 9 SAMPLE competitor ads
│   ├── test_calculate.py # pytest: Test 1, SCALE, KILL x2, NEED_MORE_DATA, fees
│   └── requirements.txt
└── frontend/
    └── src/
        ├── App.tsx       # Kill Switch + Ad Spy tabs
        ├── api.ts        # Typed API client
        ├── types.ts      # Shared types + Neluna Test 1 defaults
        └── App.css
```
