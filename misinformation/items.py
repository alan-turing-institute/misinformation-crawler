# -*- coding: utf-8 -*-

import scrapy


class Article(scrapy.Item):
    crawl_id = scrapy.Field()
    crawl_date = scrapy.Field()
    site_name = scrapy.Field()
    site_url = scrapy.Field()
    article_url = scrapy.Field()
    title = scrapy.Field()
    authors = scrapy.Field()
    publication_date = scrapy.Field()
    content = scrapy.Field()


