from pathlib import Path

import requests


BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_FILE = Path("cache/catalogue-page-1.html")

USER_AGENT = "FlyRankInternship-A9/1.0"
TIMEOUT = 10


def fetch_catalogue_page() -> str:
    if CACHE_FILE.exists():
        html = CACHE_FILE.read_text(encoding="utf-8")

        print("CACHE HIT")
        print(f"response_size={len(html.encode('utf-8'))} bytes")

        return html

    print("FETCH")

    headers = {
        "User-Agent": USER_AGENT,
    }

    response = requests.get(
        BASE_URL,
        headers=headers,
        timeout=TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch page: HTTP {response.status_code}"
        )

    html = response.text

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(html, encoding="utf-8")

    print(f"status={response.status_code}")
    print(f"response_size={len(response.content)} bytes")

    return html


def main() -> None:
    fetch_catalogue_page()


if __name__ == "__main__":
    main()