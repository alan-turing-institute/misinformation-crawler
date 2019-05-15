from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime

Base = declarative_base()

class Webpage(Base):
    __tablename__ = 'webpages'
    id = Column(Integer, primary_key=True)
    crawl_id = Column(String)
    crawl_datetime = Column(DateTime)
    site_name = Column(String)
    article_url = Column(String)
    file_path = Column(String)

    def __repr__(self):
        return "<Webpage(crawl_id='{}', crawl_datetime='{}', site_name={}, article_url={}, file_path={})>".format(
            self.crawl_id,
            self.crawl_datetime,
            self.site_name,
            self.article_url,
            self.file_path
            )

    def __str__(self):
        return self.__repr__()
