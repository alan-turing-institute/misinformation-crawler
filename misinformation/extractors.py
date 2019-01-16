import arrow
import logging
from misinformation.items import Article
import pendulum
from ReadabiliPy.readabilipy import parse_to_json
import warnings
from scrapy.http import XmlResponse


# Helper function for selecting elements by class name. This is a little complex in xpath as
# (i) div[@class="<classname>"] only matches a single exact class name (no whitespace padding or multiple classes)
# (ii) div[contains(@class, "<classname>")] will also select class names containing <classname> as a substring
def xpath_class(element, class_name):
    return "{element}[contains(concat(' ', normalize-space(@class), ' '), ' {class_name} ')]".format(
        class_name=class_name, element=element)


def xpath_extract_spec(xpath_expression, match_rule="single", warn_if_missing=True):
    extract_spec = {
        "select_method": "xpath",
        "select_expression": xpath_expression,
        "match_rule": match_rule,
        "warn_if_missing": warn_if_missing
    }
    return extract_spec

def extract_element(response, extract_spec):
    # Extract selector specification
    method = extract_spec['select_method']
    select_expression = extract_spec['select_expression']
    remove_expressions = extract_spec.get('remove_expressions', [])
    # Default match rule to 'single', which will log a warning message if multiple matches are found
    match_rule = extract_spec.get('match_rule', 'single')

    # This is used to suppress warnings for missing/duplicate elements
    # in cases where they are known to break for some pages on certain sites
    # The default is always to warn unless otherwise specified
    warn_if_missing = extract_spec.get('warn_if_missing', True)

    # Apply selector to response to extract chosen metadata field
    if method == 'xpath':
        # Extract all instances matching xpath expression
        elements = response.xpath(select_expression).extract()
        # Strip leading and trailing whitespace
        elements = [item.strip() for item in elements]
        # If no elements are found then return None and log a warning.
        num_matches = len(elements)
        if num_matches == 0:
            extracted_string = None
            if warn_if_missing:
                logging.warning("No elements could be found from {url} matching {xpath} expected by match_rule '{rule}'. Returning None.".format(
                    url=response.url, xpath=select_expression, rule=match_rule))
        else:
            if match_rule == 'single':
                # Return first element, with a warning if more than one is found
                extracted_string = elements[0]
                if (num_matches != 1) and warn_if_missing:
                    logging.warning("Extracted {count} elements from {url} matching {xpath}. Only one element expected by match_rule '{rule}'. Returning first element.".format(
                        count=num_matches, url=response.url, xpath=select_expression, rule=match_rule))

            elif match_rule == 'first':
                extracted_string = elements[0]

            elif match_rule == 'last':
                extracted_string = elements[-1]

            elif match_rule == 'largest':
                extracted_string = sorted(elements, key = lambda elem: len(elem))[-1]

            elif match_rule == 'concatenate':
                # Join non-empty elements together with commas
                extracted_string = ", ".join([x for x in elements if x])

            elif match_rule == 'group':
                # Group several elements and wrap them in a div
                extracted_string = "<div>" + "".join(elements) + "</div>"

            elif match_rule == 'all':
                # Nothing to do so return here. This avoids having to deal with
                # the special case interaction where extracted_string is a list
                # but we also have a non-empty remove_expressions and therefore
                # we need to apply each remove_expression to each element of
                # extracted_string
                return elements

            else:
                extracted_string = None
                logging.debug("'{match_rule}' is not a valid match_rule".format(
                              match_rule=match_rule))
    else:
        extracted_string = None
        logging.debug("'{method}' is not a valid select_expression".format(
                      method=method))

    # Sequentially find and remove elements if specified in the config
    for remove_expression in remove_expressions:
        if extracted_string:
            # Use XmlResponse as TextResponse would wrap the string in <html> and <body> tags
            xml_response = XmlResponse(body=extracted_string, url=response.url, encoding=response.encoding)
            for substr_to_remove in xml_response.xpath(remove_expression).extract():
                # This is safe even if one substr_to_remove contains another inside
                # it, since the strings are produced in the order that they appear
                # in the tree, and therefore the outside string will be removed
                # before the inside one (if this order was reversed there would be
                # a problem).
                extracted_string = extracted_string.replace(substr_to_remove, "")

    # This check ensures that blank strings return as None
    if not extracted_string:
        extracted_string = None
    return extracted_string


def extract_datetime_string(date_string, date_format=None, timezone=False):
    # First try pendulum as it seems to have fewer bugs
    # Source: http://blog.eustace.io/please-stop-using-arrow.html
    datetime = pendulum_datetime_extract(date_string, date_format)
    if not datetime:
        # then try arrow as it can extract dates froom within longer non-date strings
        datetime = arrow_datetime_extract(date_string, date_format)

    # If a datetime is successfully extracted, re-export as ISO-8601 string.
    # NOTE: Datetime objects generated by both arrow and pendulum support the format() method
    if datetime:
        if timezone:
            out_string = datetime.format('YYYY-MM-DDTHH:mm:ssZ')
        else:
            out_string = datetime.format('YYYY-MM-DDTHH:mm:ss')
    else:
        out_string = None
    return out_string


def pendulum_datetime_extract(date_string, date_format=None):
    # Attempt to extract the date using the specified format if provided
    try:
        if date_format:
            if "unix" in date_format:
                if "milliseconds" in date_format:
                    date_string = date_string[:-3]
                datetime = pendulum.from_timestamp(int(date_string))
            else:
                datetime = pendulum.from_format(date_string, date_format)
        else:
            # Assume ISO-8601
            datetime = pendulum.parse(date_string)
    except (ValueError, TypeError, RuntimeError):
        datetime = None
    return datetime


def arrow_datetime_extract(date_string, date_format=None):
    datetime = None
    # Some tricks to avoid some undesired outcomes:
    # (1) Arrow will match the first/last digits of a 4-digit year if passed a 2-digit year format
    #
    if date_format:
        # If 2-digit year at start or end of format string, first try to extract date with equivalent
        arrow_separators = ['-', '/', '.']
        if date_format[:2] == 'YY' and date_format[2] in arrow_separators:
            datetime = arrow_datetime_extract(date_string, "YY{}".format(date_format))
        if not datetime and date_format[-2:] == 'YY' and date_format[-3] in arrow_separators:
            datetime = arrow_datetime_extract(date_string, "{}YY".format(date_format))

    if not datetime:
        try:
            if date_format:
                datetime = arrow.get(date_string, date_format)
            else:
                # Assume ISO-8601
                datetime = arrow.get(date_string)
        except (ValueError, TypeError, RuntimeError):
            # If we fail to parse a datetime, return None
            datetime = None
    return datetime


def extract_article(response, config, crawl_info=None, content_digests=False, node_indexes=False):
    # Create new article and set URL from the response (not the request). The idea here is that this should be the same
    # for the same article, regardless of how it was requested (e.g. aliases, redirects etc).
    article = Article()
    article['site_name'] = config['site_name']
    article['article_url'] = response.url

    # Set default article fields by running readability on full page HTML
    page_spec = xpath_extract_spec("/html", "largest")
    page_html = extract_element(response, page_spec)

    # Look for a set of extraction specifications
    if 'article' in config:
        # Extract title
        if 'title' in config['article']:
            article['title'] = extract_element(response, config['article']['title'])
        # Extract byline
        if 'byline' in config['article']:
            article['byline'] = extract_element(response, config['article']['byline'])
        # Extract publication_datetime
        if 'publication_datetime' in config['article']:
            datetime_string = extract_element(response, config['article']['publication_datetime'])
            if 'datetime-format' in config['article']['publication_datetime']:
                format = config['article']['publication_datetime']['datetime-format']
                iso_string = extract_datetime_string(datetime_string, format)
            else:
                iso_string = extract_datetime_string(datetime_string)
            article['publication_datetime'] = iso_string
        # Extract article content
        if 'content' in config['article']:
            # Extract article content from specified element
            article_html = extract_element(response, config['article']['content'])
            if article_html is not None:
                custom_readability_article = parse_to_json(article_html, content_digests, node_indexes, False)
                article["content"] = custom_readability_article["content"]
                article["plain_content"] = custom_readability_article["plain_content"]
                article["plain_text"] = custom_readability_article["plain_text"]
    # ... otherwise simply use the default values from parsing the whole page
    else:
        default_readability_article = parse_to_json(page_html, content_digests, node_indexes, False)
        article["title"] = default_readability_article["title"]
        article["byline"] = default_readability_article["byline"]
        article["content"] = default_readability_article["content"]
        article["plain_content"] = default_readability_article["plain_content"]
        article["plain_text"] = default_readability_article["plain_text"]


    # Extract additional article metadata
    if 'metadata' in config:
        # Initialise metadata field
        article['metadata'] = dict()
        # Attempt to extract all metadata fields
        for fieldname in config['metadata']:
            article['metadata'][fieldname] = extract_element(response, config['metadata'][fieldname])

    # Add crawl information if provided
    if crawl_info:
        article["crawl_id"] = crawl_info["crawl_id"]
        article["crawl_datetime"] = crawl_info["crawl_datetime"]

    # Ensure all fields included in article even if no data extracted for them
    if 'title' not in article:
        article['title'] = None
    if 'byline' not in article:
        article['byline'] = None
    if 'publication_datetime' not in article:
        article['publication_datetime'] = None
    if 'content' not in article:
        article['content'] = None
    if 'plain_content' not in article:
        article['plain_content'] = None
    if 'plain_content' not in article:
        article['plain_text'] = None
    if 'metadata' not in article:
        article['metadata'] = None

    return article
