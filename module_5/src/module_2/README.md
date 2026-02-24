# Module 2: Web Scraping - GradCafe Admissions Data

## Student Information

- **Name:** Dameion Ayers
- **JHED ID:** 8489A0

## Module Info

- **Module:** Module 2
- **Assignment:** Web Scraping
- **Course:** EN.605.256.82.SP26 - Software Concepts
- **Institution:** Johns Hopkins University
- **Due Date:** 2.1.26

---

## Approach

This project implements a complete web scraping and data cleaning pipeline for graduate school admissions data from TheGradCafe.com. The implementation follows a multi-stage approach:

### Stage 1: Web Scraping

1. **robots.txt Compliance Check**: Before any scraping begins, the scraper programmatically reads and parses the site's robots.txt file using Python's `urllib.robotparser` module to ensure compliance with the site's crawling policies.

2. **HTTP Request Handling**: All HTTP requests are made using Python's standard `urllib` library with realistic browser headers (User-Agent, Accept, Accept-Language). A 30-second timeout is configured for each request.

3. **HTML Parsing with BeautifulSoup**: Each page's HTML content is parsed using BeautifulSoup. The parser uses multiple CSS selector fallbacks to handle potential variations in site structure:
   - Table-based layouts (`table tbody tr`)
   - Card-based layouts (`.result-row`, `.card`)
   - Generic repeating elements with regex matching

4. **Pagination**: The scraper iterates through paginated results by constructing sequential page URLs (`?page=2`, `?page=3`, etc.) until the target entry count is reached or no more pages exist.

5. **Rate Limiting**: A random delay of 1-3 seconds is applied between requests to respect server resources. No parallel requests are made.

6. **Retry Logic with Exponential Backoff**: Transient errors (HTTP 429, 5xx) trigger automatic retries with exponential backoff (1s, 2s, 4s, 8s, 16s) up to 5 attempts.

7. **Raw Data Storage**: Scraped data is stored in JSON format (`applicant_data.json`), preserving the raw HTML content of each entry for downstream processing.

### Stage 2: Data Cleaning with Instructor-Provided Local LLM Tooling

The local LLM tooling used in this stage is provided by the instructor as part of the assignment materials. It is used exclusively for post-scraping data normalization and structured field extraction—it does not generate or fabricate any data.

1. **LLM-Based Cleaning**: The provided local LLM tooling (`llm_hosting/app.py`) is used to clean and normalize the scraped records. This processes each entry to extract structured fields from unstructured text.

2. **Field Extraction**: The LLM extracts and normalizes:
   - Standardized university/institution names
   - Normalized program and degree names
   - Decision status categorization
   - GPA and GRE score extraction where available

3. **Original Field Preservation**: Original program names and raw content are preserved alongside cleaned fields to ensure traceability and reproducibility. This allows verification that the cleaning process did not alter the source data incorrectly.

4. **Output Format**: The LLM tooling writes output as newline-delimited JSON (JSONL format) — one JSON object per line — matching the behavior of the provided tooling.

### Stage 3: Output Generation

1. **Sample Output**: A fully validated cleaned sample file is generated to demonstrate correctness of the entire pipeline.

2. **Full Dataset Output**: A large partial output file from full-dataset processing is generated to demonstrate execution at scale.

---

## Files Structure

```
module_2/
├── scrape.py                      # Main scraping module
├── clean.py                       # Data cleaning utilities
├── requirements.txt               # Python dependencies
├── .gitignore                     # Git ignore patterns
├── README.md                      # This file
└── llm_hosting/                   # Instructor-provided LLM tooling
    ├── app.py                     # LLM processing script
    ├── requirements.txt           # LLM dependencies
    └── models/                    # Model files (not tracked in git)
```

**Generated at Runtime (not tracked in git):**
- `applicant_data.json` — Raw scraped data (~30,000+ entries)
- `applicant_data_sample.json` — Sample subset for validation
- `llm_extend_applicant_data.json` — LLM-cleaned full dataset output (partial)
- `llm_extend_applicant_data_sample.json` — LLM-cleaned sample output (complete)

---

## Known Bugs / Limitations

### LLM Processing Constraints

1. **CPU-Only Execution**: The local LLM runs on CPU only, which is extremely time-consuming at scale. There is no GPU acceleration available in this configuration.

2. **Extended Runtime**: Full LLM processing of the entire dataset (~30,000+ records) requires multiple hours on typical laptop hardware. Each record requires individual inference.

3. **Incomplete Full-Dataset Processing**: Execution was halted before full completion due to runtime constraints. The pipeline logic is complete and correct, but practical time limitations prevented processing all records.

4. **Validated Sample Included**: A fully validated cleaned sample file (`llm_extend_applicant_data_sample.json`) is generated to demonstrate correctness of the pipeline on a representative subset.

5. **Partial Full-Dataset Output**: A large partial output file (`llm_extend_applicant_data.json`) is generated to demonstrate that execution at scale was attempted and the pipeline functions correctly.

### Output Format

6. **Newline-Delimited JSON**: The LLM output is written as newline-delimited JSON (one JSON object per record), not a single JSON array. This matches the behavior of the provided tooling and is intentional.

### Platform-Specific Issues

7. **Windows Unicode Encoding**: A Unicode encoding issue was encountered when streaming LLM output to stdout on Windows. Non-ASCII characters in institution or program names caused `UnicodeEncodeError` exceptions.

8. **Applied Fix**: A small, necessary fix was applied to ensure compatibility:
   - In `llm_hosting/app.py`, the output was modified to use `json.dump(..., ensure_ascii=True)` to prevent `UnicodeEncodeError` during stdout streaming.
   - This change affects only character encoding in the output (ASCII-escaping non-ASCII characters), not data content or processing logic.

### Scraping Limitations

9. **Site Structure Dependency**: The scraper's CSS selectors may need updating if GradCafe redesigns their website structure.

10. **No JavaScript Rendering**: The scraper uses `urllib` only and cannot process dynamically-loaded content that requires JavaScript execution.

### Technical Issues — 2.3.26

A second attempt was made to run the instructor-provided local LLM tool on 2.3.26 against the full scraped dataset.

Unlike the prior run on 2.2.26, which executed for several hours and was manually stopped due to extended runtime, this attempt terminated unexpectedly before any usable output was written.

The PowerShell session closed after approximately 3.5 hours of execution. No output file was produced during this run, and no Python traceback was visible in the terminal at the time of termination. The most likely contributing factors are prolonged CPU utilization and system instability during long-running, CPU-bound inference on a Windows laptop environment.

The earlier partial output file (`llm_extend_applicant_data.json`) remains from the 2.2.26 run and was not modified by this attempt. A further run will be attempted under improved runtime conditions to allow the process to complete.

---

## Reproducibility Notes

- **Full Execution**: The complete pipeline can be executed given sufficient runtime and CPU resources. All logic is implemented and functional.

- **Sample Validation**: The generated sample output (`llm_extend_applicant_data_sample.json`) demonstrates expected behavior for all processed records and can be used to verify pipeline correctness.

- **Resumability**: The scraper stores raw data to JSON before LLM processing, allowing the expensive scraping step to be performed once and LLM processing to be resumed or rerun independently.

---

## Usage Instructions

### Prerequisites

- Python 3.10+
- pip package manager

### Installation

```bash
cd module_2
py -m pip install -r requirements.txt
```

### Running the Scraper

```bash
py scrape.py
```

### Running the LLM Cleaning

```bash
cd llm_hosting
py -m pip install -r requirements.txt
py app.py --file "../applicant_data.json" > "../llm_extend_applicant_data.json"
```

For sample processing:
```bash
py app.py --file "../applicant_data_sample.json" > "../llm_extend_applicant_data_sample.json"
```

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| beautifulsoup4 | >= 4.12.0 | HTML parsing |

All other functionality uses Python standard library:
- `urllib` - HTTP requests
- `json` - Data serialization
- `re` - Regular expressions

---

## Academic Integrity

This project was completed as an individual assignment for EN.605.256.82.SP26.
