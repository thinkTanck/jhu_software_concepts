#!/usr/bin/env python3
"""
GradCafe Data Cleaning Module

This module loads scraped applicant data, performs initial cleaning,
and prepares data for structured field extraction.

Module 2 Assignment - Johns Hopkins EN.605.256.82.SP26
"""

import json
import re
from typing import Optional


# Configuration
INPUT_FILE = "applicant_data.json"
OUTPUT_FILE = "cleaned_applicant_data.json"
EXTENDED_OUTPUT_FILE = "extended_applicant_data.json"


def load_data(filename: str = INPUT_FILE) -> list:
    """
    Load scraped applicant data from JSON file.

    Args:
        filename: Path to the JSON file containing scraped data

    Returns:
        List of entry dictionaries
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"[LOADED] {len(data)} entries from {filename}")
        return data
    except FileNotFoundError:
        print(f"[ERROR] File not found: {filename}")
        return []
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in {filename}: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Failed to load data: {e}")
        return []


def remove_html_tags(text: str) -> str:
    """
    Remove HTML tags from text content.

    Args:
        text: String potentially containing HTML tags

    Returns:
        Cleaned string with HTML tags removed
    """
    if not text:
        return ""

    # Remove HTML tags
    clean = re.sub(r"<[^>]+>", " ", text)

    # Remove HTML entities
    clean = re.sub(r"&nbsp;", " ", clean)
    clean = re.sub(r"&amp;", "&", clean)
    clean = re.sub(r"&lt;", "<", clean)
    clean = re.sub(r"&gt;", ">", clean)
    clean = re.sub(r"&quot;", '"', clean)
    clean = re.sub(r"&#\d+;", " ", clean)
    clean = re.sub(r"&[a-zA-Z]+;", " ", clean)

    return clean


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text content.

    Args:
        text: String with potentially irregular whitespace

    Returns:
        String with normalized whitespace
    """
    if not text:
        return ""

    # Replace various whitespace characters with single space
    clean = re.sub(r"[\t\n\r\f\v]+", " ", text)

    # Collapse multiple spaces into one
    clean = re.sub(r" +", " ", clean)

    # Strip leading/trailing whitespace
    clean = clean.strip()

    return clean


def clean_field(value) -> str:
    """
    Clean a single field value.

    Args:
        value: Field value (may be string, None, or other type)

    Returns:
        Cleaned string value
    """
    if value is None:
        return ""

    if not isinstance(value, str):
        value = str(value)

    # Apply cleaning steps
    value = remove_html_tags(value)
    value = normalize_whitespace(value)

    return value


def clean_entry(entry: dict) -> dict:
    """
    Clean a single data entry, preserving original fields.

    Args:
        entry: Dictionary containing entry data

    Returns:
        Cleaned entry dictionary with original fields preserved
    """
    cleaned = {}

    # List of fields to clean (text fields)
    text_fields = [
        "institution",
        "program",
        "decision",
        "date_added",
        "details",
        "comments",
        "raw_content",
    ]

    for key, value in entry.items():
        if key == "raw_html":
            # Preserve raw HTML for further processing but don't include in cleaned output
            cleaned["_raw_html"] = value
        elif key in text_fields:
            # Clean text fields
            cleaned[key] = clean_field(value)
            # Store original if different
            original = str(value) if value else ""
            if original != cleaned[key]:
                cleaned[f"_original_{key}"] = original
        else:
            # Preserve other fields as-is (e.g., source_page)
            cleaned[key] = value

    return cleaned


def clean_data(entries: list) -> list:
    """
    Clean all entries in the dataset.

    This function performs initial cleaning to remove HTML artifacts
    and normalize whitespace, preparing data for field extraction.

    Args:
        entries: List of raw entry dictionaries

    Returns:
        List of cleaned entry dictionaries
    """
    print(f"[CLEAN] Processing {len(entries)} entries...")

    cleaned_entries = []
    for i, entry in enumerate(entries):
        cleaned = clean_entry(entry)
        cleaned_entries.append(cleaned)

        # Progress indicator
        if (i + 1) % 1000 == 0:
            print(f"[PROGRESS] Cleaned {i + 1}/{len(entries)} entries")

    print(f"[COMPLETE] Cleaned {len(cleaned_entries)} entries")
    return cleaned_entries


def save_data(entries: list, filename: str = OUTPUT_FILE) -> bool:
    """
    Save cleaned entries to a JSON file.

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


def merge_extracted_output(original_entries: list, extracted_entries: list) -> list:
    """
    Merge extracted data back with original entries.

    This function combines the extracted fields with the original
    data while preserving all original fields.

    Args:
        original_entries: List of original cleaned entries
        extracted_entries: List of entries with extracted fields

    Returns:
        List of merged entries with both original and extracted fields
    """
    merged = []

    # Create index for faster lookup
    extracted_by_index = {i: entry for i, entry in enumerate(extracted_entries)}

    for i, original in enumerate(original_entries):
        entry = original.copy()

        if i in extracted_by_index:
            extracted_data = extracted_by_index[i]
            # Add extracted fields with prefix to distinguish
            for key, value in extracted_data.items():
                if key not in entry:
                    entry[f"parsed_{key}"] = value
                elif key.startswith("extracted_"):
                    entry[key] = value

        merged.append(entry)

    print(f"[MERGED] Combined {len(merged)} entries with extracted output")
    return merged


def prepare_for_extraction(entries: list) -> list:
    """
    Prepare cleaned data for field extraction processing.

    This function formats entries for the extraction tool to process,
    extracting structured fields from raw text content.

    Args:
        entries: List of cleaned entry dictionaries

    Returns:
        List of entries formatted for extraction input
    """
    extraction_ready = []

    for entry in entries:
        extraction_entry = {
            "raw_content": entry.get("raw_content", ""),
            "raw_html": entry.get("_raw_html", ""),
            # Include any fields already extracted as context
            "existing_fields": {
                k: v for k, v in entry.items()
                if not k.startswith("_") and k not in ["raw_content", "raw_html"]
            }
        }
        extraction_ready.append(extraction_entry)

    return extraction_ready


def validate_extracted_output(extracted_output: list, original_entries: list) -> bool:
    """
    Validate that extracted output preserves required original fields.

    Args:
        extracted_output: List of processed entries
        original_entries: List of original entries for comparison

    Returns:
        True if validation passes, False otherwise
    """
    if len(extracted_output) != len(original_entries):
        print(f"[VALIDATE] Warning: Entry count mismatch - "
              f"Extracted: {len(extracted_output)}, Original: {len(original_entries)}")
        return False

    # Check that original program/university are preserved
    required_fields = ["institution", "program"]
    issues = 0

    for i, (extracted_entry, orig_entry) in enumerate(zip(extracted_output, original_entries)):
        for field in required_fields:
            orig_value = orig_entry.get(field, "")
            extracted_value = extracted_entry.get(field, extracted_entry.get(f"parsed_{field}", ""))

            # Allow extraction to provide value if original was empty
            if orig_value and extracted_value and orig_value != extracted_value:
                print(f"[VALIDATE] Entry {i}: {field} mismatch")
                issues += 1

    if issues > 0:
        print(f"[VALIDATE] Found {issues} field preservation issues")
        return False

    print("[VALIDATE] Extracted output validation passed")
    return True


def main():
    """Main entry point for the cleaning module."""
    print("=" * 60)
    print("GradCafe Data Cleaning Module")
    print("Module 2 - Johns Hopkins EN.605.256.82.SP26")
    print("=" * 60)

    # Load raw scraped data
    raw_data = load_data()

    if not raw_data:
        print("[ABORT] No data to clean")
        return

    # Clean the data
    cleaned_data = clean_data(raw_data)

    # Save cleaned data
    save_data(cleaned_data)

    # Prepare for field extraction processing
    extraction_input = prepare_for_extraction(cleaned_data)
    save_data(extraction_input, "extraction_input.json")

    print("\n" + "=" * 60)
    print("CLEANING SUMMARY")
    print("=" * 60)
    print(f"Total entries processed: {len(cleaned_data)}")
    print(f"Cleaned output: {OUTPUT_FILE}")
    print(f"Extraction input prepared: extraction_input.json")
    print("\nNext steps:")
    print("1. Run the field extraction tool on extraction_input.json")
    print("2. The tool will extract structured fields via pattern matching")
    print("3. Merge results back using merge_extracted_output()")


if __name__ == "__main__":
    main()
