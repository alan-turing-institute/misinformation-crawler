from contextlib import suppress
import re
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import Rule
from .misinformationspider import MisinformationSpider


class MisinformationScattergunSpider(MisinformationSpider):
    """Crawl spider for websites containing articles that can be identified using a known URL format or content element."""
    def __init__(self, *args, **kwargs):
        super().__init__(name='scattergun', *args, **kwargs)

    def define_rules(self, link_extractor_kwargs):
        # For the scattergun strategy we only need one Rule for following links
        #  - follow all links (after removing duplicates) and pass them to parse_response
        #
        # NB. To suppress KeyErrors when retrieving optional arguments from
        # nested dictionary we need one suppress per retrieve.
        # NB. the link extractor takes iterables as arguments so we wrap the
        # config output in ()
        link_kwargs = dict(link_extractor_kwargs)
        with suppress(KeyError):
            link_kwargs['allow'] = (self.config['crawl_strategy']['scattergun']['url_must_contain'])
        with suppress(KeyError):
            link_kwargs['deny'] = (self.config['crawl_strategy']['scattergun']['url_must_not_contain'])
        link_rule = Rule(LinkExtractor(canonicalize=True, unique=True,
                                       attrs=('href', 'data-href', 'data-url'),
                                       **link_kwargs),
                         follow=True, callback='parse_response')
        self.rules = (link_rule, )

        # Optional regexes which test the URL to see if this is an article
        with suppress(KeyError):
            self.article_url_require_regex = re.compile(self.config['article']['url_must_contain'])
        with suppress(KeyError):
            self.article_url_reject_regex = re.compile(self.config['article']['url_must_not_contain'])
