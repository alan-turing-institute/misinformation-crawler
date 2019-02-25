from contextlib import suppress
import re
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import Rule
from .misinformationspider import MisinformationSpider


class MisinformationIndexPageSpider(MisinformationSpider):
    """Crawl spider for websites with lists of articles that are paged and navigable to with HTML links."""
    def __init__(self, *args, **kwargs):
        super().__init__(name='index_page', *args, **kwargs)

    def define_rules(self, link_extractor_kwargs):
        # For the index_page strategy we need:
        # 1. Rule for identifying index pages of links
        # 2. Rule for identifying article links
        link_kwargs = dict(link_extractor_kwargs)
        with suppress(KeyError):
            link_kwargs['allow'] = (self.config['crawl_strategy']['index_page']['url_must_contain'])
            self.index_page_url_require_regex = re.compile(link_kwargs['allow'])
        with suppress(KeyError):
            link_kwargs['deny'] = (self.config['crawl_strategy']['index_page']['url_must_not_contain'])
            self.index_page_url_reject_regex = re.compile(link_kwargs['deny'])
        if 'allow' not in link_kwargs and 'deny' not in link_kwargs:
            self.logger.warning("Using the 'index_page' crawl strategy without giving 'url_must_contain' or 'url_must_not_contain' arguments. Only the start_url will be used as an index page.")
            link_kwargs['deny'] = ('.*')
        index_page_rule = Rule(LinkExtractor(canonicalize=True, unique=True,
                                             attrs=('href', 'data-href', 'data-url'),
                                             **link_kwargs),
                               follow=True)

        # If neither 'index_page:article_links' nor 'article:url_must_contain'
        # are provided then all links will be parsed and if content is
        # extracted from them, they will be recorded.
        #
        # NB. To suppress KeyErrors when retrieving optional arguments from
        # nested dictionary we need one suppress per retrieve.
        # NB. the link extractor takes iterables as arguments so we wrap the
        # config output in ()
        link_kwargs = dict(link_extractor_kwargs)
        with suppress(KeyError):
            link_kwargs['restrict_xpaths'] = (self.config['crawl_strategy']['index_page']['article_links'])
        with suppress(KeyError):
            link_kwargs['allow'] = (self.config['article']['url_must_contain'])
        with suppress(KeyError):
            link_kwargs['deny'] = (self.config['article']['url_must_not_contain'])
        # Construct rule
        article_rule = Rule(LinkExtractor(canonicalize=True, unique=True,
                                          attrs=('href', 'data-href', 'data-url'),
                                          **link_kwargs),
                            callback='parse_response')

        # Use both rules
        self.rules = (index_page_rule, article_rule)
