import scrapy


class Article(scrapy.Item):
    crawl_id = scrapy.Field()
    crawl_date = scrapy.Field()
    site_name = scrapy.Field()
    article_url = scrapy.Field()
    title = scrapy.Field()
    authors = scrapy.Field()
    publication_date = scrapy.Field()
    plain_content = scrapy.Field()
    structured_content = scrapy.Field()
    metadata = scrapy.Field()


