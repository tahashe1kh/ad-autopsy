"""Tests for the Kill Switch calculator.

Neluna Test 1 (real numbers, Nov 14-15, 2026):
  spend $123.66 CAD, 4,114 impressions, 139 clicks, 121 LP views,
  1 add-to-cart, 0 purchases, price $44.95, COGS $11.
  Expected: CTR ~3.38%, LP-to-ATC ~0.8%, verdict FIX_LANDER.
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from calculator import calculate


def test_neluna_test1():
    r = calculate(spend=123.66, impressions=4114, clicks=139, lp_views=121,
                  atc=1, purchases=0, price=44.95, cogs=11.0, stop_loss=300.0)
    assert r["ctr_pct"] == 3.38, r["ctr_pct"]
    assert r["lp_to_atc_pct"] == 0.83, r["lp_to_atc_pct"]
    assert r["cpa"] is None
    assert r["break_even_cpa"] == 33.95
    assert r["profit"] == -123.66
    assert r["verdict"] == "FIX_LANDER", r
    assert any("landing page" in x.lower() for x in r["reasoning"])


def test_scale_case():
    # Profitable at volume: CPA $25 < break-even $33.95, 4 purchases.
    r = calculate(spend=100, impressions=10000, clicks=300, lp_views=260,
                  atc=13, purchases=4, price=44.95, cogs=11.0, stop_loss=300.0)
    assert r["ctr_pct"] == 3.0
    assert r["cpa"] == 25.0
    assert r["verdict"] == "SCALE", r


def test_kill_bad_ctr():
    # CTR 1.0% — the ad itself is the problem.
    r = calculate(spend=150, impressions=10000, clicks=100, lp_views=80,
                  atc=1, purchases=0, price=44.95, cogs=11.0, stop_loss=300.0)
    assert r["ctr_pct"] == 1.0
    assert r["verdict"] == "KILL", r


def test_kill_cpa_above_break_even():
    # Good CTR and lander, but CPA $60 > break-even $33.95.
    r = calculate(spend=120, impressions=10000, clicks=300, lp_views=260,
                  atc=20, purchases=2, price=44.95, cogs=11.0, stop_loss=300.0)
    assert r["cpa"] == 60.0
    assert r["verdict"] == "KILL", r


def test_need_more_data_tiny_spend():
    r = calculate(spend=20, impressions=1000, clicks=30, lp_views=25,
                  atc=1, purchases=0, price=44.95, cogs=11.0, stop_loss=300.0)
    assert r["verdict"] == "NEED_MORE_DATA", r


def test_break_even_with_fees():
    r = calculate(spend=0, impressions=0, clicks=0, lp_views=0, atc=0,
                  purchases=0, price=100, cogs=20, fees_pct=10)
    # fees $10, so BE CPA = 100 - 20 - 10 = 70
    assert r["break_even_cpa"] == 70.0
    assert r["cpc"] is None  # no clicks -> no CPC, no crash
