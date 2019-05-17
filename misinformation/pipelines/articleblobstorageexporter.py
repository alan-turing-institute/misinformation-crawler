import hashlib
from scrapy.exceptions import NotConfigured
from ..database import Connector, RecoverableDatabaseError, NonRecoverableDatabaseError, Webpage


class ArticleBlobStorageExporter(Connector):
    @classmethod
    def from_crawler(cls, crawler):
        exporter = crawler.settings['ARTICLE_EXPORTER']
        if exporter != 'blob':
            # if this isn't specified in settings, the pipeline will be completely disabled
            raise NotConfigured
        return cls()


    def process_item(self, crawl_response, spider):
        '''Add an article to blob storage and track it in the database'''
        # Construct blob data and associated key
        blob_data = crawl_response["warc_data"]
        blob_key = hashlib.md5(crawl_response["url"].encode("utf-8")).hexdigest()

        # Check whether blob already exists and add it if not
        if list(self.block_blob_service.list_blobs(self.blob_container_name, blob_key)):
            spider.logger.info("  refusing to overwrite file that already exists in blob storage: {}".format(crawl_response["url"]))
        else:
            spider.logger.info("  uploading WARC file for: {}".format(crawl_response["url"]))
            self.block_blob_service.create_blob_from_text(self.blob_container_name, blob_key, blob_data)

        # Construct webpage table entry
        webpage_data = Webpage(
            site_name=crawl_response["site_name"],
            article_url=crawl_response["url"],
            crawl_id=crawl_response["crawl_id"],
            crawl_datetime=crawl_response["crawl_datetime"],
            blob_key=blob_key,
        )

        # Add webpage entry to database
        try:
            self.add_entry(webpage_data)
        except RecoverableDatabaseError as err:
            spider.logger.info(str(err))
        except NonRecoverableDatabaseError as err:
            spider.request_closure = True
            spider.logger.critical(str(err))

        # Log end of item processing and return the item
        spider.logger.info("Finished processing: {}".format(crawl_response["url"]))
        return crawl_response
