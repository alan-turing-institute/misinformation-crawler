from dataclasses import dataclass
import datetime


@dataclass
class CrawlFile:
    article_url: str
    crawl_id: str
    crawl_datetime: datetime.datetime
    site_name: str
    warc_data: bytes
