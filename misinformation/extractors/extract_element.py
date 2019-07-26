import copy
import logging


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


def extract_element(response, extract_spec, postprocessing_fn=None):
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
        selectors = response.xpath(select_expression)
        # Remove all instances matching xpath expressions
        selectors = remove_xpath_expressions(selectors, remove_expressions)
        # Stringify elements then strip leading and trailing whitespace
        elements = selectors.extract()
        elements = [item.strip() for item in elements]
        # Additional processing for each element, if required
        if postprocessing_fn:
            elements = [elem for elem in map(postprocessing_fn, elements) if elem]
        # If no elements are found then return None and log a warning.
        num_matches = len(elements)
        if num_matches == 0:
            extracted_element = None
            if warn_if_missing:
                logging.warning("No elements could be found from %s matching %s expected by match_rule '%s'. Returning None.",
                                response.url, select_expression, match_rule)
        else:
            if match_rule == 'single':
                # Return first element, with a warning if more than one is found
                extracted_element = elements[0]
                if (num_matches != 1) and warn_if_missing:
                    logging.warning("Extracted %s elements from %s matching %s. Only one element expected by match_rule '%s'. Returning first element.",
                                    num_matches, response.url, select_expression, match_rule)

            elif match_rule == 'first':
                extracted_element = elements[0]

            elif match_rule == 'last':
                extracted_element = elements[-1]

            elif match_rule == 'largest':
                extracted_element = sorted(elements, key=len)[-1]

            elif match_rule == 'concatenate':
                # Join non-empty elements together with no spacing
                extracted_element = "".join([x for x in elements if x])

            elif match_rule == 'comma_join':
                # Join non-empty elements together with commas
                extracted_element = ", ".join([x for x in elements if x])

            elif match_rule == 'concatenate_with_space':
                # Join non-empty elements together with single spaces
                extracted_element = " ".join([x for x in elements if x])

            elif match_rule == 'group':
                # Group several elements and wrap them in a div
                extracted_element = "<div>" + "".join(elements) + "</div>"

            elif match_rule == 'all':
                # Keep the full list of elements
                extracted_element = elements

            else:
                extracted_element = None
                logging.debug("'%s' is not a valid match_rule", match_rule)
    else:
        extracted_element = None
        logging.debug("'%s' is not a valid select_expression", method)

    # This check ensures that blank strings/empty lists return as None
    if not extracted_element:
        extracted_element = None
    return extracted_element
