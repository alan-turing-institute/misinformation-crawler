import datetime
from contextlib import suppress
from ReadabiliPy.readabilipy import parse_to_json
from .extract_element import extract_element
from .extract_datetime import extract_datetime_string


def xpath_extract_spec(xpath_expression, match_rule="single", warn_if_missing=True):
    extract_spec = {
        "select_method": "xpath",
        "select_expression": xpath_expression,
        "match_rule": match_rule,
        "warn_if_missing": warn_if_missing
    }
    return extract_spec


def extract_article(response, config, db_entry=None, content_digests=False, node_indexes=False):
    # Initialise an article dictionary
    article = {
        "site_name": config["site_name"],
        "article_url": response.url,
        "title": None,
        "byline": None,
        "publication_datetime": None,
        "content": None,
        "plain_content": None,
        "plain_text": None,
        "metadata": None,
    }
    # Include data from the db entry if available
    if db_entry:
        article["crawl_id"] = db_entry.crawl_id
        article["crawl_datetime"] = db_entry.crawl_datetime.replace(tzinfo=datetime.timezone.utc).isoformat()

    # Set default article fields by running readability on full page HTML
    page_html = extract_element(response, xpath_extract_spec("/html", "largest"))

    # Always extract the article elements from the page_html with ReadabiliPy first
    default_readability_article = parse_to_json(page_html, content_digests, node_indexes, use_readability=False)
    article['title'] = default_readability_article['title']
    article["publication_datetime"] = default_readability_article["date"]
    article["byline"] = default_readability_article["byline"]
    article["content"] = default_readability_article["content"]
    article["plain_content"] = default_readability_article["plain_content"]
    article["plain_text"] = default_readability_article["plain_text"]

    # Next overwite with site config versions, if they exist
    if "article" in config:
        article_html = extract_element(response, config["article"]["content"])
        if article_html:
            readabilipy_article = parse_to_json(article_html, content_digests, node_indexes, use_readability=False)
            article["content"] = readabilipy_article["content"]
            article["plain_content"] = readabilipy_article["plain_content"]
            article["plain_text"] = readabilipy_article["plain_text"]

        # Try to extract other data if the article has identified content
        if "content" in article and article["content"]:
            # Extract title if in config
            with suppress(KeyError):
                article["title"] = extract_element(response, config["article"]["title"])
            # Extract byline
            with suppress(KeyError):
                article["byline"] = extract_element(response, config["article"]["byline"])
            # Extract publication_datetime
            with suppress(KeyError):
                datetime_string = extract_element(response, config["article"]["publication_datetime"])
                if "datetime-format" in config["article"]["publication_datetime"]:
                    dt_format = config["article"]["publication_datetime"]["datetime-format"]
                    iso_string = extract_datetime_string(datetime_string, dt_format)
                else:
                    iso_string = extract_datetime_string(datetime_string)
                article["publication_datetime"] = iso_string

    # Extract additional article metadata
    if "metadata" in config:
        # Initialise metadata field
        metadata = dict()
        # Attempt to extract all metadata fields
        for fieldname in config["metadata"]:
            metadata[fieldname] = extract_element(response, config["metadata"][fieldname])
        article["metadata"] = metadata

    return article