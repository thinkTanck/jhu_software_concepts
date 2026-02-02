#!/usr/bin/env python3
"""
GradCafe Admissions Data Scraper

This module scrapes graduate school admissions data from TheGradCafe.com,
respecting robots.txt and implementing proper rate limiting and retry logic.

Module 2 Assignment - Johns Hopkins EN.605.256.82.SP26
"""

import json
import re
import time
import random
from urllib import request, parse, error, robotparser
from bs4 import BeautifulSoup
from typing import Optional


# Configuration
BASE_URL = "https://www.thegradcafe.com"
RESULTS_URL = f"{BASE_URL}/survey"
ROBOTS_URL = f"{BASE_URL}/robots.txt"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
OUTPUT_FILE = "applicant_data.json"

# Rate limiting configuration
MIN_DELAY = 1.0  # Minimum seconds between requests
MAX_DELAY = 3.0  # Maximum seconds between requests
MAX_RETRIES = 5  # Maximum retry attempts for failed requests
RETRY_BACKOFF = 2  # Exponential backoff multiplier

# Target number of entries
TARGET_ENTRIES = 30000
ENTRIES_PER_PAGE = 25  # Approximate entries per page on GradCafe


def check_robots_txt(url: str) -> bool:
    """
    Check if scraping the given URL is allowed by robots.txt.

    Args:
        url: The URL to check against robots.txt rules

    Returns:
        True if scraping is allowed, False otherwise
    """
    rp = robotparser.RobotFileParser()
    rp.set_url(ROBOTS_URL)

    try:
        rp.read()
        can_fetch = rp.can_fetch(USER_AGENT, url)
        print(f"[ROBOTS.TXT] Checking {url}")
        print(f"[ROBOTS.TXT] Can fetch: {can_fetch}")
        return can_fetch
    except Exception as e:
        print(f"[ROBOTS.TXT] Error reading robots.txt: {e}")
        # If we can't read robots.txt, we should be cautious
        # For this assignment, we'll proceed but log the issue
        print("[ROBOTS.TXT] Proceeding with caution...")
        return True


def make_request(url: str, retry_count: int = 0) -> Optional[str]:
    """
    Make an HTTP request with proper headers and retry logic.

    Args:
        url: The URL to fetch
        retry_count: Current retry attempt number

    Returns:
        Response content as string, or None if all retries failed
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "identity",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    req = request.Request(url, headers=headers)

    try:
        with request.urlopen(req, timeout=30) as response:
            return response.read().decode("utf-8", errors="replace")
    except error.HTTPError as e:
        if e.code in (429, 500, 502, 503, 504):
            if retry_count < MAX_RETRIES:
                wait_time = (RETRY_BACKOFF ** retry_count) * MIN_DELAY
                print(f"[RETRY] HTTP {e.code} error. Waiting {wait_time:.1f}s before retry {retry_count + 1}/{MAX_RETRIES}")
                time.sleep(wait_time)
                return make_request(url, retry_count + 1)
            else:
                print(f"[ERROR] Max retries exceeded for {url}")
                return None
        else:
            print(f"[ERROR] HTTP error {e.code}: {e.reason}")
            return None
    except error.URLError as e:
        if retry_count < MAX_RETRIES:
            wait_time = (RETRY_BACKOFF ** retry_count) * MIN_DELAY
            print(f"[RETRY] URL error: {e.reason}. Waiting {wait_time:.1f}s before retry {retry_count + 1}/{MAX_RETRIES}")
            time.sleep(wait_time)
            return make_request(url, retry_count + 1)
        else:
            print(f"[ERROR] Max retries exceeded for {url}")
            return None
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return None


def parse_entry(row) -> Optional[dict]:
    """
    Parse a single admission entry row from the HTML.

    Args:
        row: BeautifulSoup element representing a table row or card

    Returns:
        Dictionary containing parsed entry data, or None if parsing fails
    """
    try:
        entry = {}

        # Extract institution/program info
        # GradCafe structure varies, so we try multiple selectors
        institution_elem = row.select_one(".institution, .school, [class*='school'], [class*='institution']")
        if institution_elem:
            entry["institution"] = institution_elem.get_text(strip=True)

        program_elem = row.select_one(".program, .major, [class*='program'], [class*='major']")
        if program_elem:
            entry["program"] = program_elem.get_text(strip=True)

        # Extract decision status
        decision_elem = row.select_one(".decision, .status, [class*='decision'], [class*='status']")
        if decision_elem:
            entry["decision"] = decision_elem.get_text(strip=True)

        # Extract date
        date_elem = row.select_one(".date, [class*='date'], time")
        if date_elem:
            entry["date_added"] = date_elem.get_text(strip=True)

        # Extract additional details (GPA, GRE, etc.)
        details_elem = row.select_one(".details, .extra, [class*='detail']")
        if details_elem:
            entry["details"] = details_elem.get_text(strip=True)

        # Extract comments/notes
        comments_elem = row.select_one(".comments, .notes, [class*='comment'], [class*='note']")
        if comments_elem:
            entry["comments"] = comments_elem.get_text(strip=True)

        # If we couldn't find specific fields, try to extract all text content
        if not entry:
            # Get all text from the row and store as raw_content
            all_text = row.get_text(separator=" | ", strip=True)
            if all_text:
                entry["raw_content"] = all_text

        # Also store the raw HTML for later processing if needed
        entry["raw_html"] = str(row)

        return entry if entry else None

    except Exception as e:
        print(f"[PARSE] Error parsing entry: {e}")
        return None


def extract_entries_from_page(html_content: str) -> list:
    """
    Extract all admission entries from a page's HTML content.

    Args:
        html_content: Raw HTML string of the page

    Returns:
        List of parsed entry dictionaries
    """
    entries = []
    soup = BeautifulSoup(html_content, "html.parser")

    # Try various selectors that GradCafe might use
    # The site structure may vary, so we try multiple approaches
    selectors = [
        "table.results tbody tr",
        "table tbody tr",
        ".result-row",
        ".survey-result",
        "[class*='result']",
        ".card",
        "article",
    ]

    rows = []
    for selector in selectors:
        rows = soup.select(selector)
        if rows:
            print(f"[PARSE] Found {len(rows)} entries using selector: {selector}")
            break

    # If no specific rows found, try to find any structured data
    if not rows:
        # Look for any repeating elements that might contain data
        rows = soup.find_all("div", class_=re.compile(r"(result|entry|row|item)", re.I))

    for row in rows:
        entry = parse_entry(row)
        if entry:
            entries.append(entry)

    return entries


def get_next_page_url(html_content: str, current_page: int) -> Optional[str]:
    """
    Extract the URL for the next page of results.

    Args:
        html_content: Raw HTML string of the current page
        current_page: Current page number

    Returns:
        URL string for the next page, or None if no next page
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Try to find next page link
    next_link = soup.select_one("a.next, a[rel='next'], .pagination a.next, [class*='next'] a")
    if next_link and next_link.get("href"):
        href = next_link.get("href")
        if href.startswith("http"):
            return href
        else:
            return parse.urljoin(BASE_URL, href)

    # Try to construct next page URL based on pagination pattern
    # GradCafe often uses ?page=N or /page/N patterns
    next_page = current_page + 1

    # Check for pagination links to understand the pattern
    page_links = soup.select(".pagination a, [class*='page'] a")
    for link in page_links:
        href = link.get("href", "")
        # Look for page number pattern
        if re.search(r"[?&]page=\d+", href):
            # URL uses query parameter
            return f"{RESULTS_URL}?page={next_page}"
        elif re.search(r"/page/\d+", href):
            # URL uses path segment
            return f"{RESULTS_URL}/page/{next_page}"

    # Default to query parameter approach
    return f"{RESULTS_URL}?page={next_page}"


def scrape_data(max_entries: int = TARGET_ENTRIES) -> list:
    """
    Main scraping function that collects admission data from GradCafe.

    Args:
        max_entries: Maximum number of entries to collect

    Returns:
        List of all collected entry dictionaries
    """
    print(f"[START] Beginning scrape of GradCafe data")
    print(f"[TARGET] Collecting up to {max_entries} entries")

    # Check robots.txt compliance
    if not check_robots_txt(RESULTS_URL):
        print("[ABORT] Scraping not allowed by robots.txt")
        return []

    all_entries = []
    current_page = 1
    consecutive_empty = 0
    max_consecutive_empty = 3

    while len(all_entries) < max_entries:
        # Construct page URL
        if current_page == 1:
            page_url = RESULTS_URL
        else:
            page_url = f"{RESULTS_URL}?page={current_page}"

        print(f"\n[PAGE {current_page}] Fetching: {page_url}")
        print(f"[PROGRESS] {len(all_entries)}/{max_entries} entries collected")

        # Rate limiting with random jitter
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        time.sleep(delay)

        # Fetch page content
        html_content = make_request(page_url)

        if html_content is None:
            print(f"[ERROR] Failed to fetch page {current_page}")
            consecutive_empty += 1
            if consecutive_empty >= max_consecutive_empty:
                print("[STOP] Too many consecutive failures, stopping scrape")
                break
            current_page += 1
            continue

        # Parse entries from page
        page_entries = extract_entries_from_page(html_content)

        if not page_entries:
            print(f"[WARNING] No entries found on page {current_page}")
            consecutive_empty += 1
            if consecutive_empty >= max_consecutive_empty:
                print("[STOP] Too many consecutive empty pages, stopping scrape")
                break
        else:
            consecutive_empty = 0
            # Add page number to each entry for reference
            for entry in page_entries:
                entry["source_page"] = current_page
            all_entries.extend(page_entries)
            print(f"[SUCCESS] Extracted {len(page_entries)} entries from page {current_page}")

        current_page += 1

        # Safety check for maximum pages
        max_pages = (max_entries // ENTRIES_PER_PAGE) + 100
        if current_page > max_pages:
            print(f"[STOP] Reached maximum page limit ({max_pages})")
            break

    print(f"\n[COMPLETE] Scraped {len(all_entries)} total entries from {current_page - 1} pages")
    return all_entries


def save_data(entries: list, filename: str = OUTPUT_FILE) -> bool:
    """
    Save scraped entries to a JSON file.

    Args:
        entries: List of entry dictionaries to save
        filename: Output filename

    Returns:
        True if save successful, False otherwise
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        print(f"[SAVED] {len(entries)} entries written to {filename}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save data: {e}")
        return False


def main():
    """Main entry point for the scraper."""
    print("=" * 60)
    print("GradCafe Admissions Data Scraper")
    print("Module 2 - Johns Hopkins EN.605.256.82.SP26")
    print("=" * 60)

    # Run the scraper
    entries = scrape_data()

    if entries:
        # Save to JSON
        save_data(entries)

        # Print summary
        print("\n" + "=" * 60)
        print("SCRAPING SUMMARY")
        print("=" * 60)
        print(f"Total entries collected: {len(entries)}")
        print(f"Output file: {OUTPUT_FILE}")
    else:
        print("[FINISHED] No entries were collected")


if __name__ == "__main__":
    main()
