import argparse
import logging
import pkg_resources
import yaml
from misinformation.warc import WarcParser


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description=__name__)
    parser.add_argument("--max-articles", "-n", type=int, default=-1, help="Maximum number of articles to process from each site.")
    parser.add_argument("--site-name", "-s", default="all", help="Name of site configuration.")
    parser.add_argument("--local", action="store_true", help="Use local file as input and do not write output")
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(format=r"%(asctime)s %(levelname)8s: %(message)s", datefmt=r"%Y-%m-%d %H:%M:%S", level=logging.INFO)
    logging.getLogger("azure.storage.common.storageclient").setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy").setLevel(logging.ERROR)

    # Load crawl configuration for site from configuration
    spider_config = pkg_resources.resource_string(__name__, "site_configs.yml")
    site_configs = yaml.load(spider_config, Loader=yaml.FullLoader)

    # Set up the parser with content digests and node indexes enabled
    parser = WarcParser(content_digests=True, node_indexes=True)

    # Process data for selected sites
    for site_name in site_configs:
        if args.site_name in [site_name, "all"]:
            parser.process_webpages(site_name,
                                    config=site_configs[site_name],
                                    max_articles=args.max_articles,
                                    use_local=args.local)


if __name__ == "__main__":
    main()
