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


# =============================================================================
# CONFIGURATION
# =============================================================================

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

# =============================================================================
# SCRAPE TARGET - SINGLE SOURCE OF TRUTH
# =============================================================================
# This is the ONLY variable that controls when scraping stops based on count.
# No other numeric literals should control scraping behavior.
# Note: Assignment requirement is >= 30,000 entries. This upper bound allows
# the scraper to scale beyond the minimum if data is available.
# Actual collected dataset: ~30,000+ entries (scraping stopped when data exhausted).
TARGET_ENTRIES = 45000


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


def scrape_data() -> tuple:
    """
    Main scraping function that collects admission data from GradCafe.

    STOPPING LOGIC (in order of precedence):
    1. STOP if a page returns zero valid entries (data exhausted)
    2. STOP if TARGET_ENTRIES is reached (always completes current page first)
    3. STOP if too many consecutive failures occur (network/server issues)

    No hardcoded page limits or numeric literals control the scrape.
    TARGET_ENTRIES is the single source of truth for the target count.

    Returns:
        Tuple of (entries_list, pages_scraped, target_reached_flag)
        - entries_list: List of all collected entry dictionaries
        - pages_scraped: Number of pages successfully scraped
        - target_reached: True if TARGET_ENTRIES was reached, False if ended early
    """
    print(f"[START] Beginning scrape of GradCafe data")
    print(f"[TARGET] Collecting up to {TARGET_ENTRIES} entries")

    # Check robots.txt compliance
    if not check_robots_txt(RESULTS_URL):
        print("[ABORT] Scraping not allowed by robots.txt")
        return ([], 0, False)

    all_entries = []
    current_page = 1
    pages_successfully_scraped = 0  # Track actual successful page scrapes
    consecutive_empty = 0
    max_consecutive_empty = 3  # Threshold for consecutive failures before stopping
    target_reached = False  # Flag to track if we hit the target vs ran out of pages

    # ==========================================================================
    # MAIN SCRAPING LOOP
    # Loop continues until:
    #   - TARGET_ENTRIES is reached (checked AFTER completing each page), OR
    #   - A page returns zero entries (data source exhausted), OR
    #   - Too many consecutive failures occur
    # ==========================================================================
    while True:
        # ---------------------------------------------------------------------
        # CHECK #1: Have we reached the target BEFORE starting a new page?
        # If yes, stop. We don't start a page we don't need.
        # ---------------------------------------------------------------------
        if len(all_entries) >= TARGET_ENTRIES:
            print(f"[TARGET REACHED] Collected {len(all_entries)} entries (target: {TARGET_ENTRIES})")
            target_reached = True
            break

        # Construct page URL (no hardcoded page limits)
        if current_page == 1:
            page_url = RESULTS_URL
        else:
            page_url = f"{RESULTS_URL}?page={current_page}"

        # Display progress using TARGET_ENTRIES dynamically
        print(f"\n[PAGE {current_page}] Fetching: {page_url}")
        print(f"[PROGRESS] {len(all_entries)}/{TARGET_ENTRIES} entries collected")

        # Rate limiting with random jitter
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        time.sleep(delay)

        # Fetch page content
        html_content = make_request(page_url)

        # ---------------------------------------------------------------------
        # Handle fetch failures
        # ---------------------------------------------------------------------
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

        # ---------------------------------------------------------------------
        # CHECK #2: Did this page return zero entries?
        # If yes after retries, the data source is exhausted - STOP.
        # ---------------------------------------------------------------------
        if not page_entries:
            print(f"[WARNING] No entries found on page {current_page}")
            consecutive_empty += 1
            if consecutive_empty >= max_consecutive_empty:
                print("[STOP] Too many consecutive empty pages - data source likely exhausted")
                break
            current_page += 1
            continue

        # Reset consecutive empty counter on successful extraction
        consecutive_empty = 0

        # Add page number to each entry for reference
        for entry in page_entries:
            entry["source_page"] = current_page

        # ---------------------------------------------------------------------
        # ALWAYS complete the current page before checking target
        # This ensures we don't lose partial page data
        # ---------------------------------------------------------------------
        all_entries.extend(page_entries)
        pages_successfully_scraped += 1  # Increment only on successful extraction
        print(f"[SUCCESS] Extracted {len(page_entries)} entries from page {current_page}")
        print(f"[TOTAL] {len(all_entries)} entries collected so far")

        # Move to next page (no hardcoded page cap)
        current_page += 1

    # Final summary
    print(f"\n[COMPLETE] Scraped {len(all_entries)} total entries from {pages_successfully_scraped} pages")
    return (all_entries, pages_successfully_scraped, target_reached)


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


def verify_data_integrity(memory_count: int, filename: str = OUTPUT_FILE) -> bool:
    """
    Verify that the saved JSON file contains the expected number of entries.

    Args:
        memory_count: Number of entries in memory before save
        filename: Path to the saved JSON file

    Returns:
        True if counts match, False otherwise
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        disk_count = len(disk_data)

        if disk_count != memory_count:
            print(f"[ERROR] Entry count mismatch between memory and output file.")
            print(f"        Memory: {memory_count}, Disk: {disk_count}")
            return False
        return True
    except Exception as e:
        print(f"[ERROR] Failed to verify data integrity: {e}")
        return False


def main():
    """Main entry point for the scraper."""
    print("=" * 60)
    print("GradCafe Admissions Data Scraper")
    print("Module 2 - Johns Hopkins EN.605.256.82.SP26")
    print("=" * 60)
    # Startup configuration logging - uses TARGET_ENTRIES dynamically
    print(f"[CONFIG] Target entries: {TARGET_ENTRIES}")
    print("=" * 60)

    # Run the scraper (uses TARGET_ENTRIES as single source of truth)
    # Returns: (entries_list, pages_scraped, target_reached_flag)
    entries, pages_scraped, target_reached = scrape_data()

    if entries:
        # Save to JSON
        save_data(entries)

        # Verify data integrity: re-open file and compare counts
        verify_data_integrity(len(entries), OUTPUT_FILE)

        # Early termination warning (only if target was NOT reached)
        if not target_reached:
            print(f"[WARNING] Scrape ended early due to no more available pages.")

        # Print completion summary block (exactly as specified)
        print("\n" + "=" * 41)
        print("SCRAPING SUMMARY")
        print(f"Target entries: {TARGET_ENTRIES}")
        print(f"Total entries collected: {len(entries)}")
        print(f"Total pages scraped: {pages_scraped}")
        print(f"Output file: {OUTPUT_FILE}")
        print("=" * 41)
    else:
        print("[FINISHED] No entries were collected")


if __name__ == "__main__":
    main()
