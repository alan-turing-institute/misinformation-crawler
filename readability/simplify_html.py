import os
from subprocess import check_call
import tempfile

def simplify_html(html):
    temp_dir = tempfile.gettempdir()
    # Write input HTML to temporary file so it is available to the node.js script
    html_path = os.path.join(temp_dir, "full.html");
    with open(html_path, 'w') as f:
        f.write(html)

    # Simplify the input HTML using Mozilla's Readability.js via node, writing output to a temporary file
    simple_html_path = os.path.join(temp_dir, "simple.html");
    parse_script_path = os.path.join(os.path.dirname(__file__), "parse_html.js")
    check_call(["node", parse_script_path, "-i", html_path, "-o", simple_html_path])

    # Read simplified article HTML from temporary file and return to calling function
    simple_html = None
    with open(simple_html_path) as f:
        simple_html = f.read()
    return simple_html
