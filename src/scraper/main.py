from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime, timezone
import json
import time
import re

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl, ValidationError


BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"

CACHE_DIR = Path("cache")
OUTPUT_DIR = Path("output")

USER_AGENT = "FlyRankInternship-A9/1.0"
TIMEOUT = 10
REQUEST_DELAY = 0.5
MAX_RETRIES = 1


class BookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: str | None
    source_page: HttpUrl
    fetched_at: datetime


def fetch_page(url: str, cache_file: Path) -> tuple[str | None, str]:
    if cache_file.exists():
        html = cache_file.read_text(encoding="utf-8")
        print(f"CACHE HIT: {url}")
        return html, "cache"

    for attempt in range(MAX_RETRIES + 1):
        try:
            print(f"FETCH: {url}")

            time.sleep(REQUEST_DELAY)

            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
            )

            if response.status_code == 200:
                html = response.text

                cache_file.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                cache_file.write_text(
                    html,
                    encoding="utf-8",
                )

                return html, "fetched"

            if response.status_code in (403, 404):
                print(
                    f"FAILED: HTTP {response.status_code} "
                    f"{url}"
                )
                return None, "failed"

            if attempt < MAX_RETRIES:
                print(
                    f"RETRY: HTTP {response.status_code} "
                    f"{url}"
                )
                continue

            return None, "failed"

        except requests.RequestException as error:
            print(f"REQUEST ERROR: {error}")

            if attempt < MAX_RETRIES:
                print("RETRYING...")
                continue

            return None, "failed"

    return None, "failed"


def extract_book_urls(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")

    urls = []

    for article in soup.select("article.product_pod"):
        link = article.select_one("h3 a")

        if not link:
            continue

        href = link.get("href")

        if href:
            urls.append(urljoin(page_url, href))

    return urls


def find_next_page(html: str, page_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    next_link = soup.select_one("li.next a")

    if not next_link:
        return None

    href = next_link.get("href")

    if not href:
        return None

    return urljoin(page_url, href)


def discover_book_urls() -> list[tuple[str, str]]:
    catalogue_url = BASE_URL
    discovered = []

    page_number = 1

    while catalogue_url and page_number <= 3:
        cache_file = (
            CACHE_DIR
            / f"catalogue-page-{page_number}.html"
        )

        html, status = fetch_page(
            catalogue_url,
            cache_file,
        )

        if html is None:
            page_number += 1
            continue

        for book_url in extract_book_urls(
            html,
            catalogue_url,
        ):
            discovered.append(
                (book_url, catalogue_url)
            )

        catalogue_url = find_next_page(
            html,
            catalogue_url,
        )

        page_number += 1

    unique = {}

    for book_url, source_page in discovered:
        unique.setdefault(book_url, source_page)

    return list(unique.items())


def extract_book_record(
    html: str,
    product_url: str,
    source_page: str,
) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    title = soup.select_one("div.product_main h1")
    price = soup.select_one(
        "div.product_main .price_color"
    )
    availability = soup.select_one(
        "div.product_main .availability"
    )
    rating = soup.select_one(
        "div.product_main p.star-rating"
    )
    description = soup.select_one(
        "#product_description + p"
    )

    rating_text = None

    if rating:
        classes = rating.get("class", [])
        rating_classes = [
            item
            for item in classes
            if item != "star-rating"
        ]

        if rating_classes:
            rating_text = rating_classes[0]

    return {
        "title": (
            title.get_text(strip=True)
            if title
            else None
        ),
        "product_url": product_url,
        "price_text": (
            price.get_text(strip=True)
            if price
            else None
        ),
        "availability_text": (
            availability.get_text(
                " ",
                strip=True,
            )
            if availability
            else None
        ),
        "rating_text": rating_text,
        "description": (
            description.get_text(
                " ",
                strip=True,
            )
            if description
            else None
        ),
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc),
    }


def normalize_price(price_text: str) -> float:
    value = re.sub(
        r"[^\d.]",
        "",
        price_text,
    )
    return float(value)


def normalize_record(record: dict) -> dict:
    record["price_gbp"] = normalize_price(
        record["price_text"]
    )
    return record


def main() -> None:
    started_at = datetime.now(timezone.utc)

    book_urls = discover_book_urls()

    valid_records = []
    invalid_records = []
    failed_urls = []
    fetched_count = 0
    cache_hits = 0

    for index, (product_url, source_page) in enumerate(
        book_urls,
        start=1,
    ):
        cache_file = (
            CACHE_DIR
            / "books"
            / f"{index}.html"
        )

        html, status = fetch_page(
            product_url,
            cache_file,
        )

        if status == "cache":
            cache_hits += 1

        elif status == "fetched":
            fetched_count += 1

        if html is None:
            failed_urls.append(product_url)
            continue

        try:
            raw_record = extract_book_record(
                html,
                product_url,
                source_page,
            )

            normalized = normalize_record(
                raw_record
            )

            book = BookRecord.model_validate(
                normalized
            )

            valid_records.append(
                book.model_dump(mode="json")
            )

        except ValidationError as error:
            invalid_records.append(
                {
                    "url": product_url,
                    "reason": error.errors(),
                }
            )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    Path("output/books.json").write_text(
        json.dumps(
            valid_records,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    Path("output/errors.json").write_text(
        json.dumps(
            invalid_records,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    finished_at = datetime.now(timezone.utc)

    run_report = {
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "catalogue_pages": 3,
        "discovered_urls": len(book_urls),
        "fetched": fetched_count,
        "cache_hits": cache_hits,
        "valid_records": len(valid_records),
        "invalid_records": len(invalid_records),
        "failed_urls": failed_urls,
    }

    Path("output/run-report.json").write_text(
        json.dumps(
            run_report,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=== RUN REPORT ===")
    print(json.dumps(run_report, indent=2))


if __name__ == "__main__":
    main()