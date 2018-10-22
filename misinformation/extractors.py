import itertools
from misinformation.items import Article
import re


# Helper function for selecting elements by class name. This is a little complex in xpath as
# (i) div[@class="<classname>"] only matches a single exact class name (no whitespace padding or multiple classes)
# (ii) div[contains(@class, "<classname>")] will also select class names containing <classname> as a substring
def xpath_class(element, class_name):
    return "{element}[contains(concat(' ', normalize-space(@class), ' '), ' {class_name} ')]".format(
        class_name=class_name, element=element)


def extract_field(response, metadata_spec, fieldname):
    # Validate metadata specification contains specification for chosen metadata field
    if fieldname in metadata_spec:
        extract_spec = metadata_spec[fieldname]
    else:
        raise KeyError("'{field}' not present in metadata specification.".format(field=fieldname))
    if 'select-method' not in extract_spec:
        raise KeyError("'select-method' not present in '{field}' metadata specification".format(field=fieldname))
    if 'select-expression' not in extract_spec:
        raise KeyError("'select-expression' not present in '{field}' metadata specification".format(field=fieldname))

    # Extract selector specification
    method = extract_spec['select-method']
    expression = extract_spec['select-expression']

    # Apply selector to response to extract chosen metadata field (stripping leading and trailing whitespace)
    if method == 'xpath':
        field = response.xpath(expression).extract_first().strip()
    else:
        raise ValueError("{method} is not a valid select-expression".format(method=method))
    return field


def paragraphs_to_plain_content(paragraphs):
    # Break paragraphs containing <br/> or <br> into multiple paragraphs (both valid HTML line break
    paragraphs = list(itertools.chain(*[p.split("<br/>") for p in paragraphs]))
    paragraphs = list(itertools.chain(*[p.split("<br>") for p in paragraphs]))
    # Strip HTML tags and leading / trailing whitespace
    paragraphs = [re.sub("<.*?>", "", p).strip() for p in paragraphs]
    # Drop empty paragraphs
    paragraphs = list(filter(None, paragraphs))
    return paragraphs


def extract_content(response, config):
    # 1. Extract structured article content. We just extract all paragraphs within the article's parent container
    select_xpath = '//{content}'.format(content=xpath_class(config['article_element'], config['article_class']))
    paragraphs = response.xpath(select_xpath).xpath('.//p').extract()
    # Ensure paragraphs are encoded as unicose
    return paragraphs, paragraphs_to_plain_content(paragraphs)


def extract_article(response, config):
    article = Article()
    article['article_url'] = response.request.url
    if 'metadata' in config:
        # Attempt to extract all metadata fields
        for fieldname in config['metadata']:
            if fieldname in ['title', 'authors', 'publication_date']:
                # Store key metata as top-level article fields
                article[fieldname] = extract_field(response, config['metadata'], fieldname)
            else:
                # Store in metadata block
                article['metadata'][fieldname] = extract_field(response, config['metadata'], fieldname)
    # Extract raw microdata content
    # article['metadata']['microformats'] = extruct.extract(response.body_as_unicode(), response.url)
    # Extract article content
    article['structured_content'], article['plain_content'] = extract_content(response, config)
    return article
