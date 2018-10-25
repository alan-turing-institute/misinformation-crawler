from bs4 import BeautifulSoup
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
    simple_html_path = os.path.join(temp_dir, "simple.html");
    parse_script_path = os.path.join(os.path.dirname(__file__), "extract_readable_article.js")
    check_call(["node", parse_script_path, "-i", html_path, "-o", simple_html_path])

    # Read simplified article HTML from temporary file and return to calling function
    simple_html = None
    with open(simple_html_path) as f:
        simple_html = f.read()
    return simple_html


def extract_paragraphs_as_plain_text(readable_article):
    # Load article as DOM
    soup = BeautifulSoup(readable_article, 'html.parser')
    # Select all paragraphs
    paragraphs = soup.find_all('p')
    # Extract text for each paragraph with leading/trailing whitespace trimmed
    paragraphs = [p.get_text().strip() for p in paragraphs]
    return paragraphs
