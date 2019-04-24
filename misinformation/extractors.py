import copy
import logging
from misinformation.items import Article
from ReadabiliPy.readabilipy import parse_to_json
from ReadabiliPy.readabilipy.extractors import standardise_datetime_format

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

    # This is used to suppress warnings for missing/duplicate elements in cases
    # where they are known to break for some pages on certain sites.
    # The default is always to warn unless otherwise specified
    warn_if_missing = extract_spec.get('warn_if_missing', True)

    # Apply selector to response to extract chosen metadata field
    if method == 'xpath':
        # Extract all instances matching xpath expression
        elements = response.xpath(select_expression)
        # Remove all instances matching xpath expressions
        elements = remove_xpath_expressions(elements, remove_expressions)
        # Stringify elements then strip leading and trailing whitespace
        elements = elements.extract()
        elements = [item.strip() for item in elements]
        # If no elements are found then return None and log a warning.
        num_matches = len(elements)
        if num_matches == 0:
            extracted_element = None
            if warn_if_missing:
                logging.warning("No elements could be found from {url} matching {xpath} expected by match_rule '{rule}'. Returning None.".format(
                    url=response.url, xpath=select_expression, rule=match_rule))
        else:
            if match_rule == 'single':
                # Return first element, with a warning if more than one is found
                extracted_element = elements[0]
                if (num_matches != 1) and warn_if_missing:
                    logging.warning("Extracted {count} elements from {url} matching {xpath}. Only one element expected by match_rule '{rule}'. Returning first element.".format(
                        count=num_matches, url=response.url, xpath=select_expression, rule=match_rule))

            elif match_rule == 'first':
                extracted_element = elements[0]

            elif match_rule == 'last':
                extracted_element = elements[-1]

            elif match_rule == 'largest':
                extracted_element = sorted(elements, key=len)[-1]

            elif match_rule == 'concatenate':
                # Join non-empty elements together with commas
                extracted_element = ", ".join([x for x in elements if x])

            elif match_rule == 'group':
                # Group several elements and wrap them in a div
                extracted_element = "<div>" + "".join(elements) + "</div>"

            elif match_rule == 'all':
                # Keep the full list of elements
                extracted_element = elements

            else:
                extracted_element = None
                logging.debug("'{match_rule}' is not a valid match_rule".format(match_rule=match_rule))
    else:
        extracted_element = None
        logging.debug("'{method}' is not a valid select_expression".format(method=method))

    # This check ensures that blank strings/empty lists return as None
    if not extracted_element:
        extracted_element = None
    return extracted_element


def remove_xpath_expressions(input_selectors, remove_expressions):
    # Copy input_selectors to a new SelectorList as the remove operations will
    # modify them in-place (and we don't want to do that). We are not able to
    # use copy.deepcopy directly on the Selector as that class is incompatible
    # with it.
    output_selectors = type(input_selectors)()
    for selector in input_selectors:
        output_selectors.append(type(selector)(type=selector.type, root=copy.deepcopy(selector.root)))
    # We can access the lxml tree using the 'root' attribute - this is done in place
    for output_element in [s.root for s in output_selectors]:
        # Input element can be a string or an lxml.html.HtmlElement.
        # Ensure here that we do not call xpath() on a string
        if hasattr(output_element, 'xpath'):
            for expression in remove_expressions:
                # When searching html responses with xpath, an implicit
                # <html><body> wrapper is added. We don't want to require the
                # authors of site configs to have to worry about this, so for
                # absolute expressions (starting with /) we will attempt to
                # remove each of "<expr>", "/html/<expr>" and "/html/body/<expr>"
                # # Prefix relative paths with the implicit "/html/body"
                if expression.startswith('//'):
                    r_xpaths = [expression]
                else:
                    r_xpaths = [xpath.format(expression) for xpath in ('{}', '/html{}', '/html/body{}')]
                # For each element identified by each remove expression we find
                # the parent and then remove the child from it
                for r_xpath in r_xpaths:
                    for element_to_remove in output_element.xpath(r_xpath):
                        element_to_remove.getparent().remove(element_to_remove)
    return output_selectors


def extract_article(response, config, crawl_info=None, content_digests=False, node_indexes=False):
    # Create new article and set URL from the response (not the request).
    # The idea here is that this should be the same for the same article,
    # regardless of how it was requested (e.g. aliases, redirects etc).
    article = Article()
    article['site_name'] = config['site_name']
    article['article_url'] = response.url

    # Set default article fields by running readability on full page HTML
    page_spec = xpath_extract_spec("/html", "largest")
    page_html = extract_element(response, page_spec)

    # Always extract the article elements from the page_html with ReadabiliPy first
    # Then overwite with site config versions, if they exist
    default_readability_article = parse_to_json(page_html, content_digests, node_indexes, False)
    article['title'] = default_readability_article['title']
    article["publication_datetime"] = default_readability_article["date"]

    # Look for a set of extraction specifications
    if 'article' in config:
        # Extract article content
        if 'content' in config['article']:
            # Extract article content from specified element if present
            config['article']['content']['warn_if_missing'] = False
            article_html = extract_element(response, config['article']['content'])
            if article_html is not None:
                custom_readability_article = parse_to_json(article_html, content_digests, node_indexes, False)
                article['content'] = custom_readability_article['content']
                article['plain_content'] = custom_readability_article['plain_content']
                article['plain_text'] = custom_readability_article['plain_text']

        # Only try to extract other data if the article has identified content
        if 'content' in article:
            # Extract title if in config
            if 'title' in config['article']:
                article['title'] = extract_element(response, config['article']['title'])
            # Extract byline
            if 'byline' in config['article']:
                article['byline'] = extract_element(response, config['article']['byline'])
            # Extract publication_datetime
            if 'publication_datetime' in config['article']:
                datetime_string = extract_element(response, config['article']['publication_datetime'])
                if datetime_string:
                    article['publication_datetime'] = standardise_datetime_format(datetime_string)
    # ... otherwise simply use the default values from parsing the whole page
    else:
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
