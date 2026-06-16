import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from alerts import format_opportunity, send_telegram_message, telegram_enabled
from scanner import SPORTS, UK_BOOKMAKERS, calculate_stakes, fetch_odds, find_arbitrage

load_dotenv()

st.set_page_config(page_title="AI Arbitrage Scanner", layout="wide")
st.title("AI Arbitrage Scanner")
st.caption("Private tool for finding simple arbitrage opportunities from live bookmaker odds.")

with st.sidebar:
    st.header("Settings")
    sport_label = st.selectbox("Sport", list(SPORTS.keys()))
    market = st.selectbox("Market", ["h2h", "spreads", "totals"])
    total_stake = st.number_input("Total stake (£)", min_value=10.0, value=100.0, step=10.0)
    min_profit = st.number_input("Minimum profit margin (%)", min_value=0.0, value=float(os.getenv("MIN_PROFIT_MARGIN", "1.0")), step=0.1)

    use_specific_books = st.checkbox("Use UK bookmaker list", value=False)
    selected_books = []
    if use_specific_books:
        selected_books = st.multiselect("Bookmakers", UK_BOOKMAKERS, default=["coral", "ladbrokes_uk", "betfred"])

    send_alerts = st.checkbox("Send Telegram alerts", value=False)
    st.write("Telegram:", "Enabled" if telegram_enabled() else "Not configured")

sport_key = SPORTS[sport_label]

if st.button("Scan now", type="primary"):
    try:
        events = fetch_odds(
            sport_key=sport_key,
            region="uk",
            market=market,
            bookmakers=selected_books if use_specific_books and selected_books else None,
        )
        arbs = [a for a in find_arbitrage(events, market=market) if a.profit_margin >= min_profit]

        st.write(f"Checked {len(events)} events.")

        if not arbs:
            st.warning("No arbitrage opportunities found for these settings.")
        else:
            st.success(f"Found {len(arbs)} opportunities.")

            summary_rows = []
            for arb in arbs:
                summary_rows.append({
                    "Sport": arb.sport,
                    "Event": arb.event,
                    "Start": arb.commence_time,
                    "Market": arb.market,
                    "Profit Margin %": arb.profit_margin,
                    "Implied Probability": arb.implied_probability,
                })

            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

            for arb in arbs:
                st.divider()
                st.subheader(f"{arb.event} — {arb.profit_margin}%")
                st.write(f"Start: {arb.commence_time}")
                stakes = calculate_stakes(total_stake, arb.bets)
                df = pd.DataFrame.from_dict(stakes, orient="index")
                df.index.name = "Outcome"
                st.dataframe(df, use_container_width=True)

                if send_alerts:
                    send_telegram_message(format_opportunity(arb, total_stake, stakes))

            if send_alerts:
                st.info("Telegram alerts sent for displayed opportunities.")

    except Exception as exc:
        st.error(str(exc))

st.markdown("""
### Notes
- This scans the market you select and compares the best odds across bookmakers.
- Odds can move quickly. Always confirm prices in the bookmaker account before placing bets.
- Start with small stakes while testing.
""")
