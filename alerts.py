"""Optional alert helpers for the arbitrage scanner."""

from __future__ import annotations

import os
import requests


def send_telegram(message: str) -> bool:
    """Send a Telegram alert if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are configured."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return False

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        response = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=15)
        return response.ok
    except Exception:
        return False
