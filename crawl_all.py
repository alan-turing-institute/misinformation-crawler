import argparse
import pkg_resources
import subprocess
import yaml


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description=__name__)
    parser.add_argument('--max_articles', '-n', type=int, default=0,
                        help='Maximum number of articles to process from each site.')
    parser.add_argument('--exporter', '-e', default='blob', choices=['file', 'blob'],
                        help='Article export method.')
    args = parser.parse_args()

    # Load crawl configuration for site from configuration
    spider_config = pkg_resources.resource_string(__name__, "site_configs.yml")
    site_configs = yaml.load(spider_config)

    for site_name in site_configs:
        print(site_name)
        subprocess.call(['python', 'crawl_site.py',
                         '-n', str(args.max_articles),
                         '-s', site_name,
                         '-e', args.exporter])


if __name__ == "__main__":
    main()
