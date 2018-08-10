# -*- coding: utf-8 -*-
import logging
import os
from scrapy.exporters import JsonLinesItemExporter


class ArticleJsonExporterPipeline(object):

    def __init__(self):
        self.exporter = None

    # Initialise pipeline when crawler opened
    def open_spider(self, spider):
        output_dir = "articles"
        output_file = "{}.txt".format(spider.site_name)
        # Ensure output directory exists
        if not(os.path.isdir(output_dir)):
            os.makedirs(output_dir)
        output_path = os.path.join(output_dir, output_file)
        f = open(output_path, 'wb')
        self.exporter = JsonLinesItemExporter(f)

    # Tidy up after crawler closed
    def close_spider(self, spider):
        self.exporter.finish_exporting()
        self.exporter.file.close()

    def process_item(self, article, spider):
        self.exporter.export_item(article)
        spider.logger.info("Successfully crawled: {}".format(article["article_url"]))
        return article
