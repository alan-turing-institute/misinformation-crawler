import ast
import datetime
import json
import logging
import os
from collections import Counter
from contextlib import suppress
from dateutil import parser
from termcolor import colored
from misinformation.extractors import extract_article
from misinformation.database import Connector, RecoverableDatabaseError, NonRecoverableDatabaseError, Article, Webpage
from .crawl_file import CrawlFile
from .serialisation import response_from_warc, warc_from_string


def read_local_files(site_name):
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
            response = CrawlFile(**json_data)
            output_crawl_responses.append(response)
    return output_crawl_responses


class WarcParser(Connector):
    def __init__(self, content_digests=False, node_indexes=False):
        super().__init__()
        self.content_digests = content_digests
        self.node_indexes = node_indexes
        self.counts = None

    def load_warcfiles(self, site_name, max_entries, use_local):
        '''Load WARC files'''
        start_time = datetime.datetime.utcnow()
        if use_local:
            warcfile_entries = read_local_files(site_name)
        else:
            warcfile_entries = self.read_entries(Webpage, max_entries=max_entries, site_name=site_name)
        self.counts["warcentries"] = len(warcfile_entries)
        duration = datetime.datetime.utcnow() - start_time
        logging.info("Loaded %s crawled pages in %s",
                     colored(self.counts["warcentries"], "blue"),
                     colored(duration, "blue"),
                     )
        return warcfile_entries

    def load_existing_articles(self, site_name, max_entries):
        '''Load existing articles'''
        start_time = datetime.datetime.utcnow()
        try:
            article_entries = self.read_entries(Article.article_url, max_entries=max_entries, site_name=site_name)
            article_urls = [entry[0] for entry in article_entries]
        except RecoverableDatabaseError:
            article_urls = []
        duration = datetime.datetime.utcnow() - start_time
        logging.info("Loaded %s existing articles in %s",
                     colored(len(article_urls), "blue"),
                     colored(duration, "blue"),
                     )
        return article_urls

    def process_webpages(self, site_name, config, max_articles=-1, use_local=False):
        '''Process webpages from a single site'''
        start_time = datetime.datetime.utcnow()
        logging.info("Loading pages for %s...", colored(site_name, "green"))

        # Reset counts
        self.counts = Counter(pages=0, skipped=0, articles=0, warcentries=0,
                              no_date=0, no_byline=0, no_title=0)

        # Speed up retrieval by setting a maximum number of entries to retrieve from the tables
        max_entries = 50 * max_articles if max_articles > 0 else None

        # Load WARC files
        warcfile_entries = self.load_warcfiles(site_name, max_entries, use_local)

        # Load existing articles
        article_urls = self.load_existing_articles(site_name, max_entries)

        for idx, entry in enumerate(warcfile_entries, start=1):
            # Stop if we've reached the processing limit
            if self.counts["articles"] >= max_articles > 0:
                logging.info("Reached article processing limit: %s", max_articles)
                break

            # Skip over pages that have already been processed
            if entry.article_url in article_urls:
                logging.info("Article already extracted, skipping: %s",
                             colored(entry.article_url, "green"),
                             )
                self.counts["skipped"] += 1
                continue

            # Start article processing
            logging.info("Searching for an article at: %s", colored(entry.article_url, "green"))
            self.counts["pages"] += 1

            # Load WARC data
            if use_local:  # ... from local file
                warc_data = warc_from_string(entry.warc_data)
            else:  # ... from blob storage
                warc_data = self.get_blob_content(entry.blob_key)

            # Create a response from the WARC content and attempt to extract an article
            response = response_from_warc(warc_data)
            article = extract_article(response, config, entry, self.content_digests, self.node_indexes)
            with suppress(KeyError):
                article["plain_text"] = json.dumps(article["plain_text"])
            with suppress(KeyError):
                article["metadata"] = json.dumps(article["metadata"])

            # Check for missing fields
            if not article["publication_datetime"]:
                self.counts["no_date"] += 1
            if not article["byline"]:
                self.counts["no_byline"] += 1
            if not article["title"]:
                self.counts["no_title"] += 1

            # Add article to database unless we're running locally
            if article["content"]:
                if not use_local:
                    self.add_to_database(article)
                self.counts["articles"] += 1
            logging.info("Finished processing %s/%s: %s", idx, self.counts["warcentries"], entry.article_url)

        # Print statistics
        duration = datetime.datetime.utcnow() - start_time
        self.summarise(duration)

    def summarise(self, duration):
        '''Print summary statistics about this run'''
        # Processing rate
        processing_rate = float(self.counts["pages"] / duration.seconds) if duration.seconds > 0 else 0
        logging.info("Processed %s pages in %s => %s",
                     colored(self.counts["pages"], "blue"),
                     colored(duration, "blue"),
                     colored("{:.2f} Hz".format(processing_rate), "green"),
                     )
        # Article extraction percentage
        hit_percentage = float(100 * self.counts["articles"] / self.counts["pages"]) if self.counts["pages"] > 0 else 0
        logging.info("Found articles in %s/%s pages => %s",
                     colored(self.counts["articles"], "blue"),
                     colored(self.counts["pages"], "blue"),
                     colored("{:.2f}%".format(hit_percentage), "green"),
                     )
        # Date extraction failures
        hit_percentage = float(100 * self.counts["no_date"] / self.counts["pages"]) if self.counts["pages"] > 0 else 0
        logging.info("... of these %s/%s had no date => %s",
                     colored(self.counts["no_date"], "blue"),
                     colored(self.counts["pages"], "blue"),
                     colored("{:.2f}%".format(hit_percentage), "green"),
                     )
        # Byline extraction failures
        hit_percentage = float(100 * self.counts["no_byline"] / self.counts["pages"]) if self.counts["pages"] > 0 else 0
        logging.info("... of these %s/%s had no byline => %s",
                     colored(self.counts["no_byline"], "blue"),
                     colored(self.counts["pages"], "blue"),
                     colored("{:.2f}%".format(hit_percentage), "green"),
                     )
        # Title extraction failures
        hit_percentage = float(100 * self.counts["no_title"] / self.counts["pages"]) if self.counts["pages"] > 0 else 0
        logging.info("... of these %s/%s had no title => %s",
                     colored(self.counts["no_title"], "blue"),
                     colored(self.counts["pages"], "blue"),
                     colored("{:.2f}%".format(hit_percentage), "green"),
                     )
        # Overall article extraction percentage
        n_articles = self.counts["articles"] + self.counts["skipped"]
        n_pages = self.counts["pages"] + self.counts["skipped"]
        hit_percentage = float(100 * n_articles / n_pages) if n_pages > 0 else 0
        logging.info("Including skipped pages, there are articles in %s/%s pages => %s",
                     colored(n_articles, "blue"),
                     colored(n_pages, "blue"),
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
