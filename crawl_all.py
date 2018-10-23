import argparse
import pkg_resources
from subprocess import Popen, PIPE
import yaml

SPIDER_CONFIG = pkg_resources.resource_string(__name__, "site_configs.yml")


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description=__name__)
    parser.add_argument('--max_articles', '-n', type=int, default=None,
        help='Maximum number of articles to process from each site.')
    parser.add_argument('--exporter', '-e', default='database',
        choices=['file', 'database'], help='Article export method.')

    args = parser.parse_args()

    # Load crawl configuration for site from configuration
    site_configs = yaml.load(SPIDER_CONFIG)

    for site_name in site_configs:
        print(site_name)
        Popen(['python', 'crawl_site.py', '-n', str(args.max_articles), '-s', site_name, '-e', args.exporter]).wait()


if __name__ == "__main__":
    main()