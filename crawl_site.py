import argparse
from misinformation.spiders.spiders import MisinformationSpider
import pkg_resources
from scrapy.crawler import CrawlerProcess
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings
import yaml

SPIDER_CONFIG = pkg_resources.resource_string(__name__, "site_configs.yml")


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description=__name__)
    parser.add_argument('--site_name', '-s', required=True,
        help='Name of site configuration.')
    parser.add_argument('--max_articles', '-n', type=int, default=0,
        help='Maximum number of articles to process from each site.')
    parser.add_argument('--exporter', '-e', default='database',
        choices=['file', 'database'], help='Article export method.')

    args = parser.parse_args()

    # Load crawl configuration for site from configuration
    site_configs = yaml.load(SPIDER_CONFIG)

    configure_logging()

    # Set up a crawler runner
    # Update settings here as we can't seem to successfully do this when trying to set a spider's custom_settings
    # attribute in it's initialiser
    settings = get_project_settings()
    # Add custom settings
    settings.update({
        'ARTICLE_EXPORTER': args.exporter,
        'CONTENT_DIGESTS': True,
        'NODE_INDEXES': True,
        'ROBOTSTXT_OBEY': site_configs[args.site_name].get("obey_robots_txt", True)
    })
    # Apply an item limit if specified
    if args.max_articles:
        settings.update({
            'CLOSESPIDER_ITEMCOUNT': args.max_articles
        })
    process = CrawlerProcess(settings)

    # Run crawl for specified site
    process.crawl(MisinformationSpider, config=site_configs[args.site_name])
    process.start()


if __name__ == "__main__":
    main()