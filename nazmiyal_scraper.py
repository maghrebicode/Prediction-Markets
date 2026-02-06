#!/usr/bin/env python3
"""
Nazmiyal Antique Rugs Scraper
Scrapes rug listings from nazmiyalantiquerugs.com (WooCommerce).
Uses cloudscraper to handle Cloudflare protection.
For Pydroid 3 - Install cloudscraper and beautifulsoup4 via Pip first!
"""

try:
    import cloudscraper
except ImportError:
    print("ERROR: Install 'cloudscraper' via pip first!")
    print("  pip install cloudscraper")
    raise SystemExit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Install 'beautifulsoup4' via pip first!")
    print("  pip install beautifulsoup4")
    raise SystemExit(1)

import csv
import time
import os
import re
import json

BASE_URL = "https://nazmiyalantiquerugs.com"
OUTPUT_FILE = "nazmiyal_rugs.csv"

# Category pages to scrape
CATEGORY_URLS = [
    "/antique-rugs/",
    "/vintage-rugs/",
    "/rugs-for-sale/",
]

# Maximum pages to paginate per category (safety limit)
MAX_PAGES_PER_CATEGORY = 50

# Delay between requests to be respectful
REQUEST_DELAY = 1.5


def create_scraper():
    """Create a cloudscraper session with browser-like headers."""
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "desktop": True},
    )
    scraper.headers.update({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": BASE_URL,
    })
    return scraper


def extract_rug_number(url, title):
    """Extract the rug number (4-5 digit ID) from URL or title."""
    # Try URL first (e.g., -47486/ at the end)
    match = re.search(r"-(\d{4,6})/?$", url)
    if match:
        return match.group(1)
    # Try title (e.g., "Rug 49143" or "#49143")
    match = re.search(r"(?:rug|#)\s*(\d{4,6})", title, re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


def parse_listing_page(soup):
    """Extract product URLs and basic info from a category listing page."""
    products = []

    # WooCommerce product list items
    product_items = soup.select("ul.products li.product, .products .product")
    if not product_items:
        # Fallback: look for any links that look like product pages
        product_items = soup.select(".product, .product-item, .rug-item")

    for item in product_items:
        link = item.select_one("a.woocommerce-LoopProduct-link, a[href]")
        if not link:
            continue

        url = link.get("href", "")
        if not url or url == "#":
            continue
        if not url.startswith("http"):
            url = BASE_URL + url

        # Skip non-product URLs (category pages, etc.)
        if any(skip in url for skip in ["/product-category/", "/page/", "#"]):
            continue

        title_el = item.select_one(
            ".woocommerce-loop-product__title, .product-title, h2, h3"
        )
        title = title_el.get_text(strip=True) if title_el else ""

        price_el = item.select_one(".price, .woocommerce-Price-amount")
        price = price_el.get_text(strip=True) if price_el else ""

        img_el = item.select_one("img")
        thumbnail = img_el.get("src", "") if img_el else ""

        products.append({
            "url": url,
            "title": title,
            "price_listing": price,
            "thumbnail": thumbnail,
        })

    return products


def get_next_page_url(soup, current_url):
    """Find the next page URL from pagination."""
    next_link = soup.select_one(
        "a.next.page-numbers, .pagination a.next, .woocommerce-pagination a.next"
    )
    if next_link:
        href = next_link.get("href", "")
        if href and href != "#":
            return href if href.startswith("http") else BASE_URL + href
    return None


def parse_product_page(soup, url):
    """Extract detailed rug data from an individual product page."""
    data = {"url": url}

    # Title
    title_el = soup.select_one(
        "h1.product_title, h1.entry-title, .product-title h1, h1"
    )
    data["title"] = title_el.get_text(strip=True) if title_el else ""

    # Rug number
    data["rug_number"] = extract_rug_number(url, data["title"])

    # Price
    price_el = soup.select_one(
        ".price .woocommerce-Price-amount, .summary .price, p.price"
    )
    if price_el:
        price_text = price_el.get_text(strip=True)
        data["price"] = price_text
    else:
        data["price"] = ""

    # Short description / excerpt
    excerpt_el = soup.select_one(
        ".woocommerce-product-details__short-description, "
        ".product-short-description, .summary .description"
    )
    data["short_description"] = (
        excerpt_el.get_text(strip=True) if excerpt_el else ""
    )

    # Full description
    desc_el = soup.select_one(
        ".woocommerce-Tabs-panel--description, "
        "#tab-description, .product-description"
    )
    data["full_description"] = desc_el.get_text(strip=True) if desc_el else ""

    # Product meta / attributes (size, origin, material, etc.)
    # WooCommerce stores these in product_meta or additional info table
    data["origin"] = ""
    data["size"] = ""
    data["material"] = ""
    data["age"] = ""
    data["colors"] = ""
    data["style"] = ""

    # Try WooCommerce additional information table
    attr_rows = soup.select(
        ".woocommerce-product-attributes tr, "
        ".shop_attributes tr, "
        ".additional-information tr"
    )
    for row in attr_rows:
        label_el = row.select_one("th, .woocommerce-product-attributes-item__label")
        value_el = row.select_one("td, .woocommerce-product-attributes-item__value")
        if not label_el or not value_el:
            continue
        label = label_el.get_text(strip=True).lower()
        value = value_el.get_text(strip=True)

        if "origin" in label or "country" in label:
            data["origin"] = value
        elif "size" in label or "dimension" in label:
            data["size"] = value
        elif "material" in label or "composition" in label:
            data["material"] = value
        elif "age" in label or "period" in label or "circa" in label:
            data["age"] = value
        elif "color" in label:
            data["colors"] = value
        elif "style" in label or "design" in label or "pattern" in label:
            data["style"] = value

    # Try product meta (tags, categories)
    meta_el = soup.select_one(".product_meta")
    if meta_el:
        sku_el = meta_el.select_one(".sku")
        if sku_el and not data["rug_number"]:
            data["rug_number"] = sku_el.get_text(strip=True)

        cat_el = meta_el.select_one(".posted_in")
        data["categories"] = cat_el.get_text(strip=True) if cat_el else ""

        tag_el = meta_el.select_one(".tagged_as")
        data["tags"] = tag_el.get_text(strip=True) if tag_el else ""
    else:
        data["categories"] = ""
        data["tags"] = ""

    # Fallback: parse details from description text
    combined_text = data["short_description"] + " " + data["full_description"]
    if not data["size"]:
        size_match = re.search(
            r"(\d+[\s\']?\s*(?:ft|feet|foot)[\s.,]*\d*[\s\"]?\s*(?:in|inch|inches)?)"
            r"\s*[xX×]\s*"
            r"(\d+[\s\']?\s*(?:ft|feet|foot)[\s.,]*\d*[\s\"]?\s*(?:in|inch|inches)?)",
            combined_text,
        )
        if size_match:
            data["size"] = size_match.group(0).strip()
    if not data["origin"]:
        origin_match = re.search(
            r"(?:from|origin|woven in|made in)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)",
            combined_text,
        )
        if origin_match:
            data["origin"] = origin_match.group(1)

    # Main product image
    img_el = soup.select_one(
        ".woocommerce-product-gallery__image img, "
        ".product-image img, "
        ".wp-post-image"
    )
    data["image_url"] = img_el.get("src", "") if img_el else ""

    # Try JSON-LD structured data
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            ld = json.loads(script.string)
            if isinstance(ld, dict) and ld.get("@type") == "Product":
                if not data["title"]:
                    data["title"] = ld.get("name", "")
                if not data["price"]:
                    offers = ld.get("offers", {})
                    if isinstance(offers, dict):
                        data["price"] = offers.get("price", "")
                if not data["image_url"]:
                    data["image_url"] = ld.get("image", "")
                if not data["rug_number"]:
                    data["rug_number"] = ld.get("sku", "")
                if not data["full_description"]:
                    data["full_description"] = ld.get("description", "")
        except (json.JSONDecodeError, TypeError):
            continue

    return data


def scrape_category(scraper, category_path):
    """Scrape all product URLs from a category, handling pagination."""
    product_urls = []
    url = BASE_URL + category_path
    page_num = 0

    print(f"\n  Scraping category: {category_path}")

    while url and page_num < MAX_PAGES_PER_CATEGORY:
        page_num += 1
        print(f"    Page {page_num}: {url}")

        try:
            resp = scraper.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"    Error fetching page {page_num}: {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        products = parse_listing_page(soup)

        if not products:
            print(f"    No products found on page {page_num}, stopping.")
            break

        for p in products:
            if p["url"] not in [u["url"] for u in product_urls]:
                product_urls.append(p)

        print(f"    Found {len(products)} products (total unique: {len(product_urls)})")

        url = get_next_page_url(soup, url)
        if url:
            time.sleep(REQUEST_DELAY)

    return product_urls


def scrape_product_details(scraper, product_info):
    """Fetch and parse a single product page."""
    url = product_info["url"]

    try:
        resp = scraper.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"    Error fetching {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    data = parse_product_page(soup, url)

    # Merge listing-level data as fallback
    if not data["title"] and product_info.get("title"):
        data["title"] = product_info["title"]
    if not data["price"] and product_info.get("price_listing"):
        data["price"] = product_info["price_listing"]

    return data


def main():
    print("=" * 55)
    print("NAZMIYAL ANTIQUE RUGS SCRAPER")
    print("=" * 55)
    print(f"Target: {BASE_URL}")
    print(f"Categories: {len(CATEGORY_URLS)}")

    scraper = create_scraper()

    # Phase 1: Collect product URLs from category pages
    print("\n--- Phase 1: Collecting product URLs ---")
    all_products = []
    seen_urls = set()

    for cat_path in CATEGORY_URLS:
        products = scrape_category(scraper, cat_path)
        for p in products:
            if p["url"] not in seen_urls:
                seen_urls.add(p["url"])
                p["source_category"] = cat_path
                all_products.append(p)
        time.sleep(REQUEST_DELAY)

    print(f"\nTotal unique product URLs: {len(all_products)}")

    if not all_products:
        print("No products found! The site may be blocking requests.")
        print("Try running again later or using a VPN.")
        return

    # Phase 2: Scrape individual product pages
    print("\n--- Phase 2: Scraping product details ---")
    detailed_rugs = []

    for i, product in enumerate(all_products, 1):
        print(f"  [{i}/{len(all_products)}] {product['url'][:70]}...")

        data = scrape_product_details(scraper, product)
        if data:
            data["source_category"] = product.get("source_category", "")
            detailed_rugs.append(data)

        if i % 10 == 0:
            print(f"  Progress: {i}/{len(all_products)} scraped")

        time.sleep(REQUEST_DELAY)

    print(f"\nSuccessfully scraped: {len(detailed_rugs)} rugs")

    if not detailed_rugs:
        print("No rug details could be extracted!")
        return

    # Phase 3: Save to CSV
    print("\n--- Phase 3: Saving to CSV ---")
    fieldnames = [
        "rug_number", "title", "price", "size", "origin", "material",
        "age", "colors", "style", "categories", "tags",
        "short_description", "image_url", "url", "source_category",
    ]

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FILE)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(detailed_rugs)

    print(f"Saved: {path}")
    print(f"Total: {len(detailed_rugs)} rugs")

    # Show top 10 preview
    print("\n" + "=" * 55)
    print("PREVIEW (first 10 rugs):")
    print("=" * 55)
    for r in detailed_rugs[:10]:
        title = r["title"][:50] + "..." if len(r["title"]) > 50 else r["title"]
        print(f"  #{r['rug_number'] or 'N/A':>6} | {title}")
        details = []
        if r["price"]:
            details.append(f"Price: {r['price']}")
        if r["size"]:
            details.append(f"Size: {r['size']}")
        if r["origin"]:
            details.append(f"Origin: {r['origin']}")
        if details:
            print(f"         | {' | '.join(details)}")


if __name__ == "__main__":
    main()
