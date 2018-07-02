from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor

# Crawlers that have page links on the start URL
class ConservativeHq(CrawlSpider):
    name = 'conservativehq.com'
    allowed_domains = ['conservativehq.com']
    start_urls = ['http://conservativehq.com/exclusives']
    rules = (
        # Extract links to other pages and follow links from them (no callback means follow=True by default)
        Rule(LinkExtractor(allow=('exclusives', ),)),
        # Extract links to articles
        Rule(LinkExtractor(allow=('article/',)), callback='parse_item'),
    )

    def parse_item(self, response):
        with open('article_urls/{}.txt'.format(self.name), 'a') as f:
            # write out the title and add a newline.
            f.write(response.url + "\n")
            print(response.url)


class PalmerReport(CrawlSpider):
    name = 'palmerreport.com'
    allowed_domains = ['palmerreport.com']
    start_urls = ['https://palmerreport.com/category/analysis/']
    rules = (
        # Extract links to other pages and follow links from them (no callback means follow=True by default)
        Rule(LinkExtractor(allow=('category/analysis/page/',), )),
        # Extract links to articles
        Rule(LinkExtractor(restrict_xpaths=('//h2[@class="fl-post-title"]/a',)), callback='parse_item'),
    )

    def parse_item(self, response):
        with open('article_urls/{}.txt'.format(self.name), 'a') as f:
            # write out the title and add a newline.
            f.write(response.url + "\n")
            print(response.url)
