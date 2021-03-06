import datetime
import re
import uuid
from contextlib import suppress
from urllib.parse import urlparse
from w3lib.url import url_query_cleaner, canonicalize_url
from scrapy.exceptions import CloseSpider
from scrapy.http import Request
from misinformation.items import CrawlResponse
from misinformation.warc import warc_from_response


class MisinformationMixin():
    """Mixin to provide useful defaults for Misinformation crawl spiders."""
    # Define attributes that will be overridden by child classes
    url_regexes = {}

    def __init__(self, config, *args, **kwargs):
        # Load config and set spider display name to the name of the class
        self.config = config
        self.name = type(self).__name__
        self.n_pages = 0
        self.n_articles = 0

        # Set crawl-level metadata
        self.crawl_info = {
            "crawl_id": str(uuid.uuid4()),
            "crawl_datetime": datetime.datetime.utcnow().replace(microsecond=0).replace(tzinfo=datetime.timezone.utc).isoformat()
        }

        # Set up list of override URLs to process before starting the crawl
        self.article_overrides = config.get("article_override_list", [])
        self.logger.info("Loaded %s article overrides", len(self.article_overrides))

        # Parse domain from start URL(s) and then restrict crawl to follow only
        # links in this domain plus additional (optional) user-specifed domains
        allowed_domains = self.as_list(config.get("additional_domains", []))
        allowed_domains += [urlparse(url).netloc for url in self.load_start_urls(config)]
        self.allowed_domains = list(set(allowed_domains))

        # Add flag to allow spider to be closed from inside a pipeline
        self.request_closure = False

        # Optional regexes which test the URL to see if this is an article
        with suppress(KeyError):
            self.url_regexes["article_require"] = config["article"]["url_must_contain"]
        with suppress(KeyError):
            self.url_regexes["article_reject"] = config["article"]["url_must_not_contain"]

        # Compile regexes
        self.url_regexes = dict((k, re.compile(v)) for k, v in self.url_regexes.items())

        # Initialise a cookie jar (list of cookies each of which is a dict)
        self.cookies = []

        # On first glance, this next line seems a bit weird, since
        # MisinformationMixin has no parents. However, this is needed to
        # correctly navigate Python"s multiple inheritance structure - what it
        # will actually do is call the next constructor in MRO order for the
        # *derived* class, which will be the appropriate scrapy.Spider class
        super().__init__(*args, **kwargs)

    def update_cookies(self, cookies):
        """Add cookies to those known about by this spider."""
        self.cookies.extend(self.as_list(cookies))
        # Remove duplicates, exploiting that fact that the tuple is hashable
        # even though the dict is not. The {} are a set comprehension, which
        # automatically remove duplicates by effectively running set() over the
        # iterator of tuples.
        self.cookies = [dict(t) for t in {tuple(d.items()) for d in self.cookies}]

    @staticmethod
    def as_list(item_or_list):
        if isinstance(item_or_list, list):
            return item_or_list
        return [item_or_list]

    @staticmethod
    def load_start_urls(config):
        return MisinformationMixin.as_list(config["start_url"])

    @staticmethod
    def common_link_kwargs(config):
        """Get common arguments for link extraction"""
        try:
            # Strip query strings from URLs if requested
            strip_query_strings = config["crawl_strategy"]["strip_query_strings"]
            if strip_query_strings:
                return {"process_value": url_query_cleaner}
        except KeyError:
            pass
        return {}

    def is_article(self, url):
        """Check whether this is an article"""
        # Check whether we match the "require" or "reject" regexes
        required = self.url_regexes["article_require"].search(url) if "article_require" in self.url_regexes else True
        rejected = self.url_regexes["article_reject"].search(url) if "article_reject" in self.url_regexes else False
        # This is an article if it matches "require" (or there is not require) and does not match "reject"
        return required and not rejected

    def _build_request(self, rule, link):
        """Override the default request builder to add any cookies that we have collected."""
        request = super()._build_request(rule, link)
        request.cookies = self.cookies
        return request

    def parse_response(self, response):
        """Parse the HTML response and determine whether it should be saved."""
        # If the closure flag has been set then stop crawling
        if self.request_closure:
            raise CloseSpider(reason='Ending crawl cleanly after a close request.')
        self.n_pages += 1

        # URL may be the result of a redirect. If so, we use the redirected URL
        if response.request.meta.get("redirect_urls"):
            resolved_url = response.request.meta.get("redirect_urls")[0]
        else:
            resolved_url = response.url
        resolved_url = canonicalize_url(resolved_url, keep_blank_values=False)
        self.logger.info("Searching for a URL match at: %s", resolved_url)

        # Always reject the front page of the domain since this will change
        # over time We need this for henrymakow.com as there is no sane URL
        # match rule for identifying articles and the index page parses as one.
        if urlparse(resolved_url).path in ["", "/", "index.html"]:
            return None

        # Check whether we pass the (optional) requirements on the URL format
        if not self.is_article(resolved_url):
            return None

        # If we get here then we've found a candidate article
        self.n_articles += 1
        self.logger.info("  found a candidate article at: %s", resolved_url)
        article_percentage = float(100 * self.n_articles / self.n_pages) if self.n_pages > 0 else 0
        self.logger.info("  in this crawl session %s candidate articles have been extracted from %s pages: (%s)",
                         self.n_articles,
                         self.n_pages,
                         "{:.2f}%".format(article_percentage),
                         )

        # Prepare to return serialised response
        crawl_response = CrawlResponse()
        crawl_response["url"] = resolved_url
        crawl_response["crawl_id"] = self.crawl_info["crawl_id"]
        crawl_response["crawl_datetime"] = self.crawl_info["crawl_datetime"]
        crawl_response["site_name"] = self.config["site_name"]
        crawl_response["warc_data"] = warc_from_response(response, resolved_url)
        return crawl_response

    def start_requests(self):
        """Process article overrides first, then delegate to the per-spider function."""
        def yield_overrides():
            for url in self.article_overrides:
                self.logger.debug("Processing article override: %s", url)
                yield Request(url, callback=self.parse_response)
        yield from yield_overrides()
        if self.config["start_url"]:
            yield from super().start_requests()

    def closed(self, reason):
        """Log reason for closure."""
        self.logger.info("Spider closed: %s (%s)", self.config["site_name"], reason)
