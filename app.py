import pandas as pd
import streamlit as st

from scanner import SPORTS, fetch_odds, find_arbitrage, markets_for_sport, build_stake_plan, get_api_key

st.set_page_config(page_title="AI Arbitrage Scanner", page_icon="📈", layout="wide")

st.title("AI Arbitrage Scanner")
st.caption("Private tool for finding simple arbitrage opportunities from live bookmaker odds.")

with st.sidebar:
    st.header("Settings")
    sport_label = st.selectbox("Sport", list(SPORTS.keys()))
    sport_key = SPORTS[sport_label]
    available_markets = markets_for_sport(sport_key)
    market = st.selectbox("Market", available_markets, format_func=lambda x: {
        "h2h": "Match Winner / Head to Head",
        "totals": "Over / Under",
        "btts": "Both Teams To Score",
    }.get(x, x))
    min_profit = st.number_input("Minimum profit %", min_value=0.0, max_value=50.0, value=0.0, step=0.1)
    total_stake = st.number_input("Example total stake", min_value=1.0, max_value=100000.0, value=100.0, step=10.0)

api_key = get_api_key()
if not api_key:
    st.error("Missing ODDS_API_KEY. Add it in Streamlit: Manage app → Settings → Secrets.")
    st.code('ODDS_API_KEY = "paste_your_real_key_here"', language="toml")
    st.stop()

if st.button("Scan now", type="primary"):
    try:
        with st.spinner("Scanning live bookmaker odds..."):
            events = fetch_odds(sport_key, market)
            opportunities = find_arbitrage(events, market, min_profit)

        st.success(f"Scanned {len(events)} events. Found {len(opportunities)} arbitrage opportunities.")

        if not opportunities:
            st.info("No arbitrage found right now. Odds change quickly, so try again later or choose another sport/market.")
        else:
            rows = []
            for opp in opportunities:
                rows.append({
                    "Event": opp["event"],
                    "Start": opp["commence_time"],
                    "Market": opp["market"],
                    "Profit %": opp["profit_percent"],
                    "Implied %": opp["implied_probability"],
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

            for i, opp in enumerate(opportunities, start=1):
                with st.expander(f"#{i} {opp['event']} — {opp['profit_percent']}% profit"):
                    st.write("Best odds:")
                    st.dataframe(pd.DataFrame(opp["best_prices"]), use_container_width=True)
                    st.write(f"Example stake plan for £{total_stake:.2f} total stake:")
                    st.dataframe(pd.DataFrame(build_stake_plan(opp["best_prices"], total_stake)), use_container_width=True)

    except Exception as exc:
        st.error(str(exc))

st.markdown("---")
st.subheader("Notes")
st.write("• This scans the selected market and compares the best odds across UK bookmakers.")
st.write("• Always confirm prices in the bookmaker account before placing bets.")
st.write("• Start with small stakes while testing.")
