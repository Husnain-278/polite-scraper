import json

from scraper.main import (
    normalize_price,
    extract_book_urls,
)


def test_normalize_price():
    assert normalize_price("£51.77") == 51.77
    assert normalize_price("£10.00") == 10.00


def test_extract_book_urls():
    html = """
    <html>
        <body>
            <article class="product_pod">
                <h3>
                    <a href="../book/test-book_1/index.html">
                        Test Book
                    </a>
                </h3>
            </article>
        </body>
    </html>
    """

    urls = extract_book_urls(
        html,
        "https://books.toscrape.com/catalogue/page-1.html",
    )

    assert len(urls) == 1

    assert urls[0] == (
    "https://books.toscrape.com/"
    "book/test-book_1/index.html"
)


def test_books_json_has_60_unique_records():
    with open(
        "output/books.json",
        encoding="utf-8",
    ) as file:
        books = json.load(file)

    assert len(books) == 60

    urls = [
        book["product_url"]
        for book in books
    ]

    assert len(urls) == len(set(urls))