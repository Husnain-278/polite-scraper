# The Polite Scraper

A small, polite web scraping pipeline built for the FlyRank Internship
Backend Track — Week 5 — Assignment A9.

## Target

Books to Scrape:

https://books.toscrape.com/

Books to Scrape is a practice website designed for learning web scraping.

## Scope

The scraper processes the first three catalogue pages.

Expected:

- 3 catalogue pages
- 60 unique books

## Data Collected

For each book:

- title
- product_url
- price_text
- price_gbp
- availability_text
- rating_text
- description
- source_page
- fetched_at

## Architecture

The pipeline works in stages:

1. Fetch catalogue pages
2. Cache HTML locally
3. Discover book URLs
4. Follow catalogue `next` links
5. Fetch book detail pages
6. Cache detail pages
7. Extract raw fields
8. Normalize price values
9. Validate records with Pydantic
10. Save valid records
11. Record invalid records
12. Generate a run report

## Project Structure

```text
scraper/
├── src/
│   └── scraper/
│       ├── __init__.py
│       └── main.py
├── tests/
│   └── test_scraper.py
├── cache/
├── output/
├── README.md
├── .gitignore
└── pyproject.toml