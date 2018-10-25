import os
from readability import readability


def check_simplify_html(test_filename, expected_filename):
    test_data_dir = "data"
    # Read HTML test file
    test_filepath = os.path.join(os.path.dirname(__file__), test_data_dir, test_filename)
    with open(test_filepath) as h:
        html = h.read()

    # Return simplified article HTML
    simple_html = readability.simplify_html(html)

    # Get expected simplified article HTML
    expected_filepath = os.path.join(os.path.dirname(__file__), test_data_dir, expected_filename)
    with open(expected_filepath) as h:
        expected_simple_html = h.read()

    # Test
    assert simple_html == expected_simple_html


def test_simplify_html_full_page():
    check_simplify_html(
        "addictinginfo.com-1_full_page.html",
        "addictinginfo.com-1_simple_article_from_full_page.html"
    )

def test_simplify_html_full_article():
    check_simplify_html(
        "addictinginfo.com-1_full_article.html",
        "addictinginfo.com-1_simple_article_from_full_article.html"
    )
