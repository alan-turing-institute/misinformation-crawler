import scrapy


class Article(scrapy.Item):
    crawl_id = scrapy.Field()
    crawl_datetime = scrapy.Field()
    site_name = scrapy.Field()
    article_url = scrapy.Field()
    title = scrapy.Field()
    byline = scrapy.Field()
    published_date = scrapy.Field()
    content = scrapy.Field()
    plain_content = scrapy.Field()
    metadata = scrapy.Field()


