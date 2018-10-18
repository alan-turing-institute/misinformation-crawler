import pytest
import json
import os
import glob
import pkg_resources
from misinformation.extractors import extract_article, extract_field
from scrapy.http import Request,  TextResponse
import yaml

CONFIG_FILE = pkg_resources.resource_string("misinformation", "../site_configs.yml")

# Load site-specific spider configurations
CONFIGS = yaml.load(CONFIG_FILE)

SITE_NAMES = [site_name for site_name in CONFIGS]


def config_for_site(site_name):
    return CONFIGS[site_name]


def extract_xpath(html, xpath):
    response = TextResponse('article.html', body=html, encoding='utf-8')
    return response.xpath(xpath).extract_first()


def validate_element_extraction(html, xpath, expected):
    actual = extract_xpath(html, xpath)
    assert actual == expected


def article_stems_for_site(site_name):
    html_file_paths = glob.glob(os.path.join(os.path.dirname(__file__),site_name,'*.html'))
    article_stems = []
    for html_file_path in html_file_paths:
        path, file = os.path.split(html_file_path)
        article_stems.append(file.split('_')[0])
    return article_stems


def article_infos_for_site(site_name):
    article_stems = article_stems_for_site(site_name)
    return [{"site_name": site_name, "article_stem": article_stem} for article_stem in article_stems]


def article_infos_for_all_sites(site_names):
    article_infos = []
    for site_name in site_names:
        article_infos = article_infos + article_infos_for_site(site_name)
    return article_infos


@pytest.fixture(params=article_infos_for_all_sites(SITE_NAMES))
def article_info(request):
    return request.param


def test_article_data_extraction(article_info):
    print(article_info)
    site_name = article_info['site_name']
    config = CONFIGS[site_name]
    article_stem = article_info['article_stem']
    # Get test data from file
    data_dir = os.path.join(os.path.dirname(__file__), site_name)
    html_filename = article_stem + '_article.html'
    json_filename = article_stem + '_extracted_data.json'
    html_filepath = os.path.join(data_dir, html_filename)
    json_filepath = os.path.join(data_dir, json_filename)
    with open(html_filepath) as h, open(json_filepath) as j:
        html = h.read()
        expected_article = json.loads(j.read())

    # Construct response from html
    url = "http://{site}/{path}".format(site=site_name, path=html_filename)
    request = Request(url=url)
    response = TextResponse(url=url, body=html, encoding='utf-8', request=request)

    # Test title extraction
    expected_title = expected_article['title']
    title = extract_field(response, config['metadata'], 'title')
    assert title == expected_title

    # Test full article extraction for supported fields
    article = extract_article(response, config)
    print(article)
    assert article['title'] == expected_article['title']


