from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

BaseTableModel = declarative_base()

class Webpage(BaseTableModel):
    __tablename__ = 'webpages'
    id = Column(Integer, primary_key=True)
    site_name = Column(String)
    article_url = Column(String)
    crawl_id = Column(String)
    crawl_datetime = Column(DateTime)
    blob_key = Column(String)

    def __str__(self):
        return "<Webpage(site_name={}, article_url={}, crawl_id={}, crawl_datetime={}, blob_key={})>".format(
            self.site_name,
            self.article_url,
            self.crawl_id,
            self.crawl_datetime,
            self.blob_key,
            )

    __repr__ = __str__


class Article(BaseTableModel):
    __tablename__ = 'articles_dev'
    id = Column(Integer, primary_key=True)
    crawl_id = Column(String)
    crawl_datetime = Column(DateTime)
    site_name = Column(String)
    article_url = Column(String)
    title = Column(String)
    byline = Column(String)
    publication_datetime = Column(String)
    content = Column(String)
    plain_content = Column(String)
    plain_text = Column(String)
    _metadata = Column("metadata", String)

    def __str__(self):
        return "<Webpage(site_name={}, article_url={}, crawl_id={}, crawl_datetime={}, title={}, byline={}, publication_datetime={}, content={}, plain_content={}, plain_text={}, metadata={})>".format(
            self.site_name,
            self.article_url,
            self.crawl_id,
            self.crawl_datetime,
            self.title,
            self.byline,
            self.publication_datetime,
            self.content,
            self.plain_content,
            self.plain_text,
            self._metadata,
            )

    __repr__ = __str__
