from __future__ import annotations

import os
from typing import List

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from scanner import (
    CORE_MARKETS,
    POPULAR_EXTRA_MARKETS,
    DEFAULT_REGIONS,
    fetch_sports,
    opportunities_to_rows,
    scan_sports,
)

load_dotenv()

st.set_page_config(page_title="AI Arbitrage Scanner", page_icon="📈", layout="wide")

# Load secret safely. Streamlit throws if secrets are not configured, so guard it.
try:
    if "ODDS_API_KEY" in st.secrets:
        os.environ["ODDS_API_KEY"] = str(st.secrets["ODDS_API_KEY"]).strip()
except Exception:
    pass

st.title("AI Arbitrage Scanner")
st.caption("Private tool for finding arbitrage opportunities from live bookmaker odds.")

with st.sidebar:
    st.header("Scan settings")
    region = st.text_input("Region", DEFAULT_REGIONS, help="Use uk, eu, us, au or comma-separated regions.")

    st.subheader("Markets")
    selected_core = st.multiselect("Core markets", CORE_MARKETS, default=CORE_MARKETS)
    selected_extra = st.multiselect("Extra markets", POPULAR_EXTRA_MARKETS, default=[])
    custom_markets = st.text_input(
        "Custom markets",
        "",
        help="Comma-separated. Only markets supported by your Odds API plan/sport will work.",
    )

    st.subheader("Bookmakers")
    bookmaker_text = st.text_input(
        "Bookmaker keys (optional)",
        "",
        help="Leave blank to request all bookmakers available for the selected region/account. Or enter keys comma-separated.",
    )

    max_events = st.slider("Max events per sport", min_value=5, max_value=100, value=50, step=5)
    total_stake = st.number_input("Stake calculator total", min_value=1.0, value=100.0, step=10.0)
    include_inactive = st.checkbox("Show inactive sports", value=False)

api_key = os.getenv("ODDS_API_KEY", "").strip()
if not api_key:
    st.error("Missing ODDS_API_KEY. Add it in Streamlit Secrets.")
    st.stop()

try:
    sports = fetch_sports(include_inactive=include_inactive)
except Exception as exc:
    st.error(str(exc))
    st.stop()

if not sports:
    st.warning("No sports returned by The Odds API.")
    st.stop()

sport_options = {f"{s.get('group', 'Other')} — {s.get('title', s.get('key'))}": s.get("key") for s in sports}
sport_titles = {s.get("key"): s.get("title", s.get("key")) for s in sports}

# Default to active football/tennis/basketball where available.
default_labels: List[str] = []
for label, key in sport_options.items():
    if any(word in label.lower() for word in ["soccer", "football", "tennis", "basketball"]):
        default_labels.append(label)
    if len(default_labels) >= 6:
        break
if not default_labels:
    default_labels = list(sport_options.keys())[:3]

selected_labels = st.multiselect("Sports to scan", list(sport_options.keys()), default=default_labels)

markets = selected_core + selected_extra
if custom_markets.strip():
    markets.extend([m.strip() for m in custom_markets.split(",") if m.strip()])
markets = list(dict.fromkeys(markets))

bookmakers = [b.strip() for b in bookmaker_text.split(",") if b.strip()] if bookmaker_text.strip() else None
selected_sports = [sport_options[label] for label in selected_labels]

col1, col2, col3 = st.columns(3)
col1.metric("Sports selected", len(selected_sports))
col2.metric("Markets selected", len(markets))
col3.metric("Bookmaker filter", "All" if not bookmakers else len(bookmakers))

if st.button("Scan now", type="primary"):
    if not selected_sports:
        st.warning("Select at least one sport.")
        st.stop()
    if not markets:
        st.warning("Select at least one market.")
        st.stop()

    with st.spinner("Scanning live odds. This can take 30–90 seconds when scanning many sports/markets..."):
        opportunities, scanned_events, errors = scan_sports(
            selected_sports,
            sport_titles=sport_titles,
            regions=region,
            markets=markets,
            bookmakers=bookmakers,
            max_events_per_sport=max_events,
        )

    st.success(f"Scanned {scanned_events} events. Found {len(opportunities)} arbitrage opportunities.")

    if errors:
        with st.expander("Warnings / skipped requests"):
            for error in errors:
                st.warning(error)

    if not opportunities:
        st.info("No arbitrage found right now. Odds change quickly, so try again later or scan fewer/more markets.")
    else:
        rows = opportunities_to_rows(opportunities)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.subheader("Stake calculator")
        best = opportunities[0]
        st.write(f"Best opportunity: **{best.event}** — **{best.market_key}** — profit **{best.profit_percent:.2f}%**")
        st.dataframe(pd.DataFrame(best.stake_plan(total_stake)), use_container_width=True, hide_index=True)

st.divider()
st.subheader("Notes")
st.write(
    "• Leave bookmaker keys blank to request all bookmakers returned by The Odds API for your selected region/account.\n\n"
    "• Not every market is available for every sport or subscription plan. If a market causes an error, remove it or scan a different sport.\n\n"
    "• Odds move quickly. Always confirm prices in the bookmaker account before placing bets."
)
