import iso8601
from misinformation.items import Article
from misinformation.extractors import extract_article
import datetime
import os
from scrapy.exceptions import CloseSpider
from scrapy.exporters import JsonItemExporter
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from urllib.parse import urlparse
import uuid


# Generic crawl spider for websites that meet the following criteria
# (i) Lists of articles are paged and navigable to with HTML links
# (ii) Has metadata in a microdata format
class MisinformationSpider(CrawlSpider):
    name = 'misinformation'
    exporter = None
    crawl_date = None

    def __init__(self, config, *args, **kwargs):
        self.config = config

        # Set crawl-level metadata
        self.crawl_info = {
            "crawl_id": str(uuid.uuid4()),
            "crawl_datetime": datetime.datetime.utcnow().replace(microsecond=0).replace(
                tzinfo=datetime.timezone.utc).isoformat()
        }
        start_url = self.config['start_url']
        self.start_urls = [start_url]
        # Parse domain from start URL and use to restrict crawl to follow only internal site links
        site_domain = urlparse(start_url).netloc
        self.allowed_domains = [site_domain]

        # Rules for finding article links
        # 1. Rule for identifying links to follow to pages that might have more articles links
        if self.config['article_search'] == 'paged':
            follow_rule = Rule(LinkExtractor(allow=(self.config['follow_url_path'], ),))
        # 2. Rule for identifying article links
        # 2a. We can match the link URL itself to a pattern
        if 'article_url_path' in self.config:
            article_rule = Rule(LinkExtractor(
                allow=(self.config['article_url_path'],)), callback='parse_item')
        # 2b. We need to inspect the element containing the link
        elif 'article_url_xpath' in self.config:
            article_rule = Rule(LinkExtractor(
                restrict_xpaths=(self.config['article_url_xpath'],)), callback='parse_item')
        self.rules = (follow_rule, article_rule, )

        # Set up saving of raw responses for articles
        output_dir = "articles"
        output_file = "{}_full.txt".format(self.config['site_name'])
        # Ensure output directory exists
        if not (os.path.isdir(output_dir)):
            os.makedirs(output_dir)
        output_path = os.path.join(output_dir, output_file)
        f = open(output_path, 'wb')
        self.exporter = JsonItemExporter(f)
        self.exporter.start_exporting()

        # Add flag to allow spider to be closed from inside a pipeline
        self.close_down = False

        # We need to call the super constructor AFTER setting any rules as it calls self._compile_rules(), storing them
        # in self._rules. If we call the super constructor before we define the rules, they will not be compiled and
        # self._rules will be empty, even though self.rules will have the right rules present.
        super().__init__(*args, **kwargs)

    # This function will automatically get called as part of the item processing pipeline
    def parse_item(self, response):
        # Save the full response
        self.save_response(response)
        # Extract article metadata and structured text
        article = extract_article(response, self.config, crawl_info=self.crawl_info,
                                  content_digests=self.settings["CONTENT_DIGESTS"],
                                  node_indexes=self.settings["NODE_INDEXES"])
        return article

    def save_response(self, response):
        if self.close_down:
            raise CloseSpider(reason="Database size exceeded.")


        raw_article = dict()
        raw_article['site_name'] = self.config['site_name']
        raw_article['crawl_datetime'] = self.crawl_info['crawl_datetime']
        raw_article['request_url'] = response.request.url
        raw_article['response_url'] = response.url
        raw_article['status'] = response.status
        raw_article['body'] = response.text
        self.logger.info('Saving response for: {}'.format(response.url))
        self.exporter.export_item(raw_article)
        return

    def closed(self, reason):
        self.exporter.finish_exporting()
        self.exporter.file.close()
        self.logger.info('Spider closed: {} ({})'.format(self.config['site_name'], reason))


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
        # Extract article metadata and structured text
        article = Article()
        article['site_name'] = self.name
        article['article_url'] = response.url
        title = response.xpath('//div[@id="content"]/h1[@class="title"]/text()').extract_first()
        if title:
            article['title'] = title.strip()
        author_date_xpath = '//div[contains(concat(" ",normalize-space(@class)," ")," field-item ")]/text()'
        author_date = response.xpath(author_date_xpath).extract_first()
        if author_date:
            author, publication_date = author_date.strip().split("|")
            if author:
                article["authors"] = [author.strip()]
            if publication_date:
                pub_month, pub_day, pub_year = [int(d) for d in publication_date.strip().split("/")]
                publication_date = "{:02d}-{:02d}-{:02d}".format(pub_year, pub_month, pub_day)
                if pub_year < 100:
                    article["publication_date"] = datetime.strptime(publication_date, "%y-%m-%d")
                else:
                    article["publication_date"] = datetime.strptime(publication_date, "%Y-%m-%d")
        article['content'] = response.css('.content').xpath('.//p').extract()
        return article


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
        # Extract article metadata and structured text
        article = Article()
        article['site_name'] = self.name
        article['article_url'] = response.url
        title = response.css('.post').xpath('./h2[@class="entry-title"]/a/text()').extract_first()
        if title:
            article['title'] = title.strip()
        author = response.css('.author').xpath('./span[@class="fn"]/a/text()').extract_first()
        if author:
            article["authors"] = [author.strip()]
        publication_date = response.xpath('//span[@class="date published time"]/@title').extract_first()
        if publication_date:
            article["publication_date"] = iso8601.parse_date(publication_date)
        article['content'] = response.css('.entry-content').xpath('.//p').extract()
        return article


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
        # Extract article metadata and structured text
        article = Article()
        article['site_name'] = self.name
        article['article_url'] = response.url
        title = response.css('.fl-post-header').xpath('./h1[@class="fl-post-title"]/text()').extract_first()
        if title:
            article['title'] = title.strip()
        author = response.xpath('//span[@class="fl-post-author"]/a/text()').extract_first()
        if author:
            article["authors"] = [author.strip()]
        publication_date = response.xpath('//meta[@itemprop="datePublished"]/@content').extract_first()
        if publication_date:
            article["publication_date"] = iso8601.parse_date(publication_date)
        article['content'] = response.css('.fl-post-content').xpath('.//p').extract()
        return article


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
        # Extract article metadata and structured text
        article = Article()
        article['site_name'] = self.name
        article['article_url'] = response.url
        title = response.css('.post-title').xpath('./span[@itemprop="name"]/text()').extract_first()
        if title:
            article['title'] = title.strip()
        author = response.xpath('//span[@class="post-meta-author"]/a/text()').extract_first()
        if author:
            article["authors"] = [author.strip()]
        publication_date = response.xpath('//span[@class="tie-date"]/text()').extract_first()
        if publication_date:
            article["publication_date"] = datetime.strptime(publication_date, '%B %d, %Y')
        article['content'] = response.css('.entry').xpath('.//p').extract()
        return article

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
        # Extract article metadata and structured text
        article = Article()
        article['site_name'] = self.name
        article['article_url'] = response.url
        title = response.css('.td-post-title').xpath('./h1l[@class="entry-title"]/text()').extract_first()
        if title:
            article['title'] = title.strip()
        author = response.css('.td-post-author-name').xpath('./a/text()').extract_first()
        if author:
            article["authors"] = [author.strip()]
        publication_date = response.css('.entry-date').xpath('./@datetime').extract_first()
        if publication_date:
            article["publication_date"] = iso8601.parse_date(publication_date)
        article['content'] = response.css('.td-post-content').xpath('.//p').extract()
        return article


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


class VeteransNewsReport(CrawlSpider):
    name = 'veteransnewsreport.com'
    allowed_domains = ['veteransnewsreport.com']
    start_urls = ['http://veteransnewsreport.com/category/government-and-politics/']
    rules = (
        # Extract links to other pages and follow links from them (no callback means follow=True by default)
        Rule(LinkExtractor(allow=('category/government-and-politics/page/',), )),
        # Extract links to articles
        Rule(LinkExtractor(restrict_xpaths=('//h3[contains(concat(" ",normalize-space(@class)," ")," entry-title ")]/a',)), callback='parse_item'),
    )

    def parse_item(self, response):
        with open('article_urls/{}.txt'.format(self.name), 'a') as f:
            # write out the title and add a newline.
            f.write(response.url + "\n")
            print(response.url)


class IfYouOnlyNews(CrawlSpider):
    name = 'ifyouonlynews.com'
    allowed_domains = ['ifyouonlynews.com']
    start_urls = ['http://ifyouonlynews.com/category/politics/']
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


class ScrappleFace(CrawlSpider):
    name = 'scrappleface.com'
    allowed_domains = ['scrappleface.com']
    start_urls = ['http://scrappleface.com/blog/category/politics/']
    rules = (
        # Extract links to other pages and follow links from them (no callback means follow=True by default)
        Rule(LinkExtractor(allow=('blog/category/politics/page/',), )),
        # Extract links to articles
        Rule(LinkExtractor(restrict_xpaths=('//h2[contains(concat(" ",normalize-space(@class)," ")," title ")]/a',)), callback='parse_item'),
    )

    def parse_item(self, response):
        with open('article_urls/{}.txt'.format(self.name), 'a') as f:
            # write out the title and add a newline.
            f.write(response.url + "\n")
            print(response.url)


class SatireWire(CrawlSpider):
    name = 'satirewire.com'
    allowed_domains = ['satirewire.com']
    start_urls = ['http://satirewire.com/content1/?cat=13']
    rules = (
        # Extract links to other pages and follow links from them (no callback means follow=True by default)
        Rule(LinkExtractor(allow=('content1/\?cat=13&paged=\d*',), )),
        # Extract links to articles
        Rule(LinkExtractor(restrict_xpaths=('//div[contains(concat(" ",normalize-space(@class)," ")," excerpt ")]/h2/a',)), callback='parse_item'),
    )

    def parse_item(self, response):
        with open('article_urls/{}.txt'.format(self.name), 'a') as f:
            # write out the title and add a newline.
            f.write(response.url + "\n")
            print(response.url)


class IslamicaNews(CrawlSpider):
    name = 'islamicanews.com'
    allowed_domains = ['islamicanews.com']
    start_urls = ['http://islamicanews.com/category/politics/']
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


class ThinkProgress(CrawlSpider):
    name = 'thinkprogress.org'
    allowed_domains = ['thinkprogress.org']
    start_urls = ['http://thinkprogress.org']
    rules = (
        # Extract links to articles
        Rule(LinkExtractor(restrict_xpaths=('//h2[contains(concat(" ",normalize-space(@class)," ")," post__title ")]/a',)), callback='parse_item'),
    )

    def parse_item(self, response):
        with open('article_urls/{}.txt'.format(self.name), 'a') as f:
            # write out the title and add a newline.
            f.write(response.url + "\n")
            print(response.url)


class JuficialWatch(CrawlSpider):
    name = 'judicialwatch.org'
    allowed_domains = ['judicialwatch.org']
    start_urls = ['http://judicialwatch.org/blog/']
    rules = (
        # Extract links to other pages and follow links from them (no callback means follow=True by default)
        Rule(LinkExtractor(allow=('blog/page/',), )),
        # Extract links to articles
        Rule(LinkExtractor(restrict_xpaths=('//div[contains(concat(" ",normalize-space(@class)," ")," post ")]/h2/a',)), callback='parse_item'),
    )

    def parse_item(self, response):
        with open('article_urls/{}.txt'.format(self.name), 'a') as f:
            # write out the title and add a newline.
            f.write(response.url + "\n")
            print(response.url)


class DailyKos(CrawlSpider):
    name = 'dailykos.com'
    allowed_domains = ['dailykos.com']
    start_urls = ['http://dailykos.com']
    custom_settings = {
        'ROBOTSTXT_OBEY': False
    }
    rules = (
        # Extract links to other pages and follow links from them (no callback means follow=True by default)
        Rule(LinkExtractor(allow=('/\?page=\d*',), )),
        # Extract links to articles
        Rule(LinkExtractor(restrict_xpaths=('//div[contains(concat(" ",normalize-space(@class)," ")," story-title ")]/a',)), callback='parse_item'),
    )

    def parse_item(self, response):
        with open('article_urls/{}.txt'.format(self.name), 'a') as f:
            # write out the title and add a newline.
            f.write(response.url + "\n")
            print(response.url)


class Breitbart(CrawlSpider):
    name = 'breitbart.com'
    allowed_domains = ['breitbart.com']
    start_urls = ['http://breitbart.com']
    rules = (
        # Extract links to articles
        Rule(LinkExtractor(
            restrict_xpaths=('//footer[contains(concat(" ",normalize-space(@class)," ")," byline ")]/h2/a',)),
             callback='parse_item'),
    )

    def parse_item(self, response):
        with open('article_urls/{}.txt'.format(self.name), 'a') as f:
            # write out the title and add a newline.
            f.write(response.url + "\n")


# TODO: Only parses articles on start page as does not follow "/article" link
class Alternet(CrawlSpider):
    name = 'alternet.org'
    allowed_domains = ['alternet.org']
    start_urls = ['http://alternet.org']
    rules = (
        # Extract links to other pages and follow links from them (no callback means follow=True by default)
        Rule(LinkExtractor(allow=('archive',), )),
        # Extract links to articles
        Rule(LinkExtractor(restrict_xpaths=('//div[contains(concat(" ",normalize-space(@class)," ")," title_overlay ")]/h2/a', '//div[contains(concat(" ",normalize-space(@class)," ")," node-story ")]/div/h2/a',)), callback='parse_item'),
    )

    def parse_item(self, response):
        with open('article_urls/{}.txt'.format(self.name), 'a') as f:
            # write out the title and add a newline.
            f.write(response.url + "\n")
            print(response.url)
