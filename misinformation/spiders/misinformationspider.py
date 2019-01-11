import iso8601
from misinformation.items import Article
from misinformation.extractors import extract_article
import datetime
import os
import re
from scrapy.exceptions import CloseSpider
from scrapy.exporters import JsonItemExporter
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from urllib.parse import urlparse
import uuid

# Generic crawl spider for websites that meet the following criteria
# (i) Lists of articles are paged and navigable to with HTML links
# (ii) Has metadata in a microdata format
class MisinformationSpider(CrawlSpider):
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

        # Parse domain from start URL and use to restrict crawl to follow only internal site links
        start_url = self.config['start_url']
        self.start_urls = [start_url]
        site_domain = urlparse(start_url).netloc
        self.allowed_domains = [site_domain]

        # We support two different link following strategies: 'paged' and 'all' (default)
        try:
            crawl_strategy = config['crawl_strategy']['method']
        except KeyError:
            crawl_strategy = 'scattergun'

        # - For the paged strategy we need two Rules: one for link pages; one for article pages
        if crawl_strategy == 'index_page':
            # 1. Rule for identifying index pages of links
            try:
                index_page_url_match = self.config['crawl_strategy']['index_page_url_match']
                index_page_rule = Rule(LinkExtractor(canonicalize=True, unique=True,
                                                     allow=(index_page_url_match)),
                                       follow=True)
            except KeyError:
                raise CloseSpider(reason="When using the 'index_page' crawl strategy, the 'index_page_url_match' argument is required.")

            # 2. Rule for identifying article links
            rule_kwargs = {}
            try:
                # If no options are provided then all links from index pages are allowed
                rule_kwargs["restrict_xpaths"] = self.config['crawl_strategy']['index_page_article_links']
                rule_kwargs["allow"] = self.config.get('article_url_match', '')
                article_rule = Rule(LinkExtractor(**rule_kwargs, callback='parse_response'))
            except KeyError:
                # We don't require both options to be present in the config
                pass

            # Use both rules
            self.rules = (index_page_rule, article_rule)

        # - For the scattergun strategy we only need one Rule for which links to follow
        elif crawl_strategy == 'scattergun':
            # Follow all links (after removing duplicates) and pass them to parse_response
            link_rule = Rule(LinkExtractor(canonicalize=True, unique=True,
                                           allow=(self.config.get('scattergun_url_must_contain', '')),
                                           deny=(self.config.get('scattergun_url_must_not_contain', ''))),
                             follow=True, callback="parse_response")
            self.rules = (follow_rule)

            # Optional regex for determining whether this is an article using the URL
            self.article_url_regex = re.compile(self.config.get('article_url_match', ''))

        else:
            raise CloseSpider(reason="crawl_strategy: '{0}' is not recognised".format(crawl_strategy))

        # Set up saving of raw responses for articles
        output_dir = "articles"
        output_file = "{}_full.txt".format(self.config['site_name'])
        # Ensure output directory exists
        if not (os.path.isdir(output_dir)):
            os.makedirs(output_dir)
        output_path = os.path.join(output_dir, output_file)
        f = open(output_path, 'wb')
        self.exporter = JsonItemExporter(f)
        self.exporter.start_exporting()

        # Add flag to allow spider to be closed from inside a pipeline
        self.database_limit = False

        # We need to call the super constructor AFTER setting any rules as it calls self._compile_rules(), storing them
        # in self._rules. If we call the super constructor before we define the rules, they will not be compiled and
        # self._rules will be empty, even though self.rules will have the right rules present.
        super().__init__(*args, **kwargs)

    def parse_response(self, response):
        self.logger.info('Parsing response for: {}'.format(response.url))

        # Always reject the front page of the domain since this will change over time
        # Currently testing this using simple pattern matching
        # - could be changed to something more sophisticated in future
        if urlparse(response.url).path in ['', '/', 'index.html']:
            return

        # Check whether we pass the (optional) requirement on the URL format
        if self.article_url_regex and not self.article_url_regex.search(response.url):
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
        if self.database_limit:
            raise CloseSpider(reason="Database size exceeded.")
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
        return

    def closed(self, reason):
        self.exporter.finish_exporting()
        self.exporter.file.close()
        self.logger.info('Spider closed: {} ({})'.format(self.config['site_name'], reason))
