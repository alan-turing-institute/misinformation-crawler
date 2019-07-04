"""
This module contains any project-specific Scrapy spiders

See documentation at:
https://doc.scrapy.org/en/latest/topics/spiders.html
"""
from .indexpagespider import IndexPageSpider
from .scattergunspider import ScattergunSpider
from .xmlsitemapspider import XMLSitemapSpider

__all__ = [
    "IndexPageSpider",
    "ScattergunSpider",
    "XMLSitemapSpider",
]
