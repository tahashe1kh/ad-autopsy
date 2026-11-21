"""Ad Autopsy — FastAPI backend.

Kill Switch (test decision engine) + Ad Spy (manual Meta Ad Library tracker).

IMPORTANT — Ad Library limitation: Meta Ad Library has no official API.
There is no live Ad Library feed in this app. Competitor ads are entered
manually after checking https://www.facebook.com/ads/library/ in the
browser, and the seed ads are SAMPLE data, not verified results.
"""

from __future__ import annotations

import csv
import io
from collections import Counter
from datetime import date, datetime
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from calculator import calculate
from database import CompetitorAd, SessionLocal, Test, init_db
from seed import seed as seed_data

app = FastAPI(title="Ad Autopsy", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

FORMATS = [
    "first-person story", "confessional", "listicle", "testimonial",
    "doctor-led", "discount-led", "explanatory",
]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def startup():
    init_db()
    seed_data()


# ---------- schemas ----------
class CalculateInput(BaseModel):
    spend: float = 0.0
    impressions: float = 0.0
    clicks: float = 0.0
    lp_views: float = 0.0
    atc: float = 0.0
    purchases: float = 0.0
    price: float = 0.0
    cogs: float = 0.0
    fees_pct: float = 0.0
    stop_loss: float = 300.0
    currency: str = "CAD"


class TestCreate(CalculateInput):
    name: str = "Untitled test"
    notes: str = ""


class TestOut(CalculateInput):
    id: int
    name: str
    notes: str
    created_at: Optional[datetime] = None
    calculation: dict

    class Config:
        from_attributes = True


class AdCreate(BaseModel):
    brand: str
    ad_id: str = ""
    start_date: Optional[date] = None
    format: str = ""
    country: str = "CA"
    active: bool = True
    destination_url: str = ""
    source: str = "brand_search"
    problem_word: str = ""
    notes: str = ""


class AdOut(AdCreate):
    id: int
    days_running: Optional[int] = None
    is_long_running: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


def test_to_out(t: Test) -> dict:
    calc = calculate(t.spend, t.impressions, t.clicks, t.lp_views, t.atc,
                     t.purchases, t.price, t.cogs, t.fees_pct, t.stop_loss)
    return {
        "id": t.id, "name": t.name, "spend": t.spend, "impressions": t.impressions,
        "clicks": t.clicks, "lp_views": t.lp_views, "atc": t.atc,
        "purchases": t.purchases, "price": t.price, "cogs": t.cogs,
        "fees_pct": t.fees_pct, "stop_loss": t.stop_loss, "currency": t.currency,
        "notes": t.notes or "", "created_at": t.created_at, "calculation": calc,
    }


def ad_to_out(a: CompetitorAd, threshold: int = 90) -> dict:
    days = a.days_running
    return {
        "id": a.id, "brand": a.brand, "ad_id": a.ad_id or "",
        "start_date": a.start_date.isoformat() if a.start_date else None,
        "format": a.format or "", "country": a.country, "active": a.active,
        "destination_url": a.destination_url or "", "source": a.source,
        "problem_word": a.problem_word or "", "notes": a.notes or "",
        "created_at": a.created_at, "days_running": days,
        "is_long_running": bool(days is not None and days >= threshold),
    }


# ---------- health / calculate ----------
@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    return {
        "status": "ok",
        "tests": db.query(Test).count(),
        "ads": db.query(CompetitorAd).count(),
        "formats": FORMATS,
    }


@app.post("/api/calculate")
def calculate_endpoint(payload: CalculateInput):
    result = calculate(payload.spend, payload.impressions, payload.clicks,
                       payload.lp_views, payload.atc, payload.purchases,
                       payload.price, payload.cogs, payload.fees_pct,
                       payload.stop_loss)
    result["currency"] = payload.currency
    return result


# ---------- tests ----------
@app.post("/api/tests", response_model=TestOut)
def create_test(payload: TestCreate, db: Session = Depends(get_db)):
    t = Test(**payload.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return test_to_out(t)


@app.get("/api/tests")
def list_tests(db: Session = Depends(get_db)):
    return [test_to_out(t) for t in db.query(Test).order_by(Test.id.desc()).all()]


@app.get("/api/tests/{test_id}", response_model=TestOut)
def get_test(test_id: int, db: Session = Depends(get_db)):
    t = db.query(Test).filter(Test.id == test_id).first()
    if not t:
        raise HTTPException(404, "Test not found")
    return test_to_out(t)


@app.delete("/api/tests/{test_id}")
def delete_test(test_id: int, db: Session = Depends(get_db)):
    t = db.query(Test).filter(Test.id == test_id).first()
    if not t:
        raise HTTPException(404, "Test not found")
    db.delete(t)
    db.commit()
    return {"deleted": test_id}


# ---------- CSV import ----------
# Accepts EITHER a multipart file upload OR a JSON body {"csv_text": "..."}.
# Columns (case-insensitive, missing ones default to 0 with a warning):
#   spend, impressions, clicks, lp_views, atc, purchases, ad_name
# Also understands common Meta export headers: amount spent, link clicks,
# landing page views, adds to cart / add-to-cart, results.
COLUMN_ALIASES = {
    "spend": ["spend", "amount spent", "amount_spent", "amount spent (cad)", "cost"],
    "impressions": ["impressions", "impr"],
    "clicks": ["clicks", "link clicks", "link_clicks"],
    "lp_views": ["lp_views", "landing page views", "landing_page_views", "lpv"],
    "atc": ["atc", "adds to cart", "add to cart", "add-to-cart", "addtocart", "adds_to_cart"],
    "purchases": ["purchases", "results", "purchase", "orders"],
    "ad_name": ["ad_name", "ad name", "ad", "campaign name", "name"],
    "price": ["price", "aov"],
    "cogs": ["cogs", "product cost"],
}


def _pick(row: dict, key: str):
    lowered = {str(k).strip().lower(): v for k, v in row.items()}
    for alias in COLUMN_ALIASES[key]:
        if alias in lowered and lowered[alias] not in (None, ""):
            return lowered[alias]
    return None


def _num(value, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def import_rows(rows: list[dict], db: Session, defaults: dict) -> tuple[list[dict], list[str]]:
    created, warnings = [], []
    seen_cols = {str(k).strip().lower() for r in rows for k in r.keys()}
    for key, aliases in COLUMN_ALIASES.items():
        if key in ("ad_name", "price", "cogs"):
            continue
        if not any(a in seen_cols for a in aliases):
            warnings.append(f"Missing column for '{key}' — defaulted to 0.")
    for i, row in enumerate(rows):
        if not any(str(v).strip() for v in row.values() if v is not None):
            continue
        name = _pick(row, "ad_name") or f"Imported test {i + 1}"
        t = Test(
            name=str(name),
            spend=_num(_pick(row, "spend")),
            impressions=_num(_pick(row, "impressions")),
            clicks=_num(_pick(row, "clicks")),
            lp_views=_num(_pick(row, "lp_views")),
            atc=_num(_pick(row, "atc")),
            purchases=_num(_pick(row, "purchases")),
            price=_num(_pick(row, "price"), defaults.get("price", 44.95)),
            cogs=_num(_pick(row, "cogs"), defaults.get("cogs", 11.0)),
            fees_pct=defaults.get("fees_pct", 0.0),
            stop_loss=defaults.get("stop_loss", 300.0),
            currency=defaults.get("currency", "CAD"),
            notes="Imported from CSV.",
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        created.append(test_to_out(t))
    return created, warnings


@app.post("/api/tests/import-csv")
async def import_csv(request: Request, db: Session = Depends(get_db)):
    content_type = request.headers.get("content-type", "")
    text = ""
    defaults: dict = {}
    if "multipart/form-data" in content_type:
        form = await request.form()
        file = form.get("file")
        if file is None:
            raise HTTPException(400, "No file uploaded (field name: 'file').")
        raw = await file.read()
        text = raw.decode("utf-8-sig", errors="replace")
        for k in ("price", "cogs", "fees_pct", "stop_loss"):
            if form.get(k):
                defaults[k] = _num(form.get(k))
        if form.get("currency"):
            defaults["currency"] = str(form.get("currency"))
    else:
        body = await request.json()
        text = body.get("csv_text", "")
        defaults = {k: body[k] for k in ("price", "cogs", "fees_pct", "stop_loss", "currency") if k in body}
    if not text.strip():
        raise HTTPException(400, "Empty CSV.")
    try:
        rows = list(csv.DictReader(io.StringIO(text)))
    except Exception as exc:
        raise HTTPException(400, f"Could not parse CSV: {exc}")
    if not rows:
        raise HTTPException(400, "CSV has headers but no data rows.")
    created, warnings = import_rows(rows, db, defaults)
    return {"created": len(created), "warnings": warnings, "tests": created}


# ---------- competitor ads ----------
@app.post("/api/ads", response_model=AdOut)
def create_ad(payload: AdCreate, db: Session = Depends(get_db)):
    if payload.format and payload.format not in FORMATS:
        raise HTTPException(400, f"Unknown format. Use one of: {', '.join(FORMATS)}")
    if payload.country not in ("CA", "US"):
        raise HTTPException(400, "Country must be CA or US.")
    if payload.source not in ("brand_search", "problem_word_search"):
        raise HTTPException(400, "Source must be brand_search or problem_word_search.")
    a = CompetitorAd(**payload.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return ad_to_out(a)


@app.get("/api/ads")
def list_ads(brand: Optional[str] = None, country: Optional[str] = None,
             format: Optional[str] = None, source: Optional[str] = None,
             q: Optional[str] = None, active: Optional[bool] = None,
             longevity_threshold: int = 90, db: Session = Depends(get_db)):
    query = db.query(CompetitorAd)
    if brand:
        query = query.filter(CompetitorAd.brand.ilike(f"%{brand}%"))
    if country:
        query = query.filter(CompetitorAd.country == country.upper())
    if format:
        query = query.filter(CompetitorAd.format == format)
    if source:
        query = query.filter(CompetitorAd.source == source)
    if active is not None:
        query = query.filter(CompetitorAd.active == active)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (CompetitorAd.brand.ilike(like)) | (CompetitorAd.problem_word.ilike(like))
            | (CompetitorAd.format.ilike(like)) | (CompetitorAd.ad_id.ilike(like))
        )
    ads = query.order_by(CompetitorAd.start_date.asc().nullslast()).all()
    return [ad_to_out(a, longevity_threshold) for a in ads]


@app.get("/api/ads/{ad_id}", response_model=AdOut)
def get_ad(ad_id: int, longevity_threshold: int = 90, db: Session = Depends(get_db)):
    a = db.query(CompetitorAd).filter(CompetitorAd.id == ad_id).first()
    if not a:
        raise HTTPException(404, "Ad not found")
    return ad_to_out(a, longevity_threshold)


@app.delete("/api/ads/{ad_id}")
def delete_ad(ad_id: int, db: Session = Depends(get_db)):
    a = db.query(CompetitorAd).filter(CompetitorAd.id == ad_id).first()
    if not a:
        raise HTTPException(404, "Ad not found")
    db.delete(a)
    db.commit()
    return {"deleted": ad_id}


@app.get("/api/competitors/summary")
def competitors_summary(longevity_threshold: int = 90, db: Session = Depends(get_db)):
    ads = db.query(CompetitorAd).all()
    summary: dict[str, dict] = {}
    for a in ads:
        days = a.days_running
        entry = summary.setdefault(a.brand, {
            "brand": a.brand, "total_ads": 0, "active_ads": 0,
            "long_running_count": 0, "oldest_start_date": None,
            "formats": Counter(), "countries": Counter(),
        })
        entry["total_ads"] += 1
        if a.active:
            entry["active_ads"] += 1
        if days is not None and days >= longevity_threshold:
            entry["long_running_count"] += 1
        if a.start_date and (entry["oldest_start_date"] is None
                             or a.start_date.isoformat() < entry["oldest_start_date"]):
            entry["oldest_start_date"] = a.start_date.isoformat()
        if a.format:
            entry["formats"][a.format] += 1
        entry["countries"][a.country] += 1
    out = []
    for entry in summary.values():
        entry["formats"] = dict(entry["formats"])
        entry["countries"] = dict(entry["countries"])
        out.append(entry)
    return sorted(out, key=lambda e: (-e["long_running_count"], -e["total_ads"]))
