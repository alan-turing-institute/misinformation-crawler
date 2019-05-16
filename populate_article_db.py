import argparse
import pkg_resources
import yaml
from misinformation.parsers import ArticleParser


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description=__name__)
    parser.add_argument('--max-articles', '-n', type=int, default=0, help='Maximum number of articles to process from each site.')
    parser.add_argument('--site-name', '-s', default="all", help='Name of site configuration.')

    args = parser.parse_args()

    # Load crawl configuration for site from configuration
    spider_config = pkg_resources.resource_string(__name__, "site_configs.yml")
    site_configs = yaml.load(spider_config)

    # Set up the parser
    parser = ArticleParser()

    # Process data for selected sites
    for site_name in site_configs:
        if args.site_name in [site_name, "all"]:
            parser.process_site(site_name, config=site_configs[args.site_name])


if __name__ == "__main__":
    main()
