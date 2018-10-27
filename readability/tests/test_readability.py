import json
import os
from readability import readability


def check_extract_readable_article(test_filename, expected_filename):
    test_data_dir = "data"
    # Read HTML test file
    test_filepath = os.path.join(os.path.dirname(__file__), test_data_dir, test_filename)
    with open(test_filepath) as h:
        html = h.read()

    # Extract simplified article HTML
    article_json = readability.extract_readable_article(html)

    # Get expected simplified article HTML
    expected_filepath = os.path.join(os.path.dirname(__file__), test_data_dir, expected_filename)
    with open(expected_filepath) as h:
        expected_article_json = json.loads(h.read())

    # Test full JSON matches (checks for unexpected fields in either actual or expected JSON)
    assert article_json == expected_article_json


def test_extract_readable_article_full_page():
    check_extract_readable_article(
        "addictinginfo.com-1_full_page.html",
        "addictinginfo.com-1_simple_article_from_full_page.json"
    )


def test_extract_readable_article_full_article():
    check_extract_readable_article(
        "addictinginfo.com-1_full_article.html",
        "addictinginfo.com-1_simple_article_from_full_article.json"
    )


def check_extract_paragraphs_as_plain_text(test_filename, expected_filename):
    test_data_dir = "data"
    # Read readable article test file
    test_filepath = os.path.join(os.path.dirname(__file__), test_data_dir, test_filename)
    with open(test_filepath) as h:
        article = json.loads(h.read())

    # Extract plain text paragraphs
    paragraphs = readability.extract_paragraphs_as_plain_text(article["structured_content"])

    # Get expected plain text paragraphs
    expected_filepath = os.path.join(os.path.dirname(__file__), test_data_dir, expected_filename)
    with open(expected_filepath) as h:
        expected_paragraphs = json.loads(h.read())

    # Test
    assert paragraphs == expected_paragraphs


def test_extract_paragraphs_as_plain_text():
    check_extract_paragraphs_as_plain_text(
        "addictinginfo.com-1_simple_article_from_full_article.json",
        "addictinginfo.com-1_plain_text_paragraphs_from_simple_article.json"
    )

