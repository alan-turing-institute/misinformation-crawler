from contextlib import suppress
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from .misinformationmixin import MisinformationMixin


class ScattergunSpider(MisinformationMixin, CrawlSpider):
    """Crawl spider for websites containing articles that can be identified using a known URL format or content element."""
    name = 'scattergun'

    def __init__(self, config, *args, **kwargs):
        # For the scattergun strategy we only need one Rule for following links
        #  - follow all links (after removing duplicates) and pass them to parse_response
        #
        # NB. To suppress KeyErrors when retrieving optional arguments from
        # nested dictionary we need one suppress per retrieve.
        # NB. the link extractor takes iterables as arguments so we wrap the
        # config output in ()
        link_kwargs = self.common_link_kwargs(config)
        with suppress(KeyError):
            link_kwargs['allow'] = (config['crawl_strategy']['scattergun']['url_must_contain'])
        with suppress(KeyError):
            link_kwargs['deny'] = (config['crawl_strategy']['scattergun']['url_must_not_contain'])
        link_rule = Rule(LinkExtractor(canonicalize=True, unique=True,
                                       attrs=('href', 'data-href', 'data-url'),
                                       **link_kwargs),
                         follow=True, callback='parse_response')

        # Add link following rule
        self.rules = (link_rule, )

        # Load starting URLs
        self.start_urls = self.load_start_urls(config)

        # We need to call the super constructor AFTER setting any rules as it
        # calls self._compile_rules(), storing them in self._rules. If we call
        # the super constructor before we define the rules, they will not be
        # compiled and self._rules will be empty, even though self.rules will
        # have the right rules present.
        super().__init__(config, *args, **kwargs)
