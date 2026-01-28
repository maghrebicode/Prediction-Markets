#!/usr/bin/env python3
"""
Kalshi Public Markets Scraper for Pydroid 3
============================================
Scrapes all available prediction markets from Kalshi's public API
and saves them to a CSV file.

No authentication required - uses public endpoints only.
"""

# Check for requests library availability
try:
    import requests
except ImportError:
    print("=" * 60)
    print("ERROR: The 'requests' library is not installed!")
    print("")
    print("To install in Pydroid 3:")
    print("  1. Open the side menu (swipe from left)")
    print("  2. Tap 'Pip'")
    print("  3. Search for 'requests'")
    print("  4. Tap 'INSTALL'")
    print("  5. Run this script again")
    print("=" * 60)
    raise SystemExit(1)

import csv
import time
import os
from datetime import datetime


# =============================================================================
# CONFIGURATION
# =============================================================================

# Kalshi public API base URL (serves ALL markets, not just elections)
BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

# Output file name (saved in script directory)
OUTPUT_FILE = "kalshi_public_markets.csv"

# Pagination settings
PAGE_LIMIT = 200  # Max allowed by API is 200

# Rate limiting - delay between API requests (in seconds)
REQUEST_DELAY = 0.5  # Be respectful of rate limits

# Progress reporting interval
PROGRESS_INTERVAL = 20


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_yes_probability(market):
    """
    Calculate the probability of 'Yes' for a market.

    Priority:
    1. Midpoint of yes_bid and yes_ask (if both exist)
    2. Last traded price
    3. yes_ask only (if no bid)
    4. yes_bid only (if no ask)

    Returns probability as a percentage (0-100) or None if unavailable.
    """
    yes_bid = market.get("yes_bid")
    yes_ask = market.get("yes_ask")
    last_price = market.get("last_price")

    # Prices are in cents (0-100 scale already represents probability)

    # Try midpoint of bid/ask first (most accurate current price)
    if yes_bid and yes_ask and yes_bid > 0 and yes_ask > 0:
        midpoint = (yes_bid + yes_ask) / 2
        return round(midpoint, 2)

    # Fall back to last traded price
    if last_price and last_price > 0:
        return round(last_price, 2)

    # Use ask if available
    if yes_ask and yes_ask > 0:
        return round(yes_ask, 2)

    # Use bid if available
    if yes_bid and yes_bid > 0:
        return round(yes_bid, 2)

    return None


def get_market_description(market):
    """
    Build a readable market description from title and subtitle.
    """
    title = market.get("title", "")
    subtitle = market.get("subtitle", "")

    if title and subtitle:
        return f"{title} - {subtitle}"
    elif title:
        return title
    elif subtitle:
        return subtitle
    else:
        return market.get("ticker", "Unknown")


def fetch_markets_page(cursor=None):
    """
    Fetch a single page of markets from the Kalshi API.

    Args:
        cursor: Pagination cursor (None for first page)

    Returns:
        Tuple of (markets_list, next_cursor)
        next_cursor is None if no more pages
    """
    url = f"{BASE_URL}/markets"

    params = {
        "limit": PAGE_LIMIT,
    }

    if cursor:
        params["cursor"] = cursor

    headers = {
        "Accept": "application/json",
        "User-Agent": "KalshiPublicScraper/1.0 (Pydroid3)"
    }

    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()

    markets = data.get("markets", [])
    next_cursor = data.get("cursor")

    # Empty cursor means no more pages
    if not next_cursor:
        next_cursor = None

    return markets, next_cursor


def fetch_all_markets():
    """
    Fetch all markets from the Kalshi API, handling pagination.

    Yields market dictionaries one at a time for memory efficiency.
    """
    cursor = None
    total_fetched = 0
    page_num = 0

    print("Starting to fetch markets from Kalshi API...")
    print(f"API URL: {BASE_URL}/markets")
    print("-" * 50)

    while True:
        page_num += 1

        try:
            markets, next_cursor = fetch_markets_page(cursor)
        except requests.exceptions.RequestException as e:
            print(f"\nError fetching page {page_num}: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)
            try:
                markets, next_cursor = fetch_markets_page(cursor)
            except requests.exceptions.RequestException as e:
                print(f"Retry failed: {e}")
                print("Stopping with markets collected so far.")
                break

        if not markets:
            print(f"Page {page_num}: No markets returned, ending pagination.")
            break

        for market in markets:
            total_fetched += 1
            yield market

            # Progress update every PROGRESS_INTERVAL markets
            if total_fetched % PROGRESS_INTERVAL == 0:
                print(f"Retrieved {total_fetched} markets...")

        # Check if there are more pages
        if next_cursor is None:
            print(f"Page {page_num}: Last page reached.")
            break

        cursor = next_cursor

        # Rate limiting delay
        time.sleep(REQUEST_DELAY)

    print("-" * 50)
    print(f"Total markets fetched: {total_fetched}")


def process_market(market):
    """
    Extract relevant data from a market object.

    Returns a dictionary with the fields we want to save.
    """
    ticker = market.get("ticker", "")
    description = get_market_description(market)

    # Market size metrics
    open_interest = market.get("open_interest", 0) or 0
    volume = market.get("volume", 0) or 0
    volume_24h = market.get("volume_24h", 0) or 0

    # Probability calculation
    yes_probability = calculate_yes_probability(market)

    # Additional useful fields
    status = market.get("status", "")
    event_ticker = market.get("event_ticker", "")
    close_time = market.get("close_time", "")

    # Price details (in cents)
    yes_bid = market.get("yes_bid", 0) or 0
    yes_ask = market.get("yes_ask", 0) or 0
    last_price = market.get("last_price", 0) or 0

    return {
        "ticker": ticker,
        "event_ticker": event_ticker,
        "description": description,
        "status": status,
        "open_interest": open_interest,
        "total_volume": volume,
        "volume_24h": volume_24h,
        "yes_probability_pct": yes_probability,
        "yes_bid_cents": yes_bid,
        "yes_ask_cents": yes_ask,
        "last_price_cents": last_price,
        "close_time": close_time,
    }


def save_to_csv(markets_data, filename):
    """
    Save processed market data to a CSV file.

    Args:
        markets_data: List of processed market dictionaries
        filename: Output CSV filename
    """
    if not markets_data:
        print("No market data to save!")
        return

    # Get field names from first record
    fieldnames = list(markets_data[0].keys())

    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, filename)

    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(markets_data)

    print(f"\nCSV file saved: {filepath}")
    print(f"Total records: {len(markets_data)}")

    return filepath


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """
    Main function to orchestrate the scraping process.
    """
    print("=" * 60)
    print("KALSHI PUBLIC MARKETS SCRAPER")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")

    # Collect all markets
    all_markets = []

    try:
        for market in fetch_all_markets():
            processed = process_market(market)
            all_markets.append(processed)

    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user!")
        print(f"Saving {len(all_markets)} markets collected so far...")

    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        print(f"Saving {len(all_markets)} markets collected so far...")

    # Save results
    if all_markets:
        filepath = save_to_csv(all_markets, OUTPUT_FILE)

        # Print summary statistics
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        # Count by status
        status_counts = {}
        for m in all_markets:
            status = m["status"] or "unknown"
            status_counts[status] = status_counts.get(status, 0) + 1

        print("\nMarkets by status:")
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")

        # Markets with trading activity
        active_markets = [m for m in all_markets if m["open_interest"] > 0]
        print(f"\nMarkets with open interest: {len(active_markets)}")

        # Top markets by open interest
        top_by_oi = sorted(all_markets, key=lambda x: x["open_interest"], reverse=True)[:5]
        print("\nTop 5 markets by open interest:")
        for i, m in enumerate(top_by_oi, 1):
            desc = m["description"][:50] + "..." if len(m["description"]) > 50 else m["description"]
            print(f"  {i}. {desc}")
            print(f"     Open Interest: {m['open_interest']:,} | Yes Prob: {m['yes_probability_pct']}%")

    else:
        print("\nNo markets were collected. Check your internet connection.")

    print("\n" + "=" * 60)
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
