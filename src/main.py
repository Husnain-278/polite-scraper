from pathlib import Path
from urllib.parse import urljoin
import time
import requests
from bs4 import BeautifulSoup


BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_FILE = Path("cache/catalogue-page-1.html")

USER_AGENT = "FlyRankInternship-A9/1.0"
TIMEOUT = 10
REQUEST_DELAY = 0.5


def fetch_catalogue_page(url: str, cache_file: Path) -> str:
    if cache_file.exists():
        html = cache_file.read_text(encoding="utf-8")

        print(f"CACHE HIT: {url}")
        print(f"response_size={len(html.encode('utf-8'))} bytes")

        return html

    print(f"FETCH: {url}")

    headers = {
        "User-Agent": USER_AGENT,
    }
    time.sleep(REQUEST_DELAY)

    response = requests.get(
        url,
        headers=headers,
        timeout=TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch {url}: HTTP {response.status_code}"
        )

    html = response.text

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(html, encoding="utf-8")

    print(f"status={response.status_code}")
    print(f"response_size={len(response.content)} bytes")

    return html


def extract_book_urls(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")

    book_urls = []

    for article in soup.select("article.product_pod"):
        link = article.select_one("h3 a")

        if not link:
            continue

        href = link.get("href")

        if not href:
            continue

        absolute_url = urljoin(page_url, href)
        book_urls.append(absolute_url)

    return book_urls


def find_next_page(html: str, page_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    next_link = soup.select_one("li.next a")

    if not next_link:
        return None

    href = next_link.get("href")

    if not href:
        return None

    return urljoin(page_url, href)


def main() -> None:
    catalogue_url = BASE_URL
    all_book_urls = []
    catalogue_pages = 0

    while catalogue_url and catalogue_pages < 3:
        if catalogue_pages == 0:
            cache_file = CACHE_FILE
        else:
            page_number = catalogue_pages + 1
            cache_file = Path(
                f"cache/catalogue-page-{page_number}.html"
            )

        html = fetch_catalogue_page(
            catalogue_url,
            cache_file,
        )

        catalogue_pages += 1

        book_urls = extract_book_urls(
            html,
            catalogue_url,
        )

        all_book_urls.extend(book_urls)

        catalogue_url = find_next_page(
            html,
            catalogue_url,
        )

    unique_urls = list(dict.fromkeys(all_book_urls))

    print()
    print(f"catalogue_pages={catalogue_pages}")
    print(f"discovered={len(all_book_urls)}")
    print(f"unique_urls={len(unique_urls)}")


if __name__ == "__main__":
    main()