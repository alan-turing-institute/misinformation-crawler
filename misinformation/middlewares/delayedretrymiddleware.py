import time
from scrapy.downloadermiddlewares.retry import RetryMiddleware


class DelayedRetryMiddleware(RetryMiddleware):
    '''Scrapy middleware to delay the crawl when we hit 'Service Unavailable' errors.

    These are most frequently caused by a high crawl frequency, so we
    deliberately introduce a delay to bypass this.
    '''
    def __init__(self, settings):
        self.delay_http_codes = [503]
        self.delay_increment = 0.1
        self.delay_interval = 0
        super().__init__(settings)

    def process_response(self, request, response, spider):
        if response.status in self.delay_http_codes:
            self.delay_interval += self.delay_increment
            spider.logger.info(
                "Too many requests - server returned an error (code {}). "
                "Adding {:.2f}s delay to future requests. "
                "Current delay interval is {:.2f}s".format(
                    response.status, self.delay_increment, self.delay_interval))
        if self.delay_interval:
            time.sleep(self.delay_interval)
        return super().process_response(request, response, spider)
