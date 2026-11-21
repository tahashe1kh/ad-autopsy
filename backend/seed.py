"""Seed demo data.

DEMO DATA — clearly labelled, do NOT treat as verified.
- The Neluna Test 1 row is Taha's REAL test (Nov 14-15, 2026): $123.66 CAD,
  4,114 impressions, 139 link clicks, 121 landing-page views, 1 add-to-cart,
  0 purchases. Price $44.95, COGS $11 CAD, stop loss $300 USD.
- The competitor ads below are SAMPLE / PLACEHOLDER rows so the Ad Spy UI
  has something to show and filter. They are NOT live-verified Meta Ad
  Library results. Dates, formats and counts are invented for demo purposes.
  Meta Ad Library has no official API — real ads must be entered manually
  after checking https://www.facebook.com/ads/library/ in the browser.
  Never present these sample rows as verified ad counts or run dates.
"""

from __future__ import annotations

from datetime import date

from database import CompetitorAd, SessionLocal, Test, init_db

SAMPLE_ADS = [
    # brand, ad_id, start_date, format, country, active, destination, source, problem_word
    ("Cevera", "SAMPLE-CEV-001", date(2026, 6, 15), "first-person story", "US", True,
     "https://example.com/cevera-neck", "brand_search", ""),
    ("Cevera", "SAMPLE-CEV-002", date(2026, 8, 2), "listicle", "US", True,
     "https://example.com/cevera-7-reasons", "brand_search", ""),
    ("Cevera", "SAMPLE-CEV-003", date(2026, 9, 20), "testimonial", "CA", True,
     "https://example.com/cevera-ca", "problem_word_search", "neck pain"),
    ("CerviTrax", "SAMPLE-CER-001", date(2026, 7, 10), "doctor-led", "US", True,
     "https://example.com/cervitrax", "brand_search", ""),
    ("CerviTrax", "SAMPLE-CER-002", date(2026, 10, 5), "explanatory", "CA", False,
     "https://example.com/cervitrax-ca", "problem_word_search", "tech neck"),
    ("Neck Cloud", "SAMPLE-NEC-001", date(2026, 10, 28), "discount-led", "US", True,
     "https://example.com/neck-cloud", "brand_search", ""),
    ("Neck Cloud", "SAMPLE-NEC-002", date(2026, 11, 2), "confessional", "CA", True,
     "https://example.com/neck-cloud-ca", "problem_word_search", "stiff neck"),
    ("FurTherapy", "SAMPLE-FUR-001", date(2026, 5, 1), "first-person story", "US", True,
     "https://example.com/furtherapy", "brand_search", ""),
    ("FurTherapy", "SAMPLE-FUR-002", date(2026, 11, 10), "listicle", "US", False,
     "https://example.com/furtherapy-listicle", "problem_word_search", "neck hump"),
]


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.query(Test).count() == 0:
            db.add(Test(
                name="Neluna Test 1 — DEMO (real numbers, Nov 14-15)",
                spend=123.66, impressions=4114, clicks=139, lp_views=121,
                atc=1, purchases=0, price=44.95, cogs=11.0, fees_pct=0.0,
                stop_loss=300.0, currency="CAD",
                notes="DEMO: Taha's real Test 1. CTR 3.38% (ads fine), LP-to-ATC 0.8% (lander break). Verdict: FIX_LANDER.",
            ))
        if db.query(CompetitorAd).count() == 0:
            for brand, ad_id, start, fmt, country, active, url, source, word in SAMPLE_ADS:
                db.add(CompetitorAd(
                    brand=brand, ad_id=ad_id, start_date=start, format=fmt,
                    country=country, active=active, destination_url=url,
                    source=source, problem_word=word,
                    notes="SAMPLE — not a live-verified Ad Library result.",
                ))
        db.commit()
        print(f"Seeded: {db.query(Test).count()} test(s), {db.query(CompetitorAd).count()} ad(s).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
