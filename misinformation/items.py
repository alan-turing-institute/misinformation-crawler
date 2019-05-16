import scrapy


class CrawlResponse(scrapy.Item):
    url = scrapy.Field()
    status = scrapy.Field()
    headers = scrapy.Field()
    text = scrapy.Field()
    request = scrapy.Field()
    flags = scrapy.Field()
    crawl_id = scrapy.Field()
    crawl_datetime = scrapy.Field()
    site_name = scrapy.Field()


class Article(scrapy.Item):
    crawl_id = scrapy.Field()
    crawl_datetime = scrapy.Field()
    site_name = scrapy.Field()
    article_url = scrapy.Field()
    title = scrapy.Field()
    byline = scrapy.Field()
    publication_datetime = scrapy.Field()
    metadata = scrapy.Field()
    content = scrapy.Field()
    plain_content = scrapy.Field()
    plain_text = scrapy.Field()
    request_meta = scrapy.Field()
    page_html = scrapy.Field()
