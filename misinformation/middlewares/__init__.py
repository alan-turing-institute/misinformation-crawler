# This package contains any project-specific Scrapy middleware
#
# See documentation at:
# https://doc.scrapy.org/en/latest/topics/spider-middleware.html
from .cloudflaremiddleware import CloudFlareMiddleware

__all__ = ['CloudFlareMiddleware']
