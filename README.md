# AI Arbitrage Scanner

Streamlit app for scanning live odds from The Odds API and calculating arbitrage opportunities.

## Streamlit Secrets

Add this in Streamlit Cloud > Manage app > Settings > Secrets:

```toml
ODDS_API_KEY = "your_real_key_here"
```

## Deploy

Main file path:

```text
app.py
```

Recommended Python version: 3.11 or 3.12.

## Notes

- Leave bookmaker filter blank to request all bookmakers available for the selected region/account.
- Core markets: h2h, spreads, totals.
- Extra/custom markets depend on the sport and your Odds API plan.
