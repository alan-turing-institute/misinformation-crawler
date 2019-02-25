# This module contains any project-specific Scrapy spiders
#
# See documentation at:
# https://doc.scrapy.org/en/latest/topics/spiders.html
from .misinformationindexpagespider import MisinformationIndexPageSpider
from .misinformationscattergunspider import MisinformationScattergunSpider

__all__ = ['MisinformationIndexPageSpider', 'MisinformationScattergunSpider']
