# AI Arbitrage Scanner

A private Streamlit dashboard for scanning live bookmaker odds and finding basic arbitrage opportunities.

## What it does

- Connects to The Odds API v4
- Scans UK bookmaker odds
- Finds arbitrage on `h2h`, `spreads`, and `totals` markets
- Calculates exact stakes for a chosen total stake
- Optional Telegram alerts

The Odds API v4 uses `GET /v4/sports/{sport}/odds` for live and upcoming events, with parameters such as `regions`, `markets`, and `oddsFormat=decimal`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Mac/Linux
# or: .venv\Scripts\activate on Windows

pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and add your Odds API key:

```env
ODDS_API_KEY=your_real_key_here
```

Run:

```bash
streamlit run app.py
```

## Telegram alerts

1. Create a bot with Telegram's BotFather.
2. Put your bot token in `.env`.
3. Get your chat ID and put it in `.env`.
4. Enable alerts in the dashboard sidebar.

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Important

Arbitrage is not risk-free in practice. Odds can move, accounts can be limited, markets can suspend, and stake limits can differ by bookmaker. Confirm all odds before placing bets.
