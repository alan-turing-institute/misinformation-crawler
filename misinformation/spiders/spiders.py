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


class FederalistPress(CrawlSpider):
    name = 'federalistpress.com'
    allowed_domains = ['federalistpress.com']
    start_urls = ['http://federalistpress.com/category/all-stories']
    rules = (
        # Extract links to other pages and follow links from them (no callback means follow=True by default)
        Rule(LinkExtractor(allow=('category/all-stories/page/',), )),
        # Extract links to articles
        Rule(LinkExtractor(restrict_xpaths=('//h2[@class="entry-title"]/a',)), callback='parse_item'),
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


class PatriotNewsDaily(CrawlSpider):
    name = 'patriotnewsdaily.com'
    allowed_domains = ['patriotnewsdaily.com']
    start_urls = ['http://patriotnewsdaily.com/category/all-conservative-news/']
    rules = (
        # Extract links to other pages and follow links from them (no callback means follow=True by default)
        Rule(LinkExtractor(allow=('category/all-conservative-news/page/',), )),
        # Extract links to articles
        Rule(LinkExtractor(restrict_xpaths=('//h2[@class="post-title"]/a',)), callback='parse_item'),
    )

    def parse_item(self, response):
        with open('article_urls/{}.txt'.format(self.name), 'a') as f:
            # write out the title and add a newline.
            f.write(response.url + "\n")
            print(response.url)


# Crawler doesn't extract any links
# class RedStateWatcher(CrawlSpider):
#     name = 'redstatewatcher.com'
#     allowed_domains = ['redstatewatcher.com']
#     start_urls = ['http://redstatewatcher.com/news.asp']
#     custom_settings = {
#         'CLOSESPIDER_ITEMCOUNT': 10
#     }
#     rules = (
#         # Extract links to other pages and follow links from them (no callback means follow=True by default)
#         Rule(LinkExtractor(allow=('news.asp',), )),
#         # Extract links to articles
#         Rule(LinkExtractor(restrict_xpaths=('//h1[@class="newsheaderpreview"]/a',)), callback='parse_item'),
#     )
#
#     def parse_item(self, response):
#         with open('article_urls/{}.txt'.format(self.name), 'a') as f:
#             # write out the title and add a newline.
#             f.write(response.url + "\n")
#             print(response.url)


class YoungCons(CrawlSpider):
    name = 'youngcons.com'
    allowed_domains = ['youngcons.com']
    start_urls = ['http://youngcons.com/category/politics/']
    rules = (
        # Extract links to other pages and follow links from them (no callback means follow=True by default)
        Rule(LinkExtractor(allow=('category/politics/page/',), )),
        # Extract links to articles
        Rule(LinkExtractor(restrict_xpaths=('//h3[contains(concat(" ",normalize-space(@class)," ")," entry-title ")]/a',)), callback='parse_item'),
    )

    def parse_item(self, response):
        with open('article_urls/{}.txt'.format(self.name), 'a') as f:
            # write out the title and add a newline.
            f.write(response.url + "\n")
            print(response.url)


class AddictingInfo(CrawlSpider):
    name = 'addictinginfo.com'
    allowed_domains = ['addictinginfo.com']
    start_urls = ['http://addictinginfo.com/category/news/']
    rules = (
        # Extract links to other pages and follow links from them (no callback means follow=True by default)
        Rule(LinkExtractor(allow=('category/news/page/',), )),
        # Extract links to articles
        Rule(LinkExtractor(restrict_xpaths=('//h2[contains(concat(" ",normalize-space(@class)," ")," entry-title ")]/a',)), callback='parse_item'),
    )

    def parse_item(self, response):
        with open('article_urls/{}.txt'.format(self.name), 'a') as f:
            # write out the title and add a newline.
            f.write(response.url + "\n")
            print(response.url)


class OccupyDemocrats(CrawlSpider):
    name = 'occupydemocrats.com'
    allowed_domains = ['occupydemocrats.com']
    start_urls = ['http://occupydemocrats.com']
    rules = (
        # Extract links to other pages and follow links from them (no callback means follow=True by default)
        Rule(LinkExtractor(allow=('page/',), )),
        # Extract links to articles
        Rule(LinkExtractor(restrict_xpaths=('//h3[contains(concat(" ",normalize-space(@itemprop)," ")," headline ")]/a',)), callback='parse_item'),
    )

    def parse_item(self, response):
        with open('article_urls/{}.txt'.format(self.name), 'a') as f:
            # write out the title and add a newline.
            f.write(response.url + "\n")
            print(response.url)

# Doesn't work (entry page gives 403 error)
# class DavidWolfe(CrawlSpider):
#     name = 'davidwolfe.com'
#     allowed_domains = ['davidwolfe.com']
#     start_urls = ['https://www.davidwolfe.com/category/news/']
#     rules = (
#         # Extract links to other pages and follow links from them (no callback means follow=True by default)
#         Rule(LinkExtractor(allow=('category/news/page/',), )),
#         # Extract links to articles
#         Rule(LinkExtractor(restrict_xpaths=('//h2[contains(concat(" ",normalize-space(@class)," ")," entry-title ")]/a',)), callback='parse_item'),
#     )
#
#     def parse_item(self, response):
#         with open('article_urls/{}.txt'.format(self.name), 'a') as f:
#             # write out the title and add a newline.
#             f.write(response.url + "\n")
#             print(response.url)


class EyeOpening(CrawlSpider):
    name = 'eyeopening.info'
    allowed_domains = ['eyeopening.info']
    start_urls = ['http://eyeopening.info/category/politics/']
    rules = (
        # Extract links to other pages and follow links from them (no callback means follow=True by default)
        Rule(LinkExtractor(allow=('category/politics/page/',), )),
        # Extract links to articles
        Rule(LinkExtractor(restrict_xpaths=('//h2[contains(concat(" ",normalize-space(@class)," ")," entry-title ")]/a',)), callback='parse_item'),
    )

    def parse_item(self, response):
        with open('article_urls/{}.txt'.format(self.name), 'a') as f:
            # write out the title and add a newline.
            f.write(response.url + "\n")
            print(response.url)


# Doesn't work (entry page gives 403 error)
# class GlobalResearch(CrawlSpider):
#     name = 'globalresearch.ca'
#     allowed_domains = ['globalresearch.ca']
#     start_urls = ['http://globalresearch.ca/latest-news-and-top-stories']
#     rules = (
#         # Extract links to other pages and follow links from them (no callback means follow=True by default)
#         Rule(LinkExtractor(allow=('latest-news-and-top-stories/page/',), )),
#         # Extract links to articles
#         Rule(LinkExtractor(restrict_xpaths=('//strong[contains(concat(" ",normalize-space(@class)," ")," title ")]/a',)), callback='parse_item'),
#     )
#
#     def parse_item(self, response):
#         with open('article_urls/{}.txt'.format(self.name), 'a') as f:
#             # write out the title and add a newline.
#             f.write(response.url + "\n")
#             print(response.url)


class HenryMakow(CrawlSpider):
    name = 'henrymakow.com'
    allowed_domains = ['henrymakow.com']
    start_urls = ['http://henrymakow.com/archives.html']
    rules = (
        # Extract links to other pages and follow links from them (no callback means follow=True by default)
        Rule(LinkExtractor(allow=('category/politics/page/',), )),
        # Extract links to articles
        Rule(LinkExtractor(restrict_xpaths=('//p[not(@class)]/a',)), callback='parse_item'),
    )

    def parse_item(self, response):
        with open('article_urls/{}.txt'.format(self.name), 'a') as f:
            # write out the title and add a newline.
            f.write(response.url + "\n")
            print(response.url)

# Crawler doesn't extract any links
# class GellerReport(CrawlSpider):
#     name = 'gellerreport.com'
#     allowed_domains = ['gellerreport.com']
#     start_urls = ['http://gellerreport.com/category/atlas-articles/']
#     rules = (
#         # Extract links to other pages and follow links from them (no callback means follow=True by default)
#         Rule(LinkExtractor(allow=('ategory/atlas-articles/page/',), )),
#         # Extract links to articles
#         Rule(LinkExtractor(
#             restrict_xpaths=('//h2[contains(concat(" ",normalize-space(@class)," ")," archive-entry-title ")]/a',)), callback='parse_item'),
#     )
#
#     def parse_item(self, response):
#         with open('article_urls/{}.txt'.format(self.name), 'a') as f:
#             # write out the title and add a newline.
#             f.write(response.url + "\n")
#             print(response.url)

# Crawler doesn't extract any links
# class PrisonPlanet(CrawlSpider):
#     name = 'prisonplanet.com'
#     allowed_domains = ['prisonplanet.com']
#     start_urls = ['http://prisonplanet.co/section/featured-stories/']
#     rules = (
#         # Extract links to other pages and follow links from them (no callback means follow=True by default)
#         Rule(LinkExtractor(allow=('section/featured-stories/page/',), )),
#         # Extract links to articles
#         Rule(LinkExtractor(restrict_xpaths=('//div[contains(concat(" ",normalize-space(@class)," ")," nArchiveHeader ")]/a',)), callback='parse_item'),
#     )
#
#     def parse_item(self, response):
#         with open('article_urls/{}.txt'.format(self.name), 'a') as f:
#             # write out the title and add a newline.
#             f.write(response.url + "\n")
#             print(response.url)


class EmpireNews(CrawlSpider):
    name = 'empirenews.net'
    allowed_domains = ['empirenews.net']
    start_urls = ['http://empirenews.net/category/politics/']
    rules = (
        # Extract links to other pages and follow links from them (no callback means follow=True by default)
        Rule(LinkExtractor(allow=('category/politics/page/',), )),
        # Extract links to articles
        Rule(LinkExtractor(restrict_xpaths=('//h1[contains(concat(" ",normalize-space(@class)," ")," entry-title ")]/a',)), callback='parse_item'),
    )

    def parse_item(self, response):
        with open('article_urls/{}.txt'.format(self.name), 'a') as f:
            # write out the title and add a newline.
            f.write(response.url + "\n")
            print(response.url)


class MadWorldNews(CrawlSpider):
    name = 'madworldnews.com'
    allowed_domains = ['madworldnews.com']
    start_urls = ['http://madworldnews.com/politics/']
    rules = (
        # Extract links to other pages and follow links from them (no callback means follow=True by default)
        Rule(LinkExtractor(allow=('politics/page/',), )),
        # Extract links to articles
        Rule(LinkExtractor(restrict_xpaths=('//h3[contains(concat(" ",normalize-space(@class)," ")," entry-title ")]/a',)), callback='parse_item'),
    )

    def parse_item(self, response):
        with open('article_urls/{}.txt'.format(self.name), 'a') as f:
            # write out the title and add a newline.
            f.write(response.url + "\n")
            print(response.url)

