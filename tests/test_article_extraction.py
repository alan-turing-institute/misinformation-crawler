import arrow
import pytest
import json
import os
import glob
import pkg_resources
from misinformation.extractors import extract_article, extract_element, xpath_extract_spec, extract_datetime_string
from scrapy.http import Request, TextResponse
import yaml

SITE_TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "site_test_data")
UNIT_TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "unit_test_data")
SITE_CONFIG_FILE = pkg_resources.resource_string("misinformation", "../site_configs.yml")

# Load site-specific spider configurations
SITE_CONFIGS = yaml.load(SITE_CONFIG_FILE)
SITE_NAMES = sorted(SITE_CONFIGS.keys())

# ================= HELPER FUNCTIONS =================
def config_for_site(site_name):
    return SITE_CONFIGS[site_name]


def response_from_html_file(html_filepath):
    with open(html_filepath) as f:
        html = f.read()
    path_parts = os.path.split(html_filepath)
    filename = path_parts[-1]
    url = "http://{domain}/{path}".format(domain="example.com", path=filename)
    request = Request(url=url)
    response = TextResponse(url=url, body=html, encoding='utf-8', request=request)
    return response


def article_from_json_file(json_filepath):
    # Construct response from html
    with open(json_filepath) as f:
        article = json.loads(f.read())
    return article


def article_stems_for_site(site_name):
    # Find all HTML files in site test data directory
    print(os.path.join(SITE_TEST_DATA_DIR, site_name))
    html_file_paths = glob.glob(os.path.join(SITE_TEST_DATA_DIR, site_name, '*.html'))
    article_stems = []
    for html_file_path in html_file_paths:
        _file = os.path.split(html_file_path)[1]
        article_stems.append(_file.split('_')[0])
    # Fail fixture set up if no test sites found for site
    assert article_stems != [], "No HTML test files found for site '{site}'".format(site=site_name)
    return article_stems


def article_infos_for_site(site_name):
    article_stems = article_stems_for_site(site_name)
    article_infos = [{"site_name": site_name, "article_stem": article_stem} for article_stem in article_stems]
    return article_infos


def article_infos_for_all_sites(site_names):
    article_infos = []
    for site_name in site_names:
        article_infos = article_infos + article_infos_for_site(site_name)
    return article_infos


def article_info_id(param):
    return "{site}/{article}".format(site=param['site_name'], article=param['article_stem'])


@pytest.fixture(params=article_infos_for_all_sites(SITE_NAMES), ids=article_info_id)
def article_info(request):
    return request.param


# ================= TEST FUNCTIONS =================
def validate_extract_element(html, extract_spec, expected):
    actual = extract_element(html, extract_spec)
    # Ignore whitespace differences
    assert ''.join(actual.split()) == ''.join(expected.split())


def validate_extract_article(response, config, expected):
    article = extract_article(response, config)
    # Check title extraction
    assert article['title'] == expected['title']
    # Check byline extraction
    assert article['byline'] == expected['byline']
    # Check publication datetime extraction
    assert article['publication_datetime'] == expected['publication_datetime']
    # Check plain content extraction
    assert article['plain_content'] == expected['plain_content']
    # Check plain text extraction
    assert article['plain_text'] == expected['plain_text']


def test_extract_article_for_sites(article_info):
    # Select test config
    site_name = article_info['site_name']
    config = SITE_CONFIGS[site_name]

    # Define test file locations
    article_stem = article_info['article_stem']
    print("\nTesting {site}: {article}".format(site=site_name, article=article_stem))
    data_dir = os.path.join(SITE_TEST_DATA_DIR, site_name)
    html_filename = article_stem + '_article.html'
    json_filename = article_stem + '_extracted_data.json'
    html_filepath = os.path.join(data_dir, html_filename)
    json_filepath = os.path.join(data_dir, json_filename)

    # Load test data from files
    response = response_from_html_file(html_filepath)
    expected_article = article_from_json_file(json_filepath)

    # Test
    validate_extract_article(response, config, expected_article)


def test_extract_article_default():
    # Load test file
    html_filepath = os.path.join(UNIT_TEST_DATA_DIR, "addictinginfo.com-1_article.html")
    response = response_from_html_file(html_filepath)
    # Load expected article data
    article_filepath = os.path.join(UNIT_TEST_DATA_DIR, "addictinginfo.com-1_extracted_data_default.json")
    expected_article = article_from_json_file(article_filepath)

    # Mock config
    config_yaml = """
        site_name: 'example.com'
        start_url: 'http://addictinginfo.com/category/news/'
    """
    config = yaml.load(config_yaml)

    # Test
    article = extract_article(response, config)
    print(article)
    assert article == expected_article


def test_extract_article_default_with_crawl_info():
    # Load test file
    html_filepath = os.path.join(UNIT_TEST_DATA_DIR, "addictinginfo.com-1_article.html")
    response = response_from_html_file(html_filepath)
    # Load expected article data
    article_filepath = os.path.join(UNIT_TEST_DATA_DIR,
        "addictinginfo.com-1_extracted_data_default_with_crawl_info.json")
    expected_article = article_from_json_file(article_filepath)

    # Mock config
    config_yaml = """
        site_name: 'example.com'
        start_url: 'http://addictinginfo.com/category/news/'
    """
    config = yaml.load(config_yaml)

    # Mock crawl info
    crawl_info = {
        "crawl_id": "bdbcf1cf-e4,1f-4c10-9958-4ab1b07e46ae",
        "crawl_datetime": "2018-10-17T20:25:34.2345+00:00"
    }

    # Test
    article = extract_article(response, config, crawl_info)
    assert article == expected_article


def test_extract_article_custom_title_selector():
    # Load test file
    html_filepath = os.path.join(UNIT_TEST_DATA_DIR, "addictinginfo.com-1_article.html")
    response = response_from_html_file(html_filepath)
    # Load expected article data
    article_filepath = os.path.join(UNIT_TEST_DATA_DIR,
        "addictinginfo.com-1_extracted_data_default_custom_title_selector.json")
    expected_article = article_from_json_file(article_filepath)

    # Mock config
    config_yaml = """
        site_name: 'example.com'
        article:
            title:
                select_method: 'xpath'
                select_expression: '//p[@id="test-custom-title"]/text()'
                match_rule: 'single'

    """
    config = yaml.load(config_yaml)

    # Test
    article = extract_article(response, config)
    assert article["title"] == expected_article["title"]


def test_extract_article_custom_byline_selector():
    # Load test file
    html_filepath = os.path.join(UNIT_TEST_DATA_DIR, "addictinginfo.com-1_article.html")
    response = response_from_html_file(html_filepath)
    # Load expected article data
    article_filepath = os.path.join(UNIT_TEST_DATA_DIR,
        "addictinginfo.com-1_extracted_data_default_custom_byline_selector.json")
    expected_article = article_from_json_file(article_filepath)

    # Mock config
    config_yaml = """
        site_name: 'example.com'
        article:
            byline:
                select_method: 'xpath'
                select_expression: '//p[@id="test-custom-byline"]/text()'
                match_rule: 'single'

    """
    config = yaml.load(config_yaml)

    # Test
    article = extract_article(response, config)
    assert article["byline"] == expected_article["byline"]


def test_extract_article_custom_content_selector():
    # Load test file
    html_filepath = os.path.join(UNIT_TEST_DATA_DIR, "addictinginfo.com-1_article.html")
    response = response_from_html_file(html_filepath)
    # Load expected article data
    article_filepath = os.path.join(UNIT_TEST_DATA_DIR,
        "addictinginfo.com-1_extracted_data_default_custom_content_selector.json")
    expected_article = article_from_json_file(article_filepath)

    # Mock config
    config_yaml = """
        site_name: 'example.com'
        article:
            content:
                select_method: 'xpath'
                select_expression: '//div[@class="entry entry-content"]'
                match_rule: 'single'

    """
    config = yaml.load(config_yaml)

    # Test
    article = extract_article(response, config)
    assert article["content"] == expected_article["content"]

def test_extract_article_custom_publication_datetime_selector():
    # Load test file
    html_filepath = os.path.join(UNIT_TEST_DATA_DIR, "addictinginfo.com-1_article.html")
    response = response_from_html_file(html_filepath)
    # Load expected article data
    article_filepath = os.path.join(UNIT_TEST_DATA_DIR, "addictinginfo.com-1_extracted_data_default_custom_publication_datetime_selector.json")
    expected_article = article_from_json_file(article_filepath)

    # Mock config
    config_yaml = """
        site_name: 'example.com'
        start_url: 'http://addictinginfo.com/category/news/'
        article:
            publication_datetime:
                select_method: 'xpath'
                select_expression: '//time[contains(concat(" ", normalize-space(@class), " "), " entry-date ")]/@datetime'
                match_rule: 'single'

    """
    config = yaml.load(config_yaml)

    # Test
    article = extract_article(response, config)
    assert article["publication_datetime"] == expected_article["publication_datetime"]

def test_extract_article_default_content_digests():
    # Load test file
    html_filepath = os.path.join(UNIT_TEST_DATA_DIR, "addictinginfo.com-1_article.html")
    response = response_from_html_file(html_filepath)
    # Load expected article data
    article_filepath = os.path.join(UNIT_TEST_DATA_DIR, "addictinginfo.com-1_extracted_data_default_content_digests.json")
    expected_article = article_from_json_file(article_filepath)

    # Mock config
    config_yaml = """
        site_name: 'example.com'
        start_url: 'http://addictinginfo.com/category/news/'
    """
    config = yaml.load(config_yaml)

    # Test
    article = extract_article(response, config, content_digests=True)
    assert article == expected_article


def test_extract_article_default_node_indexes():
    # Load test file
    html_filepath = os.path.join(UNIT_TEST_DATA_DIR, "addictinginfo.com-1_article.html")
    response = response_from_html_file(html_filepath)
    # Load expected article data
    article_filepath = os.path.join(UNIT_TEST_DATA_DIR, "addictinginfo.com-1_extracted_data_default_node_indexes.json")
    expected_article = article_from_json_file(article_filepath)

    # Mock config
    config_yaml = """
        site_name: 'example.com'
        start_url: 'http://addictinginfo.com/category/news/'
    """
    config = yaml.load(config_yaml)

    # Test
    article = extract_article(response, config, node_indexes=True)
    assert article == expected_article


def test_extract_article_default_content_digests_node_indexes():
    # Load test file
    html_filepath = os.path.join(UNIT_TEST_DATA_DIR, "addictinginfo.com-1_article.html")
    response = response_from_html_file(html_filepath)
    # Load expected article data
    article_filepath = os.path.join(UNIT_TEST_DATA_DIR,
                                    "addictinginfo.com-1_extracted_data_default_content_digests_node_indexes.json")
    expected_article = article_from_json_file(article_filepath)
    # Mock config
    config_yaml = """
        site_name: 'example.com'
        start_url: 'http://addictinginfo.com/category/news/'
    """
    config = yaml.load(config_yaml)

    # Test
    article = extract_article(response, config, content_digests=True, node_indexes=True)
    if article != expected_article:
        for key in article.keys():
            if article[key] != expected_article[key]:
                if key == "plain_text":
                    for a, b in zip(article[key], expected_article[key]):
                        for idx, (i, j) in enumerate(zip(a, b)):
                            if i != j:
                                print("\n\n", key, "\n\n", b[idx-1:idx+10], "=>", a[idx-1:idx+10])
                                break
                else:
                    for idx, (i, j) in enumerate(zip(article[key], expected_article[key])):
                        if i != j:
                            print("\n\n", key, "\n\n", expected_article[key][idx-1:idx+10], "=>", article[key][idx-1:idx+10])
                            break

            # print(json.dumps(article[key]))
    assert article == expected_article


def test_extract_element():
    # Mock response using expected article data
    html = """<html>
    <head></head>
    <body>
        <div class="post-content">
            <h1 class="post-title">Article title</h1>
            <div class="post-content">
                <p>Paragraph 1</p>
                <p>Paragraph 2</p>
                <p>Paragraph 3</p>
            </div>
        </div>
    </body>
    </html>"""
    response = TextResponse(url="http://example.com", body=html, encoding="utf-8")

    # Mock config
    config_yaml = """
    site_name: 'example.com'
    article:
        title:
            select_method: 'xpath'
            select_expression: '//h1[@class="post-title"]/text()'
            match_rule: 'single'
        paragraphs:
            select_method: 'xpath'
            select_expression: '//p'
            match_rule: 'group'
        first-paragraph:
            select_method: 'xpath'
            select_expression: '//p/text()'
            match_rule: 'first'
    """
    config = yaml.load(config_yaml)

    # Test single element extraction
    expected_title = "Article title"
    validate_extract_element(response, config['article']['title'], expected_title)
    # Test group element extraction
    expected_paragraphs = "<div><p>Paragraph 1</p><p>Paragraph 2</p><p>Paragraph 3</p></div>"
    validate_extract_element(response, config['article']['paragraphs'], expected_paragraphs)
    # Test first element extraction
    expected_first_paragraph = "Paragraph 1"
    validate_extract_element(response, config['article']['first-paragraph'], expected_first_paragraph)


def test_remove_single_expression():
    # Mock response using expected article data
    html = """<html>
    <head></head>
    <body>
        <div class="post-content">
            <h1 class="post-title">Article title</h1>
            <div class="post-content">
                <p>Paragraph 1</p>
                <p>Paragraph 2</p>
                <p>Paragraph 3</p>
            </div>
            <div class="social">
                <p>Twitter</p>
                <p>Facebook</p>
            </div>
        </div>
    </body>
    </html>"""
    response = TextResponse(url="http://example.com", body=html, encoding="utf-8")

    # Mock config
    config_yaml = """
    site_name: 'example.com'
    article:
        content:
            select_method: 'xpath'
            select_expression: '//div[@class="post-content"]'
            match_rule: 'first'
            remove_expressions:
                - '//div[@class="social"]'
    """
    config = yaml.load(config_yaml)

    # Test content extraction with removal
    expected_html = """
        <div class="post-content">
            <h1 class="post-title">Article title</h1>
            <div class="post-content">
                <p>Paragraph 1</p>
                <p>Paragraph 2</p>
                <p>Paragraph 3</p>
            </div>
        </div>"""
    print(extract_element(response, config['article']['content']))
    validate_extract_element(response, config['article']['content'], expected_html)


def test_remove_nested_expressions():
    # Mock response using expected article data
    html = """<html>
    <head></head>
    <body>
        <div class="post-content">
            <h1 class="post-title">Article title</h1>
            <div class="post-content">
                <p>Paragraph 1</p>
                <p>Paragraph 2</p>
                <p>Paragraph 3</p>
            </div>
            <div class="social">
                <div class="social">
                    <p>Twitter</p>
                    <p>Facebook</p>
                </div>
            </div>
        </div>
    </body>
    </html>"""
    response = TextResponse(url="http://example.com", body=html, encoding="utf-8")

    # Mock config
    config_yaml = """
    site_name: 'example.com'
    article:
        content:
            select_method: 'xpath'
            select_expression: '//div[@class="post-content"]'
            match_rule: 'first'
            remove_expressions:
                - '//div[@class="social"]'
    """
    config = yaml.load(config_yaml)

    # Test content extraction with removal
    expected_html = """
        <div class="post-content">
            <h1 class="post-title">Article title</h1>
            <div class="post-content">
                <p>Paragraph 1</p>
                <p>Paragraph 2</p>
                <p>Paragraph 3</p>
            </div>
        </div>"""
    validate_extract_element(response, config['article']['content'], expected_html)


def test_remove_multiple_nested_expressions():
    # Mock response using expected article data
    html = """<html>
    <head></head>
    <body>
        <div class="post-content">
            <h1 class="post-title">Article title</h1>
            <div class="post-content">
                <p>Paragraph 1</p>
                <p>Paragraph 2</p>
                <p>Paragraph 3</p>
            </div>
            <div class="bad">
                <div class="social">
                    <p>Twitter</p>
                    <p>Facebook</p>
                </div>
            </div>
        </div>
    </body>
    </html>"""
    response = TextResponse(url="http://example.com", body=html, encoding="utf-8")

    # Mock config
    config_yaml = """
    site_name: 'example.com'
    article:
        content:
            select_method: 'xpath'
            select_expression: '//div[@class="post-content"]'
            match_rule: 'first'
            remove_expressions:
                - '//div[@class="social"]'
                - '/div/div[@class="bad"]'
    """
    config = yaml.load(config_yaml)

    # Test content extraction with removal
    expected_html = """
        <div class="post-content">
            <h1 class="post-title">Article title</h1>
            <div class="post-content">
                <p>Paragraph 1</p>
                <p>Paragraph 2</p>
                <p>Paragraph 3</p>
            </div>
        </div>"""
    validate_extract_element(response, config['article']['content'], expected_html)


def test_xpath_extract_spec_default():
    expression = '//div[@class="content"]/a/text()'
    expected_extract_spec = {
        "select_method": "xpath",
        "select_expression": expression,
        "match_rule": "single",
        "warn_if_missing": True
    }
    extract_spec = xpath_extract_spec(expression)
    assert extract_spec == expected_extract_spec


def test_xpath_extract_spec_with_match_rule():
    expression = '//div[@class="content"]/a/text()'
    match_rule = "all"
    expected_extract_spec = {
        "select_method": "xpath",
        "select_expression": expression,
        "match_rule": match_rule,
        "warn_if_missing": True
    }
    extract_spec = xpath_extract_spec(expression, match_rule)
    assert extract_spec == expected_extract_spec


def test_extract_article_with_no_data_has_all_fields_present_but_null():
    # Mock response using expected article data
    html = """<html>
    <head></head>
    <body>
        <div>
            No article here.
        </div>
    </body>
    </html>"""
    response = TextResponse(url="http://example.com", body=html, encoding="utf-8")

    # Mock config
    config_yaml = """
    site_name: 'example.com'
    """
    config = yaml.load(config_yaml)

    expected_article = {
        'site_name': "example.com",
        'article_url': "http://example.com",
        'title': None,
        'byline': None,
        'publication_datetime': None,
        'content': "<div>No article here.</div>",
        'plain_content': "<div>No article here.</div>",
        'plain_text': [{'text': 'No article here.'}],
        'metadata': None
    }

    # Test
    article = extract_article(response, config)
    assert article == expected_article


def test_extract_datetime_iso8601_keep_timezone_keep():
    datetime_string = '2014-10-24T17:32:46+12:00'
    iso_string = extract_datetime_string(datetime_string, timezone=True)
    expected_iso_string = '2014-10-24T17:32:46+12:00'

    assert iso_string == expected_iso_string


def test_extract_datetime_iso8601_drop_timezone():
    datetime_string = '2014-10-24T17:32:46+12:00'
    iso_string = extract_datetime_string(datetime_string)
    expected_iso_string = '2014-10-24T17:32:46'

    assert iso_string == expected_iso_string


def test_extract_datetime_uk_format_without_timezone():
    datetime_string = '01/03/05'
    format_string = 'DD/MM/YY'
    iso_string = extract_datetime_string(datetime_string, format_string)
    expected_iso_string = '2005-03-01T00:00:00'

    assert iso_string == expected_iso_string


def test_extract_datetime_us_format_without_timezone():
    datetime_string = '03/01/05'
    format_string = 'MM/DD/YY'
    iso_string = extract_datetime_string(datetime_string, format_string)
    expected_iso_string = '2005-03-01T00:00:00'

    assert iso_string == expected_iso_string


def test_extract_datetime_byline_mmddyy_with_mmddyy_format():
    datetime_string = 'CHQ Staff | 10/17/18'
    format_string = 'MM/DD/YY'
    iso_string = extract_datetime_string(datetime_string, format_string)
    expected_iso_string = '2018-10-17T00:00:00'

    assert iso_string == expected_iso_string


def test_extract_datetime_byline_mmddyyyy_with_mmddyy_format():
    datetime_string = 'CHQ Staff | 10/17/2018'
    format_string = 'MM/DD/YY'
    iso_string = extract_datetime_string(datetime_string, format_string)
    expected_iso_string = '2018-10-17T00:00:00'

    assert iso_string == expected_iso_string


def test_extract_datetime_byline_mdyy_with_mdyy_format():
    datetime_string = 'CHQ Staff | 1/7/18'
    format_string = 'M/D/YY'
    iso_string = extract_datetime_string(datetime_string, format_string)
    expected_iso_string = '2018-01-07T00:00:00'

    assert iso_string == expected_iso_string


def test_extract_datetime_byline_0m0dyy_with_mdyy_format():
    datetime_string = 'CHQ Staff | 01/07/18'
    format_string = 'M/D/YY'
    iso_string = extract_datetime_string(datetime_string, format_string)
    expected_iso_string = '2018-01-07T00:00:00'

    assert iso_string == expected_iso_string


def test_extract_datetime_byline_mmddyy_with_mdyy_format():
    datetime_string = 'CHQ Staff | 12/17/18'
    format_string = 'M/D/YY'
    iso_string = extract_datetime_string(datetime_string, format_string)
    expected_iso_string = '2018-12-17T00:00:00'

    assert iso_string == expected_iso_string
