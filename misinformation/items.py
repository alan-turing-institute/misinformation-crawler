import scrapy
from .warc import string_from_warc


class CrawlResponse(scrapy.Item):
    url = scrapy.Field()
    crawl_id = scrapy.Field()
    crawl_datetime = scrapy.Field()
    site_name = scrapy.Field()
    warc_data = scrapy.Field(serializer=string_from_warc)
