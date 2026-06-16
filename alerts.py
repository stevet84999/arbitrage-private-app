import os
from typing import Iterable

import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()


def telegram_enabled() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def send_telegram_message(message: str) -> None:
    if not telegram_enabled():
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    response = requests.post(url, json=payload, timeout=20)
    response.raise_for_status()


def format_opportunity(arb, total_stake: float, stakes: dict) -> str:
    lines = [
        "🚨 <b>Arbitrage Found</b>",
        f"Sport: {arb.sport}",
        f"Event: {arb.event}",
        f"Start: {arb.commence_time}",
        f"Profit margin: {arb.profit_margin}%",
        f"Total stake: £{total_stake:.2f}",
        "",
    ]
    for outcome, data in stakes.items():
        lines.append(
            f"{outcome}: £{data['stake']} at {data['odds']} with {data['bookmaker']}"
        )
    return "\n".join(lines)
