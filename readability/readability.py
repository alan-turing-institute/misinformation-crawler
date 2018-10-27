from bs4 import BeautifulSoup
import json
import os
from subprocess import check_call
import tempfile


def extract_readable_article(html):
    temp_dir = tempfile.gettempdir()
    # Write input HTML to temporary file so it is available to the node.js script
    html_path = os.path.join(temp_dir, "full.html");
    with open(html_path, 'w') as f:
        f.write(html)

    # Simplify the input HTML using Mozilla's Readability.js via node, writing output to a temporary file
    article_json_path = os.path.join(temp_dir, "article.json");
    parse_script_path = os.path.join(os.path.dirname(__file__), "extract_readable_article.js")
    check_call(["node", parse_script_path, "-i", html_path, "-o", article_json_path])

    # Read simplified article HTML from temporary file and return to calling function
    with open(article_json_path) as f:
        readability_article_json= json.loads(f.read())
    # Only keep the subset of Readability.js fields we are using (and therefore testing for accuracy of extraction)
    # TODO: Add tests for additional fields and include them when we look at packaging this wrapper up for PyPI
    article_json = dict()
    article_json["title"] = readability_article_json["title"]
    article_json["byline"] = readability_article_json["byline"]
    article_json["structured_content"] = readability_article_json["content"]
    article_json["plain_content"] = extract_paragraphs_as_plain_text(readability_article_json["content"])

    return article_json


def extract_paragraphs_as_plain_text(paragraph_html):
    # Load article as DOM
    soup = BeautifulSoup(paragraph_html, 'html.parser')
    # Select all paragraphs
    paragraphs = soup.find_all('p')
    # Extract text for each paragraph with leading/trailing whitespace trimmed
    paragraphs = [p.get_text().strip() for p in paragraphs]
    return paragraphs
