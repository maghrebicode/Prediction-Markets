#!/usr/bin/env python3
"""
Kalshi Top 100 Non-Sports Markets Scraper
For Pydroid 3 - Just copy and run!

Outputs: claude.kalshi.csv with title and yes_probability columns
"""

# Handle requests import with helpful error for Pydroid users
try:
    import requests
except ImportError:
    print("ERROR: The 'requests' library is not installed.")
    print("In Pydroid 3: Go to Menu > Pip > type 'requests' > Install")
    raise SystemExit(1)

import csv
import json
import time
import os

# Kalshi public API endpoint
BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
OUTPUT_FILE = "claude.kalshi.csv"

# Sports keywords to filter out
SPORTS_KEYWORDS = [
    "nfl", "nba", "mlb", "nhl", "ncaa", "football", "basketball",
    "baseball", "hockey", "soccer", "tennis", "golf", "ufc", "mma",
    "boxing", "wrestling", "racing", "f1", "nascar", "pga", "fifa",
    "world cup", "super bowl", "playoffs", "championship",
    "patriots", "eagles", "chiefs", "49ers", "cowboys", "packers",
    "lakers", "celtics", "warriors", "bulls", "heat", "nets",
    "yankees", "dodgers", "cubs", "red sox", "mets", "braves",
    "athlete", "coach", "mvp", "touchdown", "homerun", "slam dunk",
    "sports"
]


def is_sports_market(market):
    """Check if market is sports-related based on keywords."""
    text = (
        (market.get("title") or "") + " " +
        (market.get("subtitle") or "") + " " +
        (market.get("category") or "") + " " +
        (market.get("event_ticker") or "") + " " +
        (market.get("ticker") or "")
    ).lower()
    return any(keyword in text for keyword in SPORTS_KEYWORDS)


def get_yes_probability(market):
    """
    Calculate Yes probability from market price data.
    Price is in cents (0-100), so 54 cents = 54% probability.
    """
    # Try yes_bid/yes_ask midpoint first (most accurate)
    yes_bid = market.get("yes_bid")
    yes_ask = market.get("yes_ask")

    if yes_bid and yes_ask and yes_bid > 0 and yes_ask > 0:
        return round((yes_bid + yes_ask) / 2, 1)

    # Fall back to last traded price
    last_price = market.get("last_price")
    if last_price and last_price > 0:
        return round(last_price, 1)

    # Use whatever price is available
    if yes_ask and yes_ask > 0:
        return round(yes_ask, 1)
    if yes_bid and yes_bid > 0:
        return round(yes_bid, 1)

    return None


def fetch_markets():
    """
    Fetch all open markets from Kalshi API with pagination.
    Filter out sports markets and return top 100 by open_interest.
    """
    all_markets = []
    cursor = None
    page = 0

    print("Fetching markets from Kalshi public API...")
    print("-" * 40)

    while True:
        page += 1
        params = {"limit": 200, "status": "open"}
        if cursor:
            params["cursor"] = cursor

        try:
            response = requests.get(
                f"{BASE_URL}/markets",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

        except requests.exceptions.ConnectionError:
            print(f"Connection error on page {page}. Check your internet.")
            print("Retrying in 3 seconds...")
            time.sleep(3)
            continue

        except requests.exceptions.Timeout:
            print(f"Timeout on page {page}. Retrying...")
            time.sleep(2)
            continue

        except requests.exceptions.RequestException as e:
            print(f"Request error on page {page}: {e}")
            break

        except json.JSONDecodeError:
            print(f"Invalid JSON response on page {page}")
            break

        markets = data.get("markets", [])
        if not markets:
            break

        # Filter out sports markets
        non_sports = [m for m in markets if not is_sports_market(m)]
        all_markets.extend(non_sports)

        print(f"Page {page}: {len(markets)} fetched, {len(non_sports)} non-sports, {len(all_markets)} total")

        # Check for next page
        cursor = data.get("cursor")
        if not cursor:
            break

        # Rate limiting - be nice to the API
        time.sleep(0.3)

    print("-" * 40)
    print(f"Total non-sports markets found: {len(all_markets)}")

    # Sort by open_interest (descending) and take top 100
    all_markets.sort(
        key=lambda x: x.get("open_interest") or 0,
        reverse=True
    )

    return all_markets[:100]


def main():
    """Main function to scrape and save market data."""
    print("=" * 50)
    print("KALSHI TOP 100 NON-SPORTS MARKETS SCRAPER")
    print("=" * 50)
    print()

    try:
        markets = fetch_markets()
    except Exception as e:
        print(f"Fatal error fetching markets: {e}")
        print("Check your internet connection and try again.")
        return

    if not markets:
        print("No markets found! The API may be unavailable.")
        return

    print(f"\nProcessing top {len(markets)} markets by open interest...")

    # Extract title and yes_probability for each market
    rows = []
    for market in markets:
        title = market.get("title") or "Unknown"
        probability = get_yes_probability(market)

        rows.append({
            "title": title,
            "yes_probability": probability
        })

    # Save to CSV
    try:
        # Get script directory for output file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, OUTPUT_FILE)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["title", "yes_probability"])
            writer.writeheader()
            writer.writerows(rows)

        print(f"\nSaved to: {output_path}")
        print(f"Total markets: {len(rows)}")

    except IOError as e:
        print(f"Error saving file: {e}")
        # Try current directory as fallback
        try:
            with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["title", "yes_probability"])
                writer.writeheader()
                writer.writerows(rows)
            print(f"Saved to current directory: {OUTPUT_FILE}")
        except IOError as e2:
            print(f"Could not save file: {e2}")
            return

    # Display top 10 markets
    print("\n" + "=" * 50)
    print("TOP 10 PREDICTIONS BY OPEN INTEREST:")
    print("=" * 50)

    for i, row in enumerate(rows[:10], 1):
        title = row["title"]
        # Truncate long titles for display
        if len(title) > 50:
            title = title[:47] + "..."
        prob = row["yes_probability"]
        prob_str = f"{prob}%" if prob is not None else "N/A"
        print(f"{i:2}. {title}")
        print(f"    Yes Probability: {prob_str}")
        print()

    print("=" * 50)
    print("Done! Check claude.kalshi.csv for full results.")
    print("=" * 50)


if __name__ == "__main__":
    main()
