import os
from itertools import product
from typing import Dict, List, Any, Optional

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://api.the-odds-api.com/v4"
REGION = "uk"
ODDS_FORMAT = "decimal"
DATE_FORMAT = "iso"

SPORTS: Dict[str, str] = {
    "Football - English Premier League": "soccer_epl",
    "Football - UEFA Champions League": "soccer_uefa_champs_league",
    "Football - England Championship": "soccer_efl_champ",
    "Basketball - NBA": "basketball_nba",
    "Tennis - ATP": "tennis_atp",
    "Tennis - WTA": "tennis_wta",
    "Rugby League - NRL": "rugbyleague_nrl",
    "Horse Racing": "horse_racing",
}

UK_BOOKMAKERS = {
    "bet365", "betfair_ex_uk", "betfair_sb_uk", "betfred", "boylesports",
    "coral", "ladbrokes_uk", "paddypower", "skybet", "unibet_uk", "williamhill",
}

MARKETS_BY_SPORT = {
    "default": ["h2h"],
    "football": ["h2h", "totals", "btts"],
    "basketball": ["h2h", "totals"],
    "tennis": ["h2h"],
    "horse": ["h2h"],
}


def get_api_key() -> str:
    """Read API key from Streamlit Secrets first, then environment variables."""
    try:
        key = st.secrets.get("ODDS_API_KEY", "")
    except Exception:
        key = ""
    return key or os.getenv("ODDS_API_KEY", "")


def markets_for_sport(sport_key: str) -> List[str]:
    if sport_key.startswith("soccer_"):
        return MARKETS_BY_SPORT["football"]
    if sport_key.startswith("basketball_"):
        return MARKETS_BY_SPORT["basketball"]
    if sport_key.startswith("tennis_"):
        return MARKETS_BY_SPORT["tennis"]
    if "horse" in sport_key:
        return MARKETS_BY_SPORT["horse"]
    return MARKETS_BY_SPORT["default"]


def fetch_odds(sport_key: str, market: str = "h2h") -> List[Dict[str, Any]]:
    api_key = get_api_key()
    if not api_key:
        raise ValueError("Missing ODDS_API_KEY. Add it in Streamlit Secrets.")

    url = f"{API_BASE}/sports/{sport_key}/odds"
    params = {
        "apiKey": api_key,
        "regions": REGION,
        "markets": market,
        "oddsFormat": ODDS_FORMAT,
        "dateFormat": DATE_FORMAT,
    }
    response = requests.get(url, params=params, timeout=30)

    if response.status_code == 401:
        raise ValueError("Odds API rejected your key. Check ODDS_API_KEY in Streamlit Secrets.")
    if response.status_code == 422:
        raise ValueError(f"The selected market is not available for this sport: {market}")
    if response.status_code == 429:
        raise ValueError("Odds API limit reached. Try again later or upgrade your API plan.")

    response.raise_for_status()
    return response.json()


def _best_prices_for_event(event: Dict[str, Any], market_key: str) -> Dict[str, Dict[str, Any]]:
    best: Dict[str, Dict[str, Any]] = {}
    for bookmaker in event.get("bookmakers", []):
        if bookmaker.get("key") not in UK_BOOKMAKERS:
            continue
        for market in bookmaker.get("markets", []):
            if market.get("key") != market_key:
                continue
            for outcome in market.get("outcomes", []):
                name = outcome.get("name")
                price = outcome.get("price")
                point = outcome.get("point")
                if name is None or price is None:
                    continue
                outcome_key = f"{name} {point}" if point is not None else str(name)
                if outcome_key not in best or price > best[outcome_key]["price"]:
                    best[outcome_key] = {
                        "outcome": outcome_key,
                        "price": float(price),
                        "bookmaker": bookmaker.get("title", bookmaker.get("key", "Unknown")),
                    }
    return best


def find_arbitrage(events: List[Dict[str, Any]], market_key: str = "h2h", min_profit: float = 0.0) -> List[Dict[str, Any]]:
    opportunities: List[Dict[str, Any]] = []

    for event in events:
        best = _best_prices_for_event(event, market_key)
        if len(best) < 2:
            continue

        implied_probability = sum(1 / item["price"] for item in best.values())
        profit_percent = (1 - implied_probability) * 100

        if implied_probability < 1 and profit_percent >= min_profit:
            opportunities.append({
                "sport": event.get("sport_title", ""),
                "event": f"{event.get('home_team', '')} v {event.get('away_team', '')}".strip(" v"),
                "commence_time": event.get("commence_time", ""),
                "market": market_key,
                "profit_percent": round(profit_percent, 2),
                "implied_probability": round(implied_probability * 100, 2),
                "best_prices": list(best.values()),
            })

    opportunities.sort(key=lambda x: x["profit_percent"], reverse=True)
    return opportunities


def build_stake_plan(best_prices: List[Dict[str, Any]], total_stake: float) -> List[Dict[str, Any]]:
    inv_total = sum(1 / item["price"] for item in best_prices)
    plan = []
    for item in best_prices:
        stake = total_stake * ((1 / item["price"]) / inv_total)
        payout = stake * item["price"]
        plan.append({
            "Outcome": item["outcome"],
            "Bookmaker": item["bookmaker"],
            "Odds": item["price"],
            "Stake": round(stake, 2),
            "Return": round(payout, 2),
        })
    return plan
