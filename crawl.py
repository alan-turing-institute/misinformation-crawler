#! /usr/bin/env python
import argparse
import csv
import logging
import pkg_resources
import yaml
from collections import defaultdict
from scrapy.crawler import CrawlerProcess
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings
from misinformation.spiders import IndexPageSpider, ScattergunSpider, XMLSitemapSpider


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description=__name__)
    # Specify what type of crawl we want to do
    crawl_type = parser.add_mutually_exclusive_group(required=True)
    crawl_type.add_argument("--site", "-s", help="Name of site to crawl.")
    crawl_type.add_argument("--all", "-a", action="store_true", help="Crawl all sites.")
    crawl_type.add_argument("--list", "-l", help="CSV file of URLs to crawl with an 'article_url' column and a 'site name' column.")
    # General options
    parser.add_argument("--max_articles", "-n", type=int, default=0, help="Maximum number of articles to process from each site.")
    parser.add_argument("--exporter", "-e", default="blob", choices=["file", "blob"], help="Article export method.")
    parser.add_argument("--no-digest", action="store_true", help="Disable content digests.")
    parser.add_argument("--no-index", action="store_true", help="Disable node indexes.")
    args = parser.parse_args()

    # Set up logging
    configure_logging()
    logging.getLogger("azure.storage.common.storageclient").setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy").setLevel(logging.ERROR)

    # Load crawler settings and apply local overrides
    settings = get_project_settings()
    settings.update({
        'ARTICLE_EXPORTER': args.exporter,
        'CONTENT_DIGESTS': (not args.no_digest),
        'NODE_INDEXES': (not args.no_index),
    })
    # Apply an item limit if specified
    if args.max_articles:
        settings.update({
            'CLOSESPIDER_ITEMCOUNT': args.max_articles
        })

    # Set up a crawler process
    process = CrawlerProcess(settings)

    # Load crawler configurations for all sites
    site_configs = yaml.load(pkg_resources.resource_string(__name__, "site_configs.yml"), Loader=yaml.FullLoader)
    article_override_lists = yaml.load(pkg_resources.resource_string(__name__, "article_override_lists.yml"), Loader=yaml.FullLoader)
    for site_name in article_override_lists:
        site_configs[site_name]["article_override_list"] = article_override_lists[site_name]


    # Crawl a single site
    # -------------------
    if args.site:
        # Create a dynamic spider class and register it with the crawler
        spider_class = dynamic_spider_class(site_configs[args.site], args.max_articles)
        process.crawl(spider_class, config=site_configs[args.site])


    # Crawl all sites
    # ---------------
    elif args.all:
        for site_name in site_configs:
            # Create a dynamic spider class and register it with the crawler
            spider_class = dynamic_spider_class(site_configs[site_name], args.max_articles)
            process.crawl(spider_class, config=site_configs[site_name])


    # Crawl all URLs from a CSV file
    # ------------------------------
    elif args.list:
        # Load articles from CSV into a dictionary
        article_urls = defaultdict(list)
        with open(args.list, "r") as csvfile:
            dialect = csv.Sniffer().sniff(csvfile.read(50))
            csvfile.seek(0)
            reader = csv.DictReader(csvfile, dialect=dialect)
            if not all([f in reader.fieldnames for f in ["article_url", "site_name"]]):
                raise ValueError("CSV input must have an 'article_url' column and a 'site name' column")
            for row in reader:
                article_urls[row["site_name"]].append(row["article_url"])
        # Iterate over each site
        for site_name in sorted(article_urls.keys()):
            # Override the configuration for the specified site
            site_config = site_configs[site_name]
            site_config["start_url"] = ""
            site_config["article_override_list"] = article_urls[site_name]
            # Create a dynamic spider class and register it with the crawler
            spider_class = dynamic_spider_class(site_config, args.max_articles)
            process.crawl(spider_class, config=site_config)

    # Start the crawler
    process.start()


def dynamic_spider_class(config, max_articles):
    """
    As custom-settings are only applied at class-level, we create a new class
    for each site and set the custom_settings appropriately
    """
    # Whether to obey robots.txt
    custom_settings = {
        "ROBOTSTXT_OBEY": config.get("obey_robots_txt", True),
    }

    # For sites with a maximum per-crawler limit, use lots of shallow crawlers
    # which will self-terminate when they hit a 402 error
    if config["crawl_strategy"].get("use_shallow_crawlers", False):
        n_requests = 1000
        if max_articles > 0:
            n_requests = min(n_requests, max_articles)
        custom_settings['CONCURRENT_REQUESTS'] = n_requests

    # Determine which base-class to use
    try:
        crawl_strategy = config['crawl_strategy']['method']
    except KeyError:
        crawl_strategy = 'scattergun'
    base_spider = {
        "index_page": IndexPageSpider,
        "scattergun": ScattergunSpider,
        "sitemap": XMLSitemapSpider
    }[crawl_strategy]

    # Create a new class specific to this site which has its own custom settings
    SiteSpecificSpider = type(
        config["site_name"].split(".")[0].title() + "Spider",
        (base_spider,),
        {"custom_settings": custom_settings}
    )
    return SiteSpecificSpider


if __name__ == "__main__":
    main()
