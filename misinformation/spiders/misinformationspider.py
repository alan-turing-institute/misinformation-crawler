import datetime
import uuid
import os
from w3lib.url import url_query_cleaner
from urllib.parse import urlparse
from scrapy.exceptions import CloseSpider
from scrapy.exporters import JsonItemExporter
from scrapy.spiders import CrawlSpider
from misinformation.extractors import extract_article


class MisinformationSpider(CrawlSpider):
    """Generic crawl spider for websites that contain a series of articles."""
    name = 'misinformation'
    exporter = None
    crawl_date = None

    def __init__(self, name, config, *args, **kwargs):
        self.name = name
        self.config = config

        # Set crawl-level metadata
        self.crawl_info = {
            'crawl_id': str(uuid.uuid4()),
            'crawl_datetime': datetime.datetime.utcnow().replace(microsecond=0).replace(tzinfo=datetime.timezone.utc).isoformat()
        }

        # Construct list of start URL(s)
        start_urls = self.config['start_url']
        if not isinstance(start_urls, list):
            start_urls = [start_urls]
        start_urls += config.get('article_list', [])
        self.start_urls = start_urls

        # Parse domain from start URL(s) and then restrict crawl to follow only
        # links in this domain plus additional (optional) user-specifed domains
        allowed_domains = self.config.get('additional_domains', []) + [urlparse(url).netloc for url in start_urls]
        self.allowed_domains = list(set(allowed_domains))

        # Ensure that index/article page URL regexes are initialised
        self.index_page_url_require_regex = None
        self.index_page_url_reject_regex = None
        self.article_url_require_regex = None
        self.article_url_reject_regex = None

        # Add flag to allow spider to be closed from inside a pipeline
        self.request_closure = False

        # Strip query strings from URLs if requested
        try:
            strip_query_strings = config['crawl_strategy']['strip_query_strings']
            if strip_query_strings:
                link_extractor_kwargs = {'process_value': url_query_cleaner}
        except KeyError:
            link_extractor_kwargs = {}

        # Set up the link following rules
        self.define_rules(link_extractor_kwargs)

        # Set up saving of raw responses for articles
        output_dir = 'articles'
        output_file = '{}_full.txt'.format(self.config['site_name'])
        # Ensure output directory exists
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
        output_path = os.path.join(output_dir, output_file)
        file_handle = open(output_path, 'wb')
        self.exporter = JsonItemExporter(file_handle)
        self.exporter.start_exporting()

        # We need to call the super constructor AFTER setting any rules as it
        # calls self._compile_rules(), storing them in self._rules. If we call
        # the super constructor before we define the rules, they will not be
        # compiled and self._rules will be empty, even though self.rules will
        # have the right rules present.
        super().__init__(*args, **kwargs)

    def define_rules(self, link_extractor_kwargs):
        raise NotImplementedError("This method should be overridden by child classes")

    def parse_response(self, response):
        self.logger.info('Searching for an article at: {}'.format(response.url))

        # Always reject the front page of the domain since this will change
        # over time We need this for henrymakow.com as there is no sane URL
        # match rule for identifying articles and the index page parses as one.
        if urlparse(response.url).path in ['', '/', 'index.html']:
            return

        # Check whether we pass the (optional) requirements on the URL format
        if self.article_url_require_regex and not self.article_url_require_regex.search(response.url):
            return

        if self.article_url_reject_regex and self.article_url_reject_regex.search(response.url):
            return

        # Check whether we can extract an article from this page
        article = extract_article(response, self.config, crawl_info=self.crawl_info,
                                  content_digests=self.settings['CONTENT_DIGESTS'],
                                  node_indexes=self.settings['NODE_INDEXES'])
        if article['content'] is None:
            return

        # Save the full response and return parsed article
        self.logger.info('  article identification was successful')
        self.save_response(response)
        return article

    def save_response(self, response):
        # If the closure flag has been set then stop crawling
        if self.request_closure:
            raise CloseSpider(reason='Ending crawl cleanly after a close request.')
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
