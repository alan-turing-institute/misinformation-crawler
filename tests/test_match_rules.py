from misinformation.extractors import extract_element, xpath_extract_spec
from scrapy.http import Request, TextResponse
import regex

def perform_extraction(html, xpath, match_rule):
    extract_spec = xpath_extract_spec(xpath, match_rule)
    return perform_extraction_using_spec(html, extract_spec)


def perform_extraction_using_spec(html, extract_spec):
    url = "http://example.com/page.html"
    request = Request(url=url)
    response = TextResponse(url=url, body=html, encoding='utf-8', request=request)
    return extract_element(response, extract_spec)


def simplify_html(html):
    html = regex.sub(r"\s+", " ", html)
    return html.replace(" <", "<").replace("> ", ">")


def simplified_extraction(html, xpath, match_rule):
    return simplify_html(perform_extraction(html, xpath, match_rule))


def test_extract_first():
    html = """
        <div>
            <p>First</p>
            <p>Second</p>
        </div>
    """
    expected_result = "<p>First</p>"
    assert simplified_extraction(html, "//div/p", "first") == expected_result


def test_extract_single():
    html = """
        <div>
            <p>First</p>
            <p>Second</p>
        </div>
    """
    expected_result = "<p>First</p>"
    assert simplified_extraction(html, "//div/p", "single") == expected_result



def test_extract_last():
    html = """
        <div>
            <p>First</p>
            <p>Second</p>
        </div>
    """
    expected_result = "<p>Second</p>"
    assert simplified_extraction(html, "//div/p", "last") == expected_result


def test_extract_largest():
    html = """
        <div>
            <p>First</p>
            <p>Second</p>
        </div>
        <div></div>
    """
    expected_result = "<div><p>First</p><p>Second</p></div>"
    assert simplified_extraction(html, "//div", "largest") == expected_result


def test_extract_concatenate():
    html = """
        <div>
            <p>First</p>
            <p>Second</p>
        </div>
    """
    expected_result = "First, Second"
    assert simplified_extraction(html, "//div/p/text()", "concatenate") == expected_result


def test_extract_group():
    html = """
        <div>
            <p>First</p>
            <p>Second</p>
            <span>Third</span>
        </div>
    """
    expected_result = "<div><p>First</p><p>Second</p></div>"
    assert simplified_extraction(html, "//div/p", "group") == expected_result


def test_extract_all():
    html = """
        <div>
            <p>First</p>
            <p>Second</p>
            <span>Third</span>
        </div>
    """
    expected_result = ["<p>First</p>", "<p>Second</p>"]
    assert perform_extraction(html, "//div/p", "all") == expected_result


def test_extract_all_with_removal():
    html = """
        <div class="content">
            <p>First</p>
        </div>
        <div class="content">
            <p>Second</p>
            <div class="social">Twitter</div>
        </div>
        <div class="content">
            <span>Third</span>
        </div>
    """
    extract_spec = xpath_extract_spec('//div[@class="content"]', 'all')
    extract_spec['remove_expressions'] = ['//div[@class="social"]']
    expected_result = ['<div class="content"><p>First</p></div>',
                       '<div class="content"><p>Second</p></div>',
                       '<div class="content"><span>Third</span></div>']
    result = [simplify_html(h) for h in perform_extraction_using_spec(html, extract_spec)]
    assert result == expected_result
