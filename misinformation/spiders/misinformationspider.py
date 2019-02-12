from contextlib import suppress
import datetime
import uuid
import os
import re
from urllib.parse import urlparse
from scrapy.exceptions import CloseSpider
from scrapy.exporters import JsonItemExporter
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from misinformation.extractors import extract_article


class MisinformationSpider(CrawlSpider):
    """Generic crawl spider for websites that meet one of the following criteria
       (i)  Lists of articles are paged and navigable to with HTML links
       (ii) Articles can be identified using a known URL format or content element
       If they have metadata in a microdata format this can also be extracted
    """
    name = 'misinformation'
    exporter = None
    crawl_date = None

    def __init__(self, config, *args, **kwargs):
        self.config = config

        # Set crawl-level metadata
        self.crawl_info = {
            "crawl_id": str(uuid.uuid4()),
            "crawl_datetime": datetime.datetime.utcnow().replace(microsecond=0).replace(
                tzinfo=datetime.timezone.utc).isoformat()
        }

        # Parse domain from start URL(s) and use to restrict crawl to follow
        # only internal site links
        start_urls = self.config['start_url']
        if not isinstance(start_urls, list):
            start_urls = [start_urls]
        self.start_urls = start_urls
        site_domain = urlparse(start_urls[0]).netloc
        self.allowed_domains = [site_domain]
        self.article_url_require_regex = None
        self.article_url_reject_regex = None
        self.infinite_index_url_require_regex = None
        self.infinite_index_load_button_expression = None
        self.infinite_index_max_clicks = -1

        # We support three different link following strategies:
        # - 'index_page'
        # - 'infinite_index'
        # - 'scattergun' (default)
        try:
            crawl_strategy = config['crawl_strategy']['method']
        except KeyError:
            crawl_strategy = 'scattergun'

        # For the index_page and infinite_index strategies we need:
        # - one Rule for link pages
        # - one Rule for article pages
        if crawl_strategy in ['index_page', 'infinite_index']:
            # 1. Rule for identifying index pages of links
            try:
                index_page_url_must_contain = self.config['crawl_strategy'][crawl_strategy]['url_must_contain']
                index_page_rule = Rule(LinkExtractor(canonicalize=True, unique=True,
                                                     attrs=('href', 'data-href', 'data-url'),
                                                     allow=(index_page_url_must_contain)),
                                       follow=True)
            except KeyError:
                raise CloseSpider(reason="When using the 'index_page' or 'infinite_index' crawl strategies, the 'url_must_contain' argument is required.")

            # 2. Rule for identifying article links
            # If neither 'index_page_article_links' nor 'article:url_must_contain'
            # are provided then all links will be parsed and if content is
            # extracted from them, they will be recorded.
            #
            # Suppress KeyErrors when retrieving optional arguments from
            # nested dictionary - need one suppress per retrieve. NB. the link
            # extractor takes iterables as arguments so we wrap the config output in ()
            link_kwargs = {}
            with suppress(KeyError):
                link_kwargs["restrict_xpaths"] = (self.config['crawl_strategy'][crawl_strategy]['article_links'])
            with suppress(KeyError):
                link_kwargs["allow"] = (self.config['article']['url_must_contain'])
            with suppress(KeyError):
                link_kwargs["deny"] = (self.config['article']['url_must_not_contain'])
            # Construct rule
            article_rule = Rule(LinkExtractor(canonicalize=True, unique=True,
                                              attrs=('href', 'data-href', 'data-url'),
                                              **link_kwargs),
                                callback="parse_response")

            # Use both rules
            self.rules = (index_page_rule, article_rule)

            # If this is an infinite index, allow a maximum number of clicks to be specified
            if crawl_strategy == 'infinite_index':
                with suppress(KeyError):
                    self.infinite_index_max_clicks = self.config['crawl_strategy']['infinite_index']['max_button_clicks']
                self.infinite_index_url_require_regex = re.compile(index_page_url_must_contain)
                try:
                    self.infinite_index_load_button_expression = self.config['crawl_strategy']['infinite_index']['load_button_expression']
                except KeyError:
                    raise CloseSpider(reason="When using the 'infinite_index' crawl strategy, the 'load_button_expression' argument is required.")

        # For the scattergun strategy we only need one Rule for following links
        elif crawl_strategy == 'scattergun':
            # Follow all links (after removing duplicates) and pass them to
            # parse_response
            #
            # Suppress KeyErrors when retrieving optional arguments from
            # nested dictionary - need one suppress per retrieve. NB. the link
            # extractor takes iterables as arguments so we wrap the config output in ()
            link_kwargs = {}
            with suppress(KeyError):
                link_kwargs["allow"] = (self.config['crawl_strategy']['scattergun']['url_must_contain'])
            with suppress(KeyError):
                link_kwargs["deny"] = (self.config['crawl_strategy']['scattergun']['url_must_not_contain'])
            link_rule = Rule(LinkExtractor(canonicalize=True, unique=True,
                                           attrs=('href', 'data-href', 'data-url'),
                                           **link_kwargs),
                             follow=True, callback="parse_response")
            self.rules = (link_rule, )

            # Optional regexes for determining whether this is an article using the URL
            with suppress(KeyError):
                self.article_url_require_regex = re.compile(self.config['article']['url_must_contain'])
            with suppress(KeyError):
                self.article_url_reject_regex = re.compile(self.config['article']['url_must_not_contain'])

        else:
            raise CloseSpider(reason="crawl_strategy: '{0}' is not recognised".format(crawl_strategy))

        # Set up saving of raw responses for articles
        output_dir = "articles"
        output_file = "{}_full.txt".format(self.config['site_name'])
        # Ensure output directory exists
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
        output_path = os.path.join(output_dir, output_file)
        file_handle = open(output_path, 'wb')
        self.exporter = JsonItemExporter(file_handle)
        self.exporter.start_exporting()

        # Add flag to allow spider to be closed from inside a pipeline
        self.request_closure = False

        # We need to call the super constructor AFTER setting any rules as it calls self._compile_rules(), storing them
        # in self._rules. If we call the super constructor before we define the rules, they will not be compiled and
        # self._rules will be empty, even though self.rules will have the right rules present.
        super().__init__(*args, **kwargs)

    def parse_response(self, response):
        self.logger.info('Searching for an article at: {}'.format(response.url))

        # Always reject the front page of the domain since this will change over time
        # We need this for henrymakow.com as there is no sane URL match rule for identifying
        # articles and the index page parses as one.
        if urlparse(response.url).path in ['', '/', 'index.html']:
            return

        # Check whether we pass the (optional) requirements on the URL format
        if self.article_url_require_regex and not self.article_url_require_regex.search(response.url):
            return

        if self.article_url_reject_regex and self.article_url_reject_regex.search(response.url):
            return

        # Check whether we can extract an article from this page
        article = extract_article(response, self.config, crawl_info=self.crawl_info,
                                  content_digests=self.settings["CONTENT_DIGESTS"],
                                  node_indexes=self.settings["NODE_INDEXES"])
        if article['content'] is None:
            return

        # Save the full response and return parsed article
        self.logger.info('  article identification was successful')
        self.save_response(response)
        return article

    def save_response(self, response):
        # If we've hit the database size limit then stop crawling
        if self.request_closure:
            raise CloseSpider(reason="Closing spider due to database issue.")
        # Otherwise save the response
        raw_article = dict()
        raw_article['site_name'] = self.config['site_name']
        raw_article['crawl_datetime'] = self.crawl_info['crawl_datetime']
        raw_article['request_url'] = response.request.url
        raw_article['response_url'] = response.url
        raw_article['status'] = response.status
        raw_article['body'] = response.text
        self.logger.info('  saving response and adding to database')
        self.exporter.export_item(raw_article)

    def closed(self, reason):
        self.exporter.finish_exporting()
        self.exporter.file.close()
        self.logger.info('Spider closed: {} ({})'.format(self.config['site_name'], reason))
