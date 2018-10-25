import os
from readability import readability


def check_extract_readable_article(test_filename, expected_filename):
    test_data_dir = "data"
    # Read HTML test file
    test_filepath = os.path.join(os.path.dirname(__file__), test_data_dir, test_filename)
    with open(test_filepath) as h:
        html = h.read()

    # Return simplified article HTML
    simple_html = readability.extract_readable_article(html)

    # Get expected simplified article HTML
    expected_filepath = os.path.join(os.path.dirname(__file__), test_data_dir, expected_filename)
    with open(expected_filepath) as h:
        expected_simple_html = h.read()

    # Test
    assert simple_html == expected_simple_html


def test_extract_readable_article_full_page():
    check_extract_readable_article(
        "addictinginfo.com-1_full_page.html",
        "addictinginfo.com-1_simple_article_from_full_page.html"
    )

def test_extract_readable_article_full_article():
    check_extract_readable_article(
        "addictinginfo.com-1_full_article.html",
        "addictinginfo.com-1_simple_article_from_full_article.html"
    )
