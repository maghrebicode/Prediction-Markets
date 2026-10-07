"""
Find independent cafés in Hennepin and Ramsey County, Minnesota, and collect
their public contact emails.

How it works, step by step:
  1. Ask OpenStreetMap (via the free Overpass API) for every amenity=cafe and
     shop=coffee inside the two counties.
  2. Pull out name, address, city, phone, website, email and brand for each.
  3. Drop chains (anything with a brand tag, a fixed list of chain names, and
     any name that shows up at more than 2 addresses).
  4. Drop cafés you have already contacted.
  5. Visit each café's website (homepage, /contact, /about, /contact-us) and
     look for email addresses.
  6. Save the results to cafes_with_emails.csv, cafés with emails first.
  7. Print a short summary.

Usage:
  python cafe_emails.py --test   # Minneapolis only, prints 5 results
  python cafe_emails.py          # full run, both counties
"""

import argparse
import csv
import re
import sys
import time
import unicodedata
from collections import defaultdict
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

CHAIN_NAMES = [
    "Starbucks", "Caribou", "Dunn Brothers", "Five Watt", "Peet's", "Panera",
    "Dutch Bros", "Biggby", "Scooter's", "Ziggi's", "Tim Hortons", "Dunkin'",
    "Tous Les Jours", "Toastique", "Qamaria", "Haraz",
]

ALREADY_CONTACTED = [
    "Red Coral", "Take Care Coffee", "Roots Cafe", "MÖV Marketplace",
    "Cafe Alma", "Alma Provisions", "Gray Fox Cafe", "Golden Thyme", "barra",
    "Finnish Bistro", "Smith Coffee", "Caydence Records",
]

EXTRA_PAGES = ["/contact", "/about", "/contact-us"]
REQUEST_DELAY = 1   # seconds between web requests
REQUEST_TIMEOUT = 10  # give up on a site after this many seconds
HEADERS = {"User-Agent": "Mozilla/5.0 (independent cafe contact finder)"}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
JUNK_EMAIL_PARTS = [
    "sentry", "wix", "squarespace", "noreply", "no-reply", "donotreply",
    "example.com", "domain.com", "yourdomain", "email.com",
]
IMAGE_ENDINGS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp")


# ---------------------------------------------------------------------------
# Step 1: ask OpenStreetMap for cafés
# ---------------------------------------------------------------------------

def build_query(test_mode):
    """Build the Overpass query. Test mode searches only Minneapolis."""
    if test_mode:
        areas = 'area["name"="Minneapolis"]["admin_level"="8"]->.a;'
    else:
        areas = (
            'area["name"="Minnesota"]["admin_level"="4"]->.mn;'
            '(area["name"="Hennepin County"]["admin_level"="6"](area.mn);'
            ' area["name"="Ramsey County"]["admin_level"="6"](area.mn);)->.a;'
        )
    return f"""
[out:json][timeout:180];
{areas}
(
  nwr["amenity"="cafe"](area.a);
  nwr["shop"="coffee"](area.a);
);
out center tags;
"""


def fetch_cafes(test_mode):
    query = build_query(test_mode)
    for url in OVERPASS_URLS:
        try:
            print(f"  Asking {url} ...")
            resp = requests.post(url, data={"data": query}, headers=HEADERS, timeout=200)
            resp.raise_for_status()
            return resp.json()["elements"]
        except Exception as e:
            print(f"  That server failed ({e}); trying the next one.")
    sys.exit("Could not reach any Overpass server.")


# ---------------------------------------------------------------------------
# Step 2: pull out the fields we care about
# ---------------------------------------------------------------------------

def parse_cafe(el):
    t = el.get("tags", {})
    street = " ".join(p for p in [t.get("addr:housenumber"), t.get("addr:street")] if p)
    if street and t.get("addr:unit"):
        street += f" #{t['addr:unit']}"
    website = t.get("website") or t.get("contact:website") or ""
    if website and not website.startswith("http"):
        website = "http://" + website
    return {
        "osm_id": f"{el['type']}/{el['id']}",
        "name": t.get("name", "").strip(),
        "address": street,
        "city": t.get("addr:city", ""),
        "phone": t.get("phone") or t.get("contact:phone") or "",
        "website": website,
        "email": t.get("email") or t.get("contact:email") or "",
        "brand": t.get("brand", ""),
    }


# ---------------------------------------------------------------------------
# Steps 3 and 4: remove chains and cafés already contacted
# ---------------------------------------------------------------------------

def normalize(name):
    """Lowercase, strip accents and punctuation: "MÖV Café" -> "mov cafe"."""
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = re.sub(r"[^a-z0-9 ]", "", name.lower().replace("&", " and "))
    return " ".join(name.split())


def name_matches(name, phrases):
    """True if any phrase appears in the name as whole words."""
    padded = f" {normalize(name)} "
    return any(f" {normalize(p)} " in padded for p in phrases)


def filter_cafes(cafes):
    # Count how many different addresses each name appears at.
    addresses = defaultdict(set)
    for c in cafes:
        addresses[normalize(c["name"])].add(c["address"] or c["osm_id"])

    kept, seen = [], set()
    for c in cafes:
        if not c["name"]:
            continue  # no name, nothing to contact
        if c["brand"]:
            continue  # has a brand tag -> chain
        if name_matches(c["name"], CHAIN_NAMES):
            continue
        if len(addresses[normalize(c["name"])]) > 2:
            continue  # same name at 3+ addresses -> chain
        if name_matches(c["name"], ALREADY_CONTACTED):
            continue
        key = (normalize(c["name"]), c["address"])
        if key in seen:
            continue  # same café mapped twice (e.g. as both a point and a building)
        seen.add(key)
        kept.append(c)
    return kept


# ---------------------------------------------------------------------------
# Step 5: look for emails on café websites
# ---------------------------------------------------------------------------

def is_good_email(email):
    e = email.lower()
    if e.endswith(IMAGE_ENDINGS) or re.search(r"@\d+x\.", e):
        return False  # image filenames like logo@2x.png
    return not any(junk in e for junk in JUNK_EMAIL_PARTS)


def emails_from_html(html):
    """Find emails in mailto: links first, then anywhere in the page text."""
    soup = BeautifulSoup(html, "html.parser")
    found = []
    for a in soup.select('a[href^="mailto:"]'):
        addr = a["href"][7:].split("?")[0].strip()
        found += EMAIL_RE.findall(addr)
    found += EMAIL_RE.findall(soup.get_text(" "))
    result = []
    for e in found:
        e = e.strip(".").lower()
        if is_good_email(e) and e not in result:
            result.append(e)
    return result


def scrape_site(website):
    """Return (email, page_url) for the first email found, or ("", "")."""
    base = f"{urlparse(website).scheme}://{urlparse(website).netloc}"
    pages = [website] + [urljoin(base, p) for p in EXTRA_PAGES]
    for page in pages:
        time.sleep(REQUEST_DELAY)
        try:
            resp = requests.get(page, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        except requests.Timeout:
            print(f"    {page} took over {REQUEST_TIMEOUT}s; skipping this site.")
            return "", ""
        except requests.RequestException:
            if page == website:
                return "", ""  # homepage unreachable, don't bother with the rest
            continue
        if resp.status_code != 200 or "html" not in resp.headers.get("Content-Type", ""):
            continue
        emails = emails_from_html(resp.text)
        if emails:
            return emails[0], page
    return "", ""


# ---------------------------------------------------------------------------
# Steps 6 and 7: save and summarize
# ---------------------------------------------------------------------------

COLUMNS = ["name", "address", "city", "phone", "website", "email", "where_email_found"]


def save_csv(cafes, path):
    cafes = sorted(cafes, key=lambda c: (not c["email"], c["name"].lower()))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(cafes)
    return cafes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Minneapolis only, 5 results")
    args = parser.parse_args()

    print("Step 1: Getting cafés from OpenStreetMap...")
    raw = fetch_cafes(args.test)
    print(f"  Got {len(raw)} raw results.")

    print("Step 2: Reading name, address, phone, website, email, brand...")
    cafes = [parse_cafe(el) for el in raw]

    print("Steps 3-4: Removing chains and cafés you've already contacted...")
    cafes = filter_cafes(cafes)
    print(f"  {len(cafes)} independent cafés left.")

    if args.test:
        cafes = cafes[:5]
        print("  Test mode: only checking the first 5.")

    print("Step 5: Checking websites for emails (1 second between requests)...")
    for i, c in enumerate(cafes, 1):
        if c["email"]:
            c["where_email_found"] = "OpenStreetMap"
        elif c["website"]:
            print(f"  [{i}/{len(cafes)}] {c['name']}: {c['website']}")
            c["email"], c["where_email_found"] = scrape_site(c["website"])
        else:
            c["where_email_found"] = ""

    out = "cafes_test.csv" if args.test else "cafes_with_emails.csv"
    print(f"Step 6: Saving to {out}...")
    cafes = save_csv(cafes, out)

    if args.test:
        print("\nTest results:")
        for c in cafes:
            print(f"  {c['name']} | {c['address']}, {c['city']} | {c['phone'] or '-'} | "
                  f"{c['website'] or '-'} | {c['email'] or '-'} ({c['where_email_found'] or 'none'})")

    with_email = sum(1 for c in cafes if c["email"])
    phone_only = sum(1 for c in cafes if not c["email"] and c["phone"])
    print("\nStep 7: Summary")
    print(f"  Independent cafés found: {len(cafes)}")
    print(f"  With an email:           {with_email}")
    print(f"  Phone only (no email):   {phone_only}")


if __name__ == "__main__":
    main()
