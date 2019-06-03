import ast
import datetime
import json
import logging
import os
from contextlib import suppress
from dataclasses import dataclass
from dateutil import parser
from termcolor import colored
from misinformation.extractors import extract_article
from misinformation.database import Connector, RecoverableDatabaseError, NonRecoverableDatabaseError, Article, Webpage
from .serialisation import response_from_warc, warc_from_string


@dataclass
class LocalCrawlResponse:
    site_name: str
    article_url: str
    crawl_id: str
    crawl_datetime: datetime
    warc_data: bytes


class WarcParser(Connector):
    def __init__(self, content_digests=False, node_indexes=False):
        super().__init__()
        self.content_digests = content_digests
        self.node_indexes = node_indexes

    def load_local_warcfiles(self, site_name):
        input_dir = "webpages"
        input_file = "{}_extracted.txt".format(site_name)
        input_path = os.path.join(input_dir, input_file)
        output_crawl_responses = []
        with open(input_path, "rb") as f_in:
            raw_data = f_in.readlines()[0].decode("utf-8")
            data_entries = ast.literal_eval(raw_data)
            for json_data in data_entries:
                json_data["article_url"] = json_data.pop("url")
                json_data["crawl_datetime"] = parser.parse(json_data.pop("crawl_datetime"))
                response = LocalCrawlResponse(**json_data)
                output_crawl_responses.append(response)
        return output_crawl_responses

    def process_webpages(self, site_name, config, max_articles=-1, use_local=False):
        start_time = datetime.datetime.utcnow()
        logging.info("Loading pages for %s...", colored(site_name, "green"))

        # Load WARC files
        if use_local:
            warcfile_entries = self.load_local_warcfiles(site_name)
        else:
            warcfile_entries = self.read_entries(Webpage, site_name=site_name)
        n_pages, n_skipped, n_articles, n_warcentries = 0, 0, 0, len(warcfile_entries)

        # Load existing articles
        if use_local:
            article_urls = []
        else:
            article_entries = self.read_entries(Article, site_name=site_name)
            article_urls = [entry.article_url for entry in article_entries]
        duration = datetime.datetime.utcnow() - start_time
        logging.info("Loaded %s pages in %s",
                     colored(n_warcentries, "blue"),
                     colored(duration, "blue"),
                     )

        for idx, entry in enumerate(warcfile_entries, start=1):
            # Stop if we've reached the processing limit
            if n_articles >= max_articles > 0:
                logging.info("Reached article processing limit: %s", max_articles)
                break

            # Skip over pages that have already been processed
            if entry.article_url in article_urls:
                logging.info("Article already extracted, skipping: %s",
                             colored(entry.article_url, "green"),
                             )
                n_skipped += 1
                continue

            # Start article processing
            logging.info("Searching for an article at: %s", colored(entry.article_url, "green"))
            n_pages += 1

            # Load WARC data
            if use_local:
                # ... from local file
                warc_data = warc_from_string(entry.warc_data)
            else:
                # ... from blob storage
                blob = self.block_blob_service.get_blob_to_bytes(self.blob_container_name, entry.blob_key)
                warc_data = blob.content

            # Create a response from the WARC content and attempt to extract an article
            response = response_from_warc(warc_data)
            article = extract_article(response, config, entry, self.content_digests, self.node_indexes)
            with suppress(KeyError):
                article["plain_text"] = json.dumps(article["plain_text"])
            with suppress(KeyError):
                article["metadata"] = json.dumps(article["metadata"])

            # Add article to database unless we're running locally
            if article["content"]:
                if not use_local:
                    self.add_to_database(article)
                n_articles += 1
            logging.info("Finished processing %s/%s: %s", idx, n_warcentries, entry.article_url)

        # Print statistics
        duration = datetime.datetime.utcnow() - start_time
        processing_rate = float(n_pages / duration.seconds) if duration.seconds > 0 else 0
        logging.info("Processed %s pages in %s => %s",
                     colored(n_pages, "blue"),
                     colored(duration, "blue"),
                     colored("{:.2f} Hz".format(processing_rate), "green"),
                     )
        hit_percentage = float(100 * n_articles / n_pages) if n_pages > 0 else 0
        logging.info("Found articles in %s/%s pages => %s",
                     colored(n_articles, "blue"),
                     colored(n_pages, "blue"),
                     colored("{:.2f}%".format(hit_percentage), "green"),
                     )
        hit_percentage = float(100 * (n_articles + n_skipped) / (n_pages + n_skipped)) if (n_pages + n_skipped) > 0 else 0
        logging.info("Including skipped pages, there are articles in %s/%s pages => %s",
                     colored(n_articles + n_skipped, "blue"),
                     colored(n_pages + n_skipped, "blue"),
                     colored("{:.2f}%".format(hit_percentage), "green"),
                     )

    def add_to_database(self, article):
        '''Add an article to the database'''
        logging.info("  starting database export for: %s", article["article_url"])

        # Construct Article table entry
        article_data = Article(**article)

        # Add webpage entry to database
        try:
            self.add_entry(article_data)
        except RecoverableDatabaseError as err:
            logging.info(str(err))
        except NonRecoverableDatabaseError as err:
            logging.critical(str(err))
            raise

        logging.info("  finished database export for: %s", article["article_url"])
