"""Odds API scanner and arbitrage calculations.

This app intentionally does not hard-code bookmakers. If you leave the bookmaker
filter empty, The Odds API returns all bookmakers available for the selected
region/account/sport/market.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import requests

BASE_URL = "https://api.the-odds-api.com/v4"
DEFAULT_REGIONS = "uk"
ODDS_FORMAT = "decimal"
DATE_FORMAT = "iso"

# Core odds markets. Extra markets can be typed in the Streamlit app.
CORE_MARKETS = ["h2h", "spreads", "totals"]
POPULAR_EXTRA_MARKETS = [
    "btts",
    "draw_no_bet",
    "h2h_3_way",
    "alternate_spreads",
    "alternate_totals",
    "team_totals",
]


@dataclass
class BestOutcome:
    name: str
    price: float
    bookmaker: str
    market_key: str
    point: Optional[float] = None


@dataclass
class ArbitrageOpportunity:
    sport_key: str
    sport_title: str
    event: str
    commence_time: str
    market_key: str
    implied_probability: float
    profit_percent: float
    outcomes: List[BestOutcome]

    def stake_plan(self, total_stake: float) -> List[Dict[str, Any]]:
        if not self.outcomes:
            return []
        inv_sum = sum(1 / o.price for o in self.outcomes if o.price > 0)
        if inv_sum <= 0:
            return []
        guaranteed_return = total_stake / inv_sum
        return [
            {
                "Outcome": format_outcome_name(o),
                "Bookmaker": o.bookmaker,
                "Odds": o.price,
                "Stake": round(guaranteed_return / o.price, 2),
                "Return": round(guaranteed_return, 2),
            }
            for o in self.outcomes
        ]


def get_api_key() -> str:
    # Streamlit secrets are read in app.py and copied to env if available.
    return os.getenv("ODDS_API_KEY", "").strip()


def odds_api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    api_key = get_api_key()
    if not api_key:
        raise ValueError("Missing ODDS_API_KEY. Add it in Streamlit Secrets.")

    params = dict(params or {})
    params["apiKey"] = api_key
    url = f"{BASE_URL}{path}"
    response = requests.get(url, params=params, timeout=30)

    if response.status_code == 401:
        raise ValueError("Odds API rejected your key. Check ODDS_API_KEY in Streamlit Secrets.")
    if response.status_code == 422:
        raise ValueError(f"Odds API rejected the request. Try fewer markets or another sport. Details: {response.text[:300]}")
    if response.status_code == 429:
        raise ValueError("Odds API rate limit or quota reached. Try again later or reduce scans.")
    response.raise_for_status()
    return response.json()


def fetch_sports(include_inactive: bool = False) -> List[Dict[str, Any]]:
    data = odds_api_get("/sports", {"all": "true" if include_inactive else "false"})
    return sorted(data, key=lambda x: (x.get("group", ""), x.get("title", "")))


def fetch_odds(
    sport_key: str,
    regions: str = DEFAULT_REGIONS,
    markets: Sequence[str] = CORE_MARKETS,
    bookmakers: Optional[Sequence[str]] = None,
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "regions": regions,
        "markets": ",".join([m.strip() for m in markets if m.strip()]),
        "oddsFormat": ODDS_FORMAT,
        "dateFormat": DATE_FORMAT,
    }
    if bookmakers:
        cleaned = [b.strip() for b in bookmakers if b.strip()]
        if cleaned:
            params["bookmakers"] = ",".join(cleaned)
    return odds_api_get(f"/sports/{sport_key}/odds", params)


def format_event(event: Dict[str, Any]) -> str:
    home = event.get("home_team", "Home")
    away = event.get("away_team", "Away")
    return f"{home} v {away}"


def format_outcome_name(outcome: BestOutcome) -> str:
    if outcome.point is None:
        return outcome.name
    return f"{outcome.name} ({outcome.point})"


def outcome_key(outcome: Dict[str, Any]) -> Tuple[str, Optional[float]]:
    return (str(outcome.get("name", "")).strip(), outcome.get("point"))


def find_arbs_in_event(event: Dict[str, Any], sport_title: str = "") -> List[ArbitrageOpportunity]:
    opportunities: List[ArbitrageOpportunity] = []
    market_best: Dict[str, Dict[Tuple[str, Optional[float]], BestOutcome]] = {}

    for bookmaker in event.get("bookmakers", []):
        book_title = bookmaker.get("title") or bookmaker.get("key") or "Unknown"
        for market in bookmaker.get("markets", []):
            market_key = market.get("key", "unknown")
            best_for_market = market_best.setdefault(market_key, {})
            for raw_outcome in market.get("outcomes", []):
                try:
                    price = float(raw_outcome.get("price"))
                except (TypeError, ValueError):
                    continue
                if price <= 1:
                    continue

                key = outcome_key(raw_outcome)
                current = best_for_market.get(key)
                if current is None or price > current.price:
                    best_for_market[key] = BestOutcome(
                        name=str(raw_outcome.get("name", "")),
                        price=price,
                        bookmaker=book_title,
                        market_key=market_key,
                        point=raw_outcome.get("point"),
                    )

    for market_key, best_outcomes_map in market_best.items():
        best_outcomes = list(best_outcomes_map.values())
        # Need at least 2 outcomes for a valid arbitrage market.
        if len(best_outcomes) < 2:
            continue

        # For point-based markets, group by point so both sides of same line are compared.
        groups: Dict[Optional[float], List[BestOutcome]] = {}
        for outcome in best_outcomes:
            groups.setdefault(outcome.point, []).append(outcome)

        for _point, outcomes in groups.items():
            if len(outcomes) < 2:
                continue
            # Avoid duplicate team totals style markets with many names unless they share a real line.
            implied = sum(1 / o.price for o in outcomes if o.price > 0)
            if 0 < implied < 1:
                opportunities.append(
                    ArbitrageOpportunity(
                        sport_key=event.get("sport_key", ""),
                        sport_title=sport_title or event.get("sport_title", ""),
                        event=format_event(event),
                        commence_time=event.get("commence_time", ""),
                        market_key=market_key,
                        implied_probability=implied,
                        profit_percent=(1 - implied) * 100,
                        outcomes=sorted(outcomes, key=lambda x: x.name),
                    )
                )

    return sorted(opportunities, key=lambda x: x.profit_percent, reverse=True)


def scan_sports(
    sport_keys: Sequence[str],
    sport_titles: Optional[Dict[str, str]] = None,
    regions: str = DEFAULT_REGIONS,
    markets: Sequence[str] = CORE_MARKETS,
    bookmakers: Optional[Sequence[str]] = None,
    max_events_per_sport: int = 50,
) -> Tuple[List[ArbitrageOpportunity], int, List[str]]:
    sport_titles = sport_titles or {}
    all_opportunities: List[ArbitrageOpportunity] = []
    scanned_events = 0
    errors: List[str] = []

    for sport_key in sport_keys:
        try:
            events = fetch_odds(sport_key, regions=regions, markets=markets, bookmakers=bookmakers)
        except Exception as exc:
            errors.append(f"{sport_key}: {exc}")
            continue

        for event in events[:max_events_per_sport]:
            scanned_events += 1
            all_opportunities.extend(find_arbs_in_event(event, sport_titles.get(sport_key, sport_key)))

    return sorted(all_opportunities, key=lambda x: x.profit_percent, reverse=True), scanned_events, errors


def opportunities_to_rows(opportunities: Iterable[ArbitrageOpportunity]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for arb in opportunities:
        rows.append(
            {
                "Sport": arb.sport_title or arb.sport_key,
                "Event": arb.event,
                "Start": arb.commence_time,
                "Market": arb.market_key,
                "Profit %": round(arb.profit_percent, 3),
                "Best odds": " | ".join(
                    f"{format_outcome_name(o)} @ {o.price} ({o.bookmaker})" for o in arb.outcomes
                ),
            }
        )
    return rows
