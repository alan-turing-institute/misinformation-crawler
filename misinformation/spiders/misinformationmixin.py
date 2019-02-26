import datetime
import os
import re
import uuid
from urllib.parse import urlparse
from w3lib.url import url_query_cleaner
from scrapy.exceptions import CloseSpider
from scrapy.exporters import JsonItemExporter
from misinformation.extractors import extract_article


class MisinformationMixin():
    """Mixin to provide useful defaults for Misinformation crawl spiders."""
    # Define attributes that will be overridden by child classes
    url_regexes = {}

    def __init__(self, config, *args, **kwargs):
        # Load config and set spider display name to the name of the class
        self.config = config
        self.name = type(self).__name__

        # Set crawl-level metadata
        self.crawl_info = {
            'crawl_id': str(uuid.uuid4()),
            'crawl_datetime': datetime.datetime.utcnow().replace(microsecond=0).replace(tzinfo=datetime.timezone.utc).isoformat()
        }

        # Parse domain from start URL(s) and then restrict crawl to follow only
        # links in this domain plus additional (optional) user-specifed domains
        allowed_domains = self.config.get('additional_domains', [])
        allowed_domains += [urlparse(url).netloc for url in self.load_start_urls(self.config)]
        self.allowed_domains = list(set(allowed_domains))

        # Add flag to allow spider to be closed from inside a pipeline
        self.request_closure = False

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

        # Compile regexes
        self.url_regexes = dict((k, re.compile(v)) for k, v in self.url_regexes.items())

        # On first glance, this next line seems a bit weird, since
        # MisinformationMixin has no parents. However, this is needed to
        # correctly navigate Python's multiple inheritance structure - what it
        # will actually do is call the next constructor in MRO order for the
        # *derived* class, which will be the appropriate scrapy.Spider class
        super().__init__(*args, **kwargs)

    @staticmethod
    def load_start_urls(config):
        start_urls = config['start_url']
        if not isinstance(start_urls, list):
            start_urls = [start_urls]
        start_urls += config.get('article_list', [])
        return start_urls

    @staticmethod
    def common_link_kwargs(config):
        """Get common arguments for link extraction"""
        try:
            # Strip query strings from URLs if requested
            strip_query_strings = config['crawl_strategy']['strip_query_strings']
            if strip_query_strings:
                return {'process_value': url_query_cleaner}
        except KeyError:
            pass
        return {}

    def is_index_page(self, url):
        if 'index_page_require' in self.url_regexes and not self.url_regexes['index_page_require'].search(url):
            return False
        if 'index_page_reject' in self.url_regexes and self.url_regexes['index_page_reject'].search(url):
            return False
        return True

    def is_article(self, url):
        # Check whether we pass the (optional) requirements on the URL format
        if 'article_require' in self.url_regexes and not self.url_regexes['article_require'].search(url):
            return False
        if 'article_reject' in self.url_regexes and self.url_regexes['article_reject'].search(url):
            return False
        return True

    def parse_response(self, response):
        self.logger.info('Searching for an article at: {}'.format(response.url))

        # Always reject the front page of the domain since this will change
        # over time We need this for henrymakow.com as there is no sane URL
        # match rule for identifying articles and the index page parses as one.
        if urlparse(response.url).path in ['', '/', 'index.html']:
            return

        # Check whether we pass the (optional) requirements on the URL format
        if not self.is_article(response.url):
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
