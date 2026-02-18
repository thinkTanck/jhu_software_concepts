#!/usr/bin/env python3
"""
GradCafe Data Cleaning Module

This module loads raw scraped applicant data, performs thorough cleaning,
and outputs a canonical JSON format with a strict, consistent schema.

Module 2 Assignment - Johns Hopkins EN.605.256.82.SP26

Pipeline:
    scrape.py  -->  raw_applicant_data.json  (raw, HTML allowed)
    clean.py   -->  applicant_data.json      (clean, canonical)

Output Contract:
- Output is a JSON array
- Every entry is a dictionary with identical keys
- All values are plain text (no HTML, no entities, no markup)
- Missing fields are empty strings, never omitted
"""

import html
import json
import re
from typing import List, Dict, Optional


# =============================================================================
# CONFIGURATION
# =============================================================================

# Input: raw scraped data (produced by scrape.py)
INPUT_FILE = "raw_applicant_data.json"

# Output: clean canonical data (consumed by llm_hosting/app.py)
OUTPUT_FILE = "applicant_data.json"

# Canonical schema - every output record will have exactly these keys
CANONICAL_SCHEMA = [
    "school",
    "program",
    "decision",
    "decision_date",
    "gpa",
    "gre",
    "notes",
]


# =============================================================================
# PRIVATE HELPER FUNCTIONS — TEXT CLEANING PIPELINE
# =============================================================================

def _strip_html_tags(text: str) -> str:
    """
    Remove all HTML tags from text.

    Args:
        text: String potentially containing HTML tags

    Returns:
        String with all HTML tags removed
    """
    if not text:
        return ""
    # Remove HTML tags (including self-closing and malformed)
    return re.sub(r"<[^>]*>", " ", text)


def _unescape_html_entities(text: str) -> str:
    """
    Convert HTML entities to their character equivalents.

    Args:
        text: String potentially containing HTML entities

    Returns:
        String with HTML entities converted to characters
    """
    if not text:
        return ""
    # Use Python's html.unescape for comprehensive entity handling
    return html.unescape(text)


def _collapse_whitespace(text: str) -> str:
    """
    Normalize all whitespace to single spaces and strip edges.

    Args:
        text: String with potentially irregular whitespace

    Returns:
        String with normalized whitespace
    """
    if not text:
        return ""
    # Replace any whitespace sequence with single space
    text = re.sub(r"\s+", " ", text)
    # Strip leading/trailing whitespace
    return text.strip()


def _clean_text(text: Optional[str]) -> str:
    """
    Apply full text cleaning pipeline to a single field value.

    This is the core cleaning function applied field-by-field.

    Pipeline:
    1. Convert to string (handle None/non-string)
    2. Remove HTML tags
    3. Unescape HTML entities
    4. Collapse whitespace

    Args:
        text: Raw field value (may be None, string, or other type)

    Returns:
        Clean plain text string
    """
    # Handle None and non-string types
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # Apply cleaning pipeline in order
    text = _strip_html_tags(text)
    text = _unescape_html_entities(text)
    text = _collapse_whitespace(text)

    return text


def _extract_from_raw_html(raw_html: str) -> Dict[str, str]:
    """
    Extract structured fields from raw HTML content using regex patterns.

    This handles cases where the scraper stored raw_html but couldn't
    extract specific fields during scraping.

    Args:
        raw_html: Raw HTML string from scraped entry

    Returns:
        Dictionary with extracted field values
    """
    extracted = {key: "" for key in CANONICAL_SCHEMA}

    if not raw_html:
        return extracted

    # Clean the HTML for text extraction
    text_content = _clean_text(raw_html)

    # Try to extract school/institution
    school_patterns = [
        r"(?:University|College|Institute|School)\s+of\s+[\w\s]+",
        r"[\w\s]+(?:University|College|Institute|School)",
        r"(?:MIT|UCLA|USC|NYU|CMU|CalTech|Stanford|Harvard|Yale|Princeton)",
    ]
    for pattern in school_patterns:
        match = re.search(pattern, text_content, re.IGNORECASE)
        if match:
            extracted["school"] = match.group(0).strip()
            break

    # Try to extract decision
    decision_match = re.search(
        r"\b(Accepted|Rejected|Waitlisted|Interview|Pending|Denied|Admitted)\b",
        text_content, re.IGNORECASE
    )
    if decision_match:
        extracted["decision"] = decision_match.group(1).strip()

    # Try to extract GPA
    gpa_match = re.search(r"\bGPA[:\s]*([0-9]\.[0-9]{1,2})\b", text_content, re.IGNORECASE)
    if gpa_match:
        extracted["gpa"] = gpa_match.group(1)

    # Try to extract GRE scores
    gre_patterns = [
        r"\bGRE[:\s]*(\d{3})[/\s]+(\d{3})",
        r"\bV[:\s]*(\d{3})[,\s]+Q[:\s]*(\d{3})",
    ]
    for pattern in gre_patterns:
        match = re.search(pattern, text_content, re.IGNORECASE)
        if match:
            extracted["gre"] = match.group(0).strip()
            break

    # Try to extract date
    date_patterns = [
        r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
        r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b",
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text_content, re.IGNORECASE)
        if match:
            extracted["decision_date"] = match.group(1).strip()
            break

    return extracted


def _map_entry_to_schema(entry: Dict) -> Dict[str, str]:
    """
    Map a raw scraped entry to the canonical schema.

    Handles various input field names and ensures output has
    exactly the canonical keys with cleaned values.

    Args:
        entry: Raw entry dictionary from scraper

    Returns:
        Dictionary with canonical schema keys and cleaned values
    """
    # Initialize with empty strings for all canonical fields
    cleaned = {key: "" for key in CANONICAL_SCHEMA}

    # Map input fields to canonical fields (apply _clean_text to each)

    # School/Institution
    for key in ["institution", "school", "university"]:
        if key in entry and entry[key]:
            cleaned["school"] = _clean_text(entry[key])
            break

    # Program
    for key in ["program", "major", "department", "degree"]:
        if key in entry and entry[key]:
            cleaned["program"] = _clean_text(entry[key])
            break

    # Decision
    for key in ["decision", "status", "result"]:
        if key in entry and entry[key]:
            cleaned["decision"] = _clean_text(entry[key])
            break

    # Decision date
    for key in ["date_added", "decision_date", "date", "notification_date"]:
        if key in entry and entry[key]:
            cleaned["decision_date"] = _clean_text(entry[key])
            break

    # GPA
    for key in ["gpa", "undergrad_gpa"]:
        if key in entry and entry[key]:
            cleaned["gpa"] = _clean_text(entry[key])
            break

    # GRE
    for key in ["gre", "gre_score", "gre_scores"]:
        if key in entry and entry[key]:
            cleaned["gre"] = _clean_text(entry[key])
            break

    # Notes/Comments - combine multiple potential sources
    notes_parts = []
    for key in ["comments", "notes", "details", "raw_content"]:
        if key in entry and entry[key]:
            cleaned_value = _clean_text(entry[key])
            if cleaned_value:
                notes_parts.append(cleaned_value)

    if notes_parts:
        cleaned["notes"] = " | ".join(notes_parts)
        # Truncate if too long
        if len(cleaned["notes"]) > 1000:
            cleaned["notes"] = cleaned["notes"][:1000] + "..."

    # If we have raw_html but missing critical fields, try to extract them
    if "raw_html" in entry and entry["raw_html"]:
        if not cleaned["school"] or not cleaned["program"] or not cleaned["decision"]:
            extracted = _extract_from_raw_html(entry["raw_html"])
            # Only fill in missing fields
            for key in CANONICAL_SCHEMA:
                if not cleaned[key] and extracted.get(key):
                    cleaned[key] = extracted[key]

    return cleaned


# =============================================================================
# PUBLIC API FUNCTIONS
# =============================================================================

def load_data(filename: str = INPUT_FILE) -> List[Dict]:
    """
    Load raw scraped applicant data from JSON file.

    Args:
        filename: Path to the JSON file containing raw scraped data

    Returns:
        List of entry dictionaries (may be empty on error)
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            print(f"[ERROR] Expected JSON array, got {type(data).__name__}")
            return []

        print(f"[LOADED] {len(data)} entries from {filename}")
        return data

    except FileNotFoundError:
        print(f"[ERROR] File not found: {filename}")
        print(f"[HINT] Run scrape.py first to generate {filename}")
        return []
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in {filename}: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Failed to load data: {e}")
        return []


def clean_data(entries: List[Dict]) -> List[Dict[str, str]]:
    """
    Clean all entries and enforce canonical schema.

    Output Contract:
    - Returns a list of dictionaries
    - Every dictionary has exactly the same keys (CANONICAL_SCHEMA)
    - All values are plain text strings (no HTML, no entities)
    - Missing values are empty strings, never None or omitted

    Args:
        entries: List of raw entry dictionaries from scraper

    Returns:
        List of cleaned entry dictionaries with canonical schema
    """
    print(f"[CLEAN] Processing {len(entries)} entries...")
    print(f"[SCHEMA] Enforcing canonical fields: {CANONICAL_SCHEMA}")

    cleaned_entries = []

    for i, entry in enumerate(entries):
        # Skip non-dict entries
        if not isinstance(entry, dict):
            print(f"[WARNING] Entry {i} is not a dictionary, skipping")
            continue

        # Map to canonical schema with cleaning
        cleaned = _map_entry_to_schema(entry)

        # Verify all keys are present (defensive check)
        for key in CANONICAL_SCHEMA:
            if key not in cleaned:
                cleaned[key] = ""

        cleaned_entries.append(cleaned)

        # Progress indicator
        if (i + 1) % 5000 == 0:
            print(f"[PROGRESS] Cleaned {i + 1}/{len(entries)} entries")

    print(f"[COMPLETE] Cleaned {len(cleaned_entries)} entries")
    return cleaned_entries


def save_data(entries: List[Dict], filename: str = OUTPUT_FILE) -> bool:
    """
    Save cleaned entries to a JSON file.

    Output is a JSON array with consistent formatting.

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


def _validate_output(filename: str) -> bool:
    """
    Validate that output file meets the canonical format requirements.

    Checks:
    1. Output is a JSON array
    2. All records share identical keys (exactly CANONICAL_SCHEMA)
    3. No HTML tags remain in any value

    Args:
        filename: Path to the output file to verify

    Returns:
        True if validation passes, False otherwise
    """
    print(f"\n[VALIDATE] Checking output file: {filename}")

    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[VALIDATE] FAIL: Cannot read output file: {e}")
        return False

    # Check 1: Output is a JSON array
    if not isinstance(data, list):
        print(f"[VALIDATE] FAIL: Output is not a JSON array (got {type(data).__name__})")
        return False

    if len(data) == 0:
        print(f"[VALIDATE] WARNING: Output is empty")
        return True

    # Check 2: All records have identical keys matching CANONICAL_SCHEMA
    expected_keys = set(CANONICAL_SCHEMA)
    issues = 0

    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            print(f"[VALIDATE] FAIL: Entry {i} is not a dictionary")
            issues += 1
            continue

        entry_keys = set(entry.keys())
        missing_keys = expected_keys - entry_keys
        extra_keys = entry_keys - expected_keys

        if missing_keys:
            print(f"[VALIDATE] FAIL: Entry {i} missing keys: {missing_keys}")
            issues += 1

        if extra_keys:
            print(f"[VALIDATE] FAIL: Entry {i} has extra keys: {extra_keys}")
            issues += 1

        # Check 3: No HTML tags in any value
        html_pattern = re.compile(r"<[^>]+>")
        for key, value in entry.items():
            if not isinstance(value, str):
                print(f"[VALIDATE] FAIL: Entry {i}, field '{key}' is not a string")
                issues += 1
            elif html_pattern.search(value):
                print(f"[VALIDATE] FAIL: Entry {i}, field '{key}' contains HTML tags")
                issues += 1

        # Stop after 10 issues to avoid spam
        if issues >= 10:
            print(f"[VALIDATE] Stopping after 10 issues...")
            break

    if issues > 0:
        print(f"[VALIDATE] FAIL: Found {issues} validation issues")
        return False

    print(f"[VALIDATE] PASS: Output is canonical JSON with {len(data)} valid entries")
    return True


def main():
    """Main entry point for the cleaning module."""
    print("=" * 60)
    print("GradCafe Data Cleaning Module")
    print("Module 2 - Johns Hopkins EN.605.256.82.SP26")
    print("=" * 60)
    print(f"[CONFIG] Input:  {INPUT_FILE} (raw scraped data)")
    print(f"[CONFIG] Output: {OUTPUT_FILE} (clean canonical data)")
    print("=" * 60)

    # Load raw scraped data
    raw_data = load_data()

    if not raw_data:
        print("[ABORT] No data to clean")
        return

    # Clean the data with strict schema enforcement
    cleaned_data = clean_data(raw_data)

    if not cleaned_data:
        print("[ABORT] No entries survived cleaning")
        return

    # Save cleaned data
    success = save_data(cleaned_data)

    if not success:
        print("[ABORT] Failed to save cleaned data")
        return

    # Validate output
    valid = _validate_output(OUTPUT_FILE)

    # Print summary
    print("\n" + "=" * 60)
    print("CLEANING SUMMARY")
    print("=" * 60)
    print(f"Input file:     {INPUT_FILE}")
    print(f"Input entries:  {len(raw_data)}")
    print(f"Output file:    {OUTPUT_FILE}")
    print(f"Output entries: {len(cleaned_data)}")
    print(f"Schema fields:  {CANONICAL_SCHEMA}")
    print(f"Validation:     {'PASSED' if valid else 'FAILED'}")
    print("=" * 60)

    if success and valid:
        print("\n[SUCCESS] Data is now in canonical format for LLM processing")
    else:
        print("\n[WARNING] Output may have issues - check validation errors above")


if __name__ == "__main__":
    main()
