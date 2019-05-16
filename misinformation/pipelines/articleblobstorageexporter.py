import json
import pickle
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
        self.block_blob_service = BlockBlobService(account_name='misinformationcrawldata', account_key=self.db_config["blob_storage_key"])
        self.blob_container_name = "raw-crawled-pages"

    @classmethod
    def from_crawler(cls, crawler):
        exporter = crawler.settings['ARTICLE_EXPORTER']
        if exporter != 'blob':
            # if this isn't specified in settings, the pipeline will be completely disabled
            raise NotConfigured
        return cls()


    def process_item(self, crawl_response, spider):
        '''Add an article to blob storage and track it in the database'''
        spider.logger.info("  attempting Azure upload for: {}".format(crawl_response["url"]))

        # Construct blob data
        # blob_data = {
        #     "request_meta": json.dumps(article["request_meta"]),
        #     "page_html": article["page_html"],
        # }
        # print(crawl_response, type(crawl_response))
        # blob_data = json.dumps(dict(crawl_response))
        blob_data = json.dumps(dict(crawl_response))
        # blob_data = pickle.dumps(crawl_response)
        blob_key = hashlib.md5(crawl_response["url"].encode("utf-8")).hexdigest()

        # crawl_id = blob_data.pop("crawl_id")
        # crawl_datetime = blob_data.pop("crawl_datetime")
        # site_name = blob_data.pop("site_name")
        # print(blob_data)

        # Check whether blob already exists and add it if not
        if len(list(self.block_blob_service.list_blobs(self.blob_container_name, blob_key))):
            spider.logger.info("  refusing to overwrite file that already exists in blob storage: {}".format(crawl_response["url"]))
        else:
            self.block_blob_service.create_blob_from_text(self.blob_container_name, blob_key, blob_data)

        # Construct webpage table entry
        webpage_data = Webpage(
            site_name = crawl_response["site_name"],
            article_url = crawl_response["url"],
            blob_key = blob_key,
        )

        # Add webpage entry to database
        try:
            self.add_entry(webpage_data)
        except RecoverableDatabaseError as err:
            spider.logger.info(str(err))
        except NonRecoverableDatabaseError as err:
            spider.request_closure = True
            spider.logger.critical(str(err))
        # spider.logger.error("Ending crawl as no connection to the database is possible.")


        spider.logger.info("Finished processing: {}".format(crawl_response["url"]))

        return crawl_response
