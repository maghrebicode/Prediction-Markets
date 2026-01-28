#!/usr/bin/env python3
"""
Kalshi Top 100 Non-Sports Markets Scraper
For Pydroid 3 - Just copy and run!
"""

try:
    import requests
except ImportError:
    print("ERROR: Install 'requests' via Pydroid Pip menu first!")
    raise SystemExit(1)

import csv
import time
import os

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
OUTPUT_FILE = "kalshi_public_markets.csv"

# Sports keywords to filter out
SPORTS_KEYWORDS = [
    "nfl", "nba", "mlb", "nhl", "ncaa", "football", "basketball",
    "baseball", "hockey", "soccer", "tennis", "golf", "ufc", "mma",
    "boxing", "wrestling", "racing", "f1", "nascar", "pga", "fifa",
    "world cup", "super bowl", "playoffs", "championship", "league",
    "team", "player", "game", "match", "score", "win", "loss",
    "patriots", "eagles", "chiefs", "49ers", "cowboys", "packers",
    "lakers", "celtics", "warriors", "bulls", "heat", "nets",
    "yankees", "dodgers", "cubs", "red sox", "mets", "braves",
    "athlete", "coach", "mvp", "touchdown", "homerun", "slam dunk"
]

def is_sports_market(market):
    """Check if market is sports-related."""
    text = (
        (market.get("title") or "") + " " +
        (market.get("subtitle") or "") + " " +
        (market.get("event_ticker") or "") + " " +
        (market.get("ticker") or "")
    ).lower()
    return any(kw in text for kw in SPORTS_KEYWORDS)

def calc_probability(m):
    """Calculate Yes probability from bid/ask or last price."""
    bid, ask, last = m.get("yes_bid"), m.get("yes_ask"), m.get("last_price")
    if bid and ask and bid > 0 and ask > 0:
        return round((bid + ask) / 2, 1)
    if last and last > 0:
        return round(last, 1)
    if ask and ask > 0:
        return round(ask, 1)
    if bid and bid > 0:
        return round(bid, 1)
    return None

def fetch_markets():
    """Fetch markets with pagination, filter sports, return top 100 by volume."""
    all_markets = []
    cursor = None
    page = 0

    print("Fetching markets from Kalshi...")

    while True:
        page += 1
        params = {"limit": 200, "status": "open"}
        if cursor:
            params["cursor"] = cursor

        try:
            r = requests.get(f"{BASE_URL}/markets", params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break

        markets = data.get("markets", [])
        if not markets:
            break

        # Filter out sports markets
        for m in markets:
            if not is_sports_market(m):
                all_markets.append(m)

        print(f"Page {page}: {len(markets)} fetched, {len(all_markets)} non-sports total")

        cursor = data.get("cursor")
        if not cursor:
            break

        time.sleep(0.3)

    # Sort by open interest + volume, take top 100
    all_markets.sort(
        key=lambda x: (x.get("open_interest") or 0) + (x.get("volume") or 0),
        reverse=True
    )
    return all_markets[:100]

def main():
    print("=" * 50)
    print("KALSHI TOP 100 NON-SPORTS MARKETS")
    print("=" * 50)

    markets = fetch_markets()

    if not markets:
        print("No markets found!")
        return

    # Process and save
    rows = []
    for i, m in enumerate(markets, 1):
        title = m.get("title") or ""
        subtitle = m.get("subtitle") or ""
        desc = f"{title} - {subtitle}" if subtitle else title

        rows.append({
            "rank": i,
            "ticker": m.get("ticker", ""),
            "description": desc,
            "open_interest": m.get("open_interest") or 0,
            "volume": m.get("volume") or 0,
            "yes_probability": calc_probability(m),
            "yes_bid": m.get("yes_bid") or 0,
            "yes_ask": m.get("yes_ask") or 0,
            "close_time": m.get("close_time") or ""
        })

        if i % 20 == 0:
            print(f"Processed {i} markets...")

    # Save CSV
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FILE)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    print(f"\nSaved: {path}")
    print(f"Total: {len(rows)} markets")

    # Show top 10
    print("\n" + "=" * 50)
    print("TOP 10 MARKETS:")
    print("=" * 50)
    for r in rows[:10]:
        d = r["description"][:45] + "..." if len(r["description"]) > 45 else r["description"]
        print(f"{r['rank']:2}. {d}")
        print(f"    OI: {r['open_interest']:,} | Vol: {r['volume']:,} | Yes: {r['yes_probability']}%")

if __name__ == "__main__":
    main()
