from contextlib import suppress
from scrapy.spiders import SitemapSpider
from .misinformationmixin import MisinformationMixin


class XMLSitemapSpider(MisinformationMixin, SitemapSpider):
    """Crawl spider for websites with XML sitemaps."""

    def __init__(self, config, *args, **kwargs):
        self.sitemap_urls = self.load_start_urls(config)

        # Define which sitemap index links to follow
        self.sitemap_follow = []
        with suppress(KeyError):
            for regex in config['crawl_strategy']['sitemap']['url_must_contain']:
                self.sitemap_follow.append(regex)
        if not self.sitemap_follow:
            self.sitemap_follow = ['']

        # For the sitemap strategy we need a single rule to identify article links:
        self.sitemap_rules = []
        with suppress(KeyError):
            for regex in config['article']['url_must_contain']:
                self.sitemap_rules.append((regex, 'parse_response'))

        # Optional regexes which test the URL to see if this is an article
        with suppress(KeyError):
            self.url_regexes['article_require'] = config['article']['url_must_contain']
        with suppress(KeyError):
            self.url_regexes['article_reject'] = config['article']['url_must_not_contain']

        # We need to call the super constructor AFTER setting any rules as it
        # calls self._compile_rules(), storing them in self._rules. If we call
        # the super constructor before we define the rules, they will not be
        # compiled and self._rules will be empty, even though self.rules will
        # have the right rules present.
        super().__init__(config, *args, **kwargs)
