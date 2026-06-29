def format_alert(opportunity: dict) -> str:
    lines = [
        "Arbitrage opportunity found",
        f"Event: {opportunity.get('event', '')}",
        f"Market: {opportunity.get('market', '')}",
        f"Profit: {opportunity.get('profit_percent', 0)}%",
        "Best prices:",
    ]
    for price in opportunity.get("best_prices", []):
        lines.append(f"- {price['outcome']}: {price['price']} at {price['bookmaker']}")
    return "\n".join(lines)
