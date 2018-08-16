# Misinformation crawler
Web crawler to collect snapshots of articles to web archive.

See [main project](https://github.com/alan-turing-institute/misinformation) for project board and issues.

Can currently crawl the following sites with configurations in `misinformation/site_configs.yml`
- conservativehq.com
- federallistpress.com
- youngcons.com

Usage: `python crawl-all.py -n=<max_articles_per_site>` (limit is optional and all areticles will be crawled if left off)

Actual number of articles returned may be up to 16 higher due to number of parallel requests scrapy has open at any time

Several other sites have custom crawlers defined in `misinformation/spiders/spiders.py` that have not yet been
converted into configurations for the custom crawler. If scrapy is installed, these can be run using
`scrapy <spider-name>` (spider name is the website domain).
