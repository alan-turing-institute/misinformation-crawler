import pytest
import json
import os
import glob
import pkg_resources
from misinformation.extractors import extract_article, extract_element, xpath_extract_spec
from scrapy.http import Request,  TextResponse
import yaml

SITE_TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "site_test_data")
UNIT_TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "unit_test_data")
SITE_CONFIG_FILE = pkg_resources.resource_string("misinformation", "../site_configs.yml")

# Load site-specific spider configurations
SITE_CONFIGS = yaml.load(SITE_CONFIG_FILE)
SITE_NAMES = [] #["addictinginfo.com"] #[site_name for site_name in CONFIGS]


# ================= HELPER FUNCTIONS =================
def config_for_site(site_name):
    return SITE_CONFIGS[site_name]


def response_from_html_file(html_filepath):
    with open(html_filepath) as f:
        html = f.read()
    filename = os.path.split(html_filepath)[-1]
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
        path, file = os.path.split(html_file_path)
        article_stems.append(file.split('_')[0])
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


@pytest.fixture(params=article_infos_for_all_sites(SITE_NAMES))
def article_info(request):
    return request.param


# ================= TEST FUNCTIONS =================
def validate_extract_element(html, extract_spec, expected):
    actual = extract_element(html, extract_spec)
    assert actual == expected


def validate_extract_article(response, config, expected):
    article = extract_article(response, config)
    # Check title extraction
    assert article['title'] == expected['title']
    # Check plain content extraction
    assert article['plain_content'] == expected['plain_content']


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
        site_name: 'addictinginfo.com'
        start_url: 'http://addictinginfo.com/category/news/'
        follow_url_path: 'page/'
        article_url_xpath: '//h2[@class="entry-title"]/a'
    """
    config = yaml.load(config_yaml)

    # Test
    article = extract_article(response, config)
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
        site_name: 'addictinginfo.com'
        start_url: 'http://addictinginfo.com/category/news/'
        follow_url_path: 'page/'
        article_url_xpath: '//h2[@class="entry-title"]/a'
    """
    config = yaml.load(config_yaml)

    # Mock crawl info
    crawl_info = {
        "crawl_id": "bdbcf1cf-e4,1f-4c10-9958-4ab1b07e46ae",
        "crawl_datetime": "2018-10-17T20:25:34.2345+00:00",
        "site_name": "addictinginfo.com"
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
        article_element: 'div'
        article_class: 'post-content'
        article:
            title:
                select-method: 'xpath'
                select-expression: '//p[@id="test-custom-title"]/text()'
                match-rule: 'single'

    """
    config = yaml.load(config_yaml)

    # Test
    article = extract_article(response, config)
    assert article == expected_article


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
        article_element: 'div'
        article_class: 'post-content'
        article:
            byline:
                select-method: 'xpath'
                select-expression: '//p[@id="test-custom-byline"]/text()'
                match-rule: 'single'

    """
    config = yaml.load(config_yaml)

    # Test
    article = extract_article(response, config)
    assert article == expected_article


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
        article_element: 'div'
        article_class: 'post-content'
        article:
            content:
                select-method: 'xpath'
                select-expression: '//div[@class="entry entry-content"]'
                match-rule: 'single'

    """
    config = yaml.load(config_yaml)

    # Test
    article = extract_article(response, config)
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
    article_element: 'div'
    article_class: 'post-content'
    article:
        title:
            select-method: 'xpath'
            select-expression: '//h1[@class="post-title"]/text()'
            match-rule: 'single'
        paragraphs:
            select-method: 'xpath'
            select-expression: '//p/text()'
            match-rule: 'all'
        first-paragraph:
            select-method: 'xpath'
            select-expression: '//p/text()'
            match-rule: 'first'

"""
    config = yaml.load(config_yaml)

    # Test single element extraction
    expected_title = "Article title"
    validate_extract_element(response, config['article']['title'], expected_title)
    # Test all element extraction
    expected_paragraphs = ["Paragraph 1", "Paragraph 2", "Paragraph 3"]
    validate_extract_element(response, config['article']['paragraphs'], expected_paragraphs)
    # Test first element extraction
    expected_first_paragraph = "Paragraph 1"
    validate_extract_element(response, config['article']['first-paragraph'], expected_first_paragraph)


def test_xpath_extract_spec_default():
    expression = '//div[@class="content"]/a/text()'
    expected_extract_spec = {
        "select-method": "xpath",
        "select-expression": expression,
        "match-rule": "single"
    }
    extract_spec = xpath_extract_spec(expression)
    assert extract_spec == expected_extract_spec


def test_xpath_extract_spec_with_match_rule():
    expression = '//div[@class="content"]/a/text()'
    match_rule = "all"
    expected_extract_spec = {
        "select-method": "xpath",
        "select-expression": expression,
        "match-rule": match_rule
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
    article_element: 'div'
    article_class: 'post-content'

"""
    config = yaml.load(config_yaml)

    expected_article = {
        'article_url': "http://example.com",
        'title': None,
        'byline': None,
        'published_date': None,
        'content': None,
        'plain_content': None,
        'metadata': None
    }

    # Test
    article = extract_article(response, config)
    assert article == expected_article

