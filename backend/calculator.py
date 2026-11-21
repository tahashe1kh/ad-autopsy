"""Ad Autopsy — Kill Switch calculator.

Pure functions, no DB / no FastAPI imports, so they are easy to test.

Formulas (all money in the test's own currency unless noted):
  CTR %           = clicks / impressions * 100
  CPC             = spend / clicks
  Click -> LP %   = lp_views / clicks * 100
  LP -> ATC %     = atc / lp_views * 100
  ATC -> Buy %    = purchases / atc * 100
  CPA             = spend / purchases            (null when 0 purchases)
  Break-even CPA  = price - cogs - fees,  fees = price * fees_pct / 100
  Revenue         = purchases * price
  Profit / loss   = revenue - spend - purchases * (cogs + fees)
  ROAS            = revenue / spend
  Stop-loss used  = spend / stop_loss * 100

Verdict rules (in order):
  1. Spend < $50 and 0 purchases -> NEED_MORE_DATA (sample too small to judge)
  2. CTR < 1.5% -> KILL (ad problem: the creative is not stopping the scroll)
  3. 3+ purchases and CPA < break-even CPA -> SCALE (profitable at volume)
  4. CTR >= 1.5% but LP -> ATC < 2% -> FIX_LANDER (ads work, page does not)
  5. CPA > break-even CPA -> KILL (losing money per order)
  6. Purchases > 0 but < 3 and CPA <= break-even -> NEED_MORE_DATA
  7. Otherwise -> NEED_MORE_DATA
"""

from __future__ import annotations


def _pct(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return round(numerator / denominator * 100, 2)


def _money(value: float) -> float:
    return round(value, 2)


def calculate(
    spend: float,
    impressions: float,
    clicks: float,
    lp_views: float,
    atc: float,
    purchases: float,
    price: float,
    cogs: float,
    fees_pct: float = 0.0,
    stop_loss: float = 300.0,
) -> dict:
    spend = float(spend or 0)
    impressions = float(impressions or 0)
    clicks = float(clicks or 0)
    lp_views = float(lp_views or 0)
    atc = float(atc or 0)
    purchases = float(purchases or 0)
    price = float(price or 0)
    cogs = float(cogs or 0)
    fees_pct = float(fees_pct or 0)
    stop_loss = float(stop_loss or 0)

    ctr = _pct(clicks, impressions)
    cpc = _money(spend / clicks) if clicks else None
    click_to_lp = _pct(lp_views, clicks)
    lp_to_atc = _pct(atc, lp_views)
    atc_to_purchase = _pct(purchases, atc)
    cpa = _money(spend / purchases) if purchases else None

    fees_per_order = _money(price * fees_pct / 100)
    break_even_cpa = _money(price - cogs - fees_per_order)
    revenue = _money(purchases * price)
    profit = _money(revenue - spend - purchases * (cogs + fees_per_order))
    roas = _money(revenue / spend) if spend else 0.0
    stop_loss_pct = _money(spend / stop_loss * 100) if stop_loss else 0.0

    reasoning: list[str] = []

    if purchases == 0 and spend < 50:
        verdict = "NEED_MORE_DATA"
        reasoning.append(
            f"Only ${spend:.2f} spent with 0 purchases — below the $50 minimum "
            "sample. Do not kill yet; keep spending to at least $50 per ad before judging."
        )
    elif ctr < 1.5:
        verdict = "KILL"
        reasoning.append(
            f"CTR is {ctr}% (target 1.5–2%+). The ad itself is the problem — "
            "people are not clicking, so fixing the landing page will not help. "
            "Kill this creative and test a new hook."
        )
    elif purchases >= 3 and cpa is not None and cpa < break_even_cpa:
        verdict = "SCALE"
        reasoning.append(
            f"CPA is ${cpa:.2f} vs break-even CPA ${break_even_cpa:.2f} across "
            f"{int(purchases)} purchases. Profitable and proven — scale budget, "
            "do not change the creative or page yet."
        )
    elif ctr >= 1.5 and lp_to_atc < 2:
        verdict = "FIX_LANDER"
        reasoning.append(
            f"CTR is {ctr}% (above the 1.5–2% target) so the ads work, but "
            f"landing-page-to-add-to-cart is only {lp_to_atc}% (target 2%+). "
            "The break is the landing page, not the ad. Fix the page before "
            "spending more or killing the product."
        )
    elif cpa is not None and cpa > break_even_cpa:
        verdict = "KILL"
        reasoning.append(
            f"CPA is ${cpa:.2f} vs break-even CPA ${break_even_cpa:.2f}. "
            "Every order loses money at this CPA. Kill unless a landing-page "
            "fix can plausibly cut CPA below break-even."
        )
    elif purchases > 0 and cpa is not None and cpa <= break_even_cpa:
        verdict = "NEED_MORE_DATA"
        reasoning.append(
            f"CPA is ${cpa:.2f} vs break-even ${break_even_cpa:.2f} — profitable "
            f"so far, but only {int(purchases)} purchase(s). Get to 3+ purchases "
            "before scaling."
        )
    else:
        verdict = "NEED_MORE_DATA"
        reasoning.append(
            "Funnel is not broken yet, but there is not enough data to call it. "
            "Keep spending until at least $50 and 3 purchases, or the stop loss."
        )

    if stop_loss and spend >= stop_loss:
        reasoning.append(
            f"Stop loss hit: ${spend:.2f} spent vs ${stop_loss:.2f} stop loss. "
            "Stop spending on this test regardless of the funnel."
        )
    elif stop_loss_pct >= 75:
        reasoning.append(
            f"You have used {stop_loss_pct}% of the ${stop_loss:.2f} stop loss. "
            "Decide now: fix and retest, or kill before it is gone."
        )

    return {
        "ctr_pct": ctr,
        "cpc": cpc,
        "click_to_lp_pct": click_to_lp,
        "lp_to_atc_pct": lp_to_atc,
        "atc_to_purchase_pct": atc_to_purchase,
        "cpa": cpa,
        "break_even_cpa": break_even_cpa,
        "fees_per_order": fees_per_order,
        "revenue": revenue,
        "profit": profit,
        "roas": roas,
        "stop_loss_pct": stop_loss_pct,
        "verdict": verdict,
        "reasoning": reasoning,
        "formulas": {
            "ctr": "clicks / impressions * 100",
            "cpc": "spend / clicks",
            "click_to_lp": "lp_views / clicks * 100",
            "lp_to_atc": "atc / lp_views * 100",
            "atc_to_purchase": "purchases / atc * 100",
            "cpa": "spend / purchases (null when 0 purchases)",
            "break_even_cpa": "price - cogs - (price * fees_pct / 100)",
            "revenue": "purchases * price",
            "profit": "revenue - spend - purchases * (cogs + fees_per_order)",
            "roas": "revenue / spend",
            "stop_loss_pct": "spend / stop_loss * 100",
        },
    }
