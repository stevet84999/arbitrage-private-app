import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.the-odds-api.com/v4"

SPORTS = {
    "Football - EPL": "soccer_epl",
    "Football - UEFA Champions League": "soccer_uefa_champs_league",
    "Football - FA Cup": "soccer_fa_cup",
    "Basketball - NBA": "basketball_nba",
    "Tennis - ATP": "tennis_atp",
    "Tennis - WTA": "tennis_wta",
    "Rugby Union": "rugbyunion",
    "Rugby League": "rugbyleague",
}

UK_BOOKMAKERS = [
    "betfair_ex_uk",
    "betfair_sb_uk",
    "betfred",
    "betvictor",
    "boylesports",
    "coral",
    "grosvenor",
    "ladbrokes_uk",
    "leovegas",
    "livescorebet",
    "matchbook",
    "paddypower",
    "skybet",
    "sport888",
    "unibet_uk",
    "virginbet",
    "williamhill",
]

PREFERRED_BOOKMAKERS = ["coral", "ladbrokes_uk", "betfred"]


@dataclass
class ArbOpportunity:
    sport: str
    event: str
    commence_time: str
    market: str
    implied_probability: float
    profit_margin: float
    bets: Dict[str, Dict[str, Any]]


def get_secret(name: str, default: str = "") -> str:
    """Read from Streamlit Secrets first, then environment/.env."""
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""

    if not value:
        value = os.getenv(name, default)

    return str(value).strip()


def get_api_key() -> str:
    return get_secret("ODDS_API_KEY")


def _require_api_key() -> str:
    api_key = get_api_key()
    if not api_key or api_key == "your_odds_api_key_here":
        raise RuntimeError(
            "Missing ODDS_API_KEY. Add it in Streamlit: Manage app → Settings → Secrets."
        )
    return api_key


def get_active_sports() -> List[Dict[str, Any]]:
    api_key = _require_api_key()
    response = requests.get(f"{BASE_URL}/sports", params={"apiKey": api_key}, timeout=25)
    response.raise_for_status()
    return response.json()


def fetch_odds(
    sport_key: str,
    region: str = "uk",
    market: str = "h2h",
    bookmakers: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    api_key = _require_api_key()

    params = {
        "apiKey": api_key,
        "regions": region,
        "markets": market,
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }

    if bookmakers:
        params["bookmakers"] = ",".join(bookmakers)
        params.pop("regions", None)

    response = requests.get(f"{BASE_URL}/sports/{sport_key}/odds", params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def find_arbitrage(events: List[Dict[str, Any]], market: str = "h2h") -> List[ArbOpportunity]:
    opportunities: List[ArbOpportunity] = []

    for event in events:
        best_by_outcome: Dict[str, Dict[str, Any]] = {}

        for bookmaker in event.get("bookmakers", []):
            book_key = bookmaker.get("key", "unknown")
            book_title = bookmaker.get("title", book_key)

            for market_data in bookmaker.get("markets", []):
                if market_data.get("key") != market:
                    continue

                for outcome in market_data.get("outcomes", []):
                    name = outcome.get("name")
                    price = outcome.get("price")

                    if not name or not isinstance(price, (int, float)) or price <= 1:
                        continue

                    current = best_by_outcome.get(name)
                    if current is None or float(price) > current["odds"]:
                        best_by_outcome[name] = {
                            "odds": float(price),
                            "bookmaker_key": book_key,
                            "bookmaker": book_title,
                        }

        if len(best_by_outcome) < 2:
            continue

        implied_probability = sum(1 / bet["odds"] for bet in best_by_outcome.values())

        if implied_probability < 1:
            home = event.get("home_team", "Home")
            away = event.get("away_team", "Away")
            profit_margin = (1 - implied_probability) * 100

            opportunities.append(
                ArbOpportunity(
                    sport=event.get("sport_title", event.get("sport_key", "Unknown sport")),
                    event=f"{home} vs {away}",
                    commence_time=event.get("commence_time", ""),
                    market=market,
                    implied_probability=round(implied_probability, 5),
                    profit_margin=round(profit_margin, 2),
                    bets=best_by_outcome,
                )
            )

    return sorted(opportunities, key=lambda x: x.profit_margin, reverse=True)


def calculate_stakes(total_stake: float, bets: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    implied_total = sum(1 / bet["odds"] for bet in bets.values())
    result: Dict[str, Dict[str, Any]] = {}

    for outcome, bet in bets.items():
        stake = total_stake * ((1 / bet["odds"]) / implied_total)
        payout = stake * bet["odds"]

        result[outcome] = {
            "bookmaker": bet["bookmaker"],
            "odds": bet["odds"],
            "stake": round(stake, 2),
            "expected_payout": round(payout, 2),
            "expected_profit": round(payout - total_stake, 2),
        }

    return result
