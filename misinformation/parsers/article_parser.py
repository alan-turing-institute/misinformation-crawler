from azure.storage.blob import BlockBlobService
from ..database import Connector, RecoverableDatabaseError, NonRecoverableDatabaseError, Article, Webpage
# from ..items import Article, Webpage
import datetime
import json
from scrapy.http.response.html import HtmlResponse
from .serialisation import response_from_warc
from ..extractors import extract_element, extract_datetime_string
from ReadabiliPy.readabilipy import parse_to_json
import logging
from termcolor import colored


class ArticleParser(Connector):


    def __init__(self, content_digests=False, node_indexes=False):
        super().__init__()
        self.block_blob_service = BlockBlobService(account_name="misinformationcrawldata", account_key=self.db_config["blob_storage_key"])
        self.blob_container_name = "raw-crawled-pages"
        self.content_digests = content_digests
        self.node_indexes = node_indexes


    def process_site(self, site_name, config):

        entries = self.read_entries(Webpage, site_name=site_name)
        logging.info("Loaded {} pages for {}".format(len(entries), colored(site_name, "green")))

        for entry in entries:
            logging.info("Searching for an article at: {}".format(colored(entry.article_url, "green")))

            # Load WARC data from blob storage
            blob_key = entry.blob_key
            blob = self.block_blob_service.get_blob_to_bytes(self.blob_container_name, blob_key)
            # Create a response from the WARC content
            response = response_from_warc(blob.content)

            # Initialise an empty article
            article = {}
            article["title"] = None
            article["byline"] = None
            article["publication_datetime"] = None
            article["content"] = None
            article["plain_content"] = None
            article["plain_text"] = None
            article["metadata"] = None

            # Insert data from the table entry
            article["site_name"] = entry.site_name
            article["article_url"] = entry.article_url
            article["crawl_id"] = entry.crawl_id
            article["crawl_datetime"] = entry.crawl_datetime.replace(tzinfo=datetime.timezone.utc).isoformat()

            # First extract the containing element (or use the whole page)
            try:
                article_html = extract_element(response, config["article"]["content"])
            except KeyError:
                article_html = extract_element(response, "/html")

            # Use this to extract content and text
            if article_html:
                readabilipy_article = parse_to_json(article_html, self.content_digests, self.node_indexes, use_readability=False)
                # article["title"] = readabilipy_article["title"]
                # article["byline"] = readabilipy_article["byline"]
                # article["publication_datetime"] = readabilipy_article["publication_datetime"]
                article["content"] = readabilipy_article["content"]
                article["plain_content"] = readabilipy_article["plain_content"]
                article["plain_text"] = json.dumps(readabilipy_article["plain_text"])

                # Try to extract other data if the article has identified content
                if "content" in article and article["content"]:
                    # Extract title if in config
                    if "title" in config["article"]:
                        article["title"] = extract_element(response, config["article"]["title"])
                    # Extract byline
                    if "byline" in config["article"]:
                        article["byline"] = extract_element(response, config["article"]["byline"])
                    # Extract publication_datetime
                    if "publication_datetime" in config["article"]:
                        datetime_string = extract_element(response, config["article"]["publication_datetime"])
                        if "datetime-format" in config["article"]["publication_datetime"]:
                            dt_format = config["article"]["publication_datetime"]["datetime-format"]
                            iso_string = extract_datetime_string(datetime_string, dt_format)
                        else:
                            iso_string = extract_datetime_string(datetime_string)
                        article["publication_datetime"] = iso_string

            # Extract additional article metadata
            if "metadata" in config:
                # Initialise metadata field
                metadata = dict()
                # Attempt to extract all metadata fields
                for fieldname in config["metadata"]:
                    metadata[fieldname] = extract_element(response, config["metadata"][fieldname])
                article["metadata"] = json.dumps(metadata)

            # Add article to database
            if article_html:
                self.add_to_database(article)
            logging.info("Finished processing: {}".format(colored(entry.article_url, "green")))


    def add_to_database(self, article):
        '''Add an article to the database'''
        logging.info("  starting database export for: {}".format(article["article_url"]))

        # Construct webpage table entry
        article_data = Article(**article)

        # Add webpage entry to database
        try:
            self.add_entry(article_data)
        except RecoverableDatabaseError as err:
            logging.info(str(err))
        except NonRecoverableDatabaseError as err:
            logging.critical(str(err))
            raise
