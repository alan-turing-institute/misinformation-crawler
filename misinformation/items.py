import scrapy


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
