import iso8601
from misinformation.items import Article
from misinformation.extractors import extract_article
import datetime
import os
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
        start_url = self.config['start_url']
        self.start_urls = [start_url]
        # Parse domain from start URL and use to restrict crawl to follow only internal site links
        site_domain = urlparse(start_url).netloc
        self.allowed_domains = [site_domain]

        # Rules for finding article links
        # 1. Rule for identifying links to follow to pages that might have more articles links
        if self.config['article_search'] == 'paged':
            follow_rule = Rule(LinkExtractor(allow=(self.config['follow_url_path'], ),))
        # 2. Rule for identifying article links
        # 2a. We can match the link URL itself to a pattern
        if 'article_url_path' in self.config:
            article_rule = Rule(LinkExtractor(
                allow=(self.config['article_url_path'],)), callback='parse_item')
        # 2b. We need to inspect the element containing the link
        elif 'article_url_xpath' in self.config:
            article_rule = Rule(LinkExtractor(
                restrict_xpaths=(self.config['article_url_xpath'],)), callback='parse_item')
        self.rules = (follow_rule, article_rule, )

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
        self.close_down = False

        # We need to call the super constructor AFTER setting any rules as it calls self._compile_rules(), storing them
        # in self._rules. If we call the super constructor before we define the rules, they will not be compiled and
        # self._rules will be empty, even though self.rules will have the right rules present.
        super().__init__(*args, **kwargs)

    # This function will automatically get called as part of the item processing pipeline
    def parse_item(self, response):
        # Save the full response
        self.save_response(response)
        # Extract article metadata and structured text
        article = extract_article(response, self.config, crawl_info=self.crawl_info,
                                  content_digests=self.settings["CONTENT_DIGESTS"],
                                  node_indexes=self.settings["NODE_INDEXES"])
        return article

    def save_response(self, response):
        if self.close_down:
            raise CloseSpider(reason="Database size exceeded.")


        raw_article = dict()
        raw_article['site_name'] = self.config['site_name']
        raw_article['crawl_datetime'] = self.crawl_info['crawl_datetime']
        raw_article['request_url'] = response.request.url
        raw_article['response_url'] = response.url
        raw_article['status'] = response.status
        raw_article['body'] = response.text
        self.logger.info('Saving response for: {}'.format(response.url))
        self.exporter.export_item(raw_article)
        return

    def closed(self, reason):
        self.exporter.finish_exporting()
        self.exporter.file.close()
        self.logger.info('Spider closed: {} ({})'.format(self.config['site_name'], reason))
