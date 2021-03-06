import os
from scrapy.exceptions import NotConfigured
from scrapy.exporters import JsonItemExporter


class ArticleJsonFileExporter():
    def __init__(self):
        self.exporter = None

    @classmethod
    def from_crawler(cls, crawler):
        exporter = crawler.settings['ARTICLE_EXPORTER']
        if exporter != 'file':
            # if this isn't specified in settings, the pipeline will be completely disabled
            raise NotConfigured
        return cls()

    # Initialise pipeline when crawler opened
    def open_spider(self, spider):
        output_dir = "webpages"
        output_file = "{}_extracted.txt".format(spider.config['site_name'])
        # Ensure output directory exists
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
        output_path = os.path.join(output_dir, output_file)
        file_handle = open(output_path, 'wb')
        self.exporter = JsonItemExporter(file_handle)
        self.exporter.start_exporting()

    # Tidy up after crawler closed
    def close_spider(self, spider):
        self.exporter.finish_exporting()
        self.exporter.file.close()
        del spider  # supress unused argument warning

    def process_item(self, crawl_response, spider):
        spider.logger.info('  preparing to save response to local file')
        self.exporter.export_item(crawl_response)
        spider.logger.info("Finished processing: {}".format(crawl_response["url"]))
        return crawl_response
