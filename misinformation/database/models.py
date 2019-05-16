from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime

Base = declarative_base()

class Webpage(Base):
    __tablename__ = 'webpages'
    id = Column(Integer, primary_key=True)
    site_name = Column(String)
    article_url = Column(String)
    blob_key = Column(String)

    def __str__(self):
        return "<Webpage(site_name={}, article_url={}, blob_key={})>".format(
                self.site_name,
                self.article_url,
                self.blob_key,
            )

    __repr__ = __str__
