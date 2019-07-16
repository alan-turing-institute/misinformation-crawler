import time
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.exceptions import IgnoreRequest


class DelayedRetryMiddleware(RetryMiddleware):
    """Scrapy middleware to delay the crawl when we hit 'Service Unavailable' errors.

    These are most frequently caused by a high crawl frequency, so we
    deliberately introduce a delay to bypass this.
    """
    def __init__(self, settings):
        self.delay_http_codes = [429, 503]
        self.ignore_http_codes = [402]
        self.delay_increment = 0.1
        self.delay_interval = 0
        self.num_responses = 0
        self.num_responses_threshold = 25
        super().__init__(settings)

    def process_response(self, request, response, spider):
        # If we hit an ignorable error (eg. "payment required") then ignore the request
        if response.status in self.ignore_http_codes:
            raise IgnoreRequest("Skipping page which returned a status code that we ignore.")
        # If we hit a 'service unavailable' error then increase the delay
        if response.status in self.delay_http_codes:
            self.delay_interval += self.delay_increment
            spider.logger.info(
                "Too many requests - server returned an error (code {}). "
                "Adding {:.2f}s delay to future requests. "
                "Current delay interval is {:.2f}s".format(
                    response.status, self.delay_increment, self.delay_interval))
            self.num_responses = 0
        # If we manage to hit 'num_responses_threshold' responses in a row
        # without problems then reduce the delay
        else:
            self.num_responses += 1
            if self.delay_interval and self.num_responses >= self.num_responses_threshold:
                self.delay_interval = max(self.delay_interval - self.delay_increment, 0)
                spider.logger.info(
                    "Made {} requests without a server error. "
                    "Reducing delay for future requests by {:.2f}s. "
                    "Current delay interval is {:.2f}s".format(
                        self.num_responses, self.delay_increment, self.delay_interval))
                self.num_responses = 0
        # Wait if the delay is non-zero
        if self.delay_interval:
            time.sleep(self.delay_interval)
        return super().process_response(request, response, spider)
