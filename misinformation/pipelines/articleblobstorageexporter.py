import json
import yaml
import pkg_resources
from scrapy.exceptions import NotConfigured
import pyodbc
import hashlib
from azure.storage.blob import BlockBlobService
from ..database import Connector, RecoverableDatabaseError, NonRecoverableDatabaseError, Webpage

import logging
logging.getLogger("azure.storage.common.storageclient").setLevel(logging.ERROR)

class ArticleBlobStorageExporter(Connector):
    def __init__(self):
        super().__init__()
        self.block_blob_service = BlockBlobService(account_name='misinformationcrawls', account_key=self.db_config["blob_storage_key"])
        self.blob_container_name = "crawldata"

    @classmethod
    def from_crawler(cls, crawler):
        exporter = crawler.settings['ARTICLE_EXPORTER']
        if exporter != 'blob':
            # if this isn't specified in settings, the pipeline will be completely disabled
            raise NotConfigured
        return cls()


    def process_item(self, article, spider):
        '''Add an article to blob storage and track it in the database'''
        spider.logger.info("  attempting Azure upload for: {}".format(article["article_url"]))

        # Construct blob data
        blob_data = {
            "request_meta": json.dumps(article["request_meta"]),
            "page_html": article["page_html"],
        }
        blob_key = hashlib.md5(article["article_url"].encode("utf-8")).hexdigest()

        # # Check whether blob already exists and abort here if it does
        # if len(list(self.block_blob_service.list_blobs(self.blob_container_name, blob_key))):
        #     spider.logger.info("Skipping this URL as it has already been recorded: {}".format(article["article_url"]))
        #     return article
        # # Add blob to storage
        # self.block_blob_service.create_blob_from_text(self.blob_container_name, blob_key, json.dumps(blob_data))

        # Construct webpage table entry
        webpage_data = Webpage(
            crawl_id = article["crawl_id"],
            crawl_datetime = article["crawl_datetime"],
            site_name = article["site_name"],
            article_url = article["article_url"],
            file_path = blob_key,
        )

        # Add webpage entry to database
        try:
            self.add_dbentry("webpages", webpage_data)
        except RecoverableDatabaseError as err:
            spider.logger.info(str(err))
        except NonRecoverableDatabaseError as err:
            spider.request_closure = True
            spider.logger.critical(str(err))
        # spider.logger.error("Ending crawl as no connection to the database is possible.")


        spider.logger.info("Finished processing: {}".format(article["article_url"]))
