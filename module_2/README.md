# Module 2: Web Scraping - GradCafe Admissions Data

**Course:** EN.605.256.82.SP26 - Software Concepts
**Institution:** Johns Hopkins University
**Assignment:** Module 2 - Web Scraping
**Due Date:** [INSERT DUE DATE]

## Student Information

- **Name:** [YOUR NAME]
- **JHED ID:** [YOUR JHED]

## Repository

- **GitHub Repository:** [thinkTanck/jhu_software_concepts](https://github.com/thinkTanck/jhu_software_concepts) (Private)
- **Module Directory:** `module_2/`

---

## Project Overview

This project implements a web scraper to collect graduate school admissions data from [TheGradCafe.com](https://www.thegradcafe.com), a community-driven platform where applicants share their admission decisions. The collected data is then cleaned and processed using regex-based pattern matching for structured field extraction.

### Objectives

1. Scrape >= 30,000 admission entries from GradCafe
2. Implement ethical scraping practices (robots.txt compliance, rate limiting)
3. Clean and normalize the scraped data
4. Extract structured fields using pattern matching and text parsing

---

## Files Structure

```
module_2/
├── scrape.py              # Main scraping module
├── clean.py               # Data cleaning and field extraction
├── requirements.txt       # Python dependencies
├── .gitignore             # Git ignore patterns
├── README.md              # This file
├── applicant_data.json    # Raw scraped data (generated)
└── cleaned_applicant_data.json  # Cleaned data (generated)
```

---

## Scraping Approach

### Data Source

TheGradCafe provides a survey/results page where users submit their graduate school admission outcomes. Each entry typically includes:

- Institution name
- Program/Department
- Decision status (Accepted, Rejected, Waitlisted, Interview)
- Date of decision
- Applicant statistics (GPA, GRE scores)
- Comments and notes

### Technical Implementation

#### 1. HTTP Requests (`urllib`)

The scraper uses Python's `urllib` library exclusively (no `requests` library):

```python
from urllib import request, parse, error, robotparser
```

- **User-Agent Header:** A realistic browser User-Agent string is sent with each request to avoid blocking
- **Request Headers:** Full browser-like headers including Accept, Accept-Language, etc.
- **Timeout Handling:** 30-second timeout for each request

#### 2. Pagination Logic

GradCafe uses URL-based pagination. The scraper:

1. Starts at the main results page (`/survey`)
2. Extracts entries from the current page
3. Constructs the next page URL (e.g., `?page=2`, `?page=3`, etc.)
4. Continues until target entry count is reached or no more pages exist

#### 3. HTML Parsing

BeautifulSoup is used for HTML parsing with multiple fallback selectors:

```python
from bs4 import BeautifulSoup
```

The parser tries various CSS selectors to accommodate potential site structure changes:
- Table-based layouts (`table tbody tr`)
- Card-based layouts (`.result-row`, `.card`)
- Generic repeating elements

#### 4. Rate Limiting

To be respectful of server resources:

- **Delay Between Requests:** Random delay between 1-3 seconds
- **No Parallel Requests:** Sequential page fetching only

#### 5. Retry Logic with Exponential Backoff

For handling transient errors:

```python
MAX_RETRIES = 5
RETRY_BACKOFF = 2  # Exponential multiplier

# On failure: wait 1s, 2s, 4s, 8s, 16s
```

Handles:
- HTTP 429 (Too Many Requests)
- HTTP 5xx (Server Errors)
- Network timeouts and URL errors

---

## robots.txt Compliance

### Automated Compliance Check

The scraper programmatically checks robots.txt before beginning:

```python
from urllib import robotparser

def check_robots_txt(url: str) -> bool:
    rp = robotparser.RobotFileParser()
    rp.set_url(ROBOTS_URL)
    rp.read()
    return rp.can_fetch(USER_AGENT, url)
```

### Compliance Measures

1. **Pre-Scrape Verification:** robots.txt is read and parsed before any scraping begins
2. **User-Agent Respect:** The scraper identifies itself and respects User-Agent specific rules
3. **Crawl-Delay:** If robots.txt specifies a crawl delay, the scraper would respect it
4. **Disallowed Paths:** Any paths marked as disallowed are not accessed

### Ethical Considerations

- The scraper does not bypass any access restrictions
- Rate limiting is implemented even if not required by robots.txt
- User-submitted public data is collected (no private/authenticated content)
- Data is used for educational purposes only

---

## Data Cleaning Process

### Initial Cleaning (`clean.py`)

The cleaning module performs several preprocessing steps:

#### 1. HTML Remnant Removal

```python
def remove_html_tags(text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", text)
    # Also handles HTML entities: &nbsp;, &amp;, etc.
```

#### 2. Whitespace Normalization

```python
def normalize_whitespace(text: str) -> str:
    clean = re.sub(r"[\t\n\r\f\v]+", " ", text)
    clean = re.sub(r" +", " ", clean)
    return clean.strip()
```

#### 3. Field Preservation

Original field values are preserved with `_original_` prefix when modified:

```python
if original != cleaned[key]:
    cleaned[f"_original_{key}"] = original
```

---

## Field Extraction Process

### Purpose

The field extraction step parses structured data from unstructured text content, handling variations in how users report their information.

### Process

1. **Preparation:** Cleaned data is formatted for processing
2. **Pattern Matching:** Regex-based extraction of structured fields:
   - Standardized institution names
   - Normalized program/degree names
   - Decision status categorization
   - GPA/GRE score extraction
   - Date parsing

3. **Validation:** Output is validated to ensure original data preservation
4. **Merging:** Extracted fields are merged with original data

### Field Extraction

The parser extracts and standardizes:

| Field | Description |
|-------|-------------|
| `extracted_institution` | Standardized university name |
| `extracted_program` | Normalized program name |
| `extracted_degree` | Degree type (PhD, MS, MA, etc.) |
| `extracted_decision` | Categorized decision |
| `extracted_gpa` | Numeric GPA if mentioned |
| `extracted_gre_v` | GRE Verbal score |
| `extracted_gre_q` | GRE Quantitative score |
| `extracted_date` | ISO-formatted date |

---

## Usage Instructions

### Prerequisites

- Python 3.10+
- pip package manager

### Installation

```bash
cd module_2
pip install -r requirements.txt
```

### Running the Scraper

```bash
python scrape.py
```

This will:
1. Check robots.txt compliance
2. Scrape admission entries (target: 45,000+)
3. Save raw data to `applicant_data.json`

### Cleaning the Data

```bash
python clean.py
```

This will:
1. Load `applicant_data.json`
2. Remove HTML remnants and normalize text
3. Save cleaned data to `cleaned_applicant_data.json`

---

## Known Limitations

### Technical Limitations

1. **Site Structure Changes:** The scraper's CSS selectors may need updating if GradCafe redesigns their website
2. **Rate Limiting:** Conservative rate limiting means scraping 45,000+ entries takes significant time
3. **No JavaScript Rendering:** Uses urllib only, so dynamically-loaded content may be missed
4. **Single-Threaded:** No parallel scraping to respect server resources

### Data Limitations

1. **User-Submitted Data:** GradCafe entries are self-reported and may contain inaccuracies
2. **Incomplete Entries:** Many entries lack complete information (GPA, GRE scores)
3. **Varied Formats:** Users report information inconsistently, requiring regex-based standardization
4. **Historical Data:** Older entries may reference outdated programs or institutions

### Potential Improvements

1. Implement caching to resume interrupted scrapes
2. Add data validation rules for GPA/GRE ranges
3. Create institution name mapping for standardization
4. Implement incremental scraping for updates

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

---

## License

This project is submitted for academic purposes only and is not licensed for external use.
