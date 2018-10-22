
from misinformation.items import Article

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


def extract_article(response, config):
    article = Article()
    article['site_url'] = response.request.url
    if 'metadata' in config:
        # Attempt to extract all metadata fields
        for fieldname in config['metadata']:
            if fieldname in ['title', 'authors', 'publication_date']:
                #Store key metata as top-level article fields
                article[fieldname] = extract_field(response, config['metadata'], fieldname)
            else:
                # Store in metadata block
                article['metadata'][fieldname] = extract_field(response, config['metadata'], fieldname)
    return article
