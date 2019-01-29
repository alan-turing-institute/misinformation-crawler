# Define here the models for your spider middleware
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/spider-middleware.html
# Taken from https://github.com/clemfromspace/scrapy-cloudflare-middleware

from cfscrape import get_tokens

class CloudFlareMiddleware:
    """Scrapy middleware to bypass the CloudFlare's anti-bot protection"""

    @staticmethod
    def is_cloudflare(response):
        """Test if the given response contains the cloudflare's anti-bot protection"""

        return (
            response.status == 503
            and response.headers.get('Server', '').startswith(b'cloudflare')
            and 'jschl_vc' in response.text
            and 'jschl_answer' in response.text
        )

    def process_response(self, request, response, spider):
        """If we can identify a cloudflare check on this page then use cfscrape to get the cookies"""

        if not self.is_cloudflare(response):
            return response

        spider.logger.info('Cloudflare protection detected on {}, trying to bypass...'.format(response.url))

        cloudflare_tokens, __ = get_tokens(request.url, user_agent=spider.settings.get('USER_AGENT'))

        spider.logger.info('Successfully bypassed the protection for {}, re-scheduling the request'.format(response.url))

        request.cookies.update(cloudflare_tokens)
        request.priority = 99999

        return request