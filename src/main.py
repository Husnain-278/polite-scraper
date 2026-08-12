from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime, timezone
import json
import time

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"

CACHE_DIR = Path("cache")
OUTPUT_DIR = Path("output")

USER_AGENT = "FlyRankInternship-A9/1.0"
TIMEOUT = 10
REQUEST_DELAY = 0.5


def fetch_page(url: str, cache_file: Path) -> str:
    if cache_file.exists():
        html = cache_file.read_text(encoding="utf-8")
        print(f"CACHE HIT: {url}")
        return html

    print(f"FETCH: {url}")

    time.sleep(REQUEST_DELAY)

    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch {url}: HTTP {response.status_code}"
        )

    html = response.text

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(html, encoding="utf-8")

    return html


def extract_book_urls(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")

    urls = []

    for article in soup.select("article.product_pod"):
        link = article.select_one("h3 a")

        if not link:
            continue

        href = link.get("href")

        if not href:
            continue

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
        cache_file = CACHE_DIR / f"catalogue-page-{page_number}.html"

        html = fetch_page(
            catalogue_url,
            cache_file,
        )

        book_urls = extract_book_urls(
            html,
            catalogue_url,
        )

        for url in book_urls:
            discovered.append((url, catalogue_url))

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

    title_element = soup.select_one("div.product_main h1")
    price_element = soup.select_one("div.product_main .price_color")
    availability_element = soup.select_one(
        "div.product_main .availability"
    )
    rating_element = soup.select_one(
        "div.product_main p.star-rating"
    )
    description_element = soup.select_one(
        "#product_description + p"
    )

    title = (
        title_element.get_text(strip=True)
        if title_element
        else None
    )

    price_text = (
        price_element.get_text(strip=True)
        if price_element
        else None
    )

    availability_text = (
        availability_element.get_text(" ", strip=True)
        if availability_element
        else None
    )

    rating_text = None

    if rating_element:
        classes = rating_element.get("class", [])

        rating_classes = [
            value
            for value in classes
            if value != "star-rating"
        ]

        if rating_classes:
            rating_text = rating_classes[0]

    description = (
        description_element.get_text(" ", strip=True)
        if description_element
        else None
    )

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    book_urls = discover_book_urls()

    print(f"discovered_books={len(book_urls)}")

    records = []

    for index, (product_url, source_page) in enumerate(
        book_urls,
        start=1,
    ):
        cache_file = CACHE_DIR / "books" / f"{index}.html"

        html = fetch_page(
            product_url,
            cache_file,
        )

        record = extract_book_record(
            html,
            product_url,
            source_page,
        )

        records.append(record)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / "raw_books.json"

    output_file.write_text(
        json.dumps(
            records,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"detail_pages={len(records)}")
    print(f"saved={output_file}")


if __name__ == "__main__":
    main()